import re
import shutil
from pathlib import Path
from typing import Optional
from ..utils.logger import setup_logger

logger = setup_logger()

class FileProcessor:
    def __init__(self, config):
        self.config = config
        self._ensure_directories()

    def _ensure_directories(self):
        """Create necessary directories if they don't exist."""
        self.config.BUCKET_DIR.mkdir(parents=True, exist_ok=True)
        self.config.ORIGINALS_DIR.mkdir(parents=True, exist_ok=True)

    def process_bucket(self) -> list:
        """Process all files in the bucket directory."""
        processed_files = []
        
        # First, check what's already in Originals
        existing_files = {file.name: file for file in self.config.ORIGINALS_DIR.glob("*")}
        logger.info(f"Found {len(existing_files)} existing files in Originals")
        
        # Process bucket files
        for file_path in self.config.BUCKET_DIR.glob("*"):
            if file_path.suffix.lower() in self.config.BOOK_FORMATS:
                try:
                    # Clean filename
                    clean_name = self.sanitize_filename(file_path.name)
                    
                    # Check if already processed
                    if clean_name in existing_files:
                        logger.info(f"File already processed: {clean_name}")
                        processed_files.append(existing_files[clean_name])
                        continue
                    
                    # Process new file
                    clean_path = file_path.with_name(clean_name)
                    if file_path != clean_path:
                        file_path.rename(clean_path)
                        file_path = clean_path
                    
                    # Move to originals
                    dest_path = self.move_to_originals(file_path)
                    if dest_path:
                        processed_files.append(dest_path)
                        logger.info(f"Processed new file: {dest_path.name}")
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
            else:
                logger.warning(f"Unsupported file type: {file_path}")
        
        return processed_files

    def sanitize_filename(self, filename: str) -> str:
        """Clean filename of problematic characters."""
        # Remove or replace problematic characters
        clean_name = filename
        clean_name = re.sub(r'[\[\]\(\)]', '', clean_name)  # Remove brackets
        clean_name = re.sub(r'[:\\/|<>*?"]', '-', clean_name)  # Replace special chars
        clean_name = re.sub(r'\s+', ' ', clean_name)  # Normalize spaces
        clean_name = clean_name.strip()
        return clean_name

    def move_to_originals(self, file_path: Path) -> Optional[Path]:
        """Move file to originals directory."""
        try:
            dest_path = self.config.ORIGINALS_DIR / file_path.name
            if dest_path.exists():
                logger.warning(f"File already exists in originals: {dest_path.name}")
                return dest_path
            
            shutil.move(str(file_path), str(dest_path))
            return dest_path
        except Exception as e:
            logger.error(f"Error moving file {file_path}: {e}")
            return None