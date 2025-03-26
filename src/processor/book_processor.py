from pathlib import Path
from typing import List, Dict, Tuple
from ..metadata.calibre import CalibreMetadata
from .markdown import MarkdownProcessor
from .index import IndexProcessor
from ..utils.logger import setup_logger

logger = setup_logger()

class BookProcessor:
    def __init__(self, config, debug=False):
        self.config = config
        self.debug = debug
        self.processed_count = 0
        self.markdown_processor = MarkdownProcessor(config)
        self.index_processor = IndexProcessor(config)
        self.calibre = CalibreMetadata(config)
        logger.info("BookProcessor initialized")
        
    def process_books(self):
        """Main processing function."""
        logger.info("Starting book processing")
        
        # Add immediate debug output
        logger.debug(f"Looking for books in: {self.config.ORIGINALS_DIR}")
        
        book_files = self._collect_book_files()
        logger.info(f"Found {len(book_files)} book files")
        
        if not book_files:
            logger.warning("No books found to process")
            return
        
        for file_path in book_files:
            if self.debug and self.processed_count >= self.config.MAX_BOOKS:
                logger.debug("Reached maximum book limit for debug mode")
                break
                
            try:
                self._process_single_book(file_path)
                self.processed_count += 1
                
                if self.debug:
                    logger.debug(f"Processed {self.processed_count}/{self.config.MAX_BOOKS}")
                    # Add a pause to inspect results
                    input("Press Enter to continue...")
                    
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}") 

    def _collect_book_files(self) -> List[Path]:
        """Collect all book files to process."""
        logger.info(f"Scanning directory: {self.config.ORIGINALS_DIR}")
        
        book_files = []
        unprocessed_files = []
        
        # Check files in Originals directory
        for file in self.config.ORIGINALS_DIR.glob("*"):
            if file.suffix.lower() in ['.pdf', '.epub', '.mobi']:
                book_files.append(file)
                logger.debug(f"Found book: {file.name}")
        
        # Look for files that haven't been moved yet
        for file in self.config.VAULT_DIR.rglob("*"):
            if any(skip_dir in str(file) for skip_dir in ["Books/Annotations", "Books/Markdown", "Books/Annotated", "Books/Originals"]):
                continue
            
            if file.suffix.lower() in ['.pdf', '.epub', '.mobi']:
                try:
                    new_path = self.config.ORIGINALS_DIR / file.name
                    file.rename(new_path)
                    book_files.append(new_path)
                    logger.info(f"Moved {file.name} to Originals directory")
                except Exception as e:
                    logger.error(f"Error moving {file}: {e}")
                    book_files.append(file)
            elif file.suffix.lower() in ['.txt', '.doc', '.docx', '.rtf']:
                unprocessed_files.append(file)
        
        if unprocessed_files:
            logger.warning("\nFiles that need manual processing:")
            for file in unprocessed_files:
                logger.warning(f"- {file}")
        
        logger.info(f"Found {len(book_files)} book files to process")
        return book_files 