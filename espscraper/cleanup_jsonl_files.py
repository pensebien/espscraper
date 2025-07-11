import os
import argparse
from espscraper.checkpoint_manager import CheckpointManager

def cleanup_file(path, id_fields, label):
    print(f"\n--- Cleaning up {label}: {path} ---")
    manager = CheckpointManager(path, id_fields=id_fields)
    scraped_ids, last_valid_id, last_valid_line = manager.get_scraped_ids_and_checkpoint()
    print(f"Kept {len(scraped_ids)} valid objects. Last valid ID: {last_valid_id}")
    manager.report_issues()
    print(f"Backup created: {path}.bak\nCleaned file: {path}")

def main():
    parser = argparse.ArgumentParser(description="Clean up/correct a JSONL file with multi-line or corruption issues.")
    parser.add_argument('--file', required=True, help='Path to the JSONL file to clean')
    parser.add_argument('--id-field', default='id', help='ID field to use for deduplication (default: id)')
    parser.add_argument('--label', default='JSONL File', help='Label for reporting')
    args = parser.parse_args()
    if os.path.exists(args.file):
        cleanup_file(args.file, id_fields=[args.id_field], label=args.label)
    else:
        print(f"File not found: {args.file}")

if __name__ == '__main__':
    main() 