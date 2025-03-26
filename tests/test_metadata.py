import pytest
from src.metadata.calibre import CalibreMetadata
from pathlib import Path

def test_metadata_extraction():
    test_file = Path("tests/fixtures/sample1.pdf")
    metadata = CalibreMetadata(test_file).extract()
    
    assert "title" in metadata
    assert "author" in metadata
    assert metadata["format"] == "PDF"

def test_metadata_sanitization():
    # Test with problematic characters
    dirty_title = "Book: With [bad] characters?"
    clean_title = sanitize_string(dirty_title)
    assert clean_title == "Book With bad characters" 