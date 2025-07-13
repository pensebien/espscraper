import json
import shutil
import sys
import os

# Usage: python deduplicator.py [input_file]
if len(sys.argv) > 1:
    input_file = sys.argv[1]
else:
    # Default to api_scraped_links.jsonl
    input_file = "espscraper/data/api_scraped_links.jsonl"

# Set output and backup file names
base, ext = os.path.splitext(input_file)
backup_file = base + ".BACKUP" + ext
output_file = base + ".deduped" + ext

# Backup the original file for safety
shutil.copy(input_file, backup_file)
print(f"Backup created at {backup_file}")

seen_ids = set()
unique_items = []
duplicate_count = 0
duplicate_ids = set()

# Preferred key order for api_scraped_links
PREFERRED_KEYS = ["url", "id", "name"]


def get_id(data):
    # Try all common id fields
    for key in ("id", "productId", "ProductID"):
        if key in data and data[key] is not None:
            return str(data[key])
    # For product detail files, ProductID is always present
    if "ProductID" in data and data["ProductID"]:
        return str(data["ProductID"])
    # Fallback: try URL
    if "url" in data and data["url"]:
        return str(data["url"])
    if "URL" in data and data["URL"]:
        return str(data["URL"])
    return None


def reorder_keys(d):
    # Only reorder for api_scraped_links
    if all(k in d for k in ("url", "id", "name")):
        ordered = {}
        for k in PREFERRED_KEYS:
            if k in d:
                ordered[k] = d[k]
        for k in sorted(d.keys()):
            if k not in ordered:
                ordered[k] = d[k]
        return ordered
    return d


with open(input_file, "r", encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            pid = get_id(data)
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                unique_items.append(data)
            elif pid:
                duplicate_count += 1
                duplicate_ids.add(pid)
        except Exception as e:
            print(f"Skipping line due to error: {e}")

with open(output_file, "w", encoding="utf-8") as f:
    for item in unique_items:
        ordered_item = reorder_keys(item)
        f.write(json.dumps(ordered_item, ensure_ascii=False) + "\n")

print(
    f"Deduplication complete. {len(unique_items)} unique items written to {output_file}."
)
print(f"Removed {duplicate_count} duplicate entries.")
if duplicate_ids:
    print(f"Duplicate IDs found ({len(duplicate_ids)}):")
    for pid in sorted(duplicate_ids):
        print(f" - {pid}")
else:
    print("No duplicate IDs found.")
print("If you are satisfied, you can replace the original file with the deduped one.")
