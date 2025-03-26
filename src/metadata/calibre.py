import subprocess
import re
import datetime
from pathlib import Path
from typing import Dict

class CalibreMetadata:
    def __init__(self, config):
        self.config = config

    def extract_metadata(self, file_path: Path) -> Dict:
        """Extract metadata using Calibre's ebook-meta tool."""
        try:
            # Run Calibre's ebook-meta command with a timeout
            result = subprocess.run(
                ["ebook-meta", str(file_path)], 
                capture_output=True, 
                text=True,
                timeout=30
            )
            
            # Parse the output
            output = result.stdout.strip()

            # Start with path in metadata
            metadata = {
                "path": str(Path("Books/Originals") / file_path.name)
            }
            
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
                    metadata[yaml_field] = self._sanitize_string(match.group(1).strip())
            
            # Add file format
            metadata["format"] = file_path.suffix[1:].upper()
            
            # Use filename as title if no title was found
            if "title" not in metadata or not metadata["title"].strip():
                metadata["title"] = self._sanitize_string(file_path.stem)
            
            # If author is still missing, try to extract from filename
            if "author" not in metadata:
                filename = file_path.stem
                author_match = re.match(r'^(.*?)\s*-\s*', filename)
                if author_match:
                    metadata["author"] = author_match.group(1).strip()
                else:
                    metadata["author"] = "Unknown Author"
            
            # Add additional metadata
            metadata["last_opened"] = datetime.datetime.now().strftime("%Y-%m-%d")
            metadata["status"] = "new"
            metadata["reading_progress"] = 0
            
            return metadata
            
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            # Return basic metadata without failing
            return {
                "path": str(Path("Books/Originals") / file_path.name),
                "format": file_path.suffix[1:].upper(),
                "title": self._sanitize_string(file_path.stem),
                "author": "Unknown Author",
                "last_opened": datetime.datetime.now().strftime("%Y-%m-%d"),
                "status": "new",
                "reading_progress": 0
            }

    def _sanitize_string(self, text: str) -> str:
        """Sanitize string to remove problematic characters."""
        if not text or not isinstance(text, str):
            return text
        
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
        return text.strip('- ') 