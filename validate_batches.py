#!/usr/bin/env python3
"""
Batch Validation Script

Validates JSONL batch files for integrity and provides statistics.
"""

import json
import os
import sys
import argparse


def validate_batches(batch_dir: str = "batch") -> bool:
    """Validate all batch files in the specified directory"""
    if not os.path.exists(batch_dir):
        print(f"❌ Batch directory '{batch_dir}' does not exist")
        return False
    
    invalid_files = 0
    total_files = 0
    total_products = 0
    
    for filename in os.listdir(batch_dir):
        if filename.startswith('batch_') and filename.endswith('.jsonl'):
            total_files += 1
            filepath = os.path.join(batch_dir, filename)
            invalid_lines = 0
            valid_lines = 0
            
            try:
                with open(filepath, 'r') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            json.loads(line)
                            valid_lines += 1
                        except json.JSONDecodeError:
                            invalid_lines += 1
                            print(f"⚠️ Invalid JSON in {filename} line {line_num}")
                
                total_products += valid_lines
                
                if invalid_lines > 0:
                    print(f"❌ {filename}: {invalid_lines} invalid lines, {valid_lines} valid lines")
                    invalid_files += 1
                else:
                    print(f"✅ {filename}: {valid_lines} valid lines")
                    
            except Exception as e:
                print(f"❌ Error reading {filename}: {e}")
                invalid_files += 1
    
    print(f"\n📊 Validation Summary:")
    print(f"  Total batch files: {total_files}")
    print(f"  Invalid files: {invalid_files}")
    print(f"  Total products: {total_products}")
    
    if invalid_files > 0:
        print("❌ Some batch files have issues")
        return False
    else:
        print("✅ All batch files are valid")
        return True


def get_batch_stats(batch_dir: str = "batch") -> dict:
    """Get statistics about batch files"""
    stats = {
        'batch_count': 0,
        'total_products': 0,
        'batch_files': []
    }
    
    if not os.path.exists(batch_dir):
        return stats
    
    for filename in os.listdir(batch_dir):
        if filename.startswith('batch_') and filename.endswith('.jsonl'):
            stats['batch_count'] += 1
            filepath = os.path.join(batch_dir, filename)
            
            try:
                with open(filepath, 'r') as f:
                    product_count = sum(1 for line in f if line.strip())
                stats['total_products'] += product_count
                stats['batch_files'].append({
                    'filename': filename,
                    'products': product_count
                })
            except Exception as e:
                print(f"⚠️ Error reading {filename}: {e}")
    
    return stats


def main():
    parser = argparse.ArgumentParser(description='Validate batch files')
    parser.add_argument('--batch-dir', default='batch', help='Batch directory')
    parser.add_argument('--stats-only', action='store_true', help='Show stats only')
    parser.add_argument('--validate-only', action='store_true', help='Validate only')
    
    args = parser.parse_args()
    
    if args.stats_only:
        stats = get_batch_stats(args.batch_dir)
        print("📊 Batch Statistics:")
        print(f"  Batch files: {stats['batch_count']}")
        print(f"  Total products: {stats['total_products']}")
        for batch in stats['batch_files']:
            print(f"  {batch['filename']}: {batch['products']} products")
        return
    
    if args.validate_only:
        success = validate_batches(args.batch_dir)
        sys.exit(0 if success else 1)
    
    # Default: show both stats and validation
    stats = get_batch_stats(args.batch_dir)
    print("📊 Batch Statistics:")
    print(f"  Batch files: {stats['batch_count']}")
    print(f"  Total products: {stats['total_products']}")
    
    print("\n🔍 Validating batches...")
    success = validate_batches(args.batch_dir)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 