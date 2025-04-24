#!/usr/bin/env python3
"""
Script to fix RST title underlines in documentation files.
This script ensures all title underlines match the length of the title text exactly.
"""

import os
import re
import glob

def fix_underlines_in_file(file_path):
    """Fix all title underlines in an RST file to match their title text length exactly."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern to match a title line followed by an underline
    pattern = r'([^\n]+)\n([=\-~]+)\n'

    def replacement(match):
        """Replace with title and correct-length underline."""
        title = match.group(1)
        underline_char = match.group(2)[0]  # Get the first character (=, -, or ~)
        
        # Create new underline with exact length of title
        new_underline = underline_char * len(title)
        
        return f"{title}\n{new_underline}\n"

    # Replace all instances in the content
    fixed_content = re.sub(pattern, replacement, content)

    # Only write back if changes were made
    if fixed_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        print(f"Fixed underlines in {file_path}")
        return True
    return False

def main():
    """Find all RST files and fix their title underlines."""
    # Find all .rst files in the source directory and subdirectories
    rst_files = glob.glob('./source/**/*.rst', recursive=True)
    
    # Counter for fixed files
    fixed_count = 0
    
    # Process each file
    for file_path in rst_files:
        if fix_underlines_in_file(file_path):
            fixed_count += 1
    
    print(f"Fixed title underlines in {fixed_count} files.")

if __name__ == "__main__":
    main()

