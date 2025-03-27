#!/usr/bin/env python3
from pathlib import Path
from rapidfuzz import fuzz, process

def test_matching():
    # Update paths to match your structure
    VAULT_DIR = Path("/Users/austinavent/Documents/VAULTTEST/TESTING")
    BOOKS_DIR = VAULT_DIR / "Books"
    ORIGINALS_DIR = BOOKS_DIR / "Originals"
    MARKDOWN_DIR = BOOKS_DIR / "Markdown"  # Changed from "Markdowns" to "Markdown"

    # Debug paths
    print("\n=== Checking Paths ===")
    print(f"VAULT_DIR: {VAULT_DIR}")
    print(f"BOOKS_DIR: {BOOKS_DIR}")
    print(f"ORIGINALS_DIR: {ORIGINALS_DIR}")
    print(f"MARKDOWN_DIR: {MARKDOWN_DIR}")
    
    # Verify directories exist
    print("\n=== Checking Directories ===")
    print(f"VAULT_DIR exists: {VAULT_DIR.exists()}")
    print(f"BOOKS_DIR exists: {BOOKS_DIR.exists()}")
    print(f"ORIGINALS_DIR exists: {ORIGINALS_DIR.exists()}")
    print(f"MARKDOWN_DIR exists: {MARKDOWN_DIR.exists()}")

    print("\n=== Book Files ===")
    book_files = list(ORIGINALS_DIR.glob("*"))
    print(f"Found {len(book_files)} books:")
    for book in book_files:
        print(f"  - {book.stem}")

    print("\n=== Markdown Directories ===")
    markdown_dirs = [d for d in MARKDOWN_DIR.glob("*") if d.is_dir()]
    print(f"Found {len(markdown_dirs)} markdown directories:")
    for md_dir in markdown_dirs:
        print(f"  - {md_dir.name}")

    if not markdown_dirs:
        print("No markdown directories found! Check the path and directory structure.")
        return

    print("\n=== Matching Results ===")
    for book in book_files:
        book_name = book.stem
        print(f"\nTrying to match: '{book_name}'")
        
        matches = process.extract(
            book_name,
            [d.name for d in markdown_dirs],
            scorer=fuzz.token_sort_ratio,
            limit=3
        )
        
        print("Top matches:")
        for match_name, score, _ in matches:
            print(f"  Score {score:>3}: '{match_name}'")

if __name__ == "__main__":
    test_matching() 