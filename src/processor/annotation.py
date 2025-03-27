from pathlib import Path
import json
import re
from typing import Dict, List, Tuple, Optional, Set
import os
from ..utils.logger import setup_logger
from .markdown import MarkdownProcessor

logger = setup_logger()

class AnnotationProcessor:
    """
    Processes annotations from different sources and syncs them to book landing pages.
    
    This class handles:
    1. Extracting annotations from Kindle clippings
    2. Extracting annotations from Obsidian annotator JSON objects
    3. Updating book landing pages with extracted highlights
    """
    
    def __init__(self, config):
        self.config = config
        self.markdown_processor = MarkdownProcessor(config)
        self._ensure_directories()
        
    def _ensure_directories(self):
        """Create necessary directories if they don't exist."""
        kindle_highlights_dir = self.config.VAULT_DIR / "Kindle_highlights"
        kindle_highlights_dir.mkdir(parents=True, exist_ok=True)
        
    def process_annotations(self):
        """Process all annotations from different sources."""
        logger.info("==== Processing Annotations ====")
        
        # Process Kindle clippings
        kindle_entries = self._process_kindle_highlights()
        
        # Process Obsidian annotations
        obsidian_entries = self._process_obsidian_annotations()
        
        # Combine all annotations
        all_annotations = kindle_entries + obsidian_entries
        
        # Group by book
        grouped_annotations = self._group_annotations_by_book(all_annotations)
        
        # Update landing pages
        self._update_landing_pages(grouped_annotations)
        
        return len(all_annotations)
    
    def _process_kindle_highlights(self) -> List[Dict]:
        """Process Kindle highlights from clippings files."""
        kindle_dir = self.config.VAULT_DIR / "Kindle_highlights"
        annotations = []
        
        if not kindle_dir.exists():
            logger.warning(f"Kindle highlights directory not found: {kindle_dir}")
            return annotations
            
        # Find all clippings files
        clippings_files = list(kindle_dir.glob("*.txt"))
        logger.info(f"Found {len(clippings_files)} Kindle clippings files")
        
        for clippings_file in clippings_files:
            logger.info(f"Processing Kindle clippings from: {clippings_file.name}")
            try:
                with open(clippings_file, 'r', encoding='utf-8-sig') as f:
                    content = f.read()
                
                # Parse clippings content
                book_entries = self._parse_kindle_clippings(content)
                annotations.extend(book_entries)
                
                logger.info(f"Extracted {len(book_entries)} annotations from {clippings_file.name}")
            except Exception as e:
                logger.error(f"Error processing Kindle clippings file {clippings_file.name}: {str(e)}")
        
        return annotations
    
    def _parse_kindle_clippings(self, content: str) -> List[Dict]:
        """Parse Kindle clippings content into structured annotations."""
        annotations = []
        
        # Split content by the Kindle delimiter (usually a line of ==========)
        entries = re.split(r'==========', content)
        
        for entry in entries:
            entry = entry.strip()
            if not entry:
                continue
                
            try:
                # Parse the entry
                lines = entry.split('\n')
                if len(lines) < 2:
                    continue
                    
                # First line contains the book title
                book_title_line = lines[0].strip()
                
                # Extract author if available (format: "Title (Author)")
                author = None
                if '(' in book_title_line and ')' in book_title_line:
                    author_match = re.search(r'\((.*?)\)$', book_title_line)
                    if author_match:
                        author = author_match.group(1).strip()
                        book_title = book_title_line[:book_title_line.rfind('(')].strip()
                    else:
                        book_title = book_title_line
                else:
                    book_title = book_title_line
                
                # Second line contains metadata like location
                metadata_line = lines[1].strip()
                location_match = re.search(r'location: \[(\d+)\]', metadata_line, re.IGNORECASE)
                location = location_match.group(1) if location_match else None
                
                # Remaining lines contain the highlight text
                highlight_text = '\n'.join(lines[2:]).strip()
                
                # Create annotation entry
                annotation = {
                    'book_title': book_title,
                    'author': author,
                    'location': location,
                    'text': highlight_text,
                    'source': 'kindle'
                }
                
                annotations.append(annotation)
            except Exception as e:
                logger.warning(f"Error parsing Kindle clipping entry: {str(e)}")
        
        return annotations
    
    def _process_obsidian_annotations(self) -> List[Dict]:
        """Extract annotations from Obsidian annotation files."""
        annotations = []
        
        # Find all annotation files in the annotation directory
        annotation_files = list(self.config.ANNOTATION_DIR.glob("*.md"))
        logger.info(f"Found {len(annotation_files)} Obsidian annotation files")
        
        for annotation_file in annotation_files:
            logger.info(f"Processing Obsidian annotations from: {annotation_file.name}")
            try:
                with open(annotation_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract JSON annotation blocks
                file_annotations = self._parse_obsidian_annotations(content, annotation_file)
                annotations.extend(file_annotations)
                
                logger.info(f"Extracted {len(file_annotations)} annotations from {annotation_file.name}")
            except Exception as e:
                logger.error(f"Error processing annotation file {annotation_file.name}: {str(e)}")
        
        return annotations
    
    def _parse_obsidian_annotations(self, content: str, file_path: Path) -> List[Dict]:
        """Parse Obsidian annotation JSON blocks into structured annotations."""
        annotations = []
        
        # Extract the book title from the file name or YAML frontmatter
        book_title = None
        title_match = re.search(r'title: "(.*?)(?:\s*-\s*Annotations)?"', content, re.IGNORECASE)
        if title_match:
            book_title = title_match.group(1).strip()
        else:
            # Try to get from filename
            book_title = file_path.stem
            if book_title.endswith(" - Annotations"):
                book_title = book_title[:-len(" - Annotations")]
        
        # Extract the annotation-target to get original file path
        target_file = None
        target_match = re.search(r'annotation-target: (.*?)$', content, re.MULTILINE)
        if target_match:
            target_file = target_match.group(1).strip()
        
        # Extract all JSON annotation blocks
        json_blocks = re.finditer(r'```annotation-json\n(.*?)\n```', content, re.DOTALL)
        
        for match in json_blocks:
            try:
                # Parse the JSON
                json_str = match.group(1)
                annotation_data = json.loads(json_str)
                
                # Extract highlighted text
                highlighted_text = None
                if 'target' in annotation_data and annotation_data['target']:
                    for target in annotation_data['target']:
                        if 'selector' in target:
                            for selector in target['selector']:
                                if selector.get('type') == 'TextQuoteSelector' and 'exact' in selector:
                                    highlighted_text = selector['exact']
                                    break
                            if highlighted_text:
                                break
                
                # Extract comment if available
                comment = annotation_data.get('text', '')
                
                # Create annotation entry
                if highlighted_text:
                    annotation = {
                        'book_title': book_title,
                        'text': highlighted_text,
                        'comment': comment,
                        'source': 'obsidian',
                        'target_file': target_file
                    }
                    annotations.append(annotation)
            except Exception as e:
                logger.warning(f"Error parsing Obsidian annotation JSON: {str(e)}")
        
        # Also parse the text quotes outside JSON blocks
        # Example: *%%PREFIX%%text1%%HIGHLIGHT%% ==highlighted text== %%POSTFIX%%text2*
        highlight_blocks = re.finditer(r'\*%%PREFIX%%(.*?)%%HIGHLIGHT%% ==(.*?)== %%POSTFIX%%(.*?)\*', content, re.DOTALL)
        
        for match in highlight_blocks:
            try:
                prefix = match.group(1).strip()
                highlighted_text = match.group(2).strip()
                postfix = match.group(3).strip()
                
                # Get comment if available (it usually appears after the highlight block)
                comment = ""
                comment_match = re.search(r'%%COMMENT%%\n(.*?)\n', content[match.end():match.end()+200], re.DOTALL)
                if comment_match:
                    comment = comment_match.group(1).strip()
                
                # Create annotation entry
                if highlighted_text:
                    annotation = {
                        'book_title': book_title,
                        'text': highlighted_text,
                        'context': {'prefix': prefix, 'postfix': postfix},
                        'comment': comment,
                        'source': 'obsidian',
                        'target_file': target_file
                    }
                    annotations.append(annotation)
            except Exception as e:
                logger.warning(f"Error parsing Obsidian text highlight: {str(e)}")
        
        return annotations
    
    def _group_annotations_by_book(self, annotations: List[Dict]) -> Dict[str, List[Dict]]:
        """Group annotations by book title."""
        grouped = {}
        
        for annotation in annotations:
            book_title = annotation.get('book_title')
            if not book_title:
                continue
                
            if book_title not in grouped:
                grouped[book_title] = []
                
            grouped[book_title].append(annotation)
        
        return grouped
    
    def _update_landing_pages(self, grouped_annotations: Dict[str, List[Dict]]):
        """Update book landing pages with annotations."""
        logger.info("Updating landing pages with annotations")
        
        # Get all existing landing pages
        landing_pages = {}
        for landing_file in self.config.LANDING_DIR.glob("*.md"):
            landing_pages[landing_file.stem] = landing_file
        
        books_updated = 0
        new_books_created = 0
        
        for book_title, annotations in grouped_annotations.items():
            if not annotations:
                continue
                
            # Clean title for file matching
            safe_title = re.sub(r'[:\\/]*?"<>|]', '-', book_title)
            
            # Try to find an existing landing page
            landing_file = None
            for title, file_path in landing_pages.items():
                # Check for exact match
                if title.lower() == safe_title.lower():
                    landing_file = file_path
                    break
                
                # Check for fuzzy match (title contains)
                if safe_title.lower() in title.lower() or title.lower() in safe_title.lower():
                    landing_file = file_path
                    break
            
            # If landing page doesn't exist, create a new one with minimal metadata
            if not landing_file:
                logger.info(f"Creating new landing page for: {book_title}")
                
                # Get author from annotations if available
                author = next((a.get('author') for a in annotations if a.get('author')), "Unknown")
                
                # Create minimal metadata
                metadata = {
                    'title': book_title,
                    'author': author,
                    'tags': 'book,clippings-only',
                    'status': 'Importing Highlights',
                    # Add dummy path for annotation document creation
                    'path': str(self.config.ORIGINALS_DIR / f"{safe_title}_dummy.txt")
                }
                
                # Create landing page
                safe_title, metadata = self.markdown_processor.create_landing_page(metadata)
                landing_file = self.config.LANDING_DIR / f"{safe_title}.md"
                new_books_created += 1
            else:
                logger.info(f"Updating existing landing page: {landing_file.name}")
                books_updated += 1
            
            # Update the landing page with annotations
            self._add_annotations_to_landing_page(landing_file, annotations)
        
        logger.info(f"Updated {books_updated} existing landing pages")
        logger.info(f"Created {new_books_created} new landing pages for books with annotations")
    
    def _add_annotations_to_landing_page(self, landing_file: Path, annotations: List[Dict]):
        """Add annotations to a landing page."""
        if not landing_file.exists():
            logger.warning(f"Landing page does not exist: {landing_file}")
            return
            
        try:
            # Read the existing content
            with open(landing_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if the file already has a Highlights section
            highlights_section = "## Highlights & Annotations"
            if highlights_section not in content:
                # Add the section before "## Notes & Highlights" if it exists
                if "## Notes & Highlights" in content:
                    content = content.replace("## Notes & Highlights", f"{highlights_section}\n\n## Notes & Highlights")
                else:
                    # Otherwise, add it at the end
                    content += f"\n\n{highlights_section}\n\n"
            
            # Build the annotations content
            annotations_content = []
            
            # Group annotations by source
            kindle_annotations = [a for a in annotations if a.get('source') == 'kindle']
            obsidian_annotations = [a for a in annotations if a.get('source') == 'obsidian']
            
            # Process Kindle annotations
            if kindle_annotations:
                annotations_content.append("### Kindle Highlights")
                for annotation in kindle_annotations:
                    text = annotation.get('text', '').strip()
                    location = annotation.get('location', '')
                    
                    # Format with location if available
                    if location:
                        annotations_content.append(f"> [!quote] Location: {location}\n> {text}\n")
                    else:
                        annotations_content.append(f"> [!quote]\n> {text}\n")
            
            # Process Obsidian annotations
            if obsidian_annotations:
                annotations_content.append("### Obsidian Annotations")
                for annotation in obsidian_annotations:
                    text = annotation.get('text', '').strip()
                    comment = annotation.get('comment', '').strip()
                    
                    # Format with highlight and comment
                    highlight_text = f"> [!highlight]+ \n> {text}\n"
                    if comment:
                        highlight_text += f"> \n> *{comment}*\n"
                    
                    annotations_content.append(highlight_text)
            
            # Insert the annotations content into the landing page
            if annotations_content:
                annotations_text = "\n\n" + "\n".join(annotations_content)
                
                # Find where to insert the annotations
                highlights_pos = content.find(highlights_section)
                if highlights_pos >= 0:
                    # Find the next section to insert before
                    next_section_pos = content.find("\n## ", highlights_pos + len(highlights_section))
                    if next_section_pos >= 0:
                        # Insert before the next section
                        new_content = content[:highlights_pos + len(highlights_section)] + annotations_text + content[next_section_pos:]
                    else:
                        # No next section, append to the end
                        new_content = content[:highlights_pos + len(highlights_section)] + annotations_text
                else:
                    # This shouldn't happen since we add the section if it doesn't exist
                    new_content = content + "\n" + highlights_section + annotations_text
                
                # Write the updated content
                with open(landing_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                logger.info(f"Added {len(annotations)} annotations to {landing_file.name}")
        except Exception as e:
            logger.error(f"Error updating landing page {landing_file.name} with annotations: {str(e)}") 