#!/usr/bin/env python3
"""
Test script to simulate the exact request that's failing with 403
"""
import os
import requests

def load_env_file(env_file):
    """Load environment variables from .env file"""
    env_vars = {}
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key] = value
    return env_vars

def test_staging_403():
    """Test the exact request that's failing"""
    print("🧪 Testing Staging 403 Error")
    print("=" * 40)
    
    # Load staging environment
    env_vars = load_env_file('.env.staging')
    wp_api_url = env_vars.get('WP_API_URL', '')
    wp_api_key = env_vars.get('WP_API_KEY', '')
    
    print(f"API URL: {wp_api_url}")
    print(f"API Key: {wp_api_key[:10] if wp_api_key else 'None'}...")
    
    # Test 1: Existing products endpoint (same as workflow pre-test)
    existing_url = f"{wp_api_url}/existing-products"
    headers = {"X-API-Key": wp_api_key}
    
    print(f"\n🔍 Test 1: Existing products endpoint")
    print(f"URL: {existing_url}")
    print(f"Headers: {headers}")
    
    try:
        response = requests.get(existing_url, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Content (first 1000 chars):")
        print(response.text[:1000])
        
        if response.status_code == 200:
            print("✅ Existing products endpoint works!")
        else:
            print(f"❌ Failed with status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Import product endpoint (the one that's failing)
    import_url = f"{wp_api_url}/import-product"
    sample_product = {
        "product_id": "test_403",
        "name": "Test 403 Product",
        "description": "Testing 403 error"
    }
    
    print(f"\n🔍 Test 2: Import product endpoint")
    print(f"URL: {import_url}")
    print(f"Headers: {headers}")
    print(f"Product: {sample_product['name']}")
    
    try:
        response = requests.post(import_url, headers=headers, json=sample_product, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Content (first 1000 chars):")
        print(response.text[:1000])
        
        if response.status_code in [200, 201, 409]:
            print("✅ Import product endpoint works!")
        else:
            print(f"❌ Failed with status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Different User-Agent (simulate browser)
    print(f"\n🔍 Test 3: With browser User-Agent")
    browser_headers = {
        "X-API-Key": wp_api_key,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.post(import_url, headers=browser_headers, json=sample_product, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response Content (first 500 chars):")
        print(response.text[:500])
        
        if response.status_code in [200, 201, 409]:
            print("✅ Works with browser User-Agent!")
        else:
            print(f"❌ Still fails with browser User-Agent")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_staging_403()
