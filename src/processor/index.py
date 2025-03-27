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
        print("Matching landing pages with markdown files...")
        logger.info("Matching landing pages with markdown files...")
        
        try:
            from rapidfuzz import fuzz, process
        except ImportError:
            print("rapidfuzz package is required for matching. Install with: python -m pip install rapidfuzz")
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
        print(f"\n=== Original Files ===")
        print(f"Found {len(original_files)} original files.")
        
        # Get all landing pages
        landing_pages = list(BOOKS_DIR.glob("*.md"))
        print(f"Found {len(landing_pages)} landing pages.")
        
        # Create a mapping from original file stem to landing page
        original_to_landing = {}
        for original_file in original_files:
            orig_stem = os.path.splitext(os.path.basename(original_file))[0]
            # Find matching landing page
            for landing_page in landing_pages:
                try:
                    content = landing_page.read_text()
                    # Check if original file is mentioned in the landing page content
                    if orig_stem in content:
                        original_to_landing[original_file] = landing_page
                        print(f"- Original '{orig_stem}' matched to landing page '{landing_page.name}'")
                        break
                except Exception as e:
                    print(f"Error reading landing page {landing_page}: {e}")
        
        # List markdown files from subdirectories using os.walk
        markdown_files = []
        print("\n=== Markdown Files from Subdirectories ===")
        for root, dirs, files in os.walk(MARKDOWN_DIR):
            # Skip the top-level MARKDOWN_DIR itself
            if Path(root) == MARKDOWN_DIR:
                continue
            for file in files:
                if file.lower().endswith(".md"):
                    full_path = os.path.join(root, file)
                    markdown_files.append(full_path)
                    print(f"  - {os.path.basename(root)} : {file}")
        print(f"\nTotal markdown files found: {len(markdown_files)}")
        
        if not markdown_files:
            print("No markdown files found in subdirectories.")
            return

        print("\n=== Matching Results ===")
        updated_count = 0
        
        # For each markdown file, find the best matching original file
        for md_file in markdown_files:
            md_dir_name = os.path.basename(os.path.dirname(md_file))
            md_name = os.path.splitext(os.path.basename(md_file))[0]
            print(f"\nMatching for markdown file: '{md_dir_name}/{md_name}.md'")
            
            # Build a list of original file stems for fuzzy matching
            original_stems = [os.path.splitext(os.path.basename(orig))[0] for orig in original_files]
            
            # Get top 3 matches using token_sort_ratio
            matches = process.extract(
                md_dir_name,  # Match on directory name instead of file name
                original_stems,
                scorer=fuzz.token_sort_ratio,
                limit=3
            )
            
            print("Top matches:")
            for match_name, score, index in matches:
                matched_file = original_files[index]
                print(f"  Score {score:>3}: '{match_name}' -> {os.path.basename(matched_file)}")
            
            # Select best match if score is high enough
            if matches and matches[0][1] >= 60:  # Using 60 as threshold
                best_match_name, best_score, best_index = matches[0]
                best_match_file = original_files[best_index]
                print(f"✓ Best match: '{os.path.basename(best_match_file)}' with score {best_score}")
                
                # Find the landing page associated with this original file
                landing_page = original_to_landing.get(best_match_file)
                
                if landing_page:
                    # Update the landing page with a link to the markdown
                    try:
                        content = landing_page.read_text()
                        
                        # Create the markdown link - link directly to the specific markdown file
                        md_rel_path = Path(md_file).relative_to(self.config.VAULT_DIR)
                        markdown_link = f"- [[{md_rel_path}|Markdown Version]]"
                        print(f"Adding link: {markdown_link}")
                        
                        # Check if any markdown link already exists
                        index_link_pattern = re.compile(r'\[\[.*?/index\|Markdown Version\]\]')
                        has_index_link = index_link_pattern.search(content) is not None
                        
                        directory_link_pattern = re.compile(r'\[\[.*?\|Markdown Directory\]\]')
                        has_directory_link = directory_link_pattern.search(content) is not None
                        
                        any_markdown_link_pattern = re.compile(r'\[\[.*?\|Markdown.*?\]\]')
                        has_any_markdown_link = any_markdown_link_pattern.search(content) is not None
                        
                        if not has_any_markdown_link:
                            # No markdown link exists, add new one
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
                                print(f"Updated {landing_page.name} with link to {md_file}")
                            else:
                                print(f"No 'Document Versions' section found in {landing_page.name}")
                        elif has_index_link or has_directory_link:
                            # Replace old style links with direct file link
                            if has_index_link:
                                updated_content = index_link_pattern.sub(markdown_link, content)
                                print(f"Replacing index link with direct file link")
                            else:
                                updated_content = directory_link_pattern.sub(markdown_link, content)
                                print(f"Replacing directory link with direct file link")
                                
                            landing_page.write_text(updated_content)
                            updated_count += 1
                            print(f"Updated {landing_page.name} by replacing old link with direct file link")
                        else:
                            print(f"Markdown link already exists in {landing_page.name}")
                    except Exception as e:
                        print(f"Error updating landing page: {e}")
                else:
                    print(f"No landing page found for original file: {os.path.basename(best_match_file)}")
            else:
                print(f"✗ No good match found for markdown directory: {md_dir_name}")
        
        print(f"Matched and updated {updated_count} landing pages with markdown files.")
