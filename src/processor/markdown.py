from pathlib import Path
from typing import Dict, Tuple, Optional, List
from difflib import SequenceMatcher
import re
from ..utils.logger import setup_logger
from rapidfuzz import fuzz, process

logger = setup_logger()

class MarkdownProcessor:
    def __init__(self, config):
        self.config = config
        self._ensure_directories()
    # ... rest of the class implementation 

    def _ensure_directories(self):
        """Create necessary directories if they don't exist."""
        self.config.MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)
        self.config.LANDING_DIR.mkdir(parents=True, exist_ok=True)

    def find_matching_markdown(self, book_filename: str) -> Optional[Tuple[Path, Path]]:
        """Find matching markdown directory for a book.
        
        Args:
            book_filename: The complete filename of the book (e.g., 'J.K Rowling - Harry Potter - the prequel.pdf')
        """
        # Clean filename (remove extension)
        search_name = Path(book_filename).stem
        logger.info(f"\n=== Markdown Directory Search ===")
        logger.info(f"Looking for directory matching: '{search_name}'")
        logger.info(f"Searching in: {self.config.MARKDOWN_DIR}")
        
        # List all directories
        markdown_dirs = [d for d in self.config.MARKDOWN_DIR.glob("*") if d.is_dir()]
        logger.info(f"Found {len(markdown_dirs)} markdown directories:")
        for d in markdown_dirs:
            logger.info(f"  - {d.name}")
        
        for md_dir in markdown_dirs:
            logger.info(f"\nChecking directory: {md_dir.name}")
            
            # Check if directory has a markdown file
            markdown_files = list(md_dir.glob("*.md"))
            if not markdown_files:
                logger.debug(f"  ✗ No markdown files found in directory")
                continue
            
            # Simple word matching
            search_words = set(re.findall(r'\w+', search_name.lower()))
            dir_words = set(re.findall(r'\w+', md_dir.name.lower()))
            
            logger.debug(f"  Search words: {search_words}")
            logger.debug(f"  Dir words: {dir_words}")
            logger.debug(f"  Matching words: {search_words.intersection(dir_words)}")
            
            score = len(search_words.intersection(dir_words)) / max(len(search_words), len(dir_words))
            logger.info(f"  Match score: {score:.2f}")
            
            if score > 0.7:  # 70% word match threshold
                logger.info(f"  ✓ Found match: {md_dir.name}")
                logger.info(f"  Markdown files available: {[f.name for f in markdown_files]}")
                return md_dir, markdown_files[0]
        
        logger.warning(f"✗ No matching markdown directory found for: {search_name}")
        return None

    def create_landing_page(self, metadata: Dict) -> Tuple[str, Dict]:
        """Create a landing page and annotation document for the book."""
        safe_title = re.sub(r'[:\/:*?"<>|]', '-', metadata["title"])
        landing_path = self.config.LANDING_DIR / f"{safe_title}.md"
        
        # Create annotation document first
        annotation_doc = self._create_annotation_document(metadata, safe_title)
        if annotation_doc:
            metadata['annotation_path'] = str(annotation_doc.relative_to(self.config.VAULT_DIR))
        
        # Track markdown matching
        markdown_result = self.find_matching_markdown(metadata['title'])
        if markdown_result:
            md_dir, md_file = markdown_result
            # Store the directory path
            metadata['markdown_path'] = str(md_dir.relative_to(self.config.VAULT_DIR))
            # Store the full path to the specific markdown file
            metadata['markdown_file'] = str(md_file.relative_to(self.config.VAULT_DIR))
            logger.info(f"✓ Matched markdown: {md_dir.name} -> {md_file.name}")
        else:
            logger.warning(f"✗ No markdown match for: {safe_title}")
        
        # Build and write content
        content = self._build_landing_page_content(metadata)
        landing_path.write_text(content)
        logger.info(f"Created/updated landing page: {landing_path.name}")
        
        return safe_title, metadata

    def _build_landing_page_content(self, metadata: Dict) -> str:
        """Build the landing page content."""
        yaml_lines = ["---"]
        
        # Add metadata fields
        for key, value in metadata.items():
            if key not in ['tags', 'annotation_path', 'markdown_file'] and value:
                yaml_lines.append(f"{key}: \"{value}\"")
        
        yaml_lines.append("tags:")
        yaml_lines.append("  - book")
        if "tags" in metadata and metadata["tags"]:
            for tag in metadata["tags"].split(","):
                yaml_lines.append(f"  - {tag.strip()}")
        
        yaml_lines.append("---")
        
        # Build main content
        content_lines = [
            "\n".join(yaml_lines),
            f"\n# {metadata.get('title', 'Untitled')}",
            "\n## Document Versions",
        ]
        
        # Add annotation document link first (this is the main reading link)
        if 'annotation_path' in metadata:
            content_lines.append(f"- [[{metadata['annotation_path']}|Read & Annotate]]")
        
        # Add markdown version if found - link directly to the markdown file
        if 'markdown_file' in metadata:
            content_lines.append(f"- [[{metadata['markdown_file']}|Markdown Version]]")
        elif 'markdown_path' in metadata:
            # If we have the path but not the specific file, try to construct a typical filename
            dir_name = Path(metadata['markdown_path']).name
            # Construct likely filename based on directory name
            likely_filename = f"{dir_name}.md"
            likely_path = f"{metadata['markdown_path']}/{likely_filename}"
            content_lines.append(f"- [[{likely_path}|Markdown Version]]")
        
        # Add reading status section
        content_lines.extend([
            "\n## Reading Status",
            f"- **Status**: {metadata.get('status', 'New')}",
            f"- **Last opened**: {metadata.get('last_opened', '')}",
            f"- **Progress**: {int(float(metadata.get('reading_progress', 0)) * 100)}%",
            "\n### Progress Bar",
            self._create_progress_bar(metadata.get('reading_progress', 0)),
            "\n## Notes & Highlights",
            "\n### Key Concepts",
            "- ",
            "\n### Important Quotes",
            "- ",
            "\n### Questions & Reflections",
            "- "
        ])
        
        return "\n".join(content_lines)

    def _create_progress_bar(self, progress_value: float) -> str:
        """Create a simple ASCII progress bar."""
        try:
            progress = float(progress_value)
        except (ValueError, TypeError):
            progress = 0
        
        progress = min(max(progress, 0), 1)  # Ensure between 0 and 1
        filled = int(progress * 20)
        empty = 20 - filled
        
        return f"`[{'█' * filled}{'░' * empty}]` {int(progress * 100)}%"

    def create_markdown(self, metadata: Dict) -> Tuple[str, Dict]:
        """Generate an Obsidian-friendly markdown file with specified YAML frontmatter."""
        # Basic implementation to get started
        safe_title = metadata.get("title", "Untitled")
        print(f"Creating markdown for: {safe_title}")
        return safe_title, metadata 

    def _create_annotation_document(self, metadata: Dict, safe_title: str) -> Optional[Path]:
        """Create an annotation document with annotation-target set."""
        annotation_filename = f"{safe_title} - Annotations.md"
        annotation_path = self.config.ANNOTATION_DIR / annotation_filename
        
        # Create the relative path for the parent document
        parent_doc_path = Path("Books") / f"{safe_title}.md"
        
        # Build YAML frontmatter
        yaml_lines = [
            "---",
            f"title: \"{metadata['title']} - Annotations\"",
            f"author: \"{metadata.get('author', 'Unknown')}\"",
            f"annotation-target: {metadata['path']}",
            f"parent_document: {parent_doc_path}",
            "---"
        ]
        
        yaml_frontmatter = "\n".join(yaml_lines)
        
        # Basic document structure
        annotation_content = (
            f"{yaml_frontmatter}\n\n"
            f"# {metadata.get('title')} - Annotations\n\n"
            "This document is for annotating the original file using the Obsidian Annotator plugin.\n"
        )
        
        # Preserve existing content if file exists
        if annotation_path.exists():
            existing_content = annotation_path.read_text()
            frontmatter_end = existing_content.find("---\n\n")
            if frontmatter_end > 0:
                post_frontmatter = existing_content[frontmatter_end + 5:]
                annotation_content = f"{yaml_frontmatter}\n\n{post_frontmatter}"
        
        # Create directory if it doesn't exist
        annotation_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the file
        annotation_path.write_text(annotation_content)
        logger.info(f"Created/updated annotation document: {annotation_path.name}")
        
        return annotation_path 

    def match_markdowns_to_books(self, book_entries: List[Tuple[str, Dict]]) -> List[Tuple[str, Dict]]:
        """Match markdown directories to books after indexing."""
        logger.info("\n=== Matching Markdowns to Books ===")
        
        # First, get all markdown directories
        markdown_dirs = [d for d in self.config.MARKDOWN_DIR.glob("*") if d.is_dir()]
        
        # Debug: Print exact strings we're working with
        logger.info("\nDEBUG: Exact string comparison:")
        for book_title, metadata in book_entries:
            book_filename = Path(metadata['path']).stem
            logger.info(f"\nBook filename: '{book_filename}'")
            logger.info("Comparing against markdown directories:")
            
            # Compare with each markdown directory
            for md_dir in markdown_dirs:
                # Get raw comparison
                ratio = fuzz.ratio(book_filename, md_dir.name)
                token_ratio = fuzz.token_sort_ratio(book_filename, md_dir.name)
                partial_ratio = fuzz.partial_ratio(book_filename, md_dir.name)
                
                logger.info(f"\nMarkdown dir: '{md_dir.name}'")
                logger.info(f"Simple ratio: {ratio}")
                logger.info(f"Token sort ratio: {token_ratio}")
                logger.info(f"Partial ratio: {partial_ratio}")
                
                # Debug: Show character-by-character comparison
                logger.info("\nCharacter comparison:")
                logger.info(f"Book:     {' '.join(book_filename)}")
                logger.info(f"Markdown: {' '.join(md_dir.name)}")
            
            def normalize(text):
                text = text.lower()
                text = re.sub(r'[^a-z0-9\s]', '', text)
                text = re.sub(r'\s+', ' ', text).strip()
                return text
            
            def extract_title_only(filename):
                parts = filename.split(" - ")
                return parts[-1] if len(parts) > 1 else filename
            
            title_only = extract_title_only(book_filename)
            normalized_title = normalize(title_only)
            
            best_score = 0
            best_match = None
            
            for md_dir in markdown_dirs:
                normalized_md_name = normalize(md_dir.name)
                score = fuzz.token_sort_ratio(normalized_title, normalized_md_name)
                logger.info(f"→ Comparing '{normalized_title}' to '{normalized_md_name}' = {score}")
                if score > best_score:
                    best_score = score
                    best_match = md_dir
            
            if best_match and best_score > 40:
                logger.info(f"✓ Selected best match: '{best_match.name}' (score: {best_score})")
                md_file = next(best_match.glob("*.md"), None)
                if md_file:
                    metadata['markdown_path'] = str(best_match.relative_to(self.config.VAULT_DIR))
            else:
                logger.warning(f"✗ No suitable match found for: {book_filename}")
            
        return book_entries 