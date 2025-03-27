from pathlib import Path
from typing import List, Tuple, Dict
from difflib import SequenceMatcher
import re
import logging
import os

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
        """Match landing pages with markdown files using test_matching from experimental/test_chatmatching.py."""
        logger.info("Matching landing pages with markdown files...")
        
        try:
            from rapidfuzz import fuzz, process
        except ImportError:
            logger.error("rapidfuzz package is required for matching. Install with: python -m pip install rapidfuzz")
            return
        
        # Define paths - using paths from config
        BOOKS_DIR = self.config.BOOKS_DIR
        ORIGINALS_DIR = self.config.ORIGINALS_DIR
        MARKDOWN_DIR = self.config.MARKDOWN_DIR
        
        # List all original files using os.walk
        original_files = []
        for root, dirs, files in os.walk(ORIGINALS_DIR):
            for file in files:
                # Append full path of the file
                original_files.append(os.path.join(root, file))
        logger.info("\n=== Original Files ===")
        logger.info(f"Found {len(original_files)} original files:")
        for orig in original_files:
            logger.debug(f"  - {os.path.splitext(os.path.basename(orig))[0]}")
        
        # Get all landing pages
        landing_pages = list(BOOKS_DIR.glob("*.md"))
        logger.info(f"Found {len(landing_pages)} landing pages.")
        
        # Create a mapping from original file stem to landing page
        original_to_landing = {}
        for original_file in original_files:
            orig_stem = os.path.splitext(os.path.basename(original_file))[0]
            # Find matching landing page
            for landing_page in landing_pages:
                content = landing_page.read_text()
                # Check if original file is mentioned in the landing page content
                if orig_stem in content:
                    original_to_landing[original_file] = landing_page
                    break
        
        # List markdown files from subdirectories using os.walk
        markdown_files = []
        logger.info("\n=== Markdown Files from Subdirectories ===")
        for root, dirs, files in os.walk(MARKDOWN_DIR):
            # Skip the top-level MARKDOWN_DIR itself
            if Path(root) == MARKDOWN_DIR:
                continue
            for file in files:
                if file.lower().endswith(".md"):
                    full_path = os.path.join(root, file)
                    markdown_files.append(full_path)
                    logger.info(f"  - {os.path.basename(root)} : {file}")
        logger.info(f"\nTotal markdown files found: {len(markdown_files)}")
        
        if not markdown_files:
            logger.warning("No markdown files found in subdirectories.")
            return

        logger.info("\n=== Matching Results ===")
        updated_count = 0
        
        # For each markdown file, find the best matching original file
        for md_file in markdown_files:
            md_dir_name = os.path.basename(os.path.dirname(md_file))
            md_name = os.path.splitext(os.path.basename(md_file))[0]
            logger.info(f"\nMatching for markdown file: '{md_name}' (from directory '{md_dir_name}')")
            
            # Build a list of original file stems for fuzzy matching
            original_stems = [os.path.splitext(os.path.basename(orig))[0] for orig in original_files]
            
            # Get top 3 matches using token_sort_ratio
            matches = process.extract(
                md_dir_name,  # Match on directory name instead of file name
                original_stems,
                scorer=fuzz.token_sort_ratio,
                limit=3
            )
            
            logger.info("Top matches:")
            for match_name, score, index in matches:
                matched_file = original_files[index]
                logger.info(f"  Score {score:>3}: '{match_name}' -> {os.path.basename(matched_file)}")
            
            # Select best match if score is high enough
            if matches and matches[0][1] >= 60:  # Using 60 as threshold
                best_match_name, best_score, best_index = matches[0]
                best_match_file = original_files[best_index]
                logger.info(f"✓ Best match: '{os.path.basename(best_match_file)}' with score {best_score}")
                
                # Find the landing page associated with this original file
                landing_page = original_to_landing.get(best_match_file)
                
                if landing_page:
                    # Update the landing page with a link to the markdown
                    try:
                        content = landing_page.read_text()
                        
                        # Create the markdown link
                        rel_path = Path(os.path.dirname(md_file)).relative_to(self.config.VAULT_DIR)
                        markdown_link = f"- [[{rel_path}/index|Markdown Version]]"
                        logger.info(f"Adding link: {markdown_link}")
                        
                        if markdown_link not in content:
                            # Find "Document Versions" section
                            doc_versions_match = re.search(r'## Document Versions(.*?)(?=\n## |$)', content, re.DOTALL)
                            
                            if doc_versions_match:
                                doc_versions = doc_versions_match.group(1)
                                updated_doc_versions = doc_versions + f"\n{markdown_link}"
                                
                                # Replace the old section with the updated one
                                updated_content = content.replace(
                                    f"## Document Versions{doc_versions}",
                                    f"## Document Versions{updated_doc_versions}"
                                )
                                
                                landing_page.write_text(updated_content)
                                updated_count += 1
                                logger.info(f"Updated {landing_page.name} with link to {md_dir_name}")
                            else:
                                logger.warning(f"No 'Document Versions' section found in {landing_page.name}")
                        else:
                            logger.info(f"Link already exists in {landing_page.name}")
                    except Exception as e:
                        logger.error(f"Error updating landing page: {e}")
                else:
                    logger.warning(f"No landing page found for original file: {os.path.basename(best_match_file)}")
            else:
                logger.warning(f"✗ No good match found for markdown directory: {md_dir_name}")
        
        logger.info(f"Matched and updated {updated_count} landing pages with markdown files.")
