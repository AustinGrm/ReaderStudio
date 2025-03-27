from pathlib import Path
import re
import json
from typing import List, Dict, Optional, Tuple
from ..utils.logger import setup_logger

logger = setup_logger()

class AnnotationParser:
    """
    Parses annotations from various sources into a standardized format.
    
    This class handles:
    1. Kindle highlights from My Clippings.txt
    2. Obsidian Annotator highlights (JSON format)
    3. Manually created annotations in markdown files
    """
    
    def __init__(self, config):
        self.config = config
        
    def parse_kindle_clippings(self, clippings_path: Optional[Path] = None) -> List[Dict]:
        """
        Parse Kindle highlights from My Clippings.txt.
        
        Args:
            clippings_path: Path to My Clippings.txt file (defaults to configured path)
            
        Returns:
            List of parsed annotation dictionaries
        """
        if not clippings_path:
            clippings_path = self.config.KINDLE_CLIPPINGS_PATH
            
        if not clippings_path or not clippings_path.exists():
            logger.warning(f"Kindle clippings file not found: {clippings_path}")
            return []
            
        logger.info(f"Parsing Kindle clippings from: {clippings_path}")
        
        annotations = []
        
        try:
            # Read clippings file
            content = clippings_path.read_text(encoding='utf-8-sig', errors='replace')
            
            # Split into individual clippings
            separator = "=========="
            clippings = content.split(separator)
            
            for clipping in clippings:
                clipping = clipping.strip()
                if not clipping:
                    continue
                    
                try:
                    # Parse the clipping
                    annotation = self._parse_single_clipping(clipping)
                    if annotation:
                        annotations.append(annotation)
                except Exception as e:
                    logger.warning(f"Error parsing clipping: {str(e)}")
                    
            logger.info(f"Parsed {len(annotations)} Kindle annotations")
            return annotations
            
        except Exception as e:
            logger.error(f"Error reading Kindle clippings file: {str(e)}")
            return []
            
    def _parse_single_clipping(self, clipping: str) -> Optional[Dict]:
        """Parse a single Kindle clipping into an annotation dictionary."""
        lines = clipping.strip().split('\n')
        if len(lines) < 2:
            return None
            
        # First line contains book title and author
        title_author = lines[0].strip()
        
        # Extract title and author
        title_match = re.match(r'^(.*?)(?:\s*\(([^)]+)\))?$', title_author)
        if title_match:
            book_title = title_match.group(1).strip()
            author = title_match.group(2) if title_match.group(2) else "Unknown"
        else:
            book_title = title_author
            author = "Unknown"
        
        # Second line contains metadata like location and date
        metadata_line = lines[1].strip()
        
        # Try to parse highlight type (highlight, note, bookmark)
        highlight_type = "highlight"
        if "Your Highlight" in metadata_line:
            highlight_type = "highlight"
        elif "Your Note" in metadata_line:
            highlight_type = "note"
        elif "Your Bookmark" in metadata_line:
            highlight_type = "bookmark"
        
        # Extract location if present
        location_match = re.search(r'Location (\d+-?\d*)', metadata_line)
        location = location_match.group(1) if location_match else ""
        
        # Extract date if present
        date_match = re.search(r'Added on (.+?)$', metadata_line)
        date = date_match.group(1).strip() if date_match else ""
        
        # Remaining lines contain the actual highlight text
        text = '\n'.join(lines[2:]).strip()
        
        # Create annotation dictionary
        annotation = {
            'source': 'kindle',
            'book_title': book_title,
            'author': author,
            'type': highlight_type,
            'location': location,
            'date': date,
            'text': text
        }
        
        return annotation
        
    def parse_obsidian_annotations(self, content: str) -> List[Dict]:
        """
        Parse annotations from Obsidian Annotator formatted text.
        
        Args:
            content: Text content containing Obsidian annotations
            
        Returns:
            List of parsed annotation dictionaries
        """
        annotations = []
        
        # Look for highlight blocks
        highlight_pattern = r'>\s*\[!highlight\]\+?\s*\n>\s*(.*?)(?:\n>.*?)*?(?:\n\n|\n$|\Z)'
        highlight_matches = re.finditer(highlight_pattern, content, re.DOTALL)
        
        for match in highlight_matches:
            # Extract highlight text
            highlight_block = match.group(0)
            highlight_text = match.group(1).strip()
            
            # Extract comment if present
            comment = ""
            comment_match = re.search(r'\n>\s*([^>][^\n]*?)$', highlight_block)
            if comment_match:
                comment = comment_match.group(1).strip()
            
            # Create annotation dictionary
            annotation = {
                'source': 'obsidian_annotator',
                'type': 'highlight',
                'text': highlight_text,
                'comment': comment
            }
            
            # Try to determine book title from the content
            title_match = re.search(r'title:\s*"(.*?)"', content)
            if title_match:
                annotation['book_title'] = title_match.group(1).strip()
            
            # Try to determine author from the content
            author_match = re.search(r'author:\s*"(.*?)"', content)
            if author_match:
                annotation['author'] = author_match.group(1).strip()
            
            annotations.append(annotation)
        
        logger.info(f"Parsed {len(annotations)} Obsidian Annotator annotations")
        return annotations
        
    def parse_annotations_from_landing_page(self, landing_path: Path) -> List[Dict]:
        """
        Extract annotations from a landing page.
        
        Args:
            landing_path: Path to the landing page file
            
        Returns:
            List of parsed annotation dictionaries
        """
        if not landing_path or not landing_path.exists():
            logger.warning(f"Landing page not found: {landing_path}")
            return []
            
        try:
            content = landing_path.read_text(encoding='utf-8')
            
            # Extract metadata from the landing page
            title_match = re.search(r'title:\s*"(.*?)"', content)
            author_match = re.search(r'author:\s*"(.*?)"', content)
            
            book_title = title_match.group(1) if title_match else landing_path.stem
            author = author_match.group(1) if author_match else "Unknown"
            
            # Parse annotations using different methods
            annotations = []
            
            # 1. Parse Kindle-style highlights
            kindle_pattern = r'> \[!quote\]\n> (.*?)(?:\n\n|\n$|\Z)'
            kindle_matches = re.finditer(kindle_pattern, content, re.DOTALL)
            
            for match in kindle_matches:
                highlight_text = match.group(1).strip()
                annotation = {
                    'source': 'kindle',
                    'book_title': book_title,
                    'author': author,
                    'type': 'highlight',
                    'text': highlight_text
                }
                annotations.append(annotation)
            
            # 2. Parse Obsidian Annotator highlights
            obsidian_annotations = self.parse_obsidian_annotations(content)
            for annotation in obsidian_annotations:
                if 'book_title' not in annotation:
                    annotation['book_title'] = book_title
                if 'author' not in annotation:
                    annotation['author'] = author
                annotations.append(annotation)
            
            logger.info(f"Parsed {len(annotations)} annotations from landing page: {landing_path.name}")
            return annotations
            
        except Exception as e:
            logger.error(f"Error parsing annotations from landing page {landing_path}: {str(e)}")
            return []
            
    def parse_all_annotations(self) -> List[Dict]:
        """
        Gather all annotations from all sources.
        
        Returns:
            List of all parsed annotations from all sources
        """
        all_annotations = []
        
        # 1. Parse Kindle clippings if available
        kindle_annotations = self.parse_kindle_clippings()
        all_annotations.extend(kindle_annotations)
        
        # 2. Parse annotations from landing pages
        try:
            for landing_file in self.config.LANDING_DIR.glob("*.md"):
                if landing_file.name == self.config.INDEX_FILE.name:
                    continue
                    
                landing_annotations = self.parse_annotations_from_landing_page(landing_file)
                all_annotations.extend(landing_annotations)
        except Exception as e:
            logger.error(f"Error parsing landing page annotations: {str(e)}")
        
        logger.info(f"Collected {len(all_annotations)} annotations in total")
        return all_annotations 