import argparse
from pathlib import Path
from src.processor.book_processor import BookProcessor
from config.default_config import Config
from src.utils.logger import setup_logger

def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description='Process book files for Obsidian vault')
    parser.add_argument('--match-only', action='store_true', 
                       help='Only match existing landing pages with markdown files')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Setup logging with debug flag
    logger = setup_logger(debug=args.debug)
    logger.info("Starting book indexer")
    
    # Initialize processor
    processor = BookProcessor(Config)
    
    # Debug output
    logger.debug(f"VAULT_DIR exists: {Config.VAULT_DIR.exists()}")
    logger.debug(f"BOOKS_DIR exists: {Config.BOOKS_DIR.exists()}")
    logger.debug(f"ORIGINALS_DIR exists: {Config.ORIGINALS_DIR.exists()}")
    
    if Config.ORIGINALS_DIR.exists():
        books = list(Config.ORIGINALS_DIR.glob("*"))
        logger.debug(f"Files in ORIGINALS_DIR: {books}")
    
    try:
        if args.match_only:
            logger.info("Running in match-only mode")
            processor.index_processor.match_landing_pages_with_markdown()
        else:
            logger.info("Running full book processing")
            processor.process_books()
            
    except Exception as e:
        logger.error(f"Error during processing: {e}", exc_info=True)
        raise
    
    logger.info("Processing completed")

if __name__ == "__main__":
    main() 