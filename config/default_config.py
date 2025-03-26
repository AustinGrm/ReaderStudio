from pathlib import Path

class Config:
    VAULT_DIR = Path("/Users/austinavent/Library/CloudStorage/Dropbox/Areas/Helen/Helena/TESTINGNOW/90.00_meta_resources")
    BOOKS_DIR = VAULT_DIR / "Books"
    ANNOTATION_DIR = BOOKS_DIR / "Annotations"
    INDEX_FILE = BOOKS_DIR / "Book Index.md"
    MARKDOWN_DIR = BOOKS_DIR / "Markdowns"
    ORIGINALS_DIR = BOOKS_DIR / "Originals" 

    # Index file location
    INDEX_FILE = BOOKS_DIR / "Book Index.md"
    
    # Supported file types
    SUPPORTED_BOOK_FORMATS = ['.pdf', '.epub', '.mobi']
    MANUAL_PROCESSING_FORMATS = ['.txt', '.doc', '.docx', '.rtf']