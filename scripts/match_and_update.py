#!/usr/bin/env python3
import os
from pathlib import Path
from rapidfuzz import fuzz, process

def find_matches(books_dir: Path, threshold: int = 85):
    """
    Match markdown files (from subdirectories) with original book files using fuzzy matching.
    
    Uses os.walk to search through the directories so that nested files are found.
    """
    originals_dir = books_dir / "Originals"
    markdown_dir = books_dir / "Markdowns"
    matches_found = {}

    # Get all original files (pdf, epub, mobi) using os.walk
    original_files = []
    for root, dirs, files in os.walk(originals_dir):
        for file in files:
            if file.lower().endswith(('.pdf', '.epub', '.mobi')):
                original_files.append(Path(root) / file)
    if not original_files:
        print("No original files found.")
    
    # Get all markdown files from subdirectories (skip the top-level MARKDOWN_DIR if needed)
    markdown_files = []
    for root, dirs, files in os.walk(markdown_dir):
        # Optionally skip the top-level markdown folder if you expect files only in subdirectories:
        if Path(root) == markdown_dir:
            continue
        for file in files:
            if file.lower().endswith('.md'):
                markdown_files.append(Path(root) / file)
    if not markdown_files:
        print("No markdown files found.")
    import pdb; pdb.set_trace()
    # For each markdown file, use its stem to fuzzy-match against original file stems
    for md_file in markdown_files:
        md_name = md_file.stem
        original_stems = [orig.stem for orig in original_files]
        
        # Get top 3 matches using token_sort_ratio
        matches = process.extract(
            md_name,
            original_stems,
            scorer=fuzz.token_sort_ratio,
            limit=3
        )
        
        # If the best match exceeds the threshold, accept it
        if matches and matches[0][1] >= threshold:
            best_match_index = matches[0][2]
            best_match_file = original_files[best_match_index]
            matches_found[best_match_file] = md_file
        else:
            print(f"No good match for markdown: {md_file}")
    
    return matches_found

def update_landing_page(landing_page_path: Path, books_dir: Path, matches: dict):
    """
    Update the landing page with markdown links for each matching book.
    
    The markdown links are calculated relative to the books directory.
    """
    if not landing_page_path.exists():
        print(f"Warning: Landing page {landing_page_path} not found")
        return
    
    content = landing_page_path.read_text()
    
    # For each match, create a markdown link and insert it under "## Available Books"
    for book_path, markdown_path in matches.items():
        book_name = book_path.stem
        try:
            # Calculate relative path from the books directory (adjust as needed)
            relative_markdown_path = markdown_path.relative_to(books_dir)
        except ValueError:
            relative_markdown_path = markdown_path  # fallback to absolute if needed
        
        markdown_link = f"- [{book_name}]({relative_markdown_path})"
        
        if "## Available Books" in content:
            # Append the link right after the section header
            content = content.replace("## Available Books", f"## Available Books\n{markdown_link}")
        else:
            # Add a new section if not present
            content += f"\n\n## Available Books\n{markdown_link}"
    
    landing_page_path.write_text(content)
    print(f"Landing page updated at: {landing_page_path}")

def main():
    # Update these paths to match your project structure
    books_dir = Path("/path/to/your/Books")   # e.g. /Users/austinavent/Documents/VAULTTEST/TESTING/Books
    landing_page = books_dir / "landing.md"     # Adjust this path as needed
    
    matches = find_matches(books_dir)
    
    if matches:
        print("Matches found:")
        for orig, md in matches.items():
            print(f"  Original: {orig}  <--> Markdown: {md}")
    else:
        print("No matches found.")
    
    update_landing_page(landing_page, books_dir, matches)

if __name__ == "__main__":
    main()