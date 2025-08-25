#!/usr/bin/env python3
"""
Test the import functionality with LocalWP site
"""
import os
import sys
import json
from datetime import datetime

# Add the current directory to Python path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from import_to_wordpress import fetch_existing_products, import_product_to_wp

def test_localwp_import():
    """Test the import functionality with LocalWP"""
    print("🧪 Testing LocalWP Import")
    print("=" * 40)
    
    # LocalWP configuration
    wp_api_url = "https://unwritten-bottle.localsite.io/wp-json/promostandards-importer/v1"
    wp_api_key = "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"
    basic_auth_user = "admin"
    # Get password from environment variable (for GitHub Actions) or prompt
    basic_auth_pass = os.getenv('LOCALWP_PASSWORD')
    if not basic_auth_pass:
        basic_auth_pass = input("Enter your LocalWP password: ").strip()
    
    if not basic_auth_pass:
        print("❌ No password provided")
        return
    
    print(f"API URL: {wp_api_url}")
    print(f"API Key: {wp_api_key[:10]}...")
    print(f"Basic Auth User: {basic_auth_user}")
    
    # Test 1: Fetch existing products
    print(f"\n🔍 Test 1: Fetch existing products")
    try:
        existing = fetch_existing_products(wp_api_url, wp_api_key, basic_auth_user, basic_auth_pass)
        print(f"✅ Successfully fetched {len(existing)} existing products")
        print(f"Sample products: {list(existing.keys())[:3]}")
    except Exception as e:
        print(f"❌ Failed to fetch existing products: {e}")
        return
    
    # Test 2: Import a test product
    print(f"\n🔍 Test 2: Import test product")
    test_product = {
        "product_id": "test_localwp_import",
        "name": "Test LocalWP Import Product",
        "description": "Testing if LocalWP import works without Cloudflare",
        "sku": "TEST-LOCAL-001",
        "price": "29.99",
        "categories": ["Test Category"],
        "images": [],
        "attributes": {}
    }
    
    try:
        result = import_product_to_wp(test_product, wp_api_url, wp_api_key, basic_auth_user, basic_auth_pass)
        print(f"✅ Successfully imported test product")
        print(f"Result: {result}")
    except Exception as e:
        print(f"❌ Failed to import test product: {e}")
        return
    
    # Test 3: Import multiple products quickly (to test rate limiting)
    print(f"\n🔍 Test 3: Import multiple products quickly")
    for i in range(3):
        test_product = {
            "product_id": f"test_localwp_batch_{i}",
            "name": f"Test LocalWP Batch Product {i}",
            "description": f"Testing batch import {i}",
            "sku": f"TEST-BATCH-{i:03d}",
            "price": f"{19.99 + i}",
            "categories": ["Test Category"],
            "images": [],
            "attributes": {}
        }
        
        try:
            result = import_product_to_wp(test_product, wp_api_url, wp_api_key, basic_auth_user, basic_auth_pass)
            print(f"✅ Successfully imported batch product {i}")
        except Exception as e:
            print(f"❌ Failed to import batch product {i}: {e}")
            break
    
    print(f"\n🎉 LocalWP tests completed!")
    
    # Save results for GitHub Actions
    results = {
        'test_type': 'localwp',
        'timestamp': datetime.now().isoformat(),
        'wp_api_url': wp_api_url,
        'basic_auth_user': basic_auth_user,
        'tests_completed': True,
        'summary': 'LocalWP import test completed successfully'
    }
    
    with open('test_results.json', 'w') as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    test_localwp_import()
