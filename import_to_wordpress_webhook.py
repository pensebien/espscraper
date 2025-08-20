#!/usr/bin/env python3
"""
Webhook-based WordPress Import Script
This script runs locally and can be triggered from WordPress to avoid Cloudflare issues
"""
import os
import sys
import json
import glob
import requests
import logging
import time
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def create_retry_session():
    """Create a requests session with retry logic"""
    session = requests.Session()
    retry_strategy = Retry(
        total=5,  # More retries
        backoff_factor=2,  # Longer delays
        status_forcelist=[403, 429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def load_products_from_files(use_enhanced_files=True, product_limit=100):
    """Load products from JSONL files"""
    products = []
    
    if use_enhanced_files:
        pattern = "enhanced/*_enhanced.jsonl"
    else:
        pattern = "batch/*.jsonl"
    
    files = glob.glob(pattern)
    logging.info(f"Found {len(files)} files matching pattern: {pattern}")
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if len(products) >= product_limit:
                        break
                    
                    line = line.strip()
                    if line:
                        try:
                            product = json.loads(line)
                            products.append(product)
                        except json.JSONDecodeError as e:
                            logging.warning(f"Invalid JSON in {file_path}:{line_num}: {e}")
                            continue
        except Exception as e:
            logging.error(f"Error reading {file_path}: {e}")
    
    logging.info(f"Loaded {len(products)} products")
    return products

def import_products_via_webhook(products, webhook_url, api_key):
    """Import products via webhook endpoint"""
    session = create_retry_session()
    
    # Add aggressive headers to bypass Cloudflare
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }
    
    successful_imports = 0
    failed_imports = 0
    
    for i, product in enumerate(products, 1):
        try:
            logging.info(f"Importing product {i}/{len(products)}: {product.get('name', 'Unknown')}")
            
            # Add longer delay between requests
            if i > 1:
                time.sleep(2)  # 2 second delay between requests
            
            response = session.post(
                webhook_url,
                json=product,
                headers=headers,
                timeout=60
            )
            
            if response.status_code in [200, 201, 409]:
                successful_imports += 1
                logging.info(f"✅ Successfully imported: {product.get('name', 'Unknown')}")
            else:
                failed_imports += 1
                logging.error(f"❌ Failed to import {product.get('name', 'Unknown')}: HTTP {response.status_code}")
                logging.error(f"Response: {response.text[:500]}")
                
        except Exception as e:
            failed_imports += 1
            logging.error(f"❌ Exception importing {product.get('name', 'Unknown')}: {e}")
    
    return successful_imports, failed_imports

def main():
    """Main function"""
    print("🚀 Webhook-based WordPress Import")
    print("=" * 50)
    
    # Configuration
    webhook_url = "https://tmgdev.dedicatedmkt.com/wp-json/promostandards-importer/v1/import-product"
    api_key = "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"
    use_enhanced_files = True
    product_limit = 10  # Start with a small number for testing
    
    print(f"Webhook URL: {webhook_url}")
    print(f"API Key: {api_key[:10]}...")
    print(f"Use Enhanced Files: {use_enhanced_files}")
    print(f"Product Limit: {product_limit}")
    
    # Load products
    print("\n📥 Loading products...")
    products = load_products_from_files(use_enhanced_files, product_limit)
    
    if not products:
        print("❌ No products found!")
        return
    
    # Import products
    print(f"\n📤 Importing {len(products)} products...")
    successful, failed = import_products_via_webhook(products, webhook_url, api_key)
    
    # Summary
    print(f"\n📊 Import Summary:")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success Rate: {(successful/(successful+failed)*100):.1f}%")

if __name__ == "__main__":
    main()
