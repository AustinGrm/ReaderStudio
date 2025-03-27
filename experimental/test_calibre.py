#!/usr/bin/env python3
import subprocess
from pathlib import Path
import re
import datetime

def extract_calibre_metadata(file_path):
    """Extract metadata using Calibre's ebook-meta tool."""
    print(f"\nTrying to extract metadata from: {file_path}")
    try:
        # Check if file exists
        if not file_path.exists():
            print(f"File does not exist: {file_path}")
            return None
            
        print("Running ebook-meta command...")
        # Run Calibre's ebook-meta command with a timeout
        result = subprocess.run(
            ["ebook-meta", str(file_path)], 
            capture_output=True, 
            text=True,
            timeout=30
        )
        
        print(f"Command return code: {result.returncode}")
        if result.stderr:
            print(f"Command error output: {result.stderr}")
        
        # Print raw output
        print("\nRaw Calibre Output:")
        print(result.stdout.strip())
        
        # Parse the output
        metadata = {"path": str(file_path)}
        
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
            match = re.search(pattern, result.stdout)
            if match and match.group(1).strip():
                metadata[yaml_field] = match.group(1).strip()
        
        # Add file format
        metadata["format"] = Path(file_path).suffix[1:].upper()
        
        # Use filename as title if no title was found
        if "title" not in metadata or not metadata["title"].strip():
            metadata["title"] = Path(file_path).stem
        
        # If author is still missing, try to extract from filename
        if "author" not in metadata:
            filename = Path(file_path).stem
            author_match = re.match(r'^(.*?)\s*-\s*', filename)
            if author_match:
                metadata["author"] = author_match.group(1).strip()
            else:
                metadata["author"] = "Unknown Author"
        
        print("\nParsed Metadata:")
        for key, value in metadata.items():
            print(f"{key}: {value}")
            
        return metadata
        
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        return None

def main():
    # Directory to scan
    dir_path = Path("/Users/austinavent/Documents/VAULTTEST/TESTING/Books/Markdowns")
    print(f"Starting script...")
    print(f"Scanning directory: {dir_path}")
    
    # Check if directory exists
    if not dir_path.exists():
        print(f"Directory does not exist: {dir_path}")
        return
        
    # List all files in directory
    files = list(dir_path.glob("*"))
    print(f"Found {len(files)} files in directory")
    print("Files found:")
    for f in files:
        print(f"  - {f.name} ({f.suffix})")
    
    # Process all PDF and EPUB files
    for file_path in files:
        if file_path.suffix.lower() in ['.pdf', '.epub', '.mobi']:
            print(f"\nProcessing file: {file_path}")
            metadata = extract_calibre_metadata(file_path)
            print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    main()