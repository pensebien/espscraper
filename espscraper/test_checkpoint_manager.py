import os
import json
from espscraper.checkpoint_manager import CheckpointManager

def make_test_file(path, lines):
    with open(path, 'w') as f:
        for line in lines:
            f.write(line + '\n')

def read_file(path):
    with open(path, 'r') as f:
        return f.read()

def main():
    test_file = 'test_output.jsonl'
    checkpoint_file = test_file + '.checkpoint'
    # Create a test file: 2 valid (ProductID), 1 valid (id), 1 invalid, 1 partial, 1 concatenated JSONs
    lines = [
        json.dumps({'ProductID': 'A1', 'value': 1}),
        json.dumps({'ProductID': 'A2', 'value': 2}),
        json.dumps({'id': 'A3', 'value': 3}),  # should be ignored
        '{invalid json',
        '{"ProductID": "A4", "value":',  # partial
        '{"ProductID": "A5", "value": 5}{"ProductID": "A6", "value": 4}',  # concatenated JSONs
    ]
    make_test_file(test_file, lines)
    print(f"Test file created: {test_file}")
    # Run CheckpointManager with ProductID only
    manager = CheckpointManager(test_file, id_fields=['ProductID'])
    scraped_ids, last_valid_id, last_valid_line = manager.get_scraped_ids_and_checkpoint()
    print(f"Scraped IDs: {scraped_ids}")
    print(f"Last valid product ID: {last_valid_id}")
    print(f"Last valid line: {last_valid_line}")
    # Show truncated file contents
    print("\nTruncated file contents:")
    print(read_file(test_file))
    # Show checkpoint file contents
    print("\nCheckpoint file contents:")
    print(read_file(checkpoint_file))
    # Show issues report
    print("\nValidation issues report:")
    manager.report_issues()
    # Clean up
    os.remove(test_file)
    os.remove(checkpoint_file)
    print("\nTest files cleaned up.")

if __name__ == '__main__':
    main() 