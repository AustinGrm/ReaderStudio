from pathlib import Path
import os

class Config:
    """Configuration for the book processing system."""
    
    # Base directories
    VAULT_DIR = Path(os.environ.get("VAULT_DIR", "/Users/austinavent/Documents/VAULTTEST/TESTING"))
    BUCKET_DIR = VAULT_DIR / "Bucket"
    ORIGINALS_DIR = VAULT_DIR / "Books/Originals"
    LANDING_DIR = VAULT_DIR / "Books"
    MARKDOWN_DIR = VAULT_DIR / "Books/Markdowns"
    ANNOTATIONS_DIR = VAULT_DIR / "Books/Annotations"
    
    # Files
    INDEX_FILE = LANDING_DIR / "Book Index.md"
    KINDLE_CLIPPINGS_PATH = Path(os.environ.get("KINDLE_CLIPPINGS_PATH", "/Users/austinavent/Documents/My Clippings.txt"))
    
    # Book formats
    BOOK_FORMATS = ['.pdf', '.epub']
    CONVERTIBLE_FORMATS = ['.docx', '.doc', '.rtf', '.odt', '.azw', '.azw3', '.xhtml', '.html', '.mobi']
    
    # Markdown settings
    ANNOTATION_TAG = "annotation"
    BOOK_TAG = "book"
    
    # Calibre settings
    CALIBRE_PATH = "ebook-meta"  # Path to calibre command line tool
    
    # Debug settings
    DEBUG = os.environ.get("DEBUG", "false").lower() == "true"