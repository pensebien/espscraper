#!/usr/bin/env python3
"""
WordPress Import Script (Batch-Aware, Global Limit, Resumable)
Imports up to a global product limit from batch files to WordPress via REST API.
Supports 'sync' (only new/updated) and 'override' (all) modes.
Tracks progress by productID and batch/line for robust resume.
"""
import os
import sys
import json
import glob
import requests
import logging
from datetime import datetime
from espscraper.batch_processor import BatchProcessor

PROGRESS_FILE = "import_progress.json"


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_progress(progress):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)


def fetch_existing_products(
    wp_api_url, wp_api_key, basic_auth_user=None, basic_auth_pass=None
):
    """Fetch existing products from WordPress for sync mode."""
    if wp_api_url.endswith("/upload"):
        existing_url = wp_api_url.replace("/upload", "/existing-products")
    else:
        existing_url = wp_api_url.rstrip("/") + "/existing-products"
    headers = {"X-API-Key": wp_api_key}
    auth = (
        (basic_auth_user, basic_auth_pass)
        if basic_auth_user and basic_auth_pass
        else None
    )
    try:
        resp = requests.get(existing_url, headers=headers, auth=auth, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        existing = {}
        for prod in data.get("products", []):
            pid = str(prod.get("product_id"))
            if pid:
                existing[pid] = prod
        return existing
    except Exception as e:
        logging.warning(f"Failed to fetch existing products: {e}")
        return {}


def import_product_to_wp(
    product, wp_api_url, wp_api_key, basic_auth_user=None, basic_auth_pass=None
):
    """Import a single product to WordPress via REST API."""
    headers = {"Authorization": f"Bearer {wp_api_key}"}
    files = {"file": ("product.json", json.dumps(product), "application/json")}
    auth = (
        (basic_auth_user, basic_auth_pass)
        if basic_auth_user and basic_auth_pass
        else None
    )
    try:
        resp = requests.post(
            wp_api_url + "/upload", headers=headers, files=files, auth=auth, timeout=60
        )
        if resp.status_code == 200:
            return True, resp.json()
        else:
            logging.warning(f"Failed to import product: {resp.status_code} {resp.text}")
            return False, resp.text
    except Exception as e:
        logging.warning(f"Exception importing product: {e}")
        return False, str(e)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="WordPress Import Script (Batch, Global Limit, Resumable)"
    )
    parser.add_argument(
        "--mode",
        default=os.getenv("IMPORT_MODE", "sync"),
        choices=["sync", "override"],
        help="Import mode",
    )
    parser.add_argument(
        "--product-limit",
        type=int,
        default=int(os.getenv("PRODUCT_LIMIT", "100")),
        help="Total number of products to import",
    )
    parser.add_argument("--wp-api-url", default=os.getenv("WP_API_URL"), required=True)
    parser.add_argument("--wp-api-key", default=os.getenv("WP_API_KEY"), required=True)
    parser.add_argument("--wp-basic-auth-user", default=os.getenv("WP_BASIC_AUTH_USER"))
    parser.add_argument("--wp-basic-auth-pass", default=os.getenv("WP_BASIC_AUTH_PASS"))
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    print(
        f"\n🚀 Starting WordPress import: mode={args.mode}, product_limit={args.product_limit}"
    )

    # Load or reset progress
    progress = load_progress()
    if progress and (
        progress.get("mode") != args.mode or progress.get("limit") != args.product_limit
    ):
        print("⚠️ Mode or limit changed since last run. Resetting progress.")
        progress = {}
    imported = progress.get("imported", 0)
    imported_ids = set(progress.get("imported_ids", []))
    last_batch = progress.get("last_batch_file")
    last_line = progress.get("last_line_number")
    batch_line_map = progress.get(
        "batch_line_map", {}
    )  # {batch_file: last_line_number}

    # Fetch existing products for sync mode
    existing_products = {}
    if args.mode == "sync":
        print("🔍 Fetching existing products from WordPress for sync mode...")
        existing_products = fetch_existing_products(
            args.wp_api_url,
            args.wp_api_key,
            args.wp_basic_auth_user,
            args.wp_basic_auth_pass,
        )
        print(f"Found {len(existing_products)} existing products in store.")

    # Prepare batch processor
    bp = BatchProcessor()
    total = args.product_limit
    start_time = datetime.now()
    current_imported = imported
    current_batch_file = None
    current_line_number = 0

    # Iterate batches and lines, resuming as needed
    batch_files = [
        f
        for f in sorted(os.listdir(bp.batch_dir))
        if f.startswith(bp.batch_prefix) and f.endswith(".jsonl")
    ]
    for batch_file in batch_files:
        batch_path = os.path.join(bp.batch_dir, batch_file)
        skip_lines = batch_line_map.get(batch_file, 0)
        with open(batch_path, "r") as f:
            for line_num, line in enumerate(f, 1):
                if current_imported >= total:
                    break
                if line_num <= skip_lines:
                    continue  # Already processed in previous run
                line = line.strip()
                if not line:
                    continue
                try:
                    product = json.loads(line)
                    product_id = str(
                        product.get("ProductID") or product.get("product_id")
                    )
                    if product_id in imported_ids:
                        continue  # Already imported
                    # Sync mode: skip if not new/updated
                    if args.mode == "sync" and existing_products:
                        store_info = existing_products.get(product_id)
                        scraped_date = product.get("scrapedDate") or product.get(
                            "scraped_date"
                        )
                        store_date = (
                            store_info.get("last_modified") if store_info else None
                        )
                        if store_date and scraped_date and scraped_date <= store_date:
                            continue
                    # Import
                    success, result = import_product_to_wp(
                        product,
                        args.wp_api_url,
                        args.wp_api_key,
                        args.wp_basic_auth_user,
                        args.wp_basic_auth_pass,
                    )
                    if success:
                        current_imported += 1
                        imported_ids.add(product_id)
                        batch_line_map[batch_file] = line_num
                        save_progress(
                            {
                                "imported": current_imported,
                                "imported_ids": list(imported_ids),
                                "last_batch_file": batch_file,
                                "last_line_number": line_num,
                                "batch_line_map": batch_line_map,
                                "mode": args.mode,
                                "limit": args.product_limit,
                                "timestamp": datetime.now().isoformat(),
                            }
                        )
                        print(
                            f"✅ Imported [{current_imported}/{total}]: {product.get('Name') or product.get('name')} (ID: {product_id})"
                        )
                    else:
                        print(f"❌ Error importing: {result}")
                    if current_imported >= total:
                        break
                except Exception as e:
                    print(f"⚠️ Error processing line {line_num} in {batch_file}: {e}")
        if current_imported >= total:
            break

    duration = (datetime.now() - start_time).total_seconds()
    print(
        f"\n🎉 Import complete! Imported: {current_imported}, Duration: {duration:.1f}s"
    )
    # Save result for workflow
    with open("import_result.json", "w") as f:
        json.dump(
            {
                "total_imported": current_imported,
                "total_errors": 0,  # For simplicity, not tracking errors here
                "total_skipped": 0,  # Not tracking skipped in this version
                "mode": args.mode,
                "duration_seconds": duration,
                "timestamp": datetime.now().isoformat(),
            },
            f,
            indent=2,
        )
    print(f"📄 Import result saved to import_result.json")
    # On completion, remove progress file
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)


if __name__ == "__main__":
    main()
