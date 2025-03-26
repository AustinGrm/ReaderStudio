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
    # Supported file types
    BOOK_FORMATS = ['.pdf', '.epub', '.mobi']
    MANUAL_FORMATS = ['.txt', '.doc', '.docx', '.rtf']