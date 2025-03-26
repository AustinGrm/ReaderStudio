#!/usr/bin/env python3
import os
import subprocess
import re
import datetime
from pathlib import Path
from difflib import SequenceMatcher

# Set your Obsidian vault's book directory
VAULT_DIR = "/Users/austinavent/Library/CloudStorage/Dropbox/Areas/orbit/90.00_meta_resources/90.01_Books"
BOOKS_DIR = os.path.join(VAULT_DIR, "Books")
ANNOTATION_DIR = os.path.join(VAULT_DIR, "Books/Annotations")
INDEX_FILE = os.path.join(BOOKS_DIR, "Book Index.md")
MARKDOWN_DIR = os.path.join(VAULT_DIR, "Books/Markdown")
ORIGINALS_DIR = os.path.join(BOOKS_DIR, "Originals")

# Ensure the Books and Annotations directories exist
os.makedirs(BOOKS_DIR, exist_ok=True)
os.makedirs(ANNOTATION_DIR, exist_ok=True)
os.makedirs(ORIGINALS_DIR, exist_ok=True)
os.makedirs(MARKDOWN_DIR, exist_ok=True)

def sanitize_string(text):
    """Sanitize string to remove problematic characters for YAML and filenames."""
    if text and isinstance(text, str):
        # Remove null bytes
        text = text.replace('\0', '')
        # Remove square brackets and parentheses
        text = re.sub(r'[\[\]\(\)]', '', text)
        # Replace problematic characters with hyphens
        text = re.sub(r'[:\/:*?"<>|]', '-', text)
        # Remove any non-ASCII characters
        text = ''.join(char for char in text if ord(char) < 128)
        # Remove multiple hyphens
        text = re.sub(r'-+', '-', text)
        # Remove leading/trailing hyphens and whitespace
        text = text.strip('- ')
        return text
    return text

def extract_calibre_metadata(file_path):
    """Extract metadata using Calibre's ebook-meta tool."""
    try:
        # Run Calibre's ebook-meta command with a timeout
        result = subprocess.run(
            ["ebook-meta", file_path], 
            capture_output=True, 
            text=True,
            timeout=30  # Add timeout to prevent hanging
        )
        
        # Parse the output
        output = result.stdout.strip()

        metadata = {"path": os.path.join("Books/Originals", Path(file_path).name)}  # Path in Originals directory
        
        # Extract all fields from Calibre
        fields_to_extract = {
            "Title": "title",
            "Title sort": "title_sort",
            "Author(s)": "author",
            "Author sort": "author_sort",
            "Publisher": "publisher",
            "Published": "published",
            "Tags": "tags",
            "Series": "series",
            "Series index": "series_index",
            "Rating": "rating",
            "Identifiers": "identifiers",
            "Languages": "language",
            "Comments": "description"
        }
        
        for calibre_field, yaml_field in fields_to_extract.items():
            pattern = rf'{calibre_field}\s+:\s*(.*)'
            match = re.search(pattern, output)
            if match and match.group(1).strip():
                # Sanitize metadata values
                metadata[yaml_field] = sanitize_string(match.group(1).strip())
        
        # Add file format
        metadata["format"] = Path(file_path).suffix[1:].upper()
        
        # Use filename as title if no title was found
        if "title" not in metadata or not metadata["title"].strip():
            metadata["title"] = sanitize_string(Path(file_path).stem)
        
        # If author is still missing, try to extract from filename or set to Unknown
        if "author" not in metadata:
            # Try to extract author from filename if it follows "Author - Title" pattern
            filename = Path(file_path).stem
            author_match = re.match(r'^(.*?)\s*-\s*', filename)
            if author_match:
                metadata["author"] = author_match.group(1).strip()
            else:
                metadata["author"] = "Unknown Author"
        
        # Add current date for last_opened
        metadata["last_opened"] = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Add default status
        metadata["status"] = "new"
        
        # Add reading_progress
        metadata["reading_progress"] = 0
            
        return metadata
        
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        # Return basic metadata without failing
        return {
            "path": os.path.relpath(file_path, start=VAULT_DIR),  # Relative path
            "format": Path(file_path).suffix[1:].upper(),
            "title": sanitize_string(Path(file_path).stem),  # Ensure title is always set and sanitized
            "author": "Unknown Author",  # Default author
            "last_opened": datetime.datetime.now().strftime("%Y-%m-%d"),
            "status": "new",
            "reading_progress": 0
        }

def update_existing_metadata(file_path, new_metadata):
    """Update metadata while preserving user-edited values like progress."""
    if not os.path.exists(file_path):
        return new_metadata
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            
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
    except Exception:
        return new_metadata

def create_annotation_document(metadata, safe_title):
    """Create an annotation document with annotation-target set."""
    annotation_filename = f"{safe_title} - Annotations.md"
    annotation_file_path = os.path.join(ANNOTATION_DIR, annotation_filename)
    
    # Create the relative path for the parent document
    parent_doc_path = os.path.join("Books", f"{safe_title}.md")
    
    # Build YAML frontmatter
    yaml_lines = ["---"]
    yaml_lines.append(f"title: \"{metadata['title']} - Annotations\"")
    if "author" in metadata:
        yaml_lines.append(f"author: \"{metadata['author']}\"")
    yaml_lines.append(f"annotation-target: {metadata['path']}")
    yaml_lines.append(f"parent_document: {parent_doc_path}")
    yaml_lines.append("---")
    
    yaml_frontmatter = "\n".join(yaml_lines)
    
    # Basic document structure
    annotation_content = f"{yaml_frontmatter}\n\n# {metadata.get('title')} - Annotations\n\n"
    annotation_content += "This document is for annotating the original file using the Obsidian Annotator plugin.\n"
    
    # Check if file already exists, if so, preserve its content
    if os.path.exists(annotation_file_path):
        with open(annotation_file_path, 'r') as f:
            existing_content = f.read()
        
        # Find the end of frontmatter and preserve everything after it
        frontmatter_end = existing_content.find("---\n\n")
        if frontmatter_end > 0:
            post_frontmatter = existing_content[frontmatter_end + 5:]
            annotation_content = f"{yaml_frontmatter}\n\n{post_frontmatter}"
    
    with open(annotation_file_path, "w") as f:
        f.write(annotation_content)
    
    print(f"Created/updated annotation document for: {safe_title}")
    
    # Return the relative path to the annotation document
    return os.path.join("Books/Annotations", f"{safe_title} - Annotations.md")

def create_markdown(metadata):
    """Generate an Obsidian-friendly markdown file with specified YAML frontmatter."""
    # Clean title for safe filenames
    safe_title = re.sub(r'[:\/:*?"<>|]', '-', metadata["title"])
    md_file_path = os.path.join(BOOKS_DIR, f"{safe_title}.md")
    
    # Check if the file already exists and preserve user-edited values
    if os.path.exists(md_file_path):
        metadata = update_existing_metadata(md_file_path, metadata)
    
    # Create annotation document first and get its path
    annotation_doc_path = create_annotation_document(metadata, safe_title)
    
    # Build YAML frontmatter with all metadata
    yaml_lines = ["---"]
    
    # Add all metadata fields
    for key, value in metadata.items():
        if key != "tags" and value:  # Handle tags separately
            yaml_lines.append(f"{key}: \"{value}\"")
    
    # Handle tags specially
    if "tags" in metadata and metadata["tags"]:
        tags = metadata["tags"].split(",")
        yaml_lines.append("tags:")
        for tag in tags:
            yaml_lines.append(f"  - {tag.strip()}")
    
    # Always add "book" tag
    if "tags" not in metadata or not metadata["tags"]:
        yaml_lines.append("tags:")
        yaml_lines.append("  - book")
    
    yaml_lines.append("---")
    
    yaml_frontmatter = "\n".join(yaml_lines)

    # Check for markdown and annotated versions
    markdown_filename = f"{safe_title}.md"
    markdown_path = os.path.join(MARKDOWN_DIR, markdown_filename)
    
    annotated_dir = os.path.join(VAULT_DIR, "Books/Annotated")
    annotated_path = os.path.join(annotated_dir, f"{safe_title}.md")

    # Store original filename in metadata for future matching
    metadata["original_filename"] = metadata["title"]
    
    # Main document structure
    markdown_content = [
        yaml_frontmatter,
        f"\n# {metadata.get('title')}",
        "\n## Document Versions",
        f"- [[{metadata['path']}|Original ({metadata.get('format')})]]",
        f"- [[{annotation_doc_path}|Annotations]]",
    ]
    
    # Add placeholders for markdown versions if they exist
    if os.path.exists(markdown_path):
        rel_path = os.path.relpath(markdown_path, start=VAULT_DIR)
        markdown_content.append(f"- [[{rel_path}|Markdown Version]]")
    
    if os.path.exists(annotated_path):
        rel_path = os.path.relpath(annotated_path, start=VAULT_DIR)
        markdown_content.append(f"- [[{rel_path}|Annotated Markdown]]")
    
    # Continue with the rest of the document
    markdown_content.extend([
        "\n## Reading Status",
        f"- **Status**: {metadata.get('status', 'New')}",
        f"- **Last opened**: {metadata.get('last_opened', '')}",
        f"- **Progress**: {int(float(metadata.get('reading_progress', 0)) * 100)}%",
        "\n### Progress Bar",
        create_progress_bar(metadata.get('reading_progress', 0)),
        "\n## Notes & Highlights",
        "\n### Key Concepts",
        "- ",
        "\n### Important Quotes",
        "- ",
        "\n### Questions & Reflections",
        "- "
    ])

    # Check if file already exists
    if os.path.exists(md_file_path):
        with open(md_file_path, 'r') as f:
            existing_content = f.read()
        
        # Find existing sections to preserve user content
        notes_section = re.search(r'## Notes & Highlights(.*?)(?=\n## |$)', existing_content, re.DOTALL)
        if notes_section:
            # Replace the placeholder with existing content
            notes_index = markdown_content.index("\n## Notes & Highlights")
            markdown_content = markdown_content[:notes_index]
            markdown_content.append("\n## Notes & Highlights" + notes_section.group(1))
    
    with open(md_file_path, "w") as f:
        f.write("\n".join(markdown_content))
    
    print(f"Created/updated metadata for: {safe_title}")
    return safe_title, metadata

def create_progress_bar(progress_value):
    """Create a simple ASCII progress bar."""
    try:
        progress = float(progress_value)
    except (ValueError, TypeError):
        progress = 0
    
    progress = min(max(progress, 0), 1)  # Ensure between 0 and 1
    
    # Create a 20-character progress bar
    filled = int(progress * 20)
    empty = 20 - filled
    
    return f"`[{'█' * filled}{'░' * empty}]` {int(progress * 100)}%"

def create_index(book_entries):
    """Create a master index file with links to all books."""
    if not book_entries:
        return
        
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
    sorted_by_title = sorted(book_entries, key=lambda x: x[0].lower())
    for title, metadata in sorted_by_title:
        author = metadata.get("author", "Unknown Author")
        format = metadata.get("format", "")
        file_path = os.path.join("Books", f"{title}.md")
        # Create a link to the book document using Obsidian wiki-link syntax
        index_content.append(f"- [[{file_path}|{title} - {author} ({format})]]")
    
    # Group by author if author info exists
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
                format = metadata.get("format", "")
                file_path = os.path.join("Books", f"{title}.md")
                index_content.append(f"- [[{file_path}|{title} ({format})]]")
            index_content.append("")  # Add a blank line between authors
    
    # Write the index file
    with open(INDEX_FILE, "w") as f:
        f.write("\n".join(index_content))
    
    print(f"Created master index at: {INDEX_FILE}")

def match_landing_pages_with_markdown():
    """Match existing landing pages with markdown files using fuzzy matching."""
    print("\nMatching landing pages with markdown files...")
    
    # Get all landing pages in the Books directory
    landing_pages = []
    for file in os.listdir(BOOKS_DIR):
        if file.endswith(".md") and not os.path.isdir(os.path.join(BOOKS_DIR, file)):
            landing_pages.append(file)
    
    # Get all markdown files in the Markdown directory
    markdown_files = []
    if os.path.exists(MARKDOWN_DIR):
        for file in os.listdir(MARKDOWN_DIR):
            if file.endswith(".md"):
                markdown_files.append(file)
    
    if not markdown_files:
        print("No markdown files found in the Markdown directory.")
        return
    
    # Dictionary to store matches
    matches = {}
    updated_count = 0
    
    print(f"Found {len(landing_pages)} landing pages and {len(markdown_files)} markdown files.")
    
    # For each landing page, find the best matching markdown file
    for landing_page in landing_pages:
        # Extract title from landing page name
        landing_title = landing_page[:-3]  # Remove .md extension
        
        # Check if we can find the original title in the YAML frontmatter
        original_title = None
        with open(os.path.join(BOOKS_DIR, landing_page), 'r') as f:
            content = f.read()
            yaml_match = re.search(r'---\n(.*?)\n---', content, re.DOTALL)
            if yaml_match:
                yaml_content = yaml_match.group(1)
                title_match = re.search(r'title:\s*"([^"]*)"', yaml_content)
                if title_match:
                    original_title = title_match.group(1)
        
        best_match = None
        best_score = 0
        
        for markdown_file in markdown_files:
            # Extract title from markdown file name
            markdown_title = markdown_file[:-3]  # Remove .md extension
            
            # Calculate similarity score
            similarity = SequenceMatcher(None, landing_title.lower(), markdown_title.lower()).ratio()
            
            # If we have the original title, also compare with that
            if original_title:
                original_similarity = SequenceMatcher(None, original_title.lower(), markdown_title.lower()).ratio()
                similarity = max(similarity, original_similarity)
            
            # Additional matching criteria - check if all words in markdown_title exist in landing_title
            landing_words = set(re.findall(r'\w+', landing_title.lower()))
            markdown_words = set(re.findall(r'\w+', markdown_title.lower()))
            
            # If all important words from markdown title exist in landing title, boost similarity
            word_overlap = len(markdown_words.intersection(landing_words)) / len(markdown_words) if markdown_words else 0
            
            # Combined score with more weight on word overlap
            combined_score = (similarity * 0.4) + (word_overlap * 0.6)
            
            if combined_score > best_score and combined_score > 0.7:  # Threshold for a good match
                best_score = combined_score
                best_match = markdown_file
        
        if best_match:
            matches[landing_page] = (best_match, best_score)
            
            # Update the landing page with a link to the markdown file
            landing_page_path = os.path.join(BOOKS_DIR, landing_page)
            
            with open(landing_page_path, 'r') as f:
                content = f.read()
            
            # Check if markdown link already exists
            rel_path = os.path.relpath(os.path.join(MARKDOWN_DIR, best_match), start=VAULT_DIR)
            markdown_link = f"- [[{rel_path}|Markdown Version]]"
            
            if markdown_link not in content:
                # Find the "Document Versions" section
                doc_versions_match = re.search(r'## Document Versions(.*?)(?=\n## |$)', content, re.DOTALL)
                
                if doc_versions_match:
                    doc_versions = doc_versions_match.group(1)
                    updated_doc_versions = doc_versions + f"\n{markdown_link}"
                    
                    # Replace the old section with the updated one
                    updated_content = content.replace(
                        f"## Document Versions{doc_versions}", 
                        f"## Document Versions{updated_doc_versions}"
                    )
                    
                    with open(landing_page_path, 'w') as f:
                        f.write(updated_content)
                    
                    updated_count += 1
                    print(f"Updated {landing_page} with link to {best_match} (score: {best_score:.2f})")
    
    print(f"\nMatched and updated {updated_count} landing pages with markdown files.")
    
    # Report unmatched files
    unmatched_landing_pages = set(landing_pages) - set(matches.keys())
    if unmatched_landing_pages:
        print(f"\nWarning: {len(unmatched_landing_pages)} landing pages have no matching markdown file:")
        for page in sorted(unmatched_landing_pages):
            print(f"- {page}")
    
    # Also report unmatched markdown files
    matched_markdown_files = set(match[0] for match in matches.values())
    unmatched_markdown_files = set(markdown_files) - matched_markdown_files
    if unmatched_markdown_files:
        print(f"\nWarning: {len(unmatched_markdown_files)} markdown files have no matching landing page:")
        for file in sorted(unmatched_markdown_files):
            print(f"- {file}")

def update_metadata():
    """Scan the directory and update markdown files using Calibre."""
    book_files = []
    unprocessed_files = []
    
    # First, check if files are already in Originals directory
    for file in os.listdir(ORIGINALS_DIR):
        if file.lower().endswith((".pdf", ".epub", ".mobi")):
            book_files.append(os.path.join(ORIGINALS_DIR, file))
    
    # Then look for any files that haven't been moved yet
    for root, _, files in os.walk(VAULT_DIR):
        if any(skip_dir in root for skip_dir in ["Books/Annotations", "Books/Markdowns", "Books/Annotated", "Books/Originals"]):
            continue
            
        for file in files:
            file_path = os.path.join(root, file)
            file_lower = file.lower()
            
            if file_lower.endswith((".pdf", ".epub", ".mobi")):
                # Move file to Originals directory
                new_path = os.path.join(ORIGINALS_DIR, file)
                try:
                    os.rename(file_path, new_path)
                    book_files.append(new_path)
                    print(f"Moved {file} to Originals directory")
                except Exception as e:
                    print(f"Error moving {file}: {e}")
                    book_files.append(file_path)  # Process in original location
            elif file_lower.endswith((".txt", ".doc", ".docx", ".rtf")):
                unprocessed_files.append(file_path)
    
    if unprocessed_files:
        print("\nFiles that need manual processing:")
        for file in unprocessed_files:
            print(f"- {file}")
    
    print(f"\nFound {len(book_files)} book files to process")
    
    book_entries = []
    for file_path in book_files:
        print(f"Processing: {file_path}")
        metadata = extract_calibre_metadata(file_path)
        title, metadata = create_markdown(metadata)
        book_entries.append((title, metadata))
    
    # Create the master index file
    create_index(book_entries)
    
    # Match landing pages with markdown files
    match_landing_pages_with_markdown()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Process book files for Obsidian vault')
    parser.add_argument('--match-only', action='store_true', help='Only match existing landing pages with markdown files')
    
    args = parser.parse_args()
    
    if args.match_only:
        match_landing_pages_with_markdown()
    else:
        update_metadata()