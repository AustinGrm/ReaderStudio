#!/usr/bin/env python3
import subprocess
from pathlib import Path
import sys

def test_calibre_extraction(file_path):
    """Test Calibre metadata extraction for a single file."""
    print(f"\n{'='*50}")
    print(f"Testing file: {file_path}")
    print(f"{'='*50}")
    
    try:
        # Check if ebook-meta is available
        try:
            subprocess.run(["ebook-meta", "--version"], capture_output=True, check=True)
            print("ebook-meta command is available")
        except subprocess.CalledProcessError as e:
            print("Error checking ebook-meta:", e)
            print("Make sure Calibre is installed and ebook-meta is in your PATH")
            return
        except FileNotFoundError:
            print("ebook-meta command not found! Please install Calibre.")
            return

        # Run Calibre command with explicit error handling
        print("\nTrying to run ebook-meta...")
        try:
            result = subprocess.run(
                ["ebook-meta", str(file_path)], 
                capture_output=True, 
                text=True,
                timeout=30
            )
            print("ebook-meta command completed")
        except subprocess.TimeoutExpired:
            print("Command timed out after 30 seconds!")
            return
        except Exception as e:
            print(f"Command failed: {e}")
            return

        # Show command results
        print("\nCommand Results:")
        print("-" * 30)
        print(f"Return code: {result.returncode}")
        
        if result.stdout:
            print("\nSTDOUT:")
            print(result.stdout)
        else:
            print("\nNo stdout output")
            
        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)
        else:
            print("\nNo stderr output")
            
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        import traceback
        print("Traceback:")
        traceback.print_exc()

def main():
    # Test specific files
    test_dir = Path("/Users/austinavent/Documents/VAULTTEST/TESTING/Books/Originals")
    print(f"Looking in: {test_dir}")
    
    # Verify directory exists
    if not test_dir.exists():
        print(f"ERROR: Directory does not exist: {test_dir}")
        sys.exit(1)
    
    # List all files
    files = list(test_dir.glob("*"))
    print(f"\nFound {len(files)} files:")
    for f in files:
        print(f"  - {f.name}")
    
    # Process each file
    print("\nStarting file processing...")
    file_count = 0
    for file_path in files:
        if file_path.suffix.lower() in ['.pdf', '.epub', '.mobi']:
            file_count += 1
            print(f"\nProcessing file {file_count}...")
            test_calibre_extraction(file_path)
    
    print("\nScript completed!")

if __name__ == "__main__":
    print("Starting script...")
    main()
    print("Script finished!") 