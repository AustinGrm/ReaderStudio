import re
import shutil
import os
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from ..utils.logger import setup_logger

logger = setup_logger()

class FileProcessor:
    """
    Handles the processing of files from the BUCKET_DIR.
    
    This class is responsible for:
    1. Checking the BUCKET_DIR for new files
    2. Moving PDF/EPUB/MOBI files directly to ORIGINALS_DIR
    3. (Future) Converting non-PDF/EPUB/MOBI files to a supported format
    
    The process_bucket method should be called before main book processing to ensure
    all files in the bucket are properly moved to the originals directory.
    """
    def __init__(self, config):
        self.config = config
        self._ensure_directories()

    def _ensure_directories(self):
        """Create necessary directories if they don't exist."""
        try:
            self.config.BUCKET_DIR.mkdir(parents=True, exist_ok=True)
            self.config.ORIGINALS_DIR.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            logger.error("Permission denied when creating directories")
        except Exception as e:
            logger.error(f"Error creating directories: {str(e)}")

    def process_bucket(self) -> List[Path]:
        """
        Process all files in the bucket directory.
        
        This method:
        1. Checks for supported file types (.pdf, .epub, .mobi)
        2. Sanitizes filenames
        3. Moves files to the ORIGINALS_DIR
        
        Returns:
            list: Paths to all processed files in ORIGINALS_DIR
        """
        processed_files = []
        skipped_files = []
        error_files = []
        
        # First, check what's already in Originals
        existing_files = {}
        try:
            existing_files = {file.name: file for file in self.config.ORIGINALS_DIR.glob("*")}
            logger.info(f"Found {len(existing_files)} existing files in Originals")
        except Exception as e:
            logger.error(f"Error scanning ORIGINALS_DIR: {str(e)}")
            # Continue with empty existing_files rather than failing
        
        # Process bucket files
        bucket_files = []
        try:
            bucket_files = list(self.config.BUCKET_DIR.glob("*"))
            logger.info(f"Found {len(bucket_files)} files in Bucket directory")
        except Exception as e:
            logger.error(f"Error scanning BUCKET_DIR: {str(e)}")
            # Return early but don't crash the program
            return []
        
        # Process each file individually - failures won't stop the whole process
        for file_path in bucket_files:
            result = self._process_single_file(file_path, existing_files)
            if result:
                status, file_info = result
                if status == "processed":
                    processed_files.append(file_info)
                elif status == "skipped":
                    skipped_files.append(file_info)
                elif status == "error":
                    error_files.append(file_info)
        
        # Summary logging
        if processed_files:
            logger.info(f"Successfully processed {len(processed_files)} files")
        if skipped_files:
            logger.info(f"Skipped {len(skipped_files)} files (already processed or unsupported)")
        if error_files:
            logger.warning(f"Failed to process {len(error_files)} files due to errors")
            
        return processed_files

    def _process_single_file(self, file_path: Path, existing_files: Dict[str, Path]) -> Optional[Tuple[str, Path]]:
        """
        Process a single file from the bucket directory.
        
        Returns:
            Tuple containing status ("processed", "skipped", "error") and the file path
        """
        try:
            # Skip directories
            if file_path.is_dir():
                logger.info(f"Skipping directory: {file_path.name}")
                return "skipped", file_path
                
            logger.info(f"Checking file: {file_path.name}")
            
            # Check if file exists and is readable
            if not file_path.exists() or not os.access(file_path, os.R_OK):
                logger.warning(f"File not accessible: {file_path.name}")
                return "error", file_path
            
            # Check if file is of supported type
            if file_path.suffix.lower() not in self.config.BOOK_FORMATS:
                logger.warning(f"Unsupported file type: {file_path.name} (supported: {self.config.BOOK_FORMATS})")
                return "skipped", file_path
            
            # Clean filename
            try:
                clean_name = self.sanitize_filename(file_path.name)
            except Exception as e:
                logger.error(f"Error sanitizing filename {file_path.name}: {str(e)}")
                clean_name = file_path.name  # Fall back to original name
            
            # Check if already processed
            if clean_name in existing_files:
                logger.info(f"File already processed: {clean_name}")
                return "skipped", existing_files[clean_name]
            
            # Rename file if necessary
            clean_path = file_path
            if file_path.name != clean_name:
                try:
                    clean_path = file_path.with_name(clean_name)
                    file_path.rename(clean_path)
                    file_path = clean_path
                except (PermissionError, OSError) as e:
                    logger.error(f"Error renaming file {file_path} to {clean_name}: {str(e)}")
                    # Continue with original name if rename fails
            
            # Move to originals
            dest_path = self.move_to_originals(file_path)
            if dest_path:
                logger.info(f"Processed new file: {dest_path.name}")
                return "processed", dest_path
            else:
                return "error", file_path
                
        except Exception as e:
            logger.error(f"Unexpected error processing {file_path}: {str(e)}")
            return "error", file_path

    def sanitize_filename(self, filename: str) -> str:
        """Clean filename of problematic characters."""
        if not filename:
            return "untitled"
            
        # Remove or replace problematic characters
        clean_name = filename
        clean_name = re.sub(r'[\[\]\(\)]', '', clean_name)  # Remove brackets
        clean_name = re.sub(r'[:\\/|<>*?"]', '-', clean_name)  # Replace special chars
        clean_name = re.sub(r'\s+', ' ', clean_name)  # Normalize spaces
        clean_name = clean_name.strip()
        
        # Ensure we have a valid filename
        if not clean_name:
            return "untitled"
            
        return clean_name

    def move_to_originals(self, file_path: Path) -> Optional[Path]:
        """Move file to originals directory."""
        if not file_path or not file_path.exists():
            logger.error(f"Cannot move nonexistent file: {file_path}")
            return None
            
        try:
            dest_path = self.config.ORIGINALS_DIR / file_path.name
            
            # Check if destination exists
            if dest_path.exists():
                logger.warning(f"File already exists in originals: {dest_path.name}")
                return dest_path
            
            # Check for destination directory existence/accessibility
            if not self.config.ORIGINALS_DIR.exists():
                logger.error(f"Destination directory doesn't exist: {self.config.ORIGINALS_DIR}")
                try:
                    self.config.ORIGINALS_DIR.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created missing directory: {self.config.ORIGINALS_DIR}")
                except Exception as e:
                    logger.error(f"Failed to create directory: {str(e)}")
                    return None
            
            # Try to move the file
            logger.info(f"Moving {file_path.name} to {dest_path}")
            
            try:
                # First try shutil.move which handles cross-device moving
                shutil.move(str(file_path), str(dest_path))
            except (shutil.Error, OSError) as e:
                logger.warning(f"Error using shutil.move: {str(e)}, trying copy and delete")
                # Fallback: copy and delete
                try:
                    shutil.copy2(str(file_path), str(dest_path))
                    if dest_path.exists() and dest_path.stat().st_size == file_path.stat().st_size:
                        file_path.unlink()  # Only delete if copy was successful
                    else:
                        logger.error("Copy succeeded but file sizes don't match, not deleting original")
                except Exception as copy_e:
                    logger.error(f"Error copying file: {str(copy_e)}")
                    return None
            
            # Verify file was successfully moved
            if dest_path.exists():
                return dest_path
            else:
                logger.error(f"File move appeared to succeed but destination file not found: {dest_path}")
                return None
                
        except Exception as e:
            logger.error(f"Unexpected error moving file {file_path}: {str(e)}")
            return None