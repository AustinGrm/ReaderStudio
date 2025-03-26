from pathlib import Path
from typing import Dict, Tuple, Optional
from difflib import SequenceMatcher
import re
from ..utils.logger import setup_logger

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

    def find_matching_markdown(self, title: str) -> Optional[Path]:
        """Find matching markdown file using fuzzy matching."""
        best_match = None
        best_score = 0
        
        for md_file in self.config.MARKDOWN_DIR.glob("*.md"):
            score = self._calculate_similarity(title, md_file.stem)
            if score > best_score and score > 0.8:  # 80% similarity threshold
                best_score = score
                best_match = md_file
        
        return best_match

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings."""
        # Basic cleaning
        str1 = str1.lower().strip()
        str2 = str2.lower().strip()
        
        # Calculate similarity
        return SequenceMatcher(None, str1, str2).ratio()

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
            metadata['markdown_path'] = str(md_dir.relative_to(self.config.VAULT_DIR))
            logger.info(f"✓ Matched markdown: {md_dir.name}")
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
            if key not in ['tags', 'annotation_path'] and value:
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
        
        # Add markdown version if found
        if 'markdown_path' in metadata:
            content_lines.append(f"- [[{metadata['markdown_path']}/index|Markdown Version]]")
        
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