import re
from pathlib import Path
from typing import Dict, Tuple

class MarkdownProcessor:
    def __init__(self, config):
        self.config = config
        self._ensure_directories()

    def _ensure_directories(self):
        """Create necessary directories if they don't exist."""
        for directory in [
            self.config.BOOKS_DIR,
            self.config.ANNOTATION_DIR,
            self.config.MARKDOWN_DIR,
            self.config.ORIGINALS_DIR
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    def create_markdown(self, metadata: Dict) -> Tuple[str, Dict]:
        """Generate an Obsidian-friendly markdown file with specified YAML frontmatter."""
        # Clean title for safe filenames
        safe_title = re.sub(r'[:\/:*?"<>|]', '-', metadata["title"])
        md_file_path = self.config.BOOKS_DIR / f"{safe_title}.md"
        
        # Check if file exists and preserve user-edited values
        if md_file_path.exists():
            metadata = self._update_existing_metadata(md_file_path, metadata)
        
        # Create annotation document first and get its path
        annotation_doc_path = self._create_annotation_document(metadata, safe_title)
        
        # Build YAML frontmatter and document content
        markdown_content = self._build_markdown_content(metadata, safe_title, annotation_doc_path)
        
        # Write the file
        md_file_path.write_text(markdown_content)
        
        print(f"Created/updated metadata for: {safe_title}")
        return safe_title, metadata

    def _update_existing_metadata(self, file_path: Path, new_metadata: Dict) -> Dict:
        """Update metadata while preserving user-edited values."""
        if not file_path.exists():
            return new_metadata
        
        try:
            content = file_path.read_text()
            
            # Extract existing YAML frontmatter
            yaml_match = re.search(r'---\n(.*?)\n---', content, re.DOTALL)
            if not yaml_match:
                return new_metadata
                
            yaml_content = yaml_match.group(1)
            
            # Extract values to preserve
            preserve_fields = ['status', 'reading_progress', 'last_annotated', 'jdnumber']
            for field in preserve_fields:
                match = re.search(rf'{field}:\s*(.*)', yaml_content)
                if match and match.group(1).strip():
                    new_metadata[field] = match.group(1).strip()
                    
            return new_metadata
        except Exception as e:
            print(f"Error updating metadata: {e}")
            return new_metadata

    def _create_annotation_document(self, metadata: Dict, safe_title: str) -> Path:
        """Create an annotation document with annotation-target set."""
        annotation_filename = f"{safe_title} - Annotations.md"
        annotation_file_path = self.config.ANNOTATION_DIR / annotation_filename
        
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
        if annotation_file_path.exists():
            existing_content = annotation_file_path.read_text()
            frontmatter_end = existing_content.find("---\n\n")
            if frontmatter_end > 0:
                post_frontmatter = existing_content[frontmatter_end + 5:]
                annotation_content = f"{yaml_frontmatter}\n\n{post_frontmatter}"
        
        annotation_file_path.write_text(annotation_content)
        print(f"Created/updated annotation document for: {safe_title}")
        
        return Path("Books/Annotations") / annotation_filename

    def _build_markdown_content(self, metadata: Dict, safe_title: str, annotation_doc_path: Path) -> str:
        """Build the markdown content including YAML frontmatter and document structure."""
        yaml_lines = self._build_yaml_frontmatter(metadata)
        
        # Main document structure
        content_lines = [
            "\n".join(yaml_lines),
            f"\n# {metadata.get('title')}",
            "\n## Document Versions",
            f"- [[{metadata['path']}|Original ({metadata.get('format')})]]",
            f"- [[{annotation_doc_path}|Annotations]]",
        ]
        
        # Add markdown and annotated versions if they exist
        self._add_version_links(content_lines, safe_title)
        
        # Add reading status and notes sections
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

    def _build_yaml_frontmatter(self, metadata: Dict) -> list:
        """Build YAML frontmatter lines."""
        yaml_lines = ["---"]
        
        # Add all metadata fields except tags
        for key, value in metadata.items():
            if key != "tags" and value:
                yaml_lines.append(f"{key}: \"{value}\"")
        
        # Handle tags
        if "tags" in metadata and metadata["tags"]:
            yaml_lines.append("tags:")
            for tag in metadata["tags"].split(","):
                yaml_lines.append(f"  - {tag.strip()}")
        else:
            yaml_lines.append("tags:")
            yaml_lines.append("  - book")
        
        yaml_lines.append("---")
        return yaml_lines

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

    def _add_version_links(self, content_lines: list, safe_title: str):
        """Add links to markdown and annotated versions if they exist."""
        markdown_path = self.config.MARKDOWN_DIR / f"{safe_title}.md"
        annotated_path = self.config.BOOKS_DIR / "Annotated" / f"{safe_title}.md"
        
        if markdown_path.exists():
            rel_path = markdown_path.relative_to(self.config.VAULT_DIR)
            content_lines.append(f"- [[{rel_path}|Markdown Version]]")
        
        if annotated_path.exists():
            rel_path = annotated_path.relative_to(self.config.VAULT_DIR)
            content_lines.append(f"- [[{rel_path}|Annotated Markdown]]")