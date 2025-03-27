# Obsidian Book Reader & Annotation Syncer

An assistant tool for managing books, annotations, and markdown content in Obsidian.

## Features

### 📚 Book Processing

- **File Management**: Organizes book files from a bucket directory to an originals directory.
- **Format Conversion**: Converts various file formats (DOCX, MOBI, AZW3, etc.) to EPUB or PDF.
- **Duplicate Detection**: Identifies duplicate books by content hash, even with different filenames.
- **Metadata Extraction**: Extracts title, author, and other metadata from book files.

### 📝 Annotation Management

- **Annotation Parsing**: Extracts highlights and notes from Kindle clippings and Obsidian Annotator.
- **Markdown Sync**: Finds matching text in markdown files and applies highlighting.
- **Block IDs**: Creates Obsidian block IDs for direct linking to highlighted passages.
- **Landing Page Links**: Updates book landing pages with direct links to highlighted passages.

### 🔍 Content Matching

- **Fuzzy Matching**: Matches books with markdown content using sophisticated fuzzy matching.
- **Duplicate Handling**: Manages different editions of the same book with intelligent landing page updates.
- **Index Creation**: Creates and maintains a master index of all books with metadata.

## Getting Started

### Prerequisites

- Python 3.8+
- Calibre (optional, for enhanced metadata extraction and format conversion)
- Obsidian vault for storing books and annotations

### Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure your vault path in `config/default_config.py` or set environment variables

### Configuration

Edit `config/default_config.py` to adjust paths:

```python
VAULT_DIR = Path(os.environ.get("VAULT_DIR", "/path/to/your/vault"))
KINDLE_CLIPPINGS_PATH = Path(os.environ.get("KINDLE_CLIPPINGS_PATH", "/path/to/My Clippings.txt"))
```

### Usage

#### Basic Processing

Process all books and sync annotations:

```bash
python main.py
```

#### Sync Annotations Only

Only sync annotations without processing books:

```bash
python main.py --sync-annotations
```

#### Match Markdown Only

Only match landing pages with markdown files:

```bash
python main.py --match-only
```

#### Debug Mode

Run with additional logging:

```bash
python main.py --debug
```

## Annotation Syncing

The annotation syncing feature matches highlights from Kindle or Obsidian Annotator to their corresponding markdown files.

### How It Works

1. Parses annotations from:
   - Kindle My Clippings.txt file
   - Obsidian Annotator highlights in landing pages

2. Matches the highlighted text in markdown files using:
   - Exact text matching
   - Fuzzy matching for slightly different text
   - Partial matching for longer highlights

3. Updates markdown files by:
   - Adding block IDs for direct linking
   - Adding highlighting to matched text (using `==highlighted text==`)
   - Adding any comments as note callouts

4. Updates landing pages with:
   - Direct links to the highlighted sections
   - Preview of highlighted text
   
### Supported Annotation Formats

#### Kindle Highlights

```
> [!quote]
> Highlighted text from Kindle clippings
```

#### Obsidian Annotator

```
> [!highlight]+ 
> Highlighted text from Obsidian Annotator
> 
> *>comment*
```

## Testing

Run the annotation syncing test:

```bash
python test/test_annotation_sync.py
```

Run the duplicate detection test:

```bash
python test/test_duplicate_detection.py
```

## Folder Structure

```
VAULT_DIR/
├── Bucket/                 # Drop new books here
├── Books/
│   ├── Originals/         # Processed book files
│   ├── Markdowns/         # Markdown versions of books
│   ├── Annotations/       # Annotation files
│   ├── Book Index.md      # Master index
│   └── [Book Title].md    # Landing pages
``` 