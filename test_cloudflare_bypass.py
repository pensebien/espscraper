#!/usr/bin/env python3
"""
Test different approaches to bypass Cloudflare protection
"""
import requests
import time

def test_cloudflare_bypass():
    """Test different methods to bypass Cloudflare"""
    print("🧪 Testing Cloudflare Bypass Methods")
    print("=" * 50)
    
    # Test URL (staging site)
    base_url = "https://tmgdev.dedicatedmkt.com"
    api_url = f"{base_url}/wp-json/promostandards-importer/v1"
    
    # You'll need to set this manually for testing
    api_key = input("Enter your API key: ").strip()
    
    if not api_key:
        print("❌ No API key provided")
        return
    
    # Test 1: Default headers
    print("\n🔍 Test 1: Default headers")
    headers = {"X-API-Key": api_key}
    
    try:
        response = requests.get(f"{api_url}/existing-products", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Content preview: {response.text[:200]}")
        if response.status_code == 200:
            print("✅ Success with default headers!")
            return
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Browser-like headers
    print("\n🔍 Test 2: Browser-like headers")
    headers = {
        "X-API-Key": api_key,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    
    try:
        response = requests.get(f"{api_url}/existing-products", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Content preview: {response.text[:200]}")
        if response.status_code == 200:
            print("✅ Success with browser headers!")
            return
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Mobile User-Agent
    print("\n🔍 Test 3: Mobile User-Agent")
    headers = {
        "X-API-Key": api_key,
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"
    }
    
    try:
        response = requests.get(f"{api_url}/existing-products", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Content preview: {response.text[:200]}")
        if response.status_code == 200:
            print("✅ Success with mobile headers!")
            return
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 4: With referer
    print("\n🔍 Test 4: With referer")
    headers = {
        "X-API-Key": api_key,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": base_url,
        "Origin": base_url
    }
    
    try:
        response = requests.get(f"{api_url}/existing-products", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Content preview: {response.text[:200]}")
        if response.status_code == 200:
            print("✅ Success with referer!")
            return
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n❌ All tests failed. Cloudflare protection is too strong.")
    print("💡 Consider:")
    print("  1. Whitelisting GitHub Actions IPs in Cloudflare")
    print("  2. Using a different deployment method")
    print("  3. Setting up a webhook-based approach")

if __name__ == "__main__":
    test_cloudflare_bypass()
