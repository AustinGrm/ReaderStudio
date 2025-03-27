#!/usr/bin/env python3
import os
import re
import shutil
from pathlib import Path

def fix_markdown_directory_structure():
    """
    Fix the markdown directory structure by moving files up one level
    and updating links in landing pages.
    """
    # Define paths
    VAULT_DIR = Path("/Users/austinavent/Documents/VAULTTEST/TESTING")
    BOOKS_DIR = VAULT_DIR / "Books"
    MARKDOWN_DIR = BOOKS_DIR / "Markdowns"
    
    print(f"Fixing markdown directory structure...")
    print(f"Markdown directory: {MARKDOWN_DIR}")
    
    # Process each top-level markdown directory
    for main_dir in MARKDOWN_DIR.glob("*"):
        if not main_dir.is_dir():
            continue
            
        print(f"\nProcessing directory: {main_dir.name}")
        nested_dirs = list(main_dir.glob("*"))
        nested_dirs = [d for d in nested_dirs if d.is_dir()]
        
        if not nested_dirs:
            print(f"  No nested directories found, skipping")
            continue
            
        for nested_dir in nested_dirs:
            print(f"  Found nested directory: {nested_dir.name}")
            
            # Get all files in the nested directory
            files = list(nested_dir.glob("*"))
            for file in files:
                # Skip directories
                if file.is_dir():
                    continue
                    
                # Define target path (one level up)
                target_path = main_dir / file.name
                
                # Move the file
                print(f"    Moving {file.name} to {target_path}")
                try:
                    # Copy instead of move as a safer operation
                    shutil.copy2(file, target_path)
                except Exception as e:
                    print(f"    Error copying file: {e}")
            
            # Force delete the nested directory and its contents
            print(f"    Removing nested directory: {nested_dir}")
            try:
                # Use os.system to force remove on Unix-like systems
                if os.name == 'posix':  # Unix/Linux/MacOS
                    os.system(f"rm -rf '{nested_dir}'")
                else:
                    # On Windows, use shutil.rmtree with ignore_errors=True
                    shutil.rmtree(nested_dir, ignore_errors=True)
                print(f"    Successfully removed: {nested_dir}")
            except Exception as e:
                print(f"    Error removing directory: {e}")
    
    # Create index.md files if they don't exist
    for main_dir in MARKDOWN_DIR.glob("*"):
        if not main_dir.is_dir():
            continue
            
        index_file = main_dir / "index.md"
        if not index_file.exists():
            print(f"Creating index.md in {main_dir.name}")
            # Find the main markdown file
            md_files = list(main_dir.glob("*.md"))
            if md_files:
                # Use the first markdown file as index
                source_md = md_files[0]
                shutil.copy2(source_md, index_file)
                print(f"  Copied {source_md.name} to index.md")
            else:
                # Create a simple index file
                with open(index_file, 'w') as f:
                    f.write(f"# {main_dir.name}\n\n")
                print(f"  Created empty index.md")
    
    # Update links in landing pages
    landing_pages = list(BOOKS_DIR.glob("*.md"))
    updated_count = 0
    
    print("\nUpdating links in landing pages...")
    for landing_page in landing_pages:
        try:
            content = landing_page.read_text()
            
            # Look for markdown links with nested structure
            nested_link_pattern = r'\[\[(Books/Markdowns/[^/]+/[^/]+)(?:/index)?\|Markdown Version\]\]'
            
            # Replace with flattened structure
            def flatten_link(match):
                path = match.group(1)
                # Extract the main directory path
                main_dir = '/'.join(path.split('/')[:3])  # Take first 3 parts: Books/Markdowns/DirName
                return f"[[{main_dir}/index|Markdown Version]]"
            
            new_content = re.sub(nested_link_pattern, flatten_link, content)
            
            # Save changes if content was modified
            if new_content != content:
                landing_page.write_text(new_content)
                updated_count += 1
                print(f"  Updated links in: {landing_page.name}")
        except Exception as e:
            print(f"  Error updating landing page {landing_page}: {e}")
    
    print(f"\nDone! Updated {updated_count} landing pages.")

if __name__ == "__main__":
    fix_markdown_directory_structure() 