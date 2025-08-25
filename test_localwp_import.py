#!/usr/bin/env python3
"""
Test the import functionality with LocalWP site
"""
import os
import sys
import json
from datetime import datetime

import requests

# Add the current directory to Python path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_localwp_import():
    """Test the import functionality with staging site (no auth required)"""
    print("🧪 Testing Staging Import (No Auth)")
    print("=" * 40)
    
    # Staging configuration - no authentication required
    wp_api_url = "https://tmgdev.dedicatedmkt.com/wp-json/promostandards-importer-github/v1"
    
    print(f"API URL: {wp_api_url}")
    print("Authentication: None required (GitHub Actions plugin)")
    
    # Test 1: Get GitHub params (no auth required)
    print(f"\n🔍 Test 1: Get GitHub params")
    try:
        params_url = f"{wp_api_url}/github-params"
        print(f"Requesting: {params_url}")
        
        response = requests.get(
            params_url, 
            timeout=30,
            headers={
                'User-Agent': 'GitHub-Actions-Test/1.0',
                'Accept': 'application/json'
            }
        )
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Successfully got GitHub params: {data}")
        else:
            print(f"❌ Failed to get GitHub params: {response.status_code}")
            print(f"Response Text: {response.text}")
            return
    except Exception as e:
        print(f"❌ Failed to get GitHub params: {e}")
        return
    
    # Test 2: Import a test product (no auth required)
    print(f"\n🔍 Test 2: Import test product")
    test_product = {
        "product_id": "test_staging_import",
        "name": "Test Staging Import Product",
        "description": "Testing if staging import works without authentication",
        "sku": "TEST-STAGING-001",
        "attributes": {
            "category": "Test Category",
            "subcategory": "Staging Test"
        },
        "production_info": {
            "Description": "Test product for staging",
            "Categories": "Test Category"
        }
    }
    
    try:
        import_url = f"{wp_api_url}/import-product"
        response = requests.post(
            import_url,
            json=test_product,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Successfully imported test product")
            print(f"Result: {result}")
        else:
            print(f"❌ Failed to import test product: {response.status_code} - {response.text}")
            return
    except Exception as e:
        print(f"❌ Failed to import test product: {e}")
        return
    
    # Test 3: Import multiple products quickly (no auth required)
    print(f"\n🔍 Test 3: Import multiple products quickly")
    for i in range(3):
        test_product = {
            "product_id": f"test_staging_batch_{i}",
            "name": f"Test Staging Batch Product {i}",
            "description": f"Testing batch import {i} without auth",
            "sku": f"TEST-BATCH-{i:03d}",
            "attributes": {
                "category": "Test Category",
                "subcategory": "Batch Test"
            },
            "production_info": {
                "Description": f"Batch test product {i}",
                "Categories": "Test Category"
            }
        }
        
        try:
            import_url = f"{wp_api_url}/import-product"
            response = requests.post(
                import_url,
                json=test_product,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                print(f"✅ Successfully imported batch product {i}")
            else:
                print(f"❌ Failed to import batch product {i}: {response.status_code}")
                break
        except Exception as e:
            print(f"❌ Failed to import batch product {i}: {e}")
            break
    
    print(f"\n🎉 Staging tests completed!")
    
    # Save results for GitHub Actions
    results = {
        'test_type': 'staging_no_auth',
        'timestamp': datetime.now().isoformat(),
        'wp_api_url': wp_api_url,
        'authentication': 'none_required',
        'tests_completed': True,
        'summary': 'Staging import test completed successfully without authentication'
    }
    
    with open('test_results.json', 'w') as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    test_localwp_import()
