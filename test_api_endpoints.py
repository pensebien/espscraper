#!/usr/bin/env python3
"""
Test script to discover and test potential API endpoints for product details
"""

import os
import sys
import time
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the espscraper directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'espscraper'))

from espscraper.session_manager import SessionManager

def test_api_endpoints():
    """Test various potential API endpoints for product details"""
    
    print("🔍 Testing Potential API Endpoints for Product Details")
    print("=" * 60)
    print("This test will try to find API endpoints that provide")
    print("product details in JSON format instead of scraping HTML")
    print("=" * 60)
    
    # Check environment variables
    required_env_vars = ['ESP_USERNAME', 'ESP_PASSWORD', 'PRODUCTS_URL']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        print("Please set these in your .env file")
        return False
    
    print("✅ Environment variables loaded")
    
    try:
        # Create session manager
        session_manager = SessionManager()
        
        # Test session loading (reuses existing session if valid)
        print("\n🔐 Testing session loading (reuses tmp session)...")
        
        # Load session data
        cookies, page_key, search_id = session_manager.load_state()
        
        if not cookies or not page_key or not search_id:
            print("❌ No valid session found. Please run the scraper first to create a session.")
            return False
        
        print("✅ Session loaded successfully")
        
        # Create session with cookies
        session = requests.Session()
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json;charset=UTF-8',
            'Referer': os.getenv("PRODUCTS_URL"),
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        session.headers.update(headers)
        
        # Load cookies into session
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'], domain=cookie.get('domain'))
        
        # Test product ID
        test_product_id = "555102402"
        
        print(f"\n🔍 Testing API endpoints for product ID: {test_product_id}")
        print("=" * 50)
        
        # List of potential API endpoints to test
        api_endpoints = [
            # Known API endpoints
            f"https://api.asicentral.com/v1/products/{test_product_id}/suggestions.json?page=1&rpp=5",
            f"https://api.asicentral.com/v1/products/{test_product_id}.json",
            f"https://api.asicentral.com/v1/products/{test_product_id}",
            
            # Potential ESP-specific endpoints
            f"https://espweb.asicentral.com/api/products/{test_product_id}",
            f"https://espweb.asicentral.com/api/product/{test_product_id}",
            f"https://espweb.asicentral.com/api/v1/products/{test_product_id}",
            f"https://espweb.asicentral.com/api/v1/product/{test_product_id}",
            
            # Potential JSON endpoints
            f"https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductDetails&productID={test_product_id}&format=json",
            f"https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductDetails&productID={test_product_id}&output=json",
            
            # Potential AJAX endpoints
            f"https://espweb.asicentral.com/ProductDetails.aspx?productID={test_product_id}&format=json",
            f"https://espweb.asicentral.com/ProductDetails.aspx?productID={test_product_id}&output=json",
            
            # Potential service endpoints
            f"https://espweb.asicentral.com/Services/ProductService.asmx/GetProduct?productID={test_product_id}",
            f"https://espweb.asicentral.com/Services/ProductService.asmx/GetProductDetails?productID={test_product_id}",
            
            # Potential REST endpoints
            f"https://espweb.asicentral.com/rest/products/{test_product_id}",
            f"https://espweb.asicentral.com/rest/product/{test_product_id}",
            
            # Potential data endpoints
            f"https://espweb.asicentral.com/data/products/{test_product_id}.json",
            f"https://espweb.asicentral.com/data/product/{test_product_id}.json",
        ]
        
        successful_endpoints = []
        
        for i, endpoint in enumerate(api_endpoints, 1):
            print(f"\n🔍 Testing endpoint {i}/{len(api_endpoints)}: {endpoint}")
            
            try:
                # Test GET request
                response = session.get(endpoint, timeout=10)
                
                print(f"   📊 Status Code: {response.status_code}")
                print(f"   📊 Content Type: {response.headers.get('content-type', 'N/A')}")
                print(f"   📊 Content Length: {len(response.content)} bytes")
                
                if response.status_code == 200:
                    try:
                        # Try to parse as JSON
                        data = response.json()
                        print(f"   ✅ JSON Response: {len(data)} keys")
                        
                        # Check if it contains product data
                        product_keys = ['product', 'Product', 'data', 'Data', 'result', 'Result']
                        has_product_data = any(key in data for key in product_keys)
                        
                        if has_product_data:
                            print(f"   🎯 Contains product data!")
                            successful_endpoints.append({
                                'endpoint': endpoint,
                                'status_code': response.status_code,
                                'data_keys': list(data.keys()),
                                'has_product_data': True,
                                'sample_data': data
                            })
                        else:
                            print(f"   ⚠️ No obvious product data found")
                            successful_endpoints.append({
                                'endpoint': endpoint,
                                'status_code': response.status_code,
                                'data_keys': list(data.keys()),
                                'has_product_data': False,
                                'sample_data': data
                            })
                            
                    except json.JSONDecodeError:
                        print(f"   ❌ Not valid JSON")
                        # Check if it's HTML that might contain JSON
                        content = response.text
                        if 'product' in content.lower() or 'json' in content.lower():
                            print(f"   ⚠️ Contains product-related content")
                            successful_endpoints.append({
                                'endpoint': endpoint,
                                'status_code': response.status_code,
                                'content_type': response.headers.get('content-type'),
                                'has_product_data': 'product' in content.lower(),
                                'sample_data': content[:500] + '...' if len(content) > 500 else content
                            })
                else:
                    print(f"   ❌ Failed with status code: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                print(f"   ❌ Request failed: {e}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        # Test POST endpoints with potential payloads
        print(f"\n🔍 Testing POST endpoints...")
        print("=" * 30)
        
        post_endpoints = [
            "https://espweb.asicentral.com/Services/ProductService.asmx/GetProduct",
            "https://espweb.asicentral.com/Services/ProductService.asmx/GetProductDetails",
            "https://espweb.asicentral.com/api/products",
            "https://espweb.asicentral.com/api/product",
        ]
        
        post_payloads = [
            {"productID": test_product_id},
            {"id": test_product_id},
            {"product_id": test_product_id},
            {"productId": test_product_id},
        ]
        
        for endpoint in post_endpoints:
            for payload in post_payloads:
                print(f"\n🔍 Testing POST: {endpoint}")
                print(f"   📤 Payload: {payload}")
                
                try:
                    response = session.post(endpoint, json=payload, timeout=10)
                    
                    print(f"   📊 Status Code: {response.status_code}")
                    print(f"   📊 Content Type: {response.headers.get('content-type', 'N/A')}")
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            print(f"   ✅ JSON Response: {len(data)} keys")
                            
                            if any(key in data for key in ['product', 'Product', 'data', 'Data']):
                                print(f"   🎯 Contains product data!")
                                successful_endpoints.append({
                                    'endpoint': endpoint,
                                    'method': 'POST',
                                    'payload': payload,
                                    'status_code': response.status_code,
                                    'data_keys': list(data.keys()),
                                    'has_product_data': True,
                                    'sample_data': data
                                })
                        except json.JSONDecodeError:
                            print(f"   ❌ Not valid JSON")
                            
                except Exception as e:
                    print(f"   ❌ Error: {e}")
        
        # Summary
        print(f"\n📊 API ENDPOINT TESTING SUMMARY:")
        print("=" * 40)
        print(f"   🔍 Total endpoints tested: {len(api_endpoints) + len(post_endpoints) * len(post_payloads)}")
        print(f"   ✅ Successful responses: {len(successful_endpoints)}")
        
        if successful_endpoints:
            print(f"\n🎯 POTENTIAL API ENDPOINTS FOUND:")
            print("=" * 40)
            
            for i, result in enumerate(successful_endpoints, 1):
                print(f"\n{i}. {result['endpoint']}")
                print(f"   Method: {result.get('method', 'GET')}")
                print(f"   Status: {result['status_code']}")
                print(f"   Has Product Data: {result['has_product_data']}")
                print(f"   Data Keys: {result.get('data_keys', 'N/A')}")
                
                if result.get('payload'):
                    print(f"   Payload: {result['payload']}")
        
        # Save results
        output_file = "api_endpoint_test_results.json"
        with open(output_file, 'w') as f:
            json.dump({
                'test_product_id': test_product_id,
                'total_endpoints_tested': len(api_endpoints) + len(post_endpoints) * len(post_payloads),
                'successful_endpoints': successful_endpoints
            }, f, indent=2)
        
        print(f"\n💾 Results saved to: {output_file}")
        
        if successful_endpoints:
            print(f"\n✅ Found {len(successful_endpoints)} potential API endpoints!")
            print("🎉 These could be used instead of scraping HTML!")
            return True
        else:
            print(f"\n❌ No working API endpoints found")
            print("⚠️ Will need to continue with HTML scraping")
            return False
            
    except Exception as e:
        print(f"❌ Failed to test API endpoints: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_api_endpoints()
    if success:
        print("\n✅ API endpoint testing completed successfully!")
    else:
        print("\n❌ API endpoint testing failed!") 