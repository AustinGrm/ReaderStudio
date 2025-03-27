#!/usr/bin/env python3
"""
Test script for annotation processing.

This script tests the AnnotationProcessor by:
1. Creating a test Kindle_highlights directory
2. Copying the sample clippings file to it
3. Running the annotation processor
4. Verifying the landing pages are updated with annotations
"""

import sys
import os
import shutil
from pathlib import Path

# Add parent directory to path so we can import our modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.default_config import Config
from src.processor.annotation import AnnotationProcessor
from src.utils.logger import setup_logger

def main():
    """Run a test of the annotation processor."""
    logger = setup_logger(debug=True)
    logger.info("Starting annotation processor test")
    
    # Create test directories
    kindle_dir = Config.VAULT_DIR / "Kindle_highlights"
    kindle_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy sample clippings file to Kindle_highlights
    sample_file = Path(__file__).parent / "sample_clippings.txt"
    if sample_file.exists():
        target_file = kindle_dir / "My Clippings.txt"
        shutil.copy(sample_file, target_file)
        logger.info(f"Copied sample clippings to {target_file}")
    else:
        logger.error(f"Sample clippings file not found: {sample_file}")
        return
    
    # Create annotation processor and run it
    processor = AnnotationProcessor(Config)
    num_annotations = processor.process_annotations()
    
    logger.info(f"Processed {num_annotations} annotations")
    
    # Check results - list the landing pages created/updated
    landing_pages = list(Config.LANDING_DIR.glob("*.md"))
    logger.info(f"Found {len(landing_pages)} landing pages:")
    for page in landing_pages:
        logger.info(f"  - {page.name}")
        
        # Check if this is a book with annotations we added
        for book_title in ["The Practicing Mind", "Thinking, Fast and Slow", "Harry Potter The Prequel"]:
            if book_title in page.name:
                logger.info(f"    Reading content of {page.name}...")
                content = page.read_text()
                
                # Check if annotations were added
                if "## Highlights & Annotations" in content:
                    logger.info(f"    ✅ Annotations section found")
                    if "### Kindle Highlights" in content:
                        logger.info(f"    ✅ Kindle highlights found")
                else:
                    logger.info(f"    ❌ No annotations section found")

if __name__ == "__main__":
    main() 