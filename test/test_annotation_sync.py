#!/usr/bin/env python3
"""
Test script for annotation syncing functionality.

This script tests the ability to:
1. Parse annotations from Kindle clippings and Obsidian Annotator
2. Match annotations to markdown files
3. Apply highlighting and block IDs to the matching text
4. Update landing pages with links to the highlights
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
from src.processor.annotation_parser import AnnotationParser
from src.processor.annotation_syncer import AnnotationSyncer
from src.utils.logger import setup_logger

logger = setup_logger(debug=True)

def setup_test_environment():
    """Set up test files and directories for annotation syncing."""
    logger.info("Setting up test environment for annotation syncing")
    
    # Create test directory structure if needed
    markdown_dir = Config.MARKDOWN_DIR
    landing_dir = Config.LANDING_DIR
    
    # Make the test directories
    for dir_path in [markdown_dir, landing_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    # Create a test markdown file for a book
    test_book_dir = markdown_dir / "J. K. Rowling - Harry Potter The Prequel"
    test_book_dir.mkdir(exist_ok=True)
    
    # Create the actual markdown file with content for testing
    test_md_file = test_book_dir / "J. K. Rowling - Harry Potter The Prequel.md"
    
    if not test_md_file.exists():
        test_content = """# Harry Potter: The Prequel

The speeding motorcycle took the sharp corner so fast in the darkness that both policemen in the pursuing car shouted, "Whoa!" 

Sergeant Fisher slammed his large foot on the brake, thinking that the boy who was riding pillion was sure to be flung under his wheels; however, the motorcycle made the turn without unseating either of its riders, and with a wink of its red tail light, vanished up the narrow side street.

"We've got 'em now!" cried PC Anderson excitedly. "That's a dead end!"

Leaning hard on the steering wheel and crashing his gears, Fisher scraped half the paint off the flank of the car as he forced it up the alleyway in pursuit.

There was a shout, a blaze of light, and Fisher slammed on the brakes, staring in disbelief at the obstacle that had appeared in the headlights; a vast bearded man in an emerald-green suit was towering over him, wearing a helmet covered with silver sequins and starting a pair of enormous red shoes.

"Get out of the way, please!" Anderson yelled. "We're in pursuit here!"

Fisher and Anderson threw their arms around each other in fright; their car had just fallen back to the ground. Now it was the motorcycle's turn to rear. Before the policemen's disbelieving eyes, it took off into the air: James and Sirius zoomed away into the night sky, their tail light twinkling behind them like a vanishing ruby star.

"Did you get the number plate, Anderson?" asked Fisher, when they had finally unclutched each other.

"No, I didn't," said Anderson, who was very white and trembling.

"I think it was a dragon. Erm, green, sort of scaly. I saw fire coming out of its back end."

"Oh and there's a guy," said Fisher, who was even paler and could hardly speak for shock. "A guy in the sky. On a broomstick."

There was a silence, then Anderson said, "So, I take it we didn't see anything tonight, Fisher? Drink?"

"Yeah," said Fisher fervently. "We didn't see a thing."

"""
        
        # Write test content to file
        with open(test_md_file, 'w') as f:
            f.write(test_content)
        logger.info(f"Created test markdown file: {test_md_file}")
    
    # Create a test landing page
    landing_page = landing_dir / "Harry Potter - The Prequel.md"
    if not landing_page.exists():
        landing_content = """---
title: "Harry Potter - The Prequel"
author: "J. K. Rowling"
tags:
  - book
  - fantasy
---

# Harry Potter: The Prequel

## Document Versions
- [[Books/Markdowns/J. K. Rowling - Harry Potter The Prequel/J. K. Rowling - Harry Potter The Prequel.md|Main Document]]

## Reading Status
- **Status**: Completed
- **Last opened**: 2024-05-01

## Notes & Highlights

### Key Concepts
- Set before the main Harry Potter series
- Features James Potter and Sirius Black

### Kindle Highlights
> [!quote]
> Fisher and Anderson threw theirarms around each other in fright; their car had just fallen back to the ground.Now it was the motorcycle's turn to rear. Before the policemen'sdisbelieving eyes, it took off into the air: James and Sirius zoomed away intothe night sky, their tail light twinkling behind them like a vanishing ruby star.

### Obsidian Annotations
> [!highlight]+ 
> r and Anderson threw theirarms around each other in fright; their car had just fallen back to the ground.Now it was the motorcycle's turn to rear. Before the policemen'sdisbelieving eyes, it took off into the air: James and Sirius zoomed away intothe night sky, their tail light twin
> 
> *>np*

"""
        with open(landing_page, 'w') as f:
            f.write(landing_content)
        logger.info(f"Created test landing page: {landing_page}")

def test_annotation_parsing():
    """Test the annotation parser."""
    logger.info("\n=== Testing Annotation Parsing ===")
    
    # Set up the test environment
    setup_test_environment()
    
    # Initialize parser
    parser = AnnotationParser(Config)
    
    # Parse annotations from the landing page
    landing_path = Config.LANDING_DIR / "Harry Potter - The Prequel.md"
    annotations = parser.parse_annotations_from_landing_page(landing_path)
    
    # Log results
    logger.info(f"Parsed {len(annotations)} annotations from landing page")
    for i, annotation in enumerate(annotations):
        logger.info(f"\nAnnotation {i+1}:")
        for key, value in annotation.items():
            if key == 'text':
                preview = value[:50] + "..." if len(value) > 50 else value
                logger.info(f"  {key}: {preview}")
            else:
                logger.info(f"  {key}: {value}")
    
    return annotations

def test_annotation_syncing(annotations):
    """Test the annotation syncer."""
    logger.info("\n=== Testing Annotation Syncing ===")
    
    # Initialize syncer
    syncer = AnnotationSyncer(Config)
    
    # Find markdown file
    markdown_path = Config.MARKDOWN_DIR / "J. K. Rowling - Harry Potter The Prequel" / "J. K. Rowling - Harry Potter The Prequel.md"
    if not markdown_path.exists():
        logger.error(f"Test markdown file not found: {markdown_path}")
        return False
    
    # Find landing page
    landing_path = Config.LANDING_DIR / "Harry Potter - The Prequel.md"
    if not landing_path.exists():
        logger.error(f"Test landing page not found: {landing_path}")
        return False
    
    # Make a backup of the files before modification
    backup_md = markdown_path.with_suffix('.md.bak')
    backup_landing = landing_path.with_suffix('.md.bak')
    
    try:
        shutil.copy2(markdown_path, backup_md)
        shutil.copy2(landing_path, backup_landing)
        logger.info("Created backups of test files")
        
        # Sync annotations
        synced_count = syncer.sync_annotations(annotations, markdown_path, landing_path)
        logger.info(f"Synced {synced_count} annotations")
        
        # Check results
        if synced_count > 0:
            # Display updated markdown file
            md_content = markdown_path.read_text()
            logger.info("\nUpdated markdown file with block IDs and highlighting:")
            highlighted_lines = []
            for i, line in enumerate(md_content.split('\n')):
                if '==' in line or '^' in line:
                    highlighted_lines.append(f"Line {i+1}: {line}")
            
            for line in highlighted_lines:
                logger.info(line)
            
            # Display updated landing page
            landing_content = landing_path.read_text()
            logger.info("\nUpdated landing page with links to highlights:")
            
            # Find direct links section
            links_section = re.search(r'### Direct Links to Highlights\n(.*?)(?:\n##|\Z)', 
                                     landing_content, re.DOTALL)
            if links_section:
                links = links_section.group(1).strip()
                logger.info(links)
            else:
                logger.warning("No links section found in landing page")
                
            return True
        else:
            logger.warning("No annotations were synced")
            return False
            
    except Exception as e:
        logger.error(f"Error in annotation syncing test: {str(e)}")
        return False
    finally:
        # Restore backups
        if backup_md.exists() and backup_landing.exists():
            try:
                shutil.copy2(backup_md, markdown_path)
                shutil.copy2(backup_landing, landing_path)
                backup_md.unlink()
                backup_landing.unlink()
                logger.info("Restored original files from backups")
            except Exception as e:
                logger.error(f"Error restoring backups: {str(e)}")

def main():
    """Run the annotation syncing tests."""
    # Setup logging
    logger.info("Starting annotation syncing tests")
    
    # Test annotation parsing
    annotations = test_annotation_parsing()
    
    # Test annotation syncing
    if annotations:
        test_annotation_syncing(annotations)
    else:
        logger.error("No annotations to sync, test failed")
    
    logger.info("Annotation syncing tests completed")

if __name__ == "__main__":
    main() 