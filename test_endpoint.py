#!/usr/bin/env python3
"""
Test script to debug WordPress API endpoint issues
"""
import requests
import json
import sys

def test_endpoint():
    # Test parameters
    base_url = "https://separate-earth.localsite.io"
    auth_user = "journal"
    auth_pass = "zealous"
    
    # Test 1: Check if the endpoint exists
    print("=== Test 1: Check endpoint availability ===")
    try:
        response = requests.get(
            f"{base_url}/wp-json/promostandards-importer/v1/",
            auth=(auth_user, auth_pass),
            timeout=10
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}...")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Try to get params with different secrets
    print("\n=== Test 2: Test different secrets ===")
    secrets_to_try = ["test-secret", "secret", "github-secret", "wp-secret", ""]
    
    for secret in secrets_to_try:
        try:
            url = f"{base_url}/wp-json/promostandards-importer/v1/github-params"
            if secret:
                url += f"?secret={secret}"
            
            response = requests.get(url, auth=(auth_user, auth_pass), timeout=10)
            print(f"Secret '{secret}': {response.status_code} - {response.text[:100]}...")
        except Exception as e:
            print(f"Secret '{secret}': Error - {e}")
    
    # Test 3: Try to upload a product with different API keys
    print("\n=== Test 3: Test upload with different API keys ===")
    
    # Sample product data
    sample_product = {
        "ProductID": "555102399",
        "Name": "Test Product",
        "description": "Test description"
    }
    
    api_keys_to_try = ["test-key", "api-key", "wordpress-key", "promostandards-key", ""]
    
    for api_key in api_keys_to_try:
        try:
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": api_key
            }
            
            response = requests.post(
                f"{base_url}/wp-json/promostandards-importer/v1/upload",
                headers=headers,
                json=sample_product,
                auth=(auth_user, auth_pass),
                timeout=10
            )
            print(f"API Key '{api_key}': {response.status_code} - {response.text[:100]}...")
        except Exception as e:
            print(f"API Key '{api_key}': Error - {e}")

if __name__ == "__main__":
    test_endpoint() 