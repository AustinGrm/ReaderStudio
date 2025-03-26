from pathlib import Path
from typing import List, Tuple, Dict
from difflib import SequenceMatcher
import re
import logging

logger = logging.getLogger(__name__)

class IndexProcessor:
    def __init__(self, config):
        self.config = config

    def create_index(self, book_entries: List[Tuple[str, Dict]]):
        """Create a master index file with links to all books."""
        if not book_entries:
            logger.warning("No book entries to index")
            return
            
        logger.info(f"Creating index with {len(book_entries)} entries")
        
        # Debug each entry
        for title, metadata in book_entries:
            logger.debug(f"Indexing book: {title}")
            logger.debug(f"  Author: {metadata.get('author', 'Unknown')}")
            logger.debug(f"  Format: {metadata.get('format', 'Unknown')}")
        
        index_content = [
            "# Book Library Index",
            "\nThis is an automatically generated index of all books in the library.\n",
            "## Current Reading",
            "\n```dataview",
            "TABLE author, format, reading_progress as \"Progress\", last_opened as \"Last Opened\"",
            "FROM #book",
            "WHERE status = \"current\"",
            "SORT last_opened DESC",
            "```\n",
            "## Next Up",
            "\n```dataview",
            "TABLE author, format",
            "FROM #book",
            "WHERE status = \"next\"",
            "```\n",
            "## Books by Title\n"
        ]
        
        # Sort by title
        sorted_entries = sorted(book_entries, key=lambda x: x[0].lower())
        
        # Add book entries
        for title, metadata in sorted_entries:
            author = metadata.get("author", "Unknown Author")
            format = metadata.get("format", "Unknown")
            
            # Create link to landing page
            landing_path = f"Books/{title}.md"
            index_content.append(f"- [[{landing_path}|{title} - {author} ({format})]]")
        
        # Add author section
        authors = {}
        for title, metadata in book_entries:
            if "author" in metadata:
                author = metadata["author"]
                if author not in authors:
                    authors[author] = []
                authors[author].append((title, metadata))
        
        if authors:
            index_content.append("\n## Books by Author\n")
            for author in sorted(authors.keys()):
                index_content.append(f"### {author}\n")
                for title, metadata in sorted(authors[author], key=lambda x: x[0].lower()):
                    format = metadata.get("format", "Unknown")
                    landing_path = f"Books/{title}.md"
                    index_content.append(f"- [[{landing_path}|{title} ({format})]]")
                index_content.append("")
        
        # Write index file
        index_path = self.config.BOOKS_DIR / "Book Index.md"
        index_path.write_text("\n".join(index_content))
        logger.info(f"Created index at: {index_path}")

    def match_landing_pages_with_markdown(self):
        """Match landing pages with markdown files."""
        print("Matching landing pages with markdown files...")
