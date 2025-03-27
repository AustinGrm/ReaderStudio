import re
import shutil
import os
import subprocess
import tempfile
import hashlib
import calendar
from pathlib import Path
from typing import List, Optional, Dict, Tuple, Set
from ..utils.logger import setup_logger
from ..metadata.calibre import CalibreMetadata

logger = setup_logger()

class FileProcessor:
    """
    Handles the processing of files from the BUCKET_DIR.
    
    This class is responsible for:
    1. Checking the BUCKET_DIR for new files
    2. Moving PDF/EPUB/MOBI files directly to ORIGINALS_DIR
    3. Converting non-PDF/EPUB/MOBI files to a supported format
    4. Avoiding duplicate files based on content hashing
    
    The process_bucket method should be called before main book processing to ensure
    all files in the bucket are properly moved to the originals directory.
    """
    def __init__(self, config):
        self.config = config
        self._ensure_directories()
        self.supported_formats = ['.pdf', '.epub']
        self.convertible_formats = ['.docx', '.doc', '.rtf', '.odt', '.azw', '.azw3', '.xhtml', '.html', '.mobi']
        # File hashes cache to avoid recalculating
        self.file_hashes = {}
        # Initialize calibre metadata extractor
        self.calibre = CalibreMetadata(config)

    def _ensure_directories(self):
        """Create necessary directories if they don't exist."""
        try:
            self.config.BUCKET_DIR.mkdir(parents=True, exist_ok=True)
            self.config.ORIGINALS_DIR.mkdir(parents=True, exist_ok=True)
            temp_dir = self.config.VAULT_DIR / "temp"
            temp_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            logger.error("Permission denied when creating directories")
        except Exception as e:
            logger.error(f"Error creating directories: {str(e)}")

    def process_bucket(self) -> List[Path]:
        """
        Process all files in the bucket directory.
        
        This method:
        1. Checks for supported file types (.pdf, .epub, .mobi)
        2. Converts unsupported file types to .epub or .pdf
        3. Sanitizes filenames
        4. Moves files to the ORIGINALS_DIR
        5. Avoids duplicate files using content-based hashing
        
        Returns:
            list: Paths to all processed files in ORIGINALS_DIR
        """
        processed_files = []
        skipped_files = []
        error_files = []
        converted_files = []
        
        # First, get existing file hashes in Originals to avoid duplicates
        try:
            existing_files = {file.name: file for file in self.config.ORIGINALS_DIR.glob("*") 
                            if file.is_file() and file.suffix.lower() in self.supported_formats}
            
            existing_hashes = self._get_existing_file_hashes(existing_files.values())
            logger.info(f"Found {len(existing_files)} existing files in Originals")
        except Exception as e:
            logger.error(f"Error scanning ORIGINALS_DIR: {str(e)}")
            existing_files = {}
            existing_hashes = set()
        
        # Process bucket files
        bucket_files = []
        try:
            bucket_files = list(self.config.BUCKET_DIR.glob("*"))
            logger.info(f"Found {len(bucket_files)} files in Bucket directory")
        except Exception as e:
            logger.error(f"Error scanning BUCKET_DIR: {str(e)}")
            return []
        
        # Process each file individually - failures won't stop the whole process
        for file_path in bucket_files:
            result = self._process_single_file(file_path, existing_files, existing_hashes)
            if result:
                status, file_info = result
                if status == "processed":
                    processed_files.append(file_info)
                elif status == "converted":
                    converted_files.append(file_info)
                    processed_files.append(file_info)
                elif status == "skipped":
                    skipped_files.append(file_info)
                elif status == "error":
                    error_files.append(file_info)
        
        # Summary logging
        if processed_files:
            logger.info(f"Successfully processed {len(processed_files)} files")
        if converted_files:
            logger.info(f"Successfully converted {len(converted_files)} files")
        if skipped_files:
            logger.info(f"Skipped {len(skipped_files)} files (already processed or unsupported)")
        if error_files:
            logger.warning(f"Failed to process {len(error_files)} files due to errors")
            
        return processed_files

    def _get_existing_file_hashes(self, files) -> Set[str]:
        """
        Generate content hashes for existing files to detect duplicates.
        Uses a simple sampling approach for large files to improve performance.
        """
        hashes = set()
        for file_path in files:
            try:
                file_hash = self._calculate_file_hash(file_path)
                if file_hash:
                    hashes.add(file_hash)
            except Exception as e:
                logger.error(f"Error calculating hash for {file_path}: {str(e)}")
        return hashes

    def _calculate_file_hash(self, file_path: Path, sample_size: int = 1024 * 1024) -> Optional[str]:
        """
        Calculate a hash of the file for duplicate detection.
        For large files, only sample parts of the file for performance.
        """
        if file_path in self.file_hashes:
            return self.file_hashes[file_path]
            
        try:
            if not file_path.exists() or not file_path.is_file():
                return None
                
            # Use file size and sampling to create hash
            file_size = file_path.stat().st_size
            md5 = hashlib.md5()
            
            with open(file_path, 'rb') as f:
                # Always read beginning of file
                beginning = f.read(min(sample_size, file_size))
                md5.update(beginning)
                
                # For larger files, also sample middle and end
                if file_size > sample_size * 2:
                    # Move to the middle
                    f.seek(file_size // 2)
                    middle = f.read(min(sample_size, file_size - file_size // 2))
                    md5.update(middle)
                    
                    # Move near the end
                    f.seek(max(0, file_size - sample_size))
                    end = f.read(sample_size)
                    md5.update(end)
            
            file_hash = md5.hexdigest()
            self.file_hashes[file_path] = file_hash
            return file_hash
            
        except Exception as e:
            logger.error(f"Error calculating hash for {file_path}: {str(e)}")
            return None

    def _process_single_file(self, file_path: Path, existing_files: Dict[str, Path], 
                            existing_hashes: Set[str]) -> Optional[Tuple[str, Path]]:
        """
        Process a single file from the bucket directory.
        
        Returns:
            Tuple containing status ("processed", "converted", "skipped", "error") and the file path
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
            
            # Calculate file hash for duplicate detection
            file_hash = self._calculate_file_hash(file_path)
            
            # Check for duplicates by content hash
            if file_hash in existing_hashes:
                logger.info(f"File is a duplicate based on content hash: {file_path.name}")
                return "skipped", file_path
            
            # Clean filename
            try:
                clean_name = self.sanitize_filename(file_path.name)
            except Exception as e:
                logger.error(f"Error sanitizing filename {file_path.name}: {str(e)}")
                clean_name = file_path.name  # Fall back to original name
            
            # Check if file with same name already exists in originals
            if clean_name in existing_files:
                existing_path = existing_files[clean_name]
                
                # Check if the extension is the same (same format)
                if file_path.suffix.lower() == existing_path.suffix.lower():
                    # Same name, same format - might be a different version (edition)
                    # Extract metadata to check publication date/year if available
                    try:
                        new_metadata = self.calibre.extract_metadata(file_path)
                        existing_metadata = self.calibre.extract_metadata(existing_path)
                        
                        new_year = self._extract_publication_year(new_metadata)
                        existing_year = self._extract_publication_year(existing_metadata)
                        
                        if new_year and existing_year:
                            logger.info(f"Publication years - New: {new_year}, Existing: {existing_year}")
                            
                            if new_year > existing_year:
                                # New file is newer, keep it with a different name
                                logger.info(f"New file is a newer edition ({new_year} vs {existing_year})")
                                clean_name = f"{file_path.stem} ({new_year}){file_path.suffix}"
                            elif new_year < existing_year:
                                # Existing file is newer, skip this one
                                logger.info(f"Existing file is a newer edition ({existing_year} vs {new_year})")
                                return "skipped", existing_path
                            else:
                                # Same year, treat as duplicate with different content
                                logger.info(f"Same publication year ({new_year}), treating as variant")
                                # Will continue to the renaming code below
                        else:
                            logger.info("Publication years not available for comparison")
                            # Continue to normal processing
                    except Exception as e:
                        logger.warning(f"Error comparing publication dates: {str(e)}")
                        # Continue to normal processing if metadata extraction fails
                    
                    # Check if a landing page already exists for this book (use base name without year)
                    base_name = re.sub(r'\s+\(\d{4}\)$', '', file_path.stem)
                    landing_path = self.config.LANDING_DIR / f"{base_name}.md"
                    if landing_path.exists():
                        logger.info(f"Found existing landing page: {landing_path.name}")
                        # We'll still process this file but log that a landing page exists
                
                elif file_path.suffix.lower() in self.supported_formats and existing_path.suffix.lower() not in self.supported_formats:
                    # New file is in a better format, use it
                    logger.info(f"New file is in a preferred format ({file_path.suffix}) compared to existing ({existing_path.suffix})")
                    # Continue processing this file
                elif file_path.suffix.lower() not in self.supported_formats and existing_path.suffix.lower() in self.supported_formats:
                    # Existing file is in a better format, skip this one
                    logger.info(f"Existing file is in a preferred format ({existing_path.suffix}) compared to new ({file_path.suffix})")
                    return "skipped", existing_path
                else:
                    # Different formats, but neither is preferred - keep both
                    logger.info(f"Different formats: {file_path.suffix} vs {existing_path.suffix}")
                    # Continue processing this file
            
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
            
            # Process based on file type
            if file_path.suffix.lower() in self.supported_formats:
                # Move directly to originals
                dest_path = self.move_to_originals(file_path)
                if dest_path:
                    logger.info(f"Processed new file: {dest_path.name}")
                    return "processed", dest_path
                else:
                    return "error", file_path
            
            # Try to convert non-supported files
            elif file_path.suffix.lower() in self.convertible_formats:
                logger.info(f"Attempting to convert {file_path.name}")
                converted_path = self._convert_file(file_path)
                
                if converted_path:
                    # Before moving, check if this converted file would be a duplicate
                    converted_hash = self._calculate_file_hash(converted_path)
                    if converted_hash in existing_hashes:
                        logger.info(f"Converted file is a duplicate: {converted_path.name}")
                        try:
                            converted_path.unlink()  # Delete the converted file
                        except Exception:
                            pass
                        return "skipped", file_path
                    
                    # Move the converted file to originals
                    dest_path = self.move_to_originals(converted_path)
                    if dest_path:
                        logger.info(f"Converted and processed: {file_path.name} -> {dest_path.name}")
                        
                        # If the original file was inside a subdirectory (like unpacked MOBI), 
                        # try to remove the subdirectory
                        if file_path.parent != self.config.BUCKET_DIR and file_path.parent.is_dir():
                            try:
                                # First try to remove the file
                                file_path.unlink()
                                
                                # See if the directory is now empty and can be removed
                                if not any(file_path.parent.iterdir()):
                                    file_path.parent.rmdir()
                                    logger.info(f"Removed empty directory: {file_path.parent}")
                            except Exception as e:
                                logger.warning(f"Could not clean up original file or directory: {str(e)}")
                                
                        return "converted", dest_path
                    else:
                        # Clean up if move fails
                        try:
                            converted_path.unlink()
                        except Exception:
                            pass
                        return "error", file_path
                else:
                    logger.warning(f"Failed to convert: {file_path.name}")
                    return "error", file_path
            else:
                logger.warning(f"Unsupported file type: {file_path.name} (supported: {self.supported_formats}, convertible: {self.convertible_formats})")
                return "skipped", file_path
                
        except Exception as e:
            logger.error(f"Unexpected error processing {file_path}: {str(e)}")
            return "error", file_path

    def _convert_file(self, file_path: Path) -> Optional[Path]:
        """
        Convert a file to a supported format using appropriate tools.
        
        Returns:
            Path to converted file or None if conversion failed
        """
        suffix = file_path.suffix.lower()
        temp_dir = self.config.VAULT_DIR / "temp"
        
        try:
            # Create a base name for the converted file
            base_name = file_path.stem
            
            # Determine output format (prefer EPUB for text-based formats, PDF for others)
            if suffix in ['.txt', '.html', '.xhtml', '.docx', '.doc', '.rtf', '.odt', '.azw', '.azw3', '.mobi']:
                output_format = '.epub'
            else:
                output_format = '.pdf'
                
            # Create output path
            output_path = temp_dir / f"{base_name}{output_format}"
            
            # Use appropriate conversion method based on file type
            if suffix in ['.txt', '.html', '.xhtml']:
                return self._convert_text_to_epub(file_path, output_path)
            elif suffix in ['.docx', '.doc', '.rtf', '.odt']:
                return self._convert_document_to_epub(file_path, output_path)
            elif suffix in ['.azw', '.azw3', '.mobi']:
                return self._convert_ebook_to_epub(file_path, output_path)
            else:
                logger.warning(f"No conversion method available for {suffix}")
                return None
                
        except Exception as e:
            logger.error(f"Error during file conversion: {str(e)}")
            return None

    def _convert_text_to_epub(self, input_path: Path, output_path: Path) -> Optional[Path]:
        """Convert text file to EPUB using Pandoc if available, otherwise a simple wrapper."""
        try:
            # Try Pandoc first
            if self._check_command_exists("pandoc"):
                cmd = [
                    "pandoc", 
                    str(input_path), 
                    "-o", str(output_path),
                    "--metadata", f"title={input_path.stem}"
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info(f"Successfully converted {input_path.name} to EPUB using Pandoc")
                    return output_path
                else:
                    logger.warning(f"Pandoc conversion failed: {result.stderr}")
            
            # Fallback to manual EPUB creation if Pandoc fails or isn't available
            try:
                # Try to use python-ebooklib if available
                import ebooklib
                from ebooklib import epub
                import html
                
                # Read content
                try:
                    with open(input_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    # Try with latin-1 if utf-8 fails
                    with open(input_path, 'r', encoding='latin-1') as f:
                        content = f.read()
                
                # Create a simple EPUB
                book = epub.EpubBook()
                
                # Set metadata
                book.set_identifier(f"id_{input_path.stem}")
                book.set_title(input_path.stem)
                book.set_language('en')
                
                # Create chapter
                c1 = epub.EpubHtml(title=input_path.stem, file_name='content.xhtml')
                # Convert plain text to HTML
                html_content = html.escape(content).replace('\n', '<br/>')
                c1.content = f'<html><body><h1>{input_path.stem}</h1><p>{html_content}</p></body></html>'
                
                # Add chapter to book
                book.add_item(c1)
                
                # Define Table of Contents
                book.toc = [epub.Link('content.xhtml', input_path.stem, 'intro')]
                
                # Add default NCX and Nav
                book.add_item(epub.EpubNcx())
                book.add_item(epub.EpubNav())
                
                # Define spine
                book.spine = ['nav', c1]
                
                # Write to file
                epub.write_epub(str(output_path), book)
                logger.info(f"Successfully created EPUB from {input_path.name} using python-ebooklib")
                return output_path
                
            except ImportError:
                logger.warning("python-ebooklib not available for EPUB creation")
                
                # Most basic fallback: just copy the file and rename with .epub extension
                shutil.copy2(input_path, output_path)
                logger.warning(f"Created basic EPUB by copying {input_path.name} (proper conversion not available)")
                return output_path
                
        except Exception as e:
            logger.error(f"Error converting text to EPUB: {str(e)}")
            return None

    def _convert_document_to_epub(self, input_path: Path, output_path: Path) -> Optional[Path]:
        """Convert document file (DOCX, DOC, etc.) to EPUB using LibreOffice/Pandoc if available."""
        try:
            # Try Pandoc first
            if self._check_command_exists("pandoc"):
                cmd = [
                    "pandoc", 
                    str(input_path), 
                    "-o", str(output_path),
                    "--metadata", f"title={input_path.stem}"
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info(f"Successfully converted {input_path.name} to EPUB using Pandoc")
                    return output_path
                else:
                    logger.warning(f"Pandoc conversion failed: {result.stderr}")
            
            # Try LibreOffice as fallback
            if self._check_command_exists("soffice"):
                # LibreOffice can convert to PDF directly
                pdf_path = output_path.with_suffix('.pdf')
                cmd = [
                    "soffice",
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", str(output_path.parent),
                    str(input_path)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0 and pdf_path.exists():
                    logger.info(f"Successfully converted {input_path.name} to PDF using LibreOffice")
                    return pdf_path
                else:
                    logger.warning(f"LibreOffice conversion failed: {result.stderr}")
            
            logger.warning(f"No available tools to convert {input_path.name}")
            return None
                
        except Exception as e:
            logger.error(f"Error converting document to EPUB/PDF: {str(e)}")
            return None

    def _convert_ebook_to_epub(self, input_path: Path, output_path: Path) -> Optional[Path]:
        """Convert Kindle format to EPUB using Calibre's ebook-convert if available."""
        try:
            # Try ebook-convert from Calibre
            if self._check_command_exists("ebook-convert"):
                cmd = [
                    "ebook-convert",
                    str(input_path),
                    str(output_path)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info(f"Successfully converted {input_path.name} to EPUB using Calibre")
                    return output_path
                else:
                    logger.warning(f"Calibre conversion failed: {result.stderr}")
            
            logger.warning(f"Calibre tools not available to convert {input_path.name}")
            return None
                
        except Exception as e:
            logger.error(f"Error converting e-book format: {str(e)}")
            return None

    def _check_command_exists(self, command: str) -> bool:
        """Check if a command is available in the system."""
        try:
            if os.name == 'nt':  # Windows
                result = subprocess.run(f"where {command}", shell=True, capture_output=True, text=True)
                return result.returncode == 0
            else:  # Unix/Linux/MacOS
                result = subprocess.run(f"which {command}", shell=True, capture_output=True, text=True)
                return result.returncode == 0
        except Exception:
            return False

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
            
            # Check if destination exists - handle duplicate filenames
            if dest_path.exists():
                # Check if they're the same file by content
                src_hash = self._calculate_file_hash(file_path)
                dest_hash = self._calculate_file_hash(dest_path)
                
                if src_hash == dest_hash:
                    logger.warning(f"Identical file already exists in originals: {dest_path.name}")
                    return dest_path
                else:
                    # Add a counter to the filename
                    base_name = dest_path.stem
                    extension = dest_path.suffix
                    counter = 1
                    
                    while True:
                        new_name = f"{base_name} ({counter}){extension}"
                        dest_path = self.config.ORIGINALS_DIR / new_name
                        if not dest_path.exists():
                            break
                        counter += 1
                    
                    logger.info(f"Renamed duplicate file to: {dest_path.name}")
            
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
                # Update the hash cache with the new file
                file_hash = self._calculate_file_hash(dest_path)
                if file_hash:
                    self.file_hashes[dest_path] = file_hash
                return dest_path
            else:
                logger.error(f"File move appeared to succeed but destination file not found: {dest_path}")
                return None
                
        except Exception as e:
            logger.error(f"Unexpected error moving file {file_path}: {str(e)}")
            return None

    def _extract_publication_year(self, metadata: Dict) -> Optional[int]:
        """Extract publication year from metadata if available."""
        if not metadata:
            return None
            
        # Try different metadata fields
        # First check explicit year field
        if 'year' in metadata and metadata['year']:
            try:
                year = int(metadata['year'])
                if 1900 <= year <= 2100:  # Sanity check
                    return year
            except (ValueError, TypeError):
                pass
        
        # Try to extract from date field
        if 'pubdate' in metadata and metadata['pubdate']:
            date_str = metadata['pubdate']
            try:
                # Check for ISO format date (YYYY-MM-DD)
                if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                    return int(date_str.split('-')[0])
                    
                # Check for other common formats
                for format_str in ['%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%m/%d/%Y', '%Y']:
                    try:
                        import datetime
                        dt = datetime.datetime.strptime(date_str, format_str)
                        return dt.year
                    except ValueError:
                        continue
            except Exception:
                pass
        
        # Try to extract from publisher info
        if 'publisher' in metadata and metadata['publisher']:
            publisher = metadata['publisher']
            # Look for years like "Publisher, 2020" or "Publisher (2020)"
            year_match = re.search(r'(\d{4})', publisher)
            if year_match:
                try:
                    year = int(year_match.group(1))
                    if 1900 <= year <= 2100:  # Sanity check
                        return year
                except (ValueError, TypeError):
                    pass
        
        return None