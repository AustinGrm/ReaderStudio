#!/usr/bin/env python3
from config.default_config import Config
import os
from pathlib import Path

def check_dirs():
    print(f"BOOKS_DIR: {Config.BOOKS_DIR}")
    print(f"BOOKS_DIR exists: {Config.BOOKS_DIR.exists()}")
    
    print(f"\nMARKDOWN_DIR: {Config.MARKDOWN_DIR}")
    print(f"MARKDOWN_DIR exists: {Config.MARKDOWN_DIR.exists()}")
    
    print("\nLanding pages:")
    landing_pages = list(Config.BOOKS_DIR.glob("*.md"))
    for page in landing_pages:
        print(f"  - {page.name}")
    
    print("\nMarkdown files in subdirectories:")
    markdown_count = 0
    for root, dirs, files in os.walk(Config.MARKDOWN_DIR):
        # Skip the top-level directory
        if Path(root) == Config.MARKDOWN_DIR:
            continue
        
        md_files = [f for f in files if f.lower().endswith('.md')]
        if md_files:
            print(f"  - Dir: {os.path.basename(root)}")
            for md_file in md_files:
                print(f"    - {md_file}")
                markdown_count += 1
    
    print(f"\nTotal markdown files found: {markdown_count}")

if __name__ == "__main__":
    check_dirs() 