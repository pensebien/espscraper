#!/usr/bin/env python3
"""
Test script to analyze network requests when loading a product page
"""

import os
import sys
import time
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the espscraper directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'espscraper'))

from espscraper.scrape_product_details import ProductDetailScraper
from espscraper.session_manager import SessionManager

def test_network_analysis():
    """Analyze network requests made when loading a product page"""
    
    print("🌐 Network Request Analysis for Product Page")
    print("=" * 60)
    print("This test will analyze all network requests made")
    print("when loading a product page to find potential API endpoints")
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
        # Create session manager and scraper (reuses session from tmp folder)
        session_manager = SessionManager()
        scraper = ProductDetailScraper(session_manager, headless=False)
        
        # Test session loading (reuses existing session if valid)
        print("\n🔐 Testing session loading (reuses tmp session)...")
        scraper.login(force_relogin=False)  # This will reuse session from tmp folder
        
        # Test accessing a product page
        print("\n🔍 Loading product page for network analysis...")
        test_url = "https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductDetails&productID=555102402&autoLaunchVS=0&tab=list"
        
        try:
            # Enable network logging
            scraper.driver.execute_cdp_cmd('Network.enable', {})
            
            # Store network requests
            network_requests = []
            
            def network_request_interceptor(request):
                network_requests.append({
                    'url': request['request']['url'],
                    'method': request['request']['method'],
                    'headers': request['request']['headers'],
                    'postData': request['request'].get('postData', ''),
                    'type': request.get('type', 'unknown')
                })
            
            # Add event listener for network requests
            scraper.driver.execute_cdp_cmd('Network.setRequestInterception', {'patterns': [{'urlPattern': '*'}]})
            
            # Navigate to the page
            scraper.driver.get(test_url)
            time.sleep(10)  # Wait for all requests to complete
            
            current_url = scraper.driver.current_url
            print(f"📍 Current URL: {current_url}")
            
            if 'login' in current_url.lower():
                print("❌ Redirected to login page - session expired")
                return False
            
            # Analyze network requests
            print(f"\n📊 NETWORK REQUEST ANALYSIS:")
            print("=" * 40)
            print(f"   📡 Total requests captured: {len(network_requests)}")
            
            # Categorize requests
            api_requests = []
            json_requests = []
            ajax_requests = []
            other_requests = []
            
            for request in network_requests:
                url = request['url']
                method = request['method']
                
                # Check for API-like requests
                if any(keyword in url.lower() for keyword in ['api', 'service', 'ajax', 'json']):
                    api_requests.append(request)
                elif url.endswith('.json') or 'json' in url.lower():
                    json_requests.append(request)
                elif method == 'POST' or 'ajax' in url.lower():
                    ajax_requests.append(request)
                else:
                    other_requests.append(request)
            
            print(f"   🔌 API-like requests: {len(api_requests)}")
            print(f"   📄 JSON requests: {len(json_requests)}")
            print(f"   ⚡ AJAX requests: {len(ajax_requests)}")
            print(f"   📦 Other requests: {len(other_requests)}")
            
            # Analyze API requests
            if api_requests:
                print(f"\n🎯 POTENTIAL API ENDPOINTS:")
                print("=" * 30)
                
                for i, request in enumerate(api_requests, 1):
                    print(f"\n{i}. {request['method']} {request['url']}")
                    print(f"   Type: {request['type']}")
                    
                    # Check headers for JSON content
                    headers = request['headers']
                    if 'application/json' in str(headers).lower():
                        print(f"   📄 Content-Type: JSON")
                    
                    # Check for product-related data
                    if 'product' in request['url'].lower():
                        print(f"   🎯 Product-related endpoint!")
                    
                    if request['postData']:
                        print(f"   📤 POST Data: {request['postData'][:100]}...")
            
            # Analyze JSON requests
            if json_requests:
                print(f"\n📄 JSON ENDPOINTS:")
                print("=" * 20)
                
                for i, request in enumerate(json_requests, 1):
                    print(f"\n{i}. {request['method']} {request['url']}")
                    print(f"   Type: {request['type']}")
                    
                    if 'product' in request['url'].lower():
                        print(f"   🎯 Product-related JSON endpoint!")
            
            # Analyze AJAX requests
            if ajax_requests:
                print(f"\n⚡ AJAX ENDPOINTS:")
                print("=" * 20)
                
                for i, request in enumerate(ajax_requests, 1):
                    print(f"\n{i}. {request['method']} {request['url']}")
                    print(f"   Type: {request['type']}")
                    
                    if request['postData']:
                        print(f"   📤 POST Data: {request['postData'][:100]}...")
                    
                    if 'product' in request['url'].lower():
                        print(f"   🎯 Product-related AJAX endpoint!")
            
            # Test the discovered endpoints
            print(f"\n🧪 TESTING DISCOVERED ENDPOINTS:")
            print("=" * 40)
            
            discovered_endpoints = []
            
            # Test API requests
            for request in api_requests:
                if 'product' in request['url'].lower():
                    discovered_endpoints.append({
                        'url': request['url'],
                        'method': request['method'],
                        'type': 'API',
                        'postData': request.get('postData', '')
                    })
            
            # Test JSON requests
            for request in json_requests:
                if 'product' in request['url'].lower():
                    discovered_endpoints.append({
                        'url': request['url'],
                        'method': request['method'],
                        'type': 'JSON',
                        'postData': request.get('postData', '')
                    })
            
            # Test AJAX requests
            for request in ajax_requests:
                if 'product' in request['url'].lower():
                    discovered_endpoints.append({
                        'url': request['url'],
                        'method': request['method'],
                        'type': 'AJAX',
                        'postData': request.get('postData', '')
                    })
            
            if discovered_endpoints:
                print(f"   🎯 Found {len(discovered_endpoints)} product-related endpoints!")
                
                for i, endpoint in enumerate(discovered_endpoints, 1):
                    print(f"\n{i}. {endpoint['method']} {endpoint['url']}")
                    print(f"   Type: {endpoint['type']}")
                    
                    if endpoint['postData']:
                        print(f"   📤 POST Data: {endpoint['postData'][:100]}...")
                
                # Save discovered endpoints
                output_file = "discovered_endpoints.json"
                with open(output_file, 'w') as f:
                    json.dump({
                        'test_url': test_url,
                        'total_requests': len(network_requests),
                        'discovered_endpoints': discovered_endpoints,
                        'all_requests': network_requests
                    }, f, indent=2)
                
                print(f"\n💾 Discovered endpoints saved to: {output_file}")
                
                return True
            else:
                print(f"   ❌ No product-related endpoints discovered")
                
                # Save all requests for manual analysis
                output_file = "all_network_requests.json"
                with open(output_file, 'w') as f:
                    json.dump({
                        'test_url': test_url,
                        'total_requests': len(network_requests),
                        'all_requests': network_requests
                    }, f, indent=2)
                
                print(f"\n💾 All network requests saved to: {output_file}")
                print("🔍 You can manually analyze this file for potential endpoints")
                
                return False
                
        except Exception as e:
            print(f"❌ Error during network analysis: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ Failed to initialize scraper: {e}")
        return False
    finally:
        try:
            scraper.driver.quit()
        except:
            pass

if __name__ == "__main__":
    success = test_network_analysis()
    if success:
        print("\n✅ Network analysis completed successfully!")
        print("🎉 Found potential API endpoints!")
    else:
        print("\n❌ Network analysis failed!") 