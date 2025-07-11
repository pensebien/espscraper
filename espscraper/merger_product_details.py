import json
import argparse
import os
from espscraper.checkpoint_manager import CheckpointManager

REQUIRED_FIELDS = ["ProductID", "Name"]  # Adjust as needed

def has_required_fields(product):
    return all(product.get(field) for field in REQUIRED_FIELDS)

def load_products(filepath):
    products = {}
    if not os.path.exists(filepath):
        return products
    with open(filepath, "r") as f:
        content = f.read().strip()
        if not content:
            return products
        try:
            # Try to parse as JSON array
            data = json.loads(content)
            if isinstance(data, list):
                for product in data:
                    if has_required_fields(product):
                        products[product["ProductID"]] = product
                return products
        except Exception:
            pass
        # Fallback: treat as JSONL
        f.seek(0)
        for line in f:
            try:
                product = json.loads(line)
                if has_required_fields(product):
                    products[product["ProductID"]] = product
            except Exception:
                continue
    return products

def merge_product_details(existing_path, new_path, output_path):
    # Use CheckpointManager to get all valid ProductIDs for indexing
    checkpoint_manager = CheckpointManager('final_product_details.jsonl', id_fields=['ProductID'])
    scraped_ids, last_valid_id, last_valid_line = checkpoint_manager.get_scraped_ids_and_checkpoint()
    # scraped_ids can now be used for deduplication or index building below
    existing = load_products(existing_path)
    new = load_products(new_path)
    existing.update(new)
    with open(output_path, "w") as f:
        for product in existing.values():
            f.write(json.dumps(product) + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge product detail files, skipping entries with missing data.")
    parser.add_argument("--existing", required=True, help="Path to existing final_product_details.jsonl or .json")
    parser.add_argument("--new", required=True, help="Path to new product details file (.json or .jsonl)")
    parser.add_argument("--output", required=True, help="Path to output merged file (.jsonl)")
    args = parser.parse_args()
    merge_product_details(args.existing, args.new, args.output)