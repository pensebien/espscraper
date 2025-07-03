import os
import json
import argparse

def read_jsonl(filepath, delimiter='\n'):
    items = []
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        for line in content.split(delimiter):
            line = line.strip()
            if line:
                try:
                    items.append(json.loads(line))
                except Exception as e:
                    print(f"⚠️ Skipping line (parse error): {line[:80]}... Error: {e}")
    return items

def write_jsonl(filepath, items):
    with open(filepath, 'w', encoding='utf-8') as f:
        for item in items:
            f.write(json.dumps(item) + '\n')

def deduplicate(items, key_fields):
    seen = set()
    deduped = []
    for item in items:
        for key in key_fields:
            val = item.get(key)
            if val and val not in seen:
                seen.add(val)
                deduped.append(item)
                break
    return deduped

def main():
    parser = argparse.ArgumentParser(description="ESP Scraper Link Merger Utility")
    parser.add_argument('--api-links-file', required=True, help='Path to new API links file to merge')
    parser.add_argument('--api-links-delim', default='\n', help='Delimiter for API links file (default: newline)')
    args = parser.parse_args()

    # Canonical file (absolute path)
    canonical_links = os.path.join(os.path.dirname(__file__), 'data', 'api_scraped_links.jsonl')

    # Load links from canonical file
    all_links = []
    if os.path.exists(canonical_links):
        links1 = read_jsonl(canonical_links, delimiter='\n')
        print(f"Loaded {len(links1)} links from canonical file: {canonical_links}")
        all_links.extend(links1)
    else:
        print(f"Canonical file does not exist, will create: {canonical_links}")

    # Load links from new file
    links2 = read_jsonl(args.api_links_file, delimiter=args.api_links_delim)
    print(f"Loaded {len(links2)} links from new file: {args.api_links_file}")
    all_links.extend(links2)

    # Deduplicate
    merged_links = deduplicate(all_links, key_fields=['id', 'url'])
    print(f"After deduplication: {len(merged_links)} unique links.")

    # Write merged links
    write_jsonl(canonical_links, merged_links)
    print(f"✅ Merged links written to {canonical_links}")

if __name__ == "__main__":
    main() 