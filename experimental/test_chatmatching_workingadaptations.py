#!/usr/bin/env python3
import os
from rapidfuzz import fuzz, process

def test_matching():
    # Define paths
    BOOKS_DIR = "/Users/austinavent/Documents/VAULTTEST/TESTING/Books"
    ORIGINALS_DIR = os.path.join(BOOKS_DIR, "Originals")
    MARKDOWN_DIR = os.path.join(BOOKS_DIR, "Markdowns")

    # List all original files using os.walk
    original_files = []
    for root, dirs, files in os.walk(ORIGINALS_DIR):
        for file in files:
            # Append full path of the file
            original_files.append(os.path.join(root, file))
    print("\n=== Original Files ===")
    print(f"Found {len(original_files)} original files:")
    for orig in original_files:
        print(f"  - {os.path.splitext(os.path.basename(orig))[0]}")

    # List markdown files from subdirectories using os.walk
    markdown_files = []
    print("\n=== Markdown Files from Subdirectories ===")
    for root, dirs, files in os.walk(MARKDOWN_DIR):
        # Skip the top-level MARKDOWN_DIR itself
        if os.path.abspath(root) == os.path.abspath(MARKDOWN_DIR):
            continue
        for file in files:
            if file.lower().endswith(".md"):
                full_path = os.path.join(root, file)
                markdown_files.append(full_path)
                print(f"  - {os.path.basename(root)} : {file}")
    print(f"\nTotal markdown files found: {len(markdown_files)}")

    print("\n=== Matching Results ===")
    # For each markdown file, find the best matching original file
    for md_file in markdown_files:
        md_name = os.path.splitext(os.path.basename(md_file))[0]
        print(f"\nMatching for markdown file: '{md_name}' (from directory '{os.path.basename(os.path.dirname(md_file))}')")

        # Build a list of original file stems for fuzzy matching
        original_stems = [os.path.splitext(os.path.basename(orig))[0] for orig in original_files]
        
        # Get top 3 matches using token_sort_ratio
        matches = process.extract(
            md_name,
            original_stems,
            scorer=fuzz.token_sort_ratio,
            limit=3
        )
        
        print("Top matches:")
        for match_name, score, index in matches:
            matched_file = original_files[index]
            print(f"  Score {score:>3}: '{match_name}' -> {os.path.basename(matched_file)}")
        
        # Select best match (assuming each markdown file has a corresponding original)
        if matches:
            best_match_name, best_score, best_index = matches[0]
            best_match_file = original_files[best_index]
            print(f"✓ Best match: '{os.path.basename(best_match_file)}' with score {best_score}")
        else:
            print("✗ No match found for this markdown file")

if __name__ == "__main__":
    test_matching()