from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
from ..metadata.calibre import CalibreMetadata
from .file_processor import FileProcessor
from .markdown import MarkdownProcessor
from .index import IndexProcessor
from ..utils.logger import setup_logger
import os
import re
import traceback

logger = setup_logger()

class BookProcessor:
    def __init__(self, config):
        self.config = config
        self.calibre = CalibreMetadata(config)
        self.file_processor = FileProcessor(config)
        self.markdown_processor = MarkdownProcessor(config)
        self.index_processor = IndexProcessor(config)

    def process_books(self):
        """Main processing function with robust error handling."""
        logger.info("Starting book processing")
        
        # First, process the bucket directory to move files to originals
        try:
            logger.info("Checking bucket directory for new files...")
            processed_files = self.file_processor.process_bucket()
            if processed_files:
                logger.info(f"Processed {len(processed_files)} files from bucket")
            else:
                logger.info("No new files found in bucket")
        except Exception as e:
            logger.error(f"Error processing bucket directory: {str(e)}")
            # Continue execution even if bucket processing fails
            processed_files = []
        
        # Collect all book files from originals dir
        book_files = []
        existing_landing_pages = set()
        
        try:
            # First check for existing landing pages to avoid reprocessing
            if self.config.LANDING_DIR.exists():
                for landing_file in self.config.LANDING_DIR.glob("*.md"):
                    if landing_file.name != self.config.INDEX_FILE.name and landing_file.is_file():
                        # Store the base name without .md extension
                        existing_landing_pages.add(landing_file.stem)
                logger.info(f"Found {len(existing_landing_pages)} existing landing pages")
            
            # Now collect only files that don't already have landing pages
            if self.config.ORIGINALS_DIR.exists():
                for file in self.config.ORIGINALS_DIR.glob("*"):
                    if (file.is_file() and 
                        file.suffix.lower() in ['.pdf', '.epub'] and 
                        file.stem not in existing_landing_pages):
                        book_files.append(file)
                
                logger.info(f"\nFound {len(book_files)} new book files to process")
                
                # Debug number of skipped files due to existing landing pages
                skipped_count = sum(1 for f in self.config.ORIGINALS_DIR.glob("*") 
                                    if f.is_file() and f.suffix.lower() in ['.pdf', '.epub'] 
                                    and f.stem in existing_landing_pages)
                if skipped_count > 0:
                    logger.info(f"Skipping {skipped_count} files that already have landing pages")
            else:
                logger.warning(f"Originals directory not found: {self.config.ORIGINALS_DIR}")
        except Exception as e:
            logger.error(f"Error collecting book files: {str(e)}")
            # If we can't collect book files, we'll proceed with an empty list
        
        # If no new files to process, we can skip metadata extraction
        if not book_files:
            logger.info("No new books to process")
            if processed_files:
                logger.info("Updating index to include previously processed books")
                try:
                    all_entries = []
                    # Create entries from all existing landing pages
                    for landing_page in self.config.LANDING_DIR.glob("*.md"):
                        if landing_page.name != self.config.INDEX_FILE.name and landing_page.is_file():
                            # Create a basic entry with just the title
                            metadata = {'title': landing_page.stem, 'has_landing_page': True}
                            all_entries.append((landing_page.stem, metadata))
                    
                    # Create/update the index with all entries
                    if all_entries:
                        self.index_processor.create_index(all_entries)
                        logger.info(f"Updated index with {len(all_entries)} entries")
                except Exception as e:
                    logger.error(f"Error updating index: {str(e)}")
            return
        
        # First pass: Create book entries with basic metadata
        book_entries = []
        for file_path in book_files:
            try:
                metadata = self.calibre.extract_metadata(file_path)
                title = metadata.get('title', file_path.stem)
                book_entries.append((title, metadata))
                logger.info(f"Extracted metadata for: {title}")
            except Exception as e:
                logger.error(f"Error extracting metadata from {file_path}: {str(e)}")
                # Create a basic entry with filename as title so we can still process this file
                basic_metadata = {
                    'title': file_path.stem,
                    'path': str(file_path),
                    'filename': file_path.name,
                    'error': f"Metadata extraction failed: {str(e)}"
                }
                book_entries.append((file_path.stem, basic_metadata))
        
        # Second pass: Match with markdown directories
        matched_entries = []
        try:
            matched_entries = self.markdown_processor.match_markdowns_to_books(book_entries)
        except Exception as e:
            logger.error(f"Error matching markdowns to books: {str(e)}")
            # Fall back to unmatched entries
            matched_entries = book_entries
        
        # Third pass: Create landing pages
        final_entries = []
        for title, metadata in matched_entries:
            try:
                title, updated_metadata = self.markdown_processor.create_landing_page(metadata)
                final_entries.append((title, updated_metadata))
            except Exception as e:
                logger.error(f"Error creating landing page for {title}: {str(e)}")
                # Still include this entry in final_entries to maintain the book count
                final_entries.append((title, metadata))
        
        # Create the index - include both new and existing landing pages
        try:
            # Add existing landing pages that weren't processed this time
            for landing_page in self.config.LANDING_DIR.glob("*.md"):
                if (landing_page.name != self.config.INDEX_FILE.name and 
                    landing_page.is_file() and 
                    landing_page.stem not in [entry[0] for entry in final_entries]):
                    # Create a basic entry with just the title
                    metadata = {'title': landing_page.stem, 'has_landing_page': True}
                    final_entries.append((landing_page.stem, metadata))
            
            if final_entries:
                self.index_processor.create_index(final_entries)
                logger.info(f"Created index with {len(final_entries)} entries")
            else:
                logger.warning("No entries to index")
        except Exception as e:
            logger.error(f"Error creating index: {str(e)}")

    def _process_single_book(self, file_path: Path) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Process a single book file with comprehensive error handling."""
        if not file_path.exists():
            logger.error(f"File does not exist: {file_path}")
            return None
            
        try:
            logger.info(f"\n=== Processing Book ===")
            logger.info(f"File: {file_path}")
            
            # Extract metadata
            try:
                metadata = self.calibre.extract_metadata(file_path)
            except Exception as e:
                logger.error(f"Failed to extract metadata from {file_path}: {str(e)}")
                # Create minimal metadata to continue processing
                metadata = {
                    'title': file_path.stem,
                    'path': str(file_path),
                    'filename': file_path.name
                }
            
            # Use the original filename for matching, not the title
            original_filename = file_path.stem
            logger.info(f"Looking for markdown using original filename: {original_filename}")
            
            try:
                markdown_match = self.markdown_processor.find_matching_markdown(original_filename)
                
                if markdown_match:
                    md_dir, md_file = markdown_match
                    metadata['markdown_path'] = str(md_dir.relative_to(self.config.VAULT_DIR))
                    logger.info(f"Found markdown: {md_dir.name}")
            except Exception as e:
                logger.error(f"Error finding matching markdown for {original_filename}: {str(e)}")
                # Continue without markdown match
            
            # Create landing page
            try:
                title, metadata = self.markdown_processor.create_landing_page(metadata)
                return title, metadata
            except Exception as e:
                logger.error(f"Error creating landing page for {metadata.get('title', 'unknown')}: {str(e)}")
                return metadata.get('title', file_path.stem), metadata
            
        except Exception as e:
            error_msg = f"Unexpected error processing {file_path}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            # Return basic information even on failure
            return file_path.stem, {'title': file_path.stem, 'path': str(file_path), 'error': error_msg}

    def find_matching_markdown(self, *, title: str, author: str = None) -> Optional[Tuple[Path, Path]]:
        """Find matching markdown directory and its main markdown file.
        
        Args:
            title: The book title to match
            author: Optional author name to improve matching
        """
        if not title:
            logger.warning("Cannot find matching markdown: No title provided")
            return None
            
        try:
            logger.info(f"Looking for markdown match: {title}")
            
            best_match_dir = None
            best_score = 0
            
            # Clean the search title
            search_title = f"{author} - {title}" if author else title
            search_title = search_title.lower()
            
            # Look through markdown directories (not files)
            try:
                markdown_dirs = list(self.config.MARKDOWN_DIR.glob("*"))
            except Exception as e:
                logger.error(f"Error listing markdown directories: {str(e)}")
                return None
                
            for md_dir in markdown_dirs:
                if not md_dir.is_dir():
                    continue
                
                try:
                    dir_name = md_dir.name.lower()
                    logger.debug(f"Checking directory: {dir_name}")
                    
                    # Calculate similarity scores
                    # 1. Direct comparison
                    direct_score = self._calculate_similarity(search_title, dir_name)
                    
                    # 2. Title-only comparison (for cases where author format differs)
                    title_only_score = self._calculate_similarity(title.lower(), dir_name)
                    
                    # 3. Word matching (handle reordered words)
                    try:
                        search_words = set(re.findall(r'\w+', search_title))
                        dir_words = set(re.findall(r'\w+', dir_name))
                        word_match_score = len(search_words.intersection(dir_words)) / max(len(search_words), len(dir_words)) if search_words and dir_words else 0
                    except:
                        word_match_score = 0
                    
                    # Combined score (weighted)
                    score = max(
                        direct_score * 0.4 + word_match_score * 0.6,
                        title_only_score * 0.4 + word_match_score * 0.6
                    )
                    
                    logger.debug(f"Match scores for {dir_name}:")
                    logger.debug(f"  Direct: {direct_score:.2f}")
                    logger.debug(f"  Title-only: {title_only_score:.2f}")
                    logger.debug(f"  Word match: {word_match_score:.2f}")
                    logger.debug(f"  Combined: {score:.2f}")
                    
                    if score > best_score and score > 0.7:  # Threshold for a good match
                        best_score = score
                        best_match_dir = md_dir
                except Exception as dir_e:
                    logger.error(f"Error processing markdown directory {md_dir}: {str(dir_e)}")
                    # Continue with next directory
            
            if best_match_dir:
                # Look for main markdown file (index.md or similarly named file)
                main_candidates = []
                try:
                    main_candidates = [
                        best_match_dir / "index.md",
                        best_match_dir / f"{best_match_dir.name}.md"
                    ]
                    
                    # Also try to find any markdown file
                    try:
                        first_md = next(best_match_dir.glob("*.md"), None)
                        if first_md:
                            main_candidates.append(first_md)
                    except Exception:
                        pass
                except Exception as e:
                    logger.error(f"Error building main candidate list: {str(e)}")
                
                for candidate in main_candidates:
                    try:
                        if candidate and candidate.exists():
                            logger.info(f"✓ Found matching markdown: {best_match_dir.name} (score: {best_score:.2f})")
                            return best_match_dir, candidate
                    except Exception:
                        # Continue with next candidate
                        continue
            
            logger.warning(f"✗ No markdown match found for: {title}")
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error finding matching markdown for {title}: {str(e)}")
            return None

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity using multiple methods."""
        if not str1 or not str2:
            return 0.0
            
        try:
            from difflib import SequenceMatcher
            
            # Clean strings
            str1 = re.sub(r'[^\w\s]', '', str1.lower())
            str2 = re.sub(r'[^\w\s]', '', str2.lower())
            
            # Sequence matcher similarity
            sequence_sim = SequenceMatcher(None, str1, str2).ratio()
            
            # Word set similarity
            words1 = set(str1.split())
            words2 = set(str2.split())
            word_sim = len(words1.intersection(words2)) / max(len(words1), len(words2)) if words1 and words2 else 0
            
            # Return weighted combination
            return (sequence_sim + word_sim) / 2
        except Exception as e:
            logger.error(f"Error calculating string similarity: {str(e)}")
            return 0.0 