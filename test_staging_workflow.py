#!/usr/bin/env python3
"""
Test staging workflow with corrected API keys
"""
import os
import sys

# Add the current directory to Python path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from import_to_wordpress import fetch_existing_products, import_product_to_wp

def test_staging_workflow():
    """Test the staging workflow with corrected API keys"""
    print("🧪 Testing Staging Workflow (Fixed API Keys)")
    print("=" * 50)
    
    # Staging configuration with CORRECTED API key
    wp_api_url = "https://tmgdev.dedicatedmkt.com/wp-json/promostandards-importer/v1"
    wp_api_key = "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"  # ← This is the CORRECT API key
    
    print(f"API URL: {wp_api_url}")
    print(f"API Key: {wp_api_key[:10]}...")
    print(f"Note: Using CORRECTED API key (not the GitHub params secret)")
    
    # Test 1: Fetch existing products
    print(f"\n🔍 Test 1: Fetch existing products")
    try:
        existing = fetch_existing_products(wp_api_url, wp_api_key)
        print(f"✅ Successfully fetched {len(existing)} existing products")
        print(f"Sample products: {list(existing.keys())[:3]}")
    except Exception as e:
        print(f"❌ Failed to fetch existing products: {e}")
        return
    
    # Test 2: Import a test product
    print(f"\n🔍 Test 2: Import test product")
    test_product = {
        "product_id": "test_staging_fixed_api",
        "name": "Test Staging Fixed API Product",
        "description": "Testing staging with corrected API key",
        "sku": "TEST-STAGING-FIXED",
        "price": "39.99",
        "categories": ["Test Category"],
        "images": [],
        "attributes": {}
    }
    
    try:
        result = import_product_to_wp(test_product, wp_api_url, wp_api_key)
        print(f"✅ Successfully imported test product")
        print(f"Result: {result}")
    except Exception as e:
        print(f"❌ Failed to import test product: {e}")
        return
    
    # Test 3: Import multiple products (to test rate limiting)
    print(f"\n🔍 Test 3: Import multiple products (rate limit test)")
    for i in range(3):
        test_product = {
            "product_id": f"test_staging_batch_{i}",
            "name": f"Test Staging Batch Product {i}",
            "description": f"Testing batch import {i} with fixed API key",
            "sku": f"TEST-BATCH-{i:03d}",
            "price": f"{29.99 + i}",
            "categories": ["Test Category"],
            "images": [],
            "attributes": {}
        }
        
        try:
            result = import_product_to_wp(test_product, wp_api_url, wp_api_key)
            print(f"✅ Successfully imported batch product {i}")
        except Exception as e:
            print(f"❌ Failed to import batch product {i}: {e}")
            break
    
    print(f"\n🎉 Staging workflow test completed!")
    print(f"💡 If this works, the GitHub workflow should now work too!")

if __name__ == "__main__":
    test_staging_workflow()
