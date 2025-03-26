from pathlib import Path

class TestConfig:
    VAULT_DIR = Path("./test_vault")
    BOOKS_DIR = VAULT_DIR / "Books"
    # ... other paths ...
    
    # Test settings
    MAX_BOOKS = 5  # Limit number of books to process
    TEST_FILES = [
        "sample1.pdf",
        "sample2.epub",
        "sample3.mobi"
    ] 