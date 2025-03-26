from pathlib import Path
from typing import List, Dict, Tuple, Optional
from ..metadata.calibre import CalibreMetadata
from .file_processor import FileProcessor
from .markdown import MarkdownProcessor
from .index import IndexProcessor
from ..utils.logger import setup_logger
import os

logger = setup_logger()

class BookProcessor:
    def __init__(self, config):
        self.config = config
        self.calibre = CalibreMetadata(config)
        self.markdown_processor = MarkdownProcessor(config)
        self.index_processor = IndexProcessor(config)

    def process_books(self):
        """Direct port of the working update_metadata function"""
        book_files = []
        unprocessed_files = []
        
        # First, check if files are already in Originals directory
        for file in os.listdir(self.config.ORIGINALS_DIR):
            if file.lower().endswith((".pdf", ".epub", ".mobi")):
                book_files.append(self.config.ORIGINALS_DIR / file)
        
        # Then look for any files that haven't been moved yet
        for root, _, files in os.walk(self.config.VAULT_DIR):
            if any(skip_dir in root for skip_dir in ["Books/Annotations", "Books/Markdowns", "Books/Annotated", "Books/Originals"]):
                continue
                
            for file in files:
                file_path = Path(root) / file
                file_lower = file.lower()
                
                if file_lower.endswith((".pdf", ".epub", ".mobi")):
                    # Move file to Originals directory
                    new_path = self.config.ORIGINALS_DIR / file
                    try:
                        file_path.rename(new_path)
                        book_files.append(new_path)
                        logger.info(f"Moved {file} to Originals directory")
                    except Exception as e:
                        logger.error(f"Error moving {file}: {e}")
                        book_files.append(file_path)  # Process in original location
                elif file_lower.endswith((".txt", ".doc", ".docx", ".rtf")):
                    unprocessed_files.append(file_path)
        
        if unprocessed_files:
            logger.info("\nFiles that need manual processing:")
            for file in unprocessed_files:
                logger.info(f"- {file}")
        
        logger.info(f"\nFound {len(book_files)} book files to process")
        
        book_entries = []
        for file_path in book_files:
            logger.info(f"Processing: {file_path}")
            metadata = self.calibre.extract_metadata(file_path)
            title, metadata = self.markdown_processor.create_markdown(metadata)
            book_entries.append((title, metadata))
        
        # Create the master index file
        self.index_processor.create_index(book_entries)
        
        # Match landing pages with markdown files
        self.index_processor.match_landing_pages_with_markdown()

    def _process_single_book(self, file_path: Path) -> Optional[Tuple[str, Dict]]:
        """Process a single book file."""
        try:
            logger.info(f"Processing book: {file_path}")
            
            # Extract metadata
            metadata = self.calibre.extract_metadata(file_path)
            logger.debug(f"Extracted metadata: {metadata}")
            
            # Create landing page and get back the title and updated metadata
            title, metadata = self.markdown_processor.create_landing_page(metadata)
            logger.debug(f"Created landing page for: {title}")
            
            return title, metadata
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}", exc_info=True)
            return None 