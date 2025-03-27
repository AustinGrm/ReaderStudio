from pathlib import Path
from typing import List, Dict, Tuple, Optional
from ..metadata.calibre import CalibreMetadata
from .file_processor import FileProcessor
from .markdown import MarkdownProcessor
from .index import IndexProcessor
from ..utils.logger import setup_logger
import os
import re

logger = setup_logger()

class BookProcessor:
    def __init__(self, config):
        self.config = config
        self.calibre = CalibreMetadata(config)
        self.markdown_processor = MarkdownProcessor(config)
        self.index_processor = IndexProcessor(config)

    def process_books(self):
        """Main processing function."""
        logger.info("Starting book processing")
        
        # Collect all book files
        book_files = []
        for file in self.config.ORIGINALS_DIR.glob("*"):
            if file.suffix.lower() in ['.pdf', '.epub', '.mobi']:
                book_files.append(file)
        
        logger.info(f"\nFound {len(book_files)} book files to process")
        
        # First pass: Create book entries with basic metadata
        book_entries = []
        for file_path in book_files:
            try:
                metadata = self.calibre.extract_metadata(file_path)
                title = metadata['title']
                book_entries.append((title, metadata))
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
        
        # Second pass: Match with markdown directories
        book_entries = self.markdown_processor.match_markdowns_to_books(book_entries)
        
        # Third pass: Create landing pages
        final_entries = []
        for title, metadata in book_entries:
            try:
                title, metadata = self.markdown_processor.create_landing_page(metadata)
                final_entries.append((title, metadata))
            except Exception as e:
                logger.error(f"Error creating landing page for {title}: {e}")
        
        # Create the index
        if final_entries:
            self.index_processor.create_index(final_entries)
            logger.info(f"Created index with {len(final_entries)} entries")
        else:
            logger.warning("No entries to index")

    def _process_single_book(self, file_path: Path) -> Optional[Tuple[str, Dict]]:
        """Process a single book file."""
        try:
            logger.info(f"\n=== Processing Book ===")
            logger.info(f"File: {file_path}")
            
            # Extract metadata
            metadata = self.calibre.extract_metadata(file_path)
            
            # Use the original filename for matching, not the title
            original_filename = file_path.stem  # This will be "J. K. Rowling - Harry Potter The Prequel"
            logger.info(f"Looking for markdown using original filename: {original_filename}")
            markdown_match = self.markdown_processor.find_matching_markdown(original_filename)
            
            if markdown_match:
                md_dir, md_file = markdown_match
                metadata['markdown_path'] = str(md_dir.relative_to(self.config.VAULT_DIR))
                logger.info(f"Found markdown: {md_dir.name}")
            
            # Create landing page
            title, metadata = self.markdown_processor.create_landing_page(metadata)
            return title, metadata
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}", exc_info=True)
            return None

    def find_matching_markdown(self, *, title: str, author: str = None) -> Optional[Tuple[Path, Path]]:
        """Find matching markdown directory and its main markdown file.
        
        Args:
            title: The book title to match
            author: Optional author name to improve matching
        """
        logger.info(f"Looking for markdown match: {title}")
        
        best_match_dir = None
        best_score = 0
        
        # Clean the search title
        search_title = f"{author} - {title}" if author else title
        search_title = search_title.lower()
        
        # Look through markdown directories (not files)
        for md_dir in self.config.MARKDOWN_DIR.glob("*"):
            if not md_dir.is_dir():
                continue
            
            dir_name = md_dir.name.lower()
            logger.debug(f"Checking directory: {dir_name}")
            
            # Calculate similarity scores
            # 1. Direct comparison
            direct_score = self._calculate_similarity(search_title, dir_name)
            
            # 2. Title-only comparison (for cases where author format differs)
            title_only_score = self._calculate_similarity(title.lower(), dir_name)
            
            # 3. Word matching (handle reordered words)
            search_words = set(re.findall(r'\w+', search_title))
            dir_words = set(re.findall(r'\w+', dir_name))
            word_match_score = len(search_words.intersection(dir_words)) / max(len(search_words), len(dir_words))
            
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
        
        if best_match_dir:
            # Look for main markdown file (index.md or similarly named file)
            main_candidates = [
                best_match_dir / "index.md",
                best_match_dir / f"{best_match_dir.name}.md",
                next(best_match_dir.glob("*.md"), None)
            ]
            
            for candidate in main_candidates:
                if candidate and candidate.exists():
                    logger.info(f"✓ Found matching markdown: {best_match_dir.name} (score: {best_score:.2f})")
                    return best_match_dir, candidate
        
        logger.warning(f"✗ No markdown match found for: {title}")
        return None

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity using multiple methods."""
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