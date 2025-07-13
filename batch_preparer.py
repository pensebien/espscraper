#!/usr/bin/env python3
"""
Batch File Preparer for PromoStandards Importer
Handles deduplication, filtering, and batch preparation for import
"""

import os
import json
import glob
import argparse
from datetime import datetime
from typing import List, Dict, Any, Set


class BatchPreparer:
    def __init__(self, output_dir: str = "prepared_batches"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def load_products_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Load products from a JSONL file"""
        products = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        product = json.loads(line)
                        products.append(product)
                    except json.JSONDecodeError as e:
                        print(f"⚠️ Error parsing line {line_num} in {file_path}: {e}")
                        continue
        except FileNotFoundError:
            print(f"❌ File not found: {file_path}")
            return []

        print(f"📁 Loaded {len(products)} products from {file_path}")
        return products

    def get_product_identifier(self, product: Dict[str, Any]) -> str:
        """Get unique identifier for a product"""
        # Try different possible field names
        product_id = (
            product.get("product_id") or product.get("ProductID") or product.get("id")
        )

        if product_id:
            return str(product_id)

        # Fallback to SKU
        sku = product.get("sku") or product.get("SKU")
        if isinstance(sku, list) and sku:
            sku = sku[0].get("SKU", "") if isinstance(sku[0], dict) else sku[0]

        if sku:
            return str(sku)

        # Last resort: use name + timestamp
        name = product.get("name") or product.get("Name", "Unknown")
        return f"{name}_{datetime.now().timestamp()}"

    def filter_products_by_mode(
        self,
        products: List[Dict[str, Any]],
        mode: str,
        existing_products: Set[str] = None,
    ) -> List[Dict[str, Any]]:
        """Filter products based on import mode"""
        if not existing_products:
            existing_products = set()

        filtered_products = []
        skipped_count = 0

        for product in products:
            product_id = self.get_product_identifier(product)

            if mode == "scrape":
                # Only include products that don't exist
                if product_id not in existing_products:
                    filtered_products.append(product)
                else:
                    skipped_count += 1
                    print(f"⏭️ Skipping existing product: {product_id}")

            elif mode == "override":
                # Include all products
                filtered_products.append(product)

            elif mode == "sync":
                # Include all products (will be updated if they exist)
                filtered_products.append(product)
                if product_id in existing_products:
                    print(f"🔄 Will update existing product: {product_id}")
                else:
                    print(f"🆕 Will create new product: {product_id}")

        print(
            f"✅ Filtered products: {len(filtered_products)} to import, {skipped_count} skipped"
        )
        return filtered_products

    def split_into_batches(
        self, products: List[Dict[str, Any]], batch_size: int = 50
    ) -> List[List[Dict[str, Any]]]:
        """Split products into smaller batches"""
        batches = []
        for i in range(0, len(products), batch_size):
            batch = products[i : i + batch_size]
            batches.append(batch)

        print(
            f"📦 Split {len(products)} products into {len(batches)} batches of {batch_size}"
        )
        return batches

    def save_batch(self, batch: List[Dict[str, Any]], batch_name: str) -> str:
        """Save a batch to a JSONL file"""
        file_path = os.path.join(self.output_dir, f"{batch_name}.jsonl")

        with open(file_path, "w", encoding="utf-8") as f:
            for product in batch:
                f.write(json.dumps(product, ensure_ascii=False) + "\n")

        print(f"💾 Saved batch {batch_name} with {len(batch)} products to {file_path}")
        return file_path

    def prepare_batches(
        self,
        input_files: List[str],
        mode: str = "scrape",
        batch_size: int = 50,
        existing_products: Set[str] = None,
    ) -> List[str]:
        """Prepare batches from input files"""
        print(f"🚀 Preparing batches in {mode} mode...")

        # Load all products from input files
        all_products = []
        for file_path in input_files:
            products = self.load_products_from_file(file_path)
            all_products.extend(products)

        if not all_products:
            print("❌ No products found in input files")
            return []

        # Remove duplicates based on product identifier
        unique_products = []
        seen_ids = set()
        duplicates_removed = 0

        for product in all_products:
            product_id = self.get_product_identifier(product)
            if product_id not in seen_ids:
                unique_products.append(product)
                seen_ids.add(product_id)
            else:
                duplicates_removed += 1

        print(f"🔄 Removed {duplicates_removed} duplicate products")

        # Filter products based on mode
        filtered_products = self.filter_products_by_mode(
            unique_products, mode, existing_products
        )

        if not filtered_products:
            print("❌ No products to import after filtering")
            return []

        # Split into batches
        batches = self.split_into_batches(filtered_products, batch_size)

        # Save batches
        batch_files = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for i, batch in enumerate(batches, 1):
            batch_name = f"prepared_batch_{timestamp}_{i}"
            file_path = self.save_batch(batch, batch_name)
            batch_files.append(file_path)

        print(f"✅ Prepared {len(batch_files)} batch files for import")
        return batch_files

    def get_existing_products_from_wordpress(
        self, api_url: str, api_key: str
    ) -> Set[str]:
        """Get existing product IDs from WordPress"""
        try:
            import requests

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            response = requests.get(
                f"{api_url}/existing-products", headers=headers, timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                existing_ids = set()

                for product in data.get("products", []):
                    product_id = product.get("product_id")
                    sku = product.get("sku")

                    if product_id:
                        existing_ids.add(str(product_id))
                    if sku:
                        existing_ids.add(str(sku))

                print(f"📊 Found {len(existing_ids)} existing products in WordPress")
                return existing_ids
            else:
                print(
                    f"⚠️ Could not fetch existing products: HTTP {response.status_code}"
                )
                return set()

        except Exception as e:
            print(f"⚠️ Error fetching existing products: {e}")
            return set()


def main():
    parser = argparse.ArgumentParser(
        description="Prepare batch files for WordPress import"
    )
    parser.add_argument(
        "--input", "-i", nargs="+", required=True, help="Input JSONL files to process"
    )
    parser.add_argument(
        "--mode",
        "-m",
        default="scrape",
        choices=["scrape", "override", "sync"],
        help="Import mode (default: scrape)",
    )
    parser.add_argument(
        "--batch-size",
        "-b",
        type=int,
        default=50,
        help="Number of products per batch (default: 50)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default="prepared_batches",
        help="Output directory for prepared batches (default: prepared_batches)",
    )
    parser.add_argument(
        "--wp-api-url", help="WordPress API URL for fetching existing products"
    )
    parser.add_argument("--wp-api-key", help="WordPress API key")

    args = parser.parse_args()

    # Initialize preparer
    preparer = BatchPreparer(args.output_dir)

    # Get existing products if WordPress API is provided
    existing_products = set()
    if args.wp_api_url and args.wp_api_key:
        existing_products = preparer.get_existing_products_from_wordpress(
            args.wp_api_url, args.wp_api_key
        )

    # Prepare batches
    batch_files = preparer.prepare_batches(
        input_files=args.input,
        mode=args.mode,
        batch_size=args.batch_size,
        existing_products=existing_products,
    )

    if batch_files:
        print(f"\n🎉 Batch preparation complete!")
        print(f"📁 Prepared {len(batch_files)} batch files in {args.output_dir}/")
        print(f"📋 Batch files:")
        for file_path in batch_files:
            print(f"  - {file_path}")
    else:
        print("\n❌ No batch files were prepared")


if __name__ == "__main__":
    main()
