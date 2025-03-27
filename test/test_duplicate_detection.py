#!/usr/bin/env python3
"""
Test script for duplicate book detection.

This script tests the improved book processing system by:
1. Creating test books with different naming conventions but same content
2. Running the book processor to detect duplicates
3. Verifying that landing pages are properly managed
"""

import sys
import os
import shutil
from pathlib import Path
import logging
import re

# Add parent directory to path so we can import our modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.default_config import Config
from src.processor.book_processor import BookProcessor
from src.processor.file_processor import FileProcessor
from src.utils.logger import setup_logger

logger = setup_logger(debug=True)

def setup_test_environment():
    """Set up test files and directories."""
    logger.info("Setting up test environment")
    
    # Create test directory structure if needed
    bucket_dir = Config.BUCKET_DIR
    originals_dir = Config.ORIGINALS_DIR
    landing_dir = Config.LANDING_DIR
    
    for dir_path in [bucket_dir, originals_dir, landing_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    # Create a test file in originals (to demonstrate existing file)
    test_file1 = originals_dir / "Thinking Fast and Slow - Daniel Kahneman.pdf"
    if not test_file1.exists():
        # Create an empty file for testing
        with open(test_file1, 'wb') as f:
            f.write(b'Test file content for book 1')
        logger.info(f"Created test file: {test_file1}")
    
    # Create a basic landing page for the existing book
    landing_page = landing_dir / "Thinking Fast and Slow - Daniel Kahneman.md"
    if not landing_page.exists():
        content = """---
title: "Thinking Fast and Slow"
author: "Daniel Kahneman"
tags:
  - book
  - psychology
---

# Thinking Fast and Slow

## Document Versions
- [[Books/Annotations/Thinking Fast and Slow - Daniel Kahneman - Annotations.md|Read & Annotate]]

## Reading Status
- **Status**: In Progress
- **Last opened**: 2024-03-25
- **Progress**: 30%

### Progress Bar
`[██████░░░░░░░░░░░░░░]` 30%

## Notes & Highlights

### Key Concepts
- System 1 and System 2 thinking
- Cognitive biases

### Important Quotes
- "A reliable way to make people believe in falsehoods is frequent repetition, because familiarity is not easily distinguished from truth."

### Questions & Reflections
- How can I apply these insights to decision making?
"""
        with open(landing_page, 'w') as f:
            f.write(content)
        logger.info(f"Created test landing page: {landing_page}")
    
    # Create test file with different naming convention in bucket
    test_file2 = bucket_dir / "Thinking, Fast and Slow.pdf"
    if not test_file2.exists():
        # Create a file with same content to test duplicate detection
        with open(test_file2, 'wb') as f:
            f.write(b'Test file content for book 1')
        logger.info(f"Created test file with different naming: {test_file2}")
    
    # Create a different book with the same author
    test_file3 = bucket_dir / "Noise - Daniel Kahneman.epub"
    if not test_file3.exists():
        with open(test_file3, 'wb') as f:
            f.write(b'Test file content for book 2')
        logger.info(f"Created test file for different book: {test_file3}")
    
    # Create a test file with year in the name
    test_file4 = bucket_dir / "Thinking Fast and Slow (2021).pdf"
    if not test_file4.exists():
        with open(test_file4, 'wb') as f:
            f.write(b'Test file content for newer edition')
        logger.info(f"Created test file with year in name: {test_file4}")

def test_duplicate_detection():
    """Test the book processor's duplicate detection capabilities."""
    logger.info("\n=== Testing Duplicate Detection ===")
    
    # Set up the test environment
    setup_test_environment()
    
    # Initialize processors
    processor = BookProcessor(Config)
    
    # First, process the bucket to move files
    logger.info("\n=== Processing Bucket ===")
    processed_files = processor.file_processor.process_bucket()
    logger.info(f"Processed {len(processed_files)} files from bucket")
    
    # Now run the book processor to detect duplicates
    logger.info("\n=== Processing Books ===")
    processor.process_books()
    
    # Check results
    logger.info("\n=== Checking Results ===")
    
    # List all landing pages
    landing_pages = list(Config.LANDING_DIR.glob("*.md"))
    logger.info(f"Found {len(landing_pages)} landing pages:")
    for page in landing_pages:
        logger.info(f"- {page.name}")
        
        # Read the content to check if it's been updated
        try:
            content = page.read_text()
            title_match = re.search(r'title: "(.*?)"', content)
            author_match = re.search(r'author: "(.*?)"', content)
            
            title = title_match.group(1) if title_match else "Unknown"
            author = author_match.group(1) if author_match else "Unknown"
            
            logger.info(f"  Title: {title}, Author: {author}")
        except Exception as e:
            logger.error(f"Error reading landing page: {str(e)}")
    
    # List all files in originals
    original_files = list(Config.ORIGINALS_DIR.glob("*"))
    logger.info(f"\nFound {len(original_files)} files in originals:")
    for file in original_files:
        logger.info(f"- {file.name}")

if __name__ == "__main__":
    test_duplicate_detection() 