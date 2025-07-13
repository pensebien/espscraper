#!/usr/bin/env python3
"""
JSONL File Repair Utility

Repairs corrupted JSONL files by removing invalid lines and ensuring
each line contains valid JSON. Useful for recovering from interrupted
scraping sessions.
"""

import json
import os
import sys
import shutil
from pathlib import Path

def validate_jsonl(filename):
    """Validate JSONL file and return statistics"""
    valid_lines = 0
    invalid_lines = 0
    invalid_line_numbers = []
    
    with open(filename, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                json.loads(line)
                valid_lines += 1
            except json.JSONDecodeError as e:
                invalid_lines += 1
                invalid_line_numbers.append(line_num)
    
    return {
        'valid_lines': valid_lines,
        'invalid_lines': invalid_lines,
        'invalid_line_numbers': invalid_line_numbers,
        'total_lines': valid_lines + invalid_lines
    }

def repair_jsonl(filename, backup=True):
    """Repair JSONL file by removing invalid lines"""
    if not os.path.exists(filename):
        print(f"❌ File {filename} does not exist")
        return False
    
    # Create backup
    if backup:
        backup_file = filename + '.backup'
        shutil.copy2(filename, backup_file)
        print(f"📋 Created backup: {backup_file}")
    
    # Read and validate all lines
    valid_lines = []
    invalid_count = 0
    
    with open(filename, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                json.loads(line)
                valid_lines.append(line)
            except json.JSONDecodeError as e:
                invalid_count += 1
                print(f"⚠️ Removing invalid JSON on line {line_num}: {e}")
    
    # Write repaired file
    temp_file = filename + '.repaired'
    with open(temp_file, 'w') as f:
        for line in valid_lines:
            f.write(line + '\n')
    
    # Atomic move
    shutil.move(temp_file, filename)
    
    print(f"✅ Repaired {filename}")
    print(f"📊 Removed {invalid_count} invalid lines")
    print(f"📊 Kept {len(valid_lines)} valid lines")
    
    return True

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python3 repair_jsonl.py <filename> [--no-backup]")
        print("       python3 repair_jsonl.py --validate <filename>")
        sys.exit(1)
    
    if sys.argv[1] == '--validate':
        if len(sys.argv) < 3:
            print("Usage: python3 repair_jsonl.py --validate <filename>")
            sys.exit(1)
        
        filename = sys.argv[2]
        if not os.path.exists(filename):
            print(f"❌ File {filename} does not exist")
            sys.exit(1)
        
        print(f"🔍 Validating {filename}:")
        stats = validate_jsonl(filename)
        
        print(f"📊 Total lines: {stats['total_lines']}")
        print(f"✅ Valid lines: {stats['valid_lines']}")
        print(f"❌ Invalid lines: {stats['invalid_lines']}")
        
        if stats['invalid_lines'] > 0:
            print(f"⚠️ Invalid line numbers: {stats['invalid_line_numbers']}")
            print("💡 Run without --validate to repair the file")
        else:
            print("✅ File is valid - no repair needed")
        
        return
    
    filename = sys.argv[1]
    backup = '--no-backup' not in sys.argv
    
    if not os.path.exists(filename):
        print(f"❌ File {filename} does not exist")
        sys.exit(1)
    
    print(f"🔧 Repairing {filename}...")
    
    # First validate
    stats = validate_jsonl(filename)
    print(f"📊 Found {stats['valid_lines']} valid and {stats['invalid_lines']} invalid lines")
    
    if stats['invalid_lines'] == 0:
        print("✅ File is already valid - no repair needed")
        return
    
    # Confirm repair
    response = input(f"Remove {stats['invalid_lines']} invalid lines? (y/N): ")
    if response.lower() != 'y':
        print("❌ Repair cancelled")
        return
    
    # Repair file
    success = repair_jsonl(filename, backup)
    
    if success:
        print("✅ Repair completed successfully")
    else:
        print("❌ Repair failed")
        sys.exit(1)

if __name__ == "__main__":
    main() 