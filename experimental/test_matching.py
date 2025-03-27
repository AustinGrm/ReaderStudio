#!/usr/bin/env python3
from pathlib import Path
from rapidfuzz import fuzz, process
import pdb
def test_matching():
    # Paths
    BOOKS_DIR = Path("/Users/austinavent/Documents/VAULTTEST/TESTING/Books")
    ORIGINALS_DIR = BOOKS_DIR / "Originals"
    MARKDOWN_DIR = BOOKS_DIR / "Markdowns"

    print("\n=== Book Files ===")
    book_files = list(ORIGINALS_DIR.glob("*"))
    print(f"Found {len(book_files)} books:")
    for book in book_files:
        print(f"  - {book.stem}")

    print("\n=== Markdown Files ===")
    # Find all .md files within markdown directories
    markdown_files = []
    print("Contents of MARKDOWN_DIR:")
    for item in MARKDOWN_DIR.iterdir():
        print(f"  - {item.name}")
        print(f"    Is directory: {item.is_dir()}")
        print(f"    Is file: {item.is_file()}")
        if item.is_dir():
            print("    Contents:")
            for subitem in item.iterdir():
                print(f"      - {subitem.name} (file: {subitem.is_file()})")

    print(f"\nFound {len(markdown_files)} total markdown files")

    print("\n=== Matching Results ===")
    for book in book_files:
        book_name = book.stem
        print(f"\nTrying to match: '{book_name}'")
        
        # Get top 3 matches for each book
        matches = process.extract(
            book_name,
            [(md_file, md_file.parent.name) for md_file in markdown_files],
            scorer=lambda x, y: fuzz.token_sort_ratio(x, y[1]),  # Compare with directory name
            limit=3
        )
        
        print("Top matches:")
        for (md_file, dir_name), score, _ in matches:
            print(f"  Score {score:>3}: '{dir_name}' -> {md_file.name}")
            
            # Show why they matched/didn't match
            print("  Word comparison:")
            book_words = set(book_name.lower().split())
            dir_words = set(dir_name.lower().split())
            print(f"    Book words:    {book_words}")
            print(f"    Match words:   {dir_words}")
            print(f"    Common words:  {book_words & dir_words}")

        # Select best match if score is high enough
        if matches and matches[0][1] >= 85:  # 85% match threshold
            (best_match_file, dir_name), score, _ = matches[0]
            print(f"\n  ✓ Best match found:")
            print(f"    Directory: '{dir_name}'")
            print(f"    File: '{best_match_file.name}'")
            print(f"    Score: {score}")
        else:
            print(f"\n  ✗ No good match found")

if __name__ == "__main__":
    test_matching()