from pathlib import Path

class Config:
    VAULT_DIR = Path("/Users/austinavent/Documents/VAULTTEST/TESTING/")
    BOOKS_DIR = VAULT_DIR / "Books"
    ANNOTATION_DIR = BOOKS_DIR / "Annotations"
    INDEX_FILE = BOOKS_DIR / "Book Index.md"
    MARKDOWN_DIR = BOOKS_DIR / "Markdowns"
    ORIGINALS_DIR = BOOKS_DIR / "Originals" 
    LANDING_DIR = BOOKS_DIR
    # Index file location
    INDEX_FILE = BOOKS_DIR / "Book Index.md"
    BUCKET_DIR = VAULT_DIR / "Bucket"
    # Supported file types (used for direct access, no conversion needed)
    BOOK_FORMATS = ['.pdf', '.epub']
    # Formats that need manual processing (not automatically processed)
    MANUAL_FORMATS = ['.rtf']
    # Formats that can be automatically converted to supported formats
    CONVERTIBLE_FORMATS = ['.docx', '.doc', '.rtf', '.odt', '.azw', '.azw3', '.xhtml', '.html', '.mobi']