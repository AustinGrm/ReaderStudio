from pathlib import Path
from typing import List, Dict, Tuple, Optional
from ..metadata.calibre import CalibreMetadata
from .file_processor import FileProcessor
from .markdown import MarkdownProcessor
from .index import IndexProcessor
from ..utils.logger import setup_logger

logger = setup_logger()

class BookProcessor:
    def __init__(self, config):
        self.config = config
        self.file_processor = FileProcessor(config)
        self.markdown_processor = MarkdownProcessor(config)
        self.index_processor = IndexProcessor(config)
        self.calibre = CalibreMetadata(config)
        logger.info("BookProcessor initialized")

    def process_books(self):
        """Main processing function."""
        logger.info("Starting book processing")
        
        # Process bucket directory
        processed_files = self.file_processor.process_bucket()
        logger.info(f"Found {len(processed_files)} files to process")
        
        if not processed_files:
            logger.info("No files to process")
            return
        
        # Process each file
        book_entries = []
        markdown_matches = 0
        total_books = len(processed_files)
        
        for file_path in processed_files:
            try:
                logger.info(f"\nProcessing book: {file_path}")
                entry = self._process_single_book(file_path)
                if entry:
                    book_entries.append(entry)
                    title, metadata = entry
                    if 'markdown_path' in metadata:
                        markdown_matches += 1
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}", exc_info=True)
        
        # Report statistics
        logger.info("\n=== Processing Summary ===")
        logger.info(f"Total books processed: {total_books}")
        logger.info(f"Markdown matches found: {markdown_matches}")
        logger.info(f"Match rate: {(markdown_matches/total_books)*100:.1f}%")
        
        # Create/update index
        if book_entries:
            logger.info(f"\nCreating index with {len(book_entries)} entries")
            self.index_processor.create_index(book_entries)
        else:
            logger.warning("No book entries to index")
        
        logger.info("Processing completed")

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