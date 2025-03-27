from pathlib import Path
import re
import json
import uuid
import difflib
from typing import Dict, List, Tuple, Optional, Set
from ..utils.logger import setup_logger

logger = setup_logger()

class AnnotationSyncer:
    """
    Syncs annotations between different formats and applies highlights to markdown files.
    
    This class:
    1. Takes highlights from Kindle clippings or Obsidian annotations
    2. Searches for the text in markdown files
    3. Adds block IDs to markdown files for direct linking
    4. Applies highlighting and comments to markdown files
    5. Updates landing pages with direct links to highlights
    """
    
    def __init__(self, config):
        self.config = config
    
    def sync_annotations(self, annotations: List[Dict], markdown_path: Optional[Path] = None, 
                        landing_page_path: Optional[Path] = None) -> int:
        """
        Sync annotations to a markdown file and update landing page with links.
        
        Args:
            annotations: List of annotation dictionaries with 'text', 'comment', etc.
            markdown_path: Path to the markdown file to sync with (or infer from annotation)
            landing_page_path: Path to the landing page to update with links (or infer)
            
        Returns:
            Number of annotations successfully synced
        """
        if not annotations:
            logger.info("No annotations to sync")
            return 0
            
        synced_count = 0
        
        # Group annotations by source file/book
        by_source = {}
        for annotation in annotations:
            book_title = annotation.get('book_title', '')
            if not book_title:
                continue
                
            if book_title not in by_source:
                by_source[book_title] = []
                
            by_source[book_title].append(annotation)
        
        # Process each book's annotations
        for book_title, book_annotations in by_source.items():
            # Find the markdown file if not provided
            md_path = markdown_path
            if not md_path:
                md_path = self._find_markdown_for_book(book_title)
                
            if not md_path or not md_path.exists():
                logger.warning(f"No markdown file found for '{book_title}', skipping annotation sync")
                continue
                
            # Find the landing page if not provided
            landing_path = landing_page_path
            if not landing_path:
                landing_path = self._find_landing_page_for_book(book_title)
                
            if not landing_path or not landing_path.exists():
                logger.warning(f"No landing page found for '{book_title}', skipping link updates")
                
            # Process annotations for this book
            book_synced = self._sync_book_annotations(book_annotations, md_path, landing_path)
            synced_count += book_synced
            logger.info(f"Synced {book_synced} annotations for '{book_title}'")
            
        return synced_count
    
    def _sync_book_annotations(self, annotations: List[Dict], markdown_path: Path, 
                             landing_page_path: Optional[Path]) -> int:
        """Sync annotations for a specific book."""
        if not markdown_path.exists():
            logger.warning(f"Markdown file not found: {markdown_path}")
            return 0
            
        # Read the markdown content
        try:
            md_content = markdown_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Error reading markdown file {markdown_path}: {str(e)}")
            return 0
            
        # Track changes to avoid multiple rewrites
        md_updated = False
        synced_count = 0
        annotations_with_links = []
        
        # Process each annotation
        for annotation in annotations:
            highlight_text = annotation.get('text', '').strip()
            if not highlight_text:
                logger.debug("Empty highlight text, skipping")
                continue
                
            # Find the text in the markdown
            match_result = self._find_text_in_markdown(highlight_text, md_content)
            if not match_result:
                logger.warning(f"Could not find text in markdown: '{highlight_text[:50]}...'")
                continue
                
            match_index, match_line, match_context = match_result
            
            # Create a block ID if it doesn't exist
            block_id, md_content, updated = self._ensure_block_id(md_content, match_index, match_line)
            if updated:
                md_updated = True
                
            # Apply highlighting if needed
            md_content, highlight_updated = self._apply_highlighting(md_content, match_index, 
                                                                   highlight_text, 
                                                                   annotation.get('comment', ''),
                                                                   block_id)
            if highlight_updated:
                md_updated = True
            
            # Save the block ID with the annotation for landing page updates
            annotation['block_id'] = block_id
            annotation['match_context'] = match_context
            annotations_with_links.append(annotation)
            synced_count += 1
        
        # Update the markdown file if changes were made
        if md_updated:
            try:
                markdown_path.write_text(md_content, encoding='utf-8')
                logger.info(f"Updated markdown file with annotations: {markdown_path.name}")
            except Exception as e:
                logger.error(f"Error writing to markdown file {markdown_path}: {str(e)}")
                return 0
        
        # Update the landing page with links if provided
        if landing_page_path and landing_page_path.exists() and annotations_with_links:
            self._update_landing_page_links(landing_page_path, annotations_with_links, markdown_path)
            
        return synced_count
    
    def _find_text_in_markdown(self, search_text: str, content: str) -> Optional[Tuple[int, str, Dict]]:
        """
        Find text in markdown content with fuzzy matching.
        
        Returns:
            Tuple of (match index, matched line, context dict) or None if not found
        """
        if not search_text or not content:
            return None
            
        # Clean up the search text
        search_text = search_text.strip()
        search_lines = search_text.split('\n')
        main_search = search_lines[0] if search_lines else search_text
        
        # Prepare a clean version for matching (remove markdown formatting)
        clean_content = re.sub(r'[*_`~#>]+', '', content)
        content_lines = content.split('\n')
        clean_lines = clean_content.split('\n')
        
        # Try exact matching first
        for i, line in enumerate(clean_lines):
            if search_text in line:
                # Found exact match
                context = {
                    'prefix': clean_lines[i-1] if i > 0 else '',
                    'line': line,
                    'suffix': clean_lines[i+1] if i < len(clean_lines) - 1 else ''
                }
                return i, content_lines[i], context
        
        # Try fuzzy matching for each line
        best_match = None
        best_ratio = 0.8  # Minimum similarity threshold
        best_index = -1
        
        for i, line in enumerate(clean_lines):
            # Skip very short lines
            if len(line) < 10:
                continue
                
            # Check for fuzzy matches
            ratio = difflib.SequenceMatcher(None, main_search, line).ratio()
            
            # For longer highlights, also try to match substrings
            if len(main_search) > 40 and len(line) > 40:
                # Check if a good portion of the search text is in the line
                for substring in self._get_substrings(main_search):
                    if len(substring) < 20:
                        continue
                    if substring in line:
                        substring_ratio = len(substring) / len(main_search)
                        ratio = max(ratio, substring_ratio)
            
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = line
                best_index = i
        
        if best_match:
            context = {
                'prefix': clean_lines[best_index-1] if best_index > 0 else '',
                'line': best_match,
                'suffix': clean_lines[best_index+1] if best_index < len(clean_lines) - 1 else '',
                'match_ratio': best_ratio
            }
            return best_index, content_lines[best_index], context
            
        return None
    
    def _get_substrings(self, text: str, min_length: int = 20) -> List[str]:
        """Generate meaningful substrings from text for partial matching."""
        words = text.split()
        result = []
        
        # Generate word chunks of different sizes
        for chunk_size in range(4, min(12, len(words))):
            for i in range(len(words) - chunk_size + 1):
                chunk = ' '.join(words[i:i+chunk_size])
                if len(chunk) >= min_length:
                    result.append(chunk)
        
        return result
    
    def _ensure_block_id(self, content: str, match_index: int, 
                        match_line: str) -> Tuple[str, str, bool]:
        """
        Ensure a block ID exists for the matched line.
        
        Returns:
            Tuple of (block_id, updated_content, was_updated)
        """
        lines = content.split('\n')
        if match_index >= len(lines):
            logger.error(f"Match index {match_index} out of range for content with {len(lines)} lines")
            return "", content, False
            
        current_line = lines[match_index]
        
        # Check if line already has a block ID
        block_id_match = re.search(r'\^([a-zA-Z0-9]+)$', current_line)
        if block_id_match:
            # Block ID already exists
            return block_id_match.group(1), content, False
            
        # Generate a new block ID
        block_id = self._generate_block_id()
        
        # Add block ID to the line
        lines[match_index] = f"{current_line} ^{block_id}"
        
        # Reassemble content
        updated_content = '\n'.join(lines)
        return block_id, updated_content, True
    
    def _generate_block_id(self) -> str:
        """Generate a unique block ID for Obsidian."""
        # Use first part of a UUID, but make it more readable
        return uuid.uuid4().hex[:10]
    
    def _apply_highlighting(self, content: str, match_index: int, highlight_text: str, 
                          comment: str, block_id: str) -> Tuple[str, bool]:
        """
        Apply highlighting formatting to the matched text.
        
        Returns:
            Tuple of (updated_content, was_updated)
        """
        lines = content.split('\n')
        if match_index >= len(lines):
            return content, False
            
        current_line = lines[match_index]
        
        # Check if already highlighted
        if '==' in current_line:
            # Already has highlighting, don't modify
            return content, False
        
        # Find the text to highlight in the line (fuzzy match)
        matcher = difflib.SequenceMatcher(None, highlight_text, current_line)
        blocks = matcher.get_matching_blocks()
        
        # Only apply if we have a good match
        good_match = False
        for block in blocks:
            if block.size > 20:  # Require at least 20 characters in a match
                good_match = True
                break
                
        if not good_match:
            # For shorter texts, require a higher overall ratio
            if matcher.ratio() < 0.7:
                return content, False
        
        # Find the best substring to highlight
        highlight_range = None
        if len(blocks) > 0:
            # Get the longest matching block
            best_block = max(blocks, key=lambda b: b.size)
            if best_block.size > 10:  # Minimum size to highlight
                highlight_range = (best_block.b, best_block.b + best_block.size)
        
        if not highlight_range:
            # Fallback: just wrap the whole line if it's similar enough
            if matcher.ratio() > 0.6:
                highlight_range = (0, len(current_line))
            else:
                return content, False
        
        # Apply the highlighting
        start, end = highlight_range
        highlighted_line = f"{current_line[:start]}=={current_line[start:end]}=={current_line[end:]}"
        
        # Update the line with highlighting
        lines[match_index] = highlighted_line
        
        # If there's a comment, add it after the line
        if comment and comment.strip():
            comment_line = f"> [!note] Comment\n> {comment.strip()}"
            lines.insert(match_index + 1, comment_line)
        
        # Reassemble content
        updated_content = '\n'.join(lines)
        return updated_content, True
    
    def _find_markdown_for_book(self, book_title: str) -> Optional[Path]:
        """Find the markdown file for a book based on its title."""
        # Try different approaches to find the markdown file
        
        # 1. Check in the Markdowns directory for a matching directory
        for md_dir in self.config.MARKDOWN_DIR.glob("*"):
            if not md_dir.is_dir():
                continue
                
            # Check if directory name contains the book title (case insensitive)
            if book_title.lower() in md_dir.name.lower():
                # Look for markdown files in this directory
                md_files = list(md_dir.glob("*.md"))
                if md_files:
                    logger.info(f"Found markdown file for '{book_title}': {md_files[0]}")
                    return md_files[0]
        
        # 2. Try to find a markdown file directly
        clean_title = re.sub(r'[^\w\s]', '', book_title).strip()
        
        # Look in Markdowns directory
        for md_file in self.config.MARKDOWN_DIR.glob("**/*.md"):
            file_name = md_file.stem
            clean_file_name = re.sub(r'[^\w\s]', '', file_name).strip()
            
            # Check for similarity
            if (clean_title.lower() in clean_file_name.lower() or 
                clean_file_name.lower() in clean_title.lower()):
                logger.info(f"Found potential markdown file for '{book_title}': {md_file}")
                return md_file
        
        return None
    
    def _find_landing_page_for_book(self, book_title: str) -> Optional[Path]:
        """Find the landing page for a book based on its title."""
        # First try exact match with title
        landing_path = self.config.LANDING_DIR / f"{book_title}.md"
        if landing_path.exists():
            logger.info(f"Found exact landing page match: {landing_path.name}")
            return landing_path
            
        # Try a fuzzy search - first normalize the titles
        clean_title = re.sub(r'[^\w\s]', '', book_title).lower().strip()
        
        best_match = None
        best_score = 0
        
        for landing_file in self.config.LANDING_DIR.glob("*.md"):
            if landing_file.name == self.config.INDEX_FILE.name:
                continue
                
            # 1. Check filename
            clean_filename = re.sub(r'[^\w\s]', '', landing_file.stem).lower().strip()
            filename_score = difflib.SequenceMatcher(None, clean_title, clean_filename).ratio()
            
            # 2. Check YAML title field
            yaml_score = 0
            try:
                content = landing_file.read_text(encoding='utf-8')
                title_match = re.search(r'title: "(.*?)"', content)
                if title_match:
                    yaml_title = title_match.group(1).strip()
                    clean_yaml = re.sub(r'[^\w\s]', '', yaml_title).lower().strip()
                    yaml_score = difflib.SequenceMatcher(None, clean_title, clean_yaml).ratio()
            except Exception:
                pass
                
            # Use the better of the two scores
            score = max(filename_score, yaml_score)
            
            # Check for common words as a backup heuristic
            words1 = set(clean_title.split())
            words2 = set(clean_filename.split())
            common_words = len(words1.intersection(words2))
            if common_words > 2 and score < 0.8:  # Boost score if at least 3 words match
                word_ratio = common_words / max(len(words1), len(words2))
                score = max(score, 0.7 * word_ratio + 0.3)  # Weighted score
            
            if score > best_score and score > 0.7:  # Threshold for matching
                best_score = score
                best_match = landing_file
                logger.debug(f"Potential landing page match: {landing_file.name} (score: {score:.2f})")
        
        if best_match:
            logger.info(f"Found fuzzy landing page match: {best_match.name} (score: {best_score:.2f})")
            return best_match
                
        # No good match found
        logger.warning(f"No landing page found for: {book_title}")
        return None
    
    def _update_landing_page_links(self, landing_path: Path, annotations: List[Dict], 
                                 markdown_path: Path) -> bool:
        """Update landing page with links to annotations in the markdown file."""
        try:
            content = landing_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Error reading landing page {landing_path}: {str(e)}")
            return False
            
        # Check if the highlights section exists
        highlights_section = "## Highlights & Annotations"
        markdown_links_section = "### Direct Links to Highlights"
        
        # First, ensure the highlights section exists
        if highlights_section not in content:
            # Add it before "## Notes & Highlights" if it exists
            if "## Notes & Highlights" in content:
                content = content.replace("## Notes & Highlights", 
                                         f"{highlights_section}\n\n{markdown_links_section}\n\n## Notes & Highlights")
            else:
                # Otherwise, add it at the end
                content += f"\n\n{highlights_section}\n\n{markdown_links_section}\n"
        elif markdown_links_section not in content:
            # Add markdown links section after the highlights section
            pos = content.find(highlights_section) + len(highlights_section)
            content = content[:pos] + f"\n\n{markdown_links_section}" + content[pos:]
        
        # Find where to insert the links
        links_pos = content.find(markdown_links_section) + len(markdown_links_section)
        
        # Check for existing links section to avoid duplicates
        existing_links = []
        next_section_pos = content.find("\n## ", links_pos)
        if next_section_pos > 0:
            existing_section = content[links_pos:next_section_pos].strip()
            # Extract existing block IDs to avoid duplicates
            for line in existing_section.split("\n"):
                if line.strip().startswith("- [[") and "^" in line:
                    block_id_match = re.search(r'\^\w+', line)
                    if block_id_match:
                        existing_links.append(block_id_match.group(0))
        
        # Prepare links section
        links_content = "\n"
        rel_path = markdown_path.relative_to(self.config.VAULT_DIR)
        
        added_links = 0
        for annotation in annotations:
            if 'block_id' not in annotation:
                continue
                
            block_id = annotation['block_id']
            highlight_text = annotation.get('text', '').strip()
            
            # Skip if this block ID already exists in the links
            if f"^{block_id}" in existing_links:
                continue
                
            # Create a link preview with the first 50 chars of the highlight
            preview = highlight_text[:50] + ("..." if len(highlight_text) > 50 else "")
            
            # Create the link
            link = f"- [[{rel_path}^{block_id}|{preview}]]\n"
            links_content += link
            added_links += 1
        
        # Only update if we have new links to add
        if added_links == 0:
            logger.info(f"No new annotation links to add for: {landing_path.name}")
            return True
            
        # Insert links into content
        if next_section_pos > 0:
            # Preserve existing links
            if existing_section.strip():
                links_content = f"\n{existing_section}\n{links_content}"
            new_content = content[:links_pos] + links_content + content[next_section_pos:]
        else:
            new_content = content[:links_pos] + links_content
            
        # Write updated content
        try:
            landing_path.write_text(new_content, encoding='utf-8')
            logger.info(f"Updated landing page with {added_links} new annotation links: {landing_path.name}")
            return True
        except Exception as e:
            logger.error(f"Error updating landing page {landing_path}: {str(e)}")
            return False 