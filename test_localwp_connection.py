#!/usr/bin/env python3
"""
Test LocalWP connection and API endpoints
"""
import requests
import json

def test_localwp_connection():
    """Test LocalWP connection"""
    print("🧪 Testing LocalWP Connection")
    print("=" * 40)
    
    base_url = "https://unwritten-bottle.localsite.io"
    api_url = f"{base_url}/wp-json/promostandards-importer/v1"
    
    # Test 1: Basic WordPress connection
    print("🔍 Test 1: Basic WordPress connection")
    try:
        response = requests.get(f"{base_url}/wp-json/", timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ WordPress REST API is accessible")
            print(f"Response: {response.text[:200]}...")
        else:
            print(f"❌ WordPress REST API failed: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Error connecting to WordPress: {e}")
        return
    
    # Test 2: Check if our plugin endpoint exists
    print(f"\n🔍 Test 2: Plugin endpoint check")
    try:
        response = requests.get(f"{api_url}/existing-products", timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
        if response.status_code == 200:
            print("✅ Plugin endpoint is working!")
        elif response.status_code == 401:
            print("⚠️ Plugin endpoint requires authentication")
        elif response.status_code == 404:
            print("❌ Plugin endpoint not found - plugin might not be active")
        else:
            print(f"❌ Unexpected status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Test with API key
    print(f"\n🔍 Test 3: Test with API key")
    api_key = "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"
    headers = {"X-API-Key": api_key}
    
    try:
        response = requests.get(f"{api_url}/existing-products", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
        if response.status_code == 200:
            print("✅ API key authentication works!")
        elif response.status_code == 401:
            print("❌ API key authentication failed")
        elif response.status_code == 404:
            print("❌ Endpoint not found with API key")
        else:
            print(f"❌ Unexpected status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 4: Test with Basic Auth
    print(f"\n🔍 Test 4: Test with Basic Auth")
    basic_auth = ("admin", "password")  # You'll need to update this
    
    try:
        response = requests.get(f"{api_url}/existing-products", auth=basic_auth, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
        if response.status_code == 200:
            print("✅ Basic Auth works!")
        elif response.status_code == 401:
            print("❌ Basic Auth failed - wrong credentials")
        else:
            print(f"❌ Unexpected status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 5: Check if plugin is active
    print(f"\n🔍 Test 5: Check plugin status")
    try:
        response = requests.get(f"{base_url}/wp-json/wp/v2/plugins", timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            plugins = response.json()
            promostandards_plugin = None
            for plugin in plugins:
                if 'promostandards' in plugin.get('plugin', '').lower():
                    promostandards_plugin = plugin
                    break
            
            if promostandards_plugin:
                print(f"✅ Plugin found: {promostandards_plugin['plugin']}")
                print(f"Status: {promostandards_plugin.get('status', 'unknown')}")
            else:
                print("❌ Promostandards plugin not found")
        else:
            print(f"❌ Could not check plugins: {response.status_code}")
    except Exception as e:
        print(f"❌ Error checking plugins: {e}")

if __name__ == "__main__":
    test_localwp_connection()
