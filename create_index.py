#!/usr/bin/env python3
"""
Create/Update product index from final_product_details.jsonl
"""

import json
import os
import sys

def create_product_index():
    index_file = 'espscraper/data/product_index.json'
    scraped_products = {}

    # Read existing index if it exists
    if os.path.exists(index_file):
        with open(index_file, 'r') as f:
            scraped_products = json.load(f)

    # Read final_product_details.jsonl and extract product IDs
    details_file = 'espscraper/data/final_product_details.jsonl'
    if os.path.exists(details_file):
        with open(details_file, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    product_id = data.get('ProductID') or data.get('id')
                    if product_id:
                        scraped_products[str(product_id)] = {
                            'name': data.get('Name', 'Unknown'),
                            'url': data.get('SourceURL', ''),
                            'scraped_at': data.get('UpdateDate', 'Unknown')
                        }
                except:
                    continue

        # Save updated index
        with open(index_file, 'w') as f:
            json.dump(scraped_products, f, indent=2)

        print(f'✅ Product index updated with {len(scraped_products)} products')
    else:
        print('⚠️ No final_product_details.jsonl found, creating empty index')
        with open(index_file, 'w') as f:
            json.dump({}, f)

if __name__ == "__main__":
    create_product_index() 