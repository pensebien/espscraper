#!/usr/bin/env python3
"""
WordPress Import Script (Batch-Aware, Global Limit, Resumable)
Imports up to a global product limit from batch files to WordPress via REST API.
Supports 'sync' (only new/updated) and 'override' (all) modes.
Tracks progress by productID and batch/line for robust resume.
Includes heartbeat for real-time progress monitoring.
"""
import os
import sys
import json
import glob
import requests
import logging
import time
from datetime import datetime
from espscraper.batch_processor import BatchProcessor
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

PROGRESS_FILE = "import_progress.json"
HEARTBEAT_FILE = "import_heartbeat.json"


def create_retry_session():
    """Create a requests session with retry logic for Cloudflare protection."""
    session = requests.Session()
    
    # Configure retry strategy (more conservative to avoid triggering Cloudflare)
    retry_strategy = Retry(
        total=1,  # only 1 retry to avoid overwhelming Cloudflare
        backoff_factor=5,  # wait 5 seconds before retry
        status_forcelist=[429, 500, 502, 503, 504],  # don't retry on 403
        allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session


def get_cloudflare_headers():
    """Get comprehensive headers to bypass Cloudflare protection."""
    # Rotate User-Agents to appear more human-like
    user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    ]
    
    import random
    user_agent = random.choice(user_agents)
    
    return {
        "User-Agent": user_agent,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "DNT": "1",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"'
    }


def create_cloudflare_session():
    """Create a session that can bypass Cloudflare protection."""
    session = requests.Session()
    
    # Set up headers that look more like a real browser
    # Disable compression to avoid Brotli issues
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "identity",  # Disable compression to avoid Brotli issues
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "DNT": "1",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"'
    })
    
    return session

def establish_cloudflare_session(base_url):
    """Establish a session with Cloudflare by visiting the main site first."""
    session = create_cloudflare_session()
    
    try:
        print("🛡️ Establishing Cloudflare session...")
        
        # First, visit the main site to establish a session
        main_response = session.get(f"{base_url}", timeout=30)
        print(f"  Main site status: {main_response.status_code}")
        
        # Wait a bit to let Cloudflare process
        time.sleep(3)
        
        # Then visit the WordPress admin to establish WordPress session
        wp_admin_response = session.get(f"{base_url}/wp-admin", timeout=30)
        print(f"  WP Admin status: {wp_admin_response.status_code}")
        
        # Wait again
        time.sleep(2)
        
        # Finally, try to access the API base to establish API session
        api_base = f"{base_url}/wp-json"
        api_response = session.get(api_base, timeout=30)
        print(f"  API base status: {api_response.status_code}")
        
        print("✅ Cloudflare session established")
        return session
        
    except Exception as e:
        print(f"⚠️ Could not establish Cloudflare session: {e}")
        # Return a basic session as fallback
        return create_cloudflare_session()


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_progress(progress):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)


def update_heartbeat(
    status, imported=0, errors=0, total=0, current_product=None, mode=None
):
    """Update heartbeat file with current progress."""
    heartbeat = {
        "status": status,  # "running", "completed", "error", "stopped"
        "imported": imported,
        "errors": errors,
        "total": total,
        "percent": round((imported / total * 100) if total > 0 else 0, 1),
        "current_product": current_product,
        "mode": mode,
        "timestamp": datetime.now().isoformat(),
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    with open(HEARTBEAT_FILE, "w") as f:
        json.dump(heartbeat, f, indent=2)


def cleanup_heartbeat():
    """Remove heartbeat file when import is complete."""
    if os.path.exists(HEARTBEAT_FILE):
        os.remove(HEARTBEAT_FILE)


def fetch_existing_products(
    wp_api_url, wp_api_key, basic_auth_user=None, basic_auth_pass=None
):
    """Fetch existing products from WordPress for sync mode."""
    # Validate URL
    if not wp_api_url or wp_api_url == "null" or wp_api_url.strip() == "":
        raise ValueError(
            "WordPress API URL is required but not provided or is empty/null"
        )

    # Extract base URL for Cloudflare session
    base_url = wp_api_url.replace("/wp-json/promostandards-importer/v1/import-product", "")
    base_url = base_url.replace("/wp-json/promostandards-importer/v1/upload", "")
    base_url = base_url.replace("/wp-json/promostandards-importer/v1", "")
    
    # Construct the correct endpoint URL
    # Normalize the URL to avoid double-appending endpoints
    if wp_api_url.endswith("/upload"):
        existing_url = wp_api_url.replace("/upload", "/existing-products")
    elif wp_api_url.endswith("/import-product"):
        # Replace import-product with existing-products
        existing_url = wp_api_url.replace("/import-product", "/existing-products")
    else:
        # Ensure we have the full API URL
        existing_url = wp_api_url.rstrip("/") + "/existing-products"
    
    # Add API key header
    headers = {
        "X-API-Key": wp_api_key,
        "Accept-Encoding": "identity"  # Disable compression to avoid Brotli issues
    }
    
    auth = (
        (basic_auth_user, basic_auth_pass)
        if basic_auth_user
        and basic_auth_pass
        and basic_auth_user.strip()
        and basic_auth_pass.strip()
        else None
    )
    
    try:
        global _cloudflare_session, _base_url
        
        # Use global session if available and same base URL
        if _cloudflare_session is None or _base_url != base_url:
            _cloudflare_session = establish_cloudflare_session(base_url)
            _base_url = base_url
        
        # Add API headers to the session
        _cloudflare_session.headers.update(headers)
        
        resp = _cloudflare_session.get(existing_url, auth=auth, timeout=30)
        resp.raise_for_status()
        
        # Handle potential encoding issues
        try:
            data = resp.json()
        except json.JSONDecodeError as json_error:
            logging.warning(f"JSON decode error: {json_error}")
            logging.warning(f"Response content: {resp.text[:500]}")
            logging.warning(f"Response headers: {dict(resp.headers)}")
            
            # Try to fix common encoding issues
            try:
                # Try with different encoding
                content = resp.content.decode('utf-8', errors='ignore')
                data = json.loads(content)
                logging.info("✅ Successfully parsed JSON after encoding fix")
            except:
                logging.error("❌ Could not parse JSON even after encoding fix")
                # For staging/production, continue without existing products
                if "tmgdev.dedicatedmkt.com" in wp_api_url or "tmg.dedicatedmkt.com" in wp_api_url:
                    logging.info("Staging/Production detected - continuing without existing products check")
                elif "localhost" in wp_api_url or "localsite.io" in wp_api_url:
                    logging.info("Local development detected - continuing without existing products check")
                return {}
        
        existing = {}
        for prod in data.get("products", []):
            pid = str(prod.get("product_id"))
            if pid:
                existing[pid] = prod
        return existing
    except Exception as e:
        logging.warning(f"Failed to fetch existing products: {e}")
        # For local development, continue without existing products
        if "localhost" in wp_api_url or "localsite.io" in wp_api_url:
            logging.info("Local development detected - continuing without existing products check")
        return {}


def import_product_to_wp(
    product, wp_api_url, wp_api_key, basic_auth_user=None, basic_auth_pass=None
):
    """Import a single product to WordPress via REST API."""
    # Validate URL
    if not wp_api_url or wp_api_url == "null" or wp_api_url.strip() == "":
        raise ValueError(
            "WordPress API URL is required but not provided or is empty/null"
        )

    # Extract base URL for Cloudflare session
    base_url = wp_api_url.replace("/wp-json/promostandards-importer/v1/import-product", "")
    base_url = base_url.replace("/wp-json/promostandards-importer/v1/upload", "")
    base_url = base_url.replace("/wp-json/promostandards-importer/v1", "")

    # Construct the correct import-product endpoint URL
    # Normalize the URL to avoid double-appending endpoints
    if wp_api_url.endswith("/upload"):
        import_url = wp_api_url.replace("/upload", "/import-product")
    elif wp_api_url.endswith("/import-product"):
        # URL already has the correct endpoint
        import_url = wp_api_url
    else:
        # Ensure we have the full API URL
        import_url = wp_api_url.rstrip("/") + "/import-product"

    # Add API headers
    headers = {
        "Content-Type": "application/json", 
        "X-API-Key": wp_api_key,
        "Accept-Encoding": "identity"  # Disable compression to avoid Brotli issues
    }
    
    auth = (
        (basic_auth_user, basic_auth_pass)
        if basic_auth_user and basic_auth_pass
        else None
    )
    
    # Debug: Show what we're about to send
    print(f"🔍 Debug: Import request details")
    print(f"  URL: {import_url}")
    print(f"  Headers: {headers}")
    print(f"  Auth: {auth}")
    print(f"  Product ID: {product.get('product_id', 'unknown')}")
    print(f"  Product Name: {product.get('name', 'unknown')}")
    
    try:
        global _cloudflare_session, _base_url
        
        # Use global session if available and same base URL
        if _cloudflare_session is None or _base_url != base_url:
            _cloudflare_session = establish_cloudflare_session(base_url)
            _base_url = base_url
        
        # Add API headers to the session
        _cloudflare_session.headers.update(headers)
        
        resp = _cloudflare_session.post(
            import_url,
            json=product,
            auth=auth,
            timeout=60,  # Increased timeout for better reliability
        )
        
        # Debug: Show response details
        print(f"🔍 Debug: Response details")
        print(f"  Status Code: {resp.status_code}")
        print(f"  Response Headers: {dict(resp.headers)}")
        print(f"  Response Content (first 500 chars): {resp.text[:500]}")
        print(f"  Content Encoding: {resp.headers.get('Content-Encoding', 'none')}")
        
        resp.raise_for_status()
        
        # Handle potential JSON parsing issues for import response
        try:
            result = resp.json()
        except json.JSONDecodeError as json_error:
            logging.warning(f"Import response JSON decode error: {json_error}")
            logging.warning(f"Import response content: {resp.text[:500]}")
            
            # Try to fix encoding issues
            try:
                content = resp.content.decode('utf-8', errors='ignore')
                result = json.loads(content)
                logging.info("✅ Successfully parsed import response after encoding fix")
            except:
                logging.error("❌ Could not parse import response even after encoding fix")
                # Return a basic success response
                result = {"success": True, "message": "Product imported (response parsing failed)"}
        
        # Add delay to avoid overwhelming the server
        # Shorter delay for local development
        if "localhost" in wp_api_url or "localsite.io" in wp_api_url:
            time.sleep(0.5)  # Short delay for local development
        else:
            time.sleep(3)  # Longer delay for production to avoid Cloudflare
        
        return result
    except requests.exceptions.RequestException as e:
        print(f"🔍 Debug: Request exception details")
        print(f"  Exception type: {type(e).__name__}")
        print(f"  Exception message: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  Response status: {e.response.status_code}")
            print(f"  Response content: {e.response.text[:500]}")
            
            # Special handling for 403 errors
            if e.response.status_code == 403:
                print(f"  🛡️ Cloudflare 403 detected - this might be temporary")
                print(f"  💡 Consider increasing delays or using different headers")
                # Don't raise immediately, let the retry logic handle it
                time.sleep(5)  # Wait 5 seconds before continuing
                
        raise Exception(f"Failed to import product: {str(e)}")


# Global session for Cloudflare bypass
_cloudflare_session = None
_base_url = None

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
    parser.add_argument(
        "--use-enhanced-files",
        action="store_true",
        default=os.getenv("USE_ENHANCED_FILES", "false").lower() == "true",
        help="Use enhanced files instead of batch files",
    )
    parser.add_argument("--wp-api-url", default=os.getenv("WP_API_URL"), required=True)
    parser.add_argument("--wp-api-key", default=os.getenv("WP_API_KEY"), required=True)
    parser.add_argument(
        "--wp-basic-auth-user", default=os.getenv("WP_BASIC_AUTH_USER"), required=False
    )
    parser.add_argument(
        "--wp-basic-auth-pass", default=os.getenv("WP_BASIC_AUTH_PASS"), required=False
    )
    args = parser.parse_args()

    # Convert string to boolean
    use_enhanced_files = args.use_enhanced_files

    # Validate required arguments
    if (
        not args.wp_api_url
        or args.wp_api_url == "null"
        or args.wp_api_url.strip() == ""
    ):
        print(
            "❌ Error: WordPress API URL is required but not provided or is empty/null"
        )
        print(
            "   Please provide --wp-api-url parameter or set WP_API_URL environment variable"
        )
        sys.exit(1)

    if (
        not args.wp_api_key
        or args.wp_api_key == "null"
        or args.wp_api_key.strip() == ""
    ):
        print(
            "❌ Error: WordPress API Key is required but not provided or is empty/null"
        )
        print(
            "   Please provide --wp-api-key parameter or set WP_API_KEY environment variable"
        )
        sys.exit(1)

    # Basic auth is optional - only validate if provided
    if args.wp_basic_auth_user and (
        not args.wp_basic_auth_pass
        or args.wp_basic_auth_pass == "null"
        or args.wp_basic_auth_pass.strip() == ""
    ):
        print(
            "❌ Error: WordPress Basic Auth password is required when username is provided"
        )
        print(
            "   Please provide --wp-basic-auth-pass parameter or set WP_BASIC_AUTH_PASS environment variable"
        )
        sys.exit(1)

    if args.wp_basic_auth_pass and (
        not args.wp_basic_auth_user
        or args.wp_basic_auth_user == "null"
        or args.wp_basic_auth_user.strip() == ""
    ):
        print(
            "❌ Error: WordPress Basic Auth username is required when password is provided"
        )
        print(
            "   Please provide --wp-basic-auth-user parameter or set WP_BASIC_AUTH_USER environment variable"
        )
        sys.exit(1)
    
    # If neither Basic Auth credential is provided, that's fine - some environments don't need it
    if not args.wp_basic_auth_user and not args.wp_basic_auth_pass:
        print("🌐 No Basic Auth credentials provided - this is fine for staging/production environments")

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    print(
        f"\n🚀 Starting WordPress import: mode={args.mode}, product_limit={args.product_limit}, use_enhanced_files={use_enhanced_files}"
    )

    # Initialize heartbeat
    update_heartbeat("starting", 0, 0, args.product_limit, None, args.mode)

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
        update_heartbeat(
            "fetching_existing",
            imported,
            0,
            args.product_limit,
            "Fetching existing products...",
            args.mode,
        )
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
    current_errors = 0
    current_batch_file = None
    current_line_number = 0

    # Update heartbeat with initial state
    update_heartbeat(
        "running",
        current_imported,
        current_errors,
        total,
        "Starting import...",
        args.mode,
    )

    # Determine which directory and file pattern to use
    if use_enhanced_files:
        import_dir = "enhanced"
        file_pattern = "*_enhanced.jsonl"
        print("📁 Using enhanced files for import")
    else:
        import_dir = bp.batch_dir
        file_pattern = f"{bp.batch_prefix}*.jsonl"
        print("📁 Using batch files for import")

    # Iterate files and lines, resuming as needed
    import_files = [
        f
        for f in sorted(os.listdir(import_dir))
        if f.endswith(".jsonl")
        and (
            use_enhanced_files
            and "_enhanced.jsonl" in f
            or not use_enhanced_files
            and f.startswith(bp.batch_prefix)
        )
    ]

    print(f"📁 Found {len(import_files)} files to process")

    for batch_file in import_files:
        batch_path = os.path.join(import_dir, batch_file)
        skip_lines = batch_line_map.get(batch_file, 0)

        print(f"📄 Processing batch file: {batch_file}")

        with open(batch_path, "r") as f:
            for line_num, line in enumerate(f, 1):
                if current_imported >= total:
                    print(f"✅ Reached product limit ({total}). Stopping import.")
                    break

                if line_num <= skip_lines:
                    continue  # Already processed in previous run

                line = line.strip()
                if not line:
                    continue

                # Additional check for whitespace-only lines
                if not line or line.isspace():
                    continue

                try:
                    product = json.loads(line)

                    # Handle enhanced file structure where product data is nested
                    if "product" in product and isinstance(product["product"], dict):
                        # Enhanced file structure: {"product": {...}, "pricing": {...}, ...}
                        product_data = product["product"]
                        # Merge other sections into the product data
                        if "pricing" in product:
                            product_data["pricing_info"] = product["pricing"]
                        if "attributes" in product:
                            product_data["attributes"] = product["attributes"]
                        if "imprinting" in product:
                            product_data["imprinting"] = product["imprinting"]
                        if "supplier" in product:
                            product_data["supplier_info"] = product["supplier"]
                        if "production" in product:
                            product_data["production_info"] = product["production"]
                        if "shipping" in product:
                            product_data["shipping"] = product["shipping"]
                        if "specifications" in product:
                            # Merge specifications into product data
                            specs = product["specifications"]
                            if "weight" in specs:
                                product_data["weight"] = specs["weight"]
                            if "dimensions" in specs:
                                product_data["dimensions"] = specs["dimensions"]
                        if "fpd_config" in product:
                            product_data["fpd_config"] = product["fpd_config"]
                        if "variants" in product:
                            product_data["variants"] = product["variants"]
                        if "virtual_samples" in product:
                            product_data["virtual_samples"] = product["virtual_samples"]
                        if "related_products" in product:
                            product_data["related_products"] = product[
                                "related_products"
                            ]
                        if "services" in product:
                            product_data["services"] = product["services"]
                        if "warnings" in product:
                            product_data["warnings"] = product["warnings"]
                        if "categories" in product:
                            product_data["categories"] = product["categories"]
                        if "themes" in product:
                            product_data["themes"] = product["themes"]

                        product = product_data

                    product_id = str(
                        product.get("ProductID")
                        or product.get("product_id")
                        or product.get("id")
                    )
                    product_name = product.get("Name") or product.get(
                        "name", "Unknown Product"
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

                    # Update heartbeat with current product
                    current_product_info = f"{product_name} (ID: {product_id})"
                    update_heartbeat(
                        "running",
                        current_imported,
                        current_errors,
                        total,
                        current_product_info,
                        args.mode,
                    )

                    # Import
                    try:
                        result = import_product_to_wp(
                            product,
                            args.wp_api_url,
                            args.wp_api_key,
                            args.wp_basic_auth_user,
                            args.wp_basic_auth_pass,
                        )

                        # Check if import was successful
                        if result.get("success") or result.get("imported", 0) > 0:
                            current_imported += 1
                            imported_ids.add(product_id)
                            batch_line_map[batch_file] = line_num
                            print(f"✅ Imported: {product_name} (ID: {product_id})")
                        else:
                            current_errors += 1
                            error_msg = result.get("message", "Unknown error")
                            print(
                                f"❌ Failed to import: {product_name} (ID: {product_id}) - {error_msg}"
                            )

                    except Exception as e:
                        current_errors += 1
                        print(
                            f"❌ Exception importing: {product_name} (ID: {product_id}) - {str(e)}"
                        )

                    # Update progress file
                    save_progress(
                        {
                            "imported": current_imported,
                            "errors": current_errors,
                            "imported_ids": list(imported_ids),
                            "last_batch_file": batch_file,
                            "last_line_number": line_num,
                            "batch_line_map": batch_line_map,
                            "mode": args.mode,
                            "limit": args.product_limit,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

                    # Update heartbeat every 5 products or on errors
                    if current_imported % 5 == 0 or current_errors > 0:
                        update_heartbeat(
                            "running",
                            current_imported,
                            current_errors,
                            total,
                            current_product_info,
                            args.mode,
                        )

                except json.JSONDecodeError as e:
                    current_errors += 1
                    print(
                        f"❌ JSON parsing error on line {line_num} in {batch_file}: {e}"
                    )
                    print(f"   Line content (first 100 chars): {repr(line[:100])}")
                    update_heartbeat(
                        "running",
                        current_imported,
                        current_errors,
                        total,
                        f"JSON Error: {str(e)}",
                        args.mode,
                    )
                except Exception as e:
                    current_errors += 1
                    print(f"❌ Error processing line {line_num} in {batch_file}: {e}")
                    update_heartbeat(
                        "running",
                        current_imported,
                        current_errors,
                        total,
                        f"Error: {str(e)}",
                        args.mode,
                    )

        if current_imported >= total:
            break

    # Final update
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print(f"\n🎉 Import complete!")
    print(f"📊 Total imported: {current_imported}")
    print(f"❌ Total errors: {current_errors}")
    print(f"⏱️ Duration: {duration:.1f} seconds")

    # Update heartbeat with completion status
    if current_errors == 0:
        update_heartbeat(
            "completed",
            current_imported,
            current_errors,
            total,
            "Import completed successfully",
            args.mode,
        )
    else:
        update_heartbeat(
            "completed_with_errors",
            current_imported,
            current_errors,
            total,
            f"Import completed with {current_errors} errors",
            args.mode,
        )

    # Clean up progress file on successful completion
    if current_imported > 0 and current_errors == 0:
        cleanup_heartbeat()
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
        print("🧹 Cleaned up progress files")


if __name__ == "__main__":
    main()
