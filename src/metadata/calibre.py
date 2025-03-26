import subprocess
from pathlib import Path
from typing import Dict
import re

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
            
            metadata = {
                "path": str(Path("Books/Originals") / file_path.name)
            }
            
            # Extract all fields from Calibre
            fields_to_extract = {
                "Title": "title",
                "Author(s)": "author",
                "Publisher": "publisher",
                "Published": "published",
                "Tags": "tags",
                "Series": "series",
                "Rating": "rating",
                "Languages": "language",
            }
            
            for calibre_field, yaml_field in fields_to_extract.items():
                pattern = rf'{calibre_field}\s+:\s*(.*)'
                match = re.search(pattern, output)
                if match and match.group(1).strip():
                    metadata[yaml_field] = self._sanitize_string(match.group(1).strip())
            
            # Add additional metadata
            metadata["format"] = file_path.suffix[1:].upper()
            metadata["title"] = metadata.get("title", file_path.stem)
            metadata["author"] = metadata.get("author", "Unknown Author")
            metadata["status"] = "new"
            metadata["reading_progress"] = 0
            
            return metadata
            
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            return {
                "path": str(Path("Books/Originals") / file_path.name),
                "format": file_path.suffix[1:].upper(),
                "title": file_path.stem,
                "author": "Unknown Author",
                "status": "new",
                "reading_progress": 0
            }

    def _sanitize_string(self, text: str) -> str:
        """Sanitize string to remove problematic characters."""
        if not text or not isinstance(text, str):
            return text
            
        # Remove problematic characters
        text = text.replace('\0', '')
        text = re.sub(r'[\[\]\(\)]', '', text)
        text = re.sub(r'[:\/:*?"<>|]', '-', text)
        text = ''.join(char for char in text if ord(char) < 128)
        text = re.sub(r'-+', '-', text)
        return text.strip('- ') 