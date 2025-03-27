import argparse
import sys
from pathlib import Path
from src.processor.book_processor import BookProcessor
from src.processor.annotation_parser import AnnotationParser
from src.processor.annotation_syncer import AnnotationSyncer
from config.default_config import Config
from src.utils.logger import setup_logger
import time

def main():
    """
    Main entry point for the book processing application.
    
    This application processes books through the following steps:
    1. Check BUCKET_DIR for new files and move them to ORIGINALS_DIR
    2. Process book files in ORIGINALS_DIR to extract metadata
    3. Match books with existing markdown files
    4. Create landing pages for books
    5. Create a master index of all books
    6. Sync annotations from various sources to book landing pages
    
    Command line arguments:
        --match-only: Only match existing landing pages with markdown files
        --sync-annotations: Only sync annotations from Kindle and Obsidian
        --debug: Enable debug logging
    """
    start_time = time.time()
    success = False
    
    try:
        # Parse arguments
        parser = argparse.ArgumentParser(description='Process book files for Obsidian vault')
        parser.add_argument('--match-only', action='store_true', 
                           help='Only match existing landing pages with markdown files')
        parser.add_argument('--sync-annotations', action='store_true',
                           help='Only sync annotations from Kindle and Obsidian')
        parser.add_argument('--debug', action='store_true',
                           help='Enable debug logging')
        
        args = parser.parse_args()
        
        # Setup logging with debug flag
        logger = setup_logger(debug=args.debug)
        logger.info("Starting book indexer")
        
        # Initialize processor
        try:
            processor = BookProcessor(Config)
        except Exception as e:
            logger.error(f"Failed to initialize BookProcessor: {str(e)}")
            sys.exit(1)
        
        # Check if essential directories exist
        essential_dirs_exist = True
        try:
            # Debug output for directories
            logger.debug(f"VAULT_DIR exists: {Config.VAULT_DIR.exists()}")
            logger.debug(f"BUCKET_DIR exists: {Config.BUCKET_DIR.exists()}")
            logger.debug(f"LANDING_DIR exists: {Config.LANDING_DIR.exists()}")
            logger.debug(f"ORIGINALS_DIR exists: {Config.ORIGINALS_DIR.exists()}")
            logger.debug(f"MARKDOWN_DIR exists: {Config.MARKDOWN_DIR.exists()}")
            
            if not Config.VAULT_DIR.exists():
                logger.error(f"VAULT_DIR does not exist: {Config.VAULT_DIR}")
                essential_dirs_exist = False
                
            # Try to create these directories if they don't exist
            for dir_path in [Config.BUCKET_DIR, Config.LANDING_DIR, Config.ORIGINALS_DIR, Config.MARKDOWN_DIR]:
                if not dir_path.exists():
                    try:
                        logger.warning(f"Creating missing directory: {dir_path}")
                        dir_path.mkdir(parents=True, exist_ok=True)
                    except Exception as mkdir_e:
                        logger.error(f"Failed to create directory {dir_path}: {str(mkdir_e)}")
                        if dir_path in [Config.ORIGINALS_DIR, Config.MARKDOWN_DIR]:
                            essential_dirs_exist = False
            
            if not essential_dirs_exist:
                logger.error("Essential directories are missing and could not be created")
                sys.exit(1)
        except Exception as dir_e:
            logger.error(f"Error checking directories: {str(dir_e)}")
        
        # Check directory contents
        try:
            if Config.BUCKET_DIR.exists():
                bucket_files = list(Config.BUCKET_DIR.glob("*"))
                logger.debug(f"Files in BUCKET_DIR: {[f.name for f in bucket_files]}")
            
            if Config.ORIGINALS_DIR.exists():
                books = list(Config.ORIGINALS_DIR.glob("*"))
                logger.debug(f"Files in ORIGINALS_DIR: {[b.name for b in books]}")
        except Exception as e:
            logger.error(f"Error checking directory contents: {str(e)}")
            # Non-fatal error, continue execution
        
        # Main processing
        try:
            if args.match_only:
                logger.info("Running in match-only mode")
                processor.index_processor.match_landing_pages_with_markdown()
            elif args.sync_annotations:
                logger.info("Running annotation sync mode")
                # Initialize our new annotation classes
                annotation_parser = AnnotationParser(Config)
                annotation_syncer = AnnotationSyncer(Config)
                
                # Parse annotations from all sources
                annotations = annotation_parser.parse_all_annotations()
                logger.info(f"Found {len(annotations)} annotations to sync")
                
                # Sync annotations to markdown files
                if annotations:
                    synced_count = annotation_syncer.sync_annotations(annotations)
                    logger.info(f"Synced {synced_count} annotations to markdown files")
                else:
                    logger.info("No annotations found to sync")
            else:
                logger.info("Running full book processing")
                processor.process_books()
                
                # Also sync annotations if any exist
                try:
                    logger.info("Checking for annotations to sync")
                    annotation_parser = AnnotationParser(Config)
                    annotation_syncer = AnnotationSyncer(Config)
                    
                    # Parse and sync annotations
                    annotations = annotation_parser.parse_all_annotations()
                    if annotations:
                        synced_count = annotation_syncer.sync_annotations(annotations)
                        logger.info(f"Synced {synced_count} annotations to markdown files")
                    else:
                        logger.info("No annotations found to sync")
                except Exception as annotation_e:
                    logger.error(f"Error syncing annotations: {str(annotation_e)}")
                
            success = True
        except Exception as e:
            logger.error(f"Error during processing: {str(e)}", exc_info=True)
            
    except KeyboardInterrupt:
        logger.warning("Process interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
    finally:
        # Calculate and log execution time
        execution_time = time.time() - start_time
        if success:
            logger.info(f"Processing completed successfully in {execution_time:.2f} seconds")
        else:
            logger.info(f"Processing completed with errors in {execution_time:.2f} seconds")

if __name__ == "__main__":
    main() 