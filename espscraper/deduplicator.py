import json
import shutil

input_file = "espscraper/data/api_scraped_links.jsonl"
backup_file = "espscraper/data/api_scraped_links.BACKUP.jsonl"
output_file = "espscraper/data/api_scraped_links.deduped.jsonl"

# Backup the original file for safety
shutil.copy(input_file, backup_file)
print(f"Backup created at {backup_file}")

seen_ids = set()
unique_links = []
duplicate_count = 0
duplicate_ids = set()

# Preferred key order
PREFERRED_KEYS = ["url","id","name"]

def get_id(data):
    return data.get("id") or data.get("productId") or data.get("ProductID")

def reorder_keys(d):
    # Start with preferred keys if present, then all others sorted
    ordered = {}
    for k in PREFERRED_KEYS:
        if k in d:
            ordered[k] = d[k]
    # Add the rest, skipping already added
    for k in sorted(d.keys()):
        if k not in ordered:
            ordered[k] = d[k]
    return ordered

with open(input_file, "r", encoding="utf-8") as f:
    for line in f:
        try:
            data = json.loads(line)
            pid = get_id(data)
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                unique_links.append(data)
            elif pid:
                duplicate_count += 1
                duplicate_ids.add(pid)
        except Exception as e:
            print(f"Skipping line due to error: {e}")

with open(output_file, "w", encoding="utf-8") as f:
    for item in unique_links:
        ordered_item = reorder_keys(item)
        f.write(json.dumps(ordered_item) + "\n")

print(f"Deduplication complete. {len(unique_links)} unique links written to {output_file}.")
print(f"Removed {duplicate_count} duplicate entries.")
if duplicate_ids:
    print(f"Duplicate product IDs found ({len(duplicate_ids)}):")
    for pid in sorted(duplicate_ids):
        print(f" - {pid}")
else:
    print("No duplicate product IDs found.")
print("If you are satisfied, you can replace the original file with the deduped one.")