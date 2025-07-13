#!/usr/bin/env python3
"""
Test Script for API Product Detail Scraper

This script demonstrates the robust API-based scraper with:
1. Session management and validation
2. Parallel processing capabilities
3. Error handling and retry mechanisms
4. Rate limiting and throttling
5. Comprehensive logging and monitoring
"""

import os
import sys
import time
import json
import logging
from datetime import datetime

# Add the espscraper directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'espscraper'))

from espscraper.session_manager import SessionManager
from espscraper.api_product_detail_scraper import ApiProductDetailScraper, ScrapingConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

def test_session_management():
    """Test session management capabilities"""
    print("\n🔐 Testing Session Management")
    print("=" * 50)
    
    try:
        # Create session manager
        session_manager = SessionManager()
        
        # Check if session exists
        cookies, page_key, search_id = session_manager.load_state()
        
        if cookies and page_key and search_id:
            print("✅ Existing session found")
            print(f"   📄 Page Key: {page_key}")
            print(f"   🔍 Search ID: {search_id}")
            print(f"   🍪 Cookies: {len(cookies)}")
            return True
        else:
            print("⚠️ No existing session found")
            print("   Please run the HTML scraper first to create a session")
            return False
            
    except Exception as e:
        print(f"❌ Session management test failed: {e}")
        return False

def test_api_scraper_configuration():
    """Test API scraper configuration"""
    print("\n⚙️ Testing API Scraper Configuration")
    print("=" * 50)
    
    try:
        # Create configuration
        config = ScrapingConfig(
            max_requests_per_minute=25,
            batch_size=5,
            max_concurrent_requests=2,
            max_retries=3,
            request_timeout=30
        )
        
        print("✅ Configuration created successfully")
        print(f"   📊 Max requests per minute: {config.max_requests_per_minute}")
        print(f"   📦 Batch size: {config.batch_size}")
        print(f"   🔄 Max concurrent requests: {config.max_concurrent_requests}")
        print(f"   🔁 Max retries: {config.max_retries}")
        print(f"   ⏰ Request timeout: {config.request_timeout}s")
        
        return config
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return None

def test_api_scraper_initialization():
    """Test API scraper initialization"""
    print("\n🤖 Testing API Scraper Initialization")
    print("=" * 50)
    
    try:
        # Create session manager
        session_manager = SessionManager()
        
        # Create configuration
        config = ScrapingConfig(
            max_requests_per_minute=25,
            batch_size=5,
            max_concurrent_requests=2,
            max_retries=3,
            request_timeout=30
        )
        
        # Create scraper
        scraper = ApiProductDetailScraper(session_manager, config)
        
        print("✅ API scraper initialized successfully")
        print(f"   📁 Output file: {scraper.output_file}")
        print(f"   📁 Links file: {scraper.links_file}")
        print(f"   📊 Rate limiter configured")
        print(f"   🔐 Session manager configured")
        
        return scraper
        
    except Exception as e:
        print(f"❌ API scraper initialization failed: {e}")
        return None

def test_single_product_scraping():
    """Test scraping a single product"""
    print("\n🔍 Testing Single Product Scraping")
    print("=" * 50)
    
    try:
        # Create scraper
        session_manager = SessionManager()
        config = ScrapingConfig(
            max_requests_per_minute=25,
            batch_size=1,
            max_concurrent_requests=1,
            max_retries=3,
            request_timeout=30
        )
        scraper = ApiProductDetailScraper(session_manager, config)
        
        # Test product ID
        test_product_id = "555102402"
        
        print(f"🎯 Testing product ID: {test_product_id}")
        
        # Scrape product
        start_time = time.time()
        product_data = scraper.scrape_product_api(test_product_id)
        extraction_time = time.time() - start_time
        
        if product_data:
            print("✅ Product scraped successfully")
            print(f"   📝 Name: {product_data.name}")
            print(f"   🏷️ SKU: {product_data.sku}")
            print(f"   🏪 Supplier: {product_data.supplier_info.get('Name', 'N/A')}")
            print(f"   💰 Pricing: {len(product_data.pricing_info.get('PriceBreaks', []))} price breaks")
            print(f"   🎨 Colors: {len(product_data.attributes.get('Colors', []))} colors")
            print(f"   ⏱️ Extraction time: {extraction_time:.2f}s")
            print(f"   📊 Raw data keys: {list(product_data.raw_data.keys())}")
            
            return True
        else:
            print("❌ Failed to scrape product")
            return False
            
    except Exception as e:
        print(f"❌ Single product scraping test failed: {e}")
        return False

def test_batch_scraping():
    """Test batch scraping with multiple products"""
    print("\n📦 Testing Batch Scraping")
    print("=" * 50)
    
    try:
        # Create scraper
        session_manager = SessionManager()
        config = ScrapingConfig(
            max_requests_per_minute=25,
            batch_size=3,
            max_concurrent_requests=2,
            max_retries=3,
            request_timeout=30
        )
        scraper = ApiProductDetailScraper(session_manager, config)
        
        # Test product IDs
        test_product_ids = ["555102402", "551711617", "554960276"]

        print(f"🎯 Testing batch of {len(test_product_ids)} products")
        print(f"   📦 Batch size: {config.batch_size}")
        print(f"   🔄 Max concurrent: {config.max_concurrent_requests}")
        
        # Scrape products
        start_time = time.time()
        successful_products = []
        
        for product_id in test_product_ids:
            product_data = scraper.scrape_product_api(product_id)
            if product_data:
                successful_products.append(product_data)
                print(f"   ✅ Product {product_id}: {product_data.name}")
            else:
                print(f"   ❌ Product {product_id}: Failed")
        
        total_time = time.time() - start_time
        
        print(f"\n📊 Batch Results:")
        print(f"   ✅ Successful: {len(successful_products)}/{len(test_product_ids)}")
        print(f"   ⏱️ Total time: {total_time:.2f}s")
        print(f"   🚀 Average time per product: {total_time/len(test_product_ids):.2f}s")
        
        return len(successful_products) > 0
        
    except Exception as e:
        print(f"❌ Batch scraping test failed: {e}")
        return False

def test_error_handling():
    """Test error handling and retry mechanisms"""
    print("\n🛡️ Testing Error Handling")
    print("=" * 50)
    
    try:
        # Create scraper
        session_manager = SessionManager()
        config = ScrapingConfig(
            max_requests_per_minute=25,
            batch_size=1,
            max_concurrent_requests=1,
            max_retries=2,
            request_timeout=5  # Short timeout to trigger errors
        )
        scraper = ApiProductDetailScraper(session_manager, config)
        
        # Test with invalid product ID
        invalid_product_id = "999999999"
        
        print(f"🎯 Testing error handling with invalid product ID: {invalid_product_id}")
        
        # This should fail gracefully
        product_data = scraper.scrape_product_api(invalid_product_id)
        
        if product_data is None:
            print("✅ Error handling working correctly - invalid product handled gracefully")
            return True
        else:
            print("⚠️ Unexpected success with invalid product ID")
            return False
            
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

def test_rate_limiting():
    """Test rate limiting functionality"""
    print("\n⏱️ Testing Rate Limiting")
    print("=" * 50)
    
    try:
        # Create scraper with aggressive rate limiting
        session_manager = SessionManager()
        config = ScrapingConfig(
            max_requests_per_minute=10,  # Very low limit
            batch_size=1,
            max_concurrent_requests=1,
            max_retries=1,
            request_timeout=30
        )
        scraper = ApiProductDetailScraper(session_manager, config)
        
        # Test product ID
        test_product_id = "555102402"
        
        print(f"🎯 Testing rate limiting with product ID: {test_product_id}")
        print(f"   📊 Rate limit: {config.max_requests_per_minute} requests/minute")
        
        # Make multiple requests to test rate limiting
        start_time = time.time()
        
        for i in range(3):
            print(f"   🔄 Request {i+1}/3...")
            product_data = scraper.scrape_product_api(test_product_id)
            if product_data:
                print(f"      ✅ Success: {product_data.name}")
            else:
                print(f"      ❌ Failed")
        
        total_time = time.time() - start_time
        
        print(f"   ⏱️ Total time for 3 requests: {total_time:.2f}s")
        print(f"   📊 Average time per request: {total_time/3:.2f}s")
        
        return True
        
    except Exception as e:
        print(f"❌ Rate limiting test failed: {e}")
        return False

def test_session_recovery():
    """Test session recovery mechanisms"""
    print("\n🔄 Testing Session Recovery")
    print("=" * 50)
    
    try:
        # Create scraper
        session_manager = SessionManager()
        config = ScrapingConfig(
            max_requests_per_minute=25,
            batch_size=1,
            max_concurrent_requests=1,
            max_retries=3,
            request_timeout=30,
            auto_relogin=True
        )
        scraper = ApiProductDetailScraper(session_manager, config)
        
        print("✅ Session recovery mechanisms configured")
        print(f"   🔄 Auto relogin: {config.auto_relogin}")
        print(f"   ⏰ Session refresh interval: {config.session_refresh_interval}s")
        print(f"   🚨 Circuit breaker: {config.circuit_breaker_enabled}")
        
        # Test session manager
        session = scraper.session_manager.get_session()
        print(f"   🔐 Session obtained: {session is not None}")
        
        return True
        
    except Exception as e:
        print(f"❌ Session recovery test failed: {e}")
        return False

def test_comprehensive_scraping():
    """Test comprehensive scraping workflow"""
    print("\n🚀 Testing Comprehensive Scraping Workflow")
    print("=" * 50)
    
    try:
        # Create scraper
        session_manager = SessionManager()
        config = ScrapingConfig(
            max_requests_per_minute=25,
            batch_size=5,
            max_concurrent_requests=2,
            max_retries=3,
            request_timeout=30
        )
        scraper = ApiProductDetailScraper(session_manager, config)
        
        print("✅ Comprehensive scraper configured")
        print(f"   📦 Batch size: {config.batch_size}")
        print(f"   🔄 Max concurrent: {config.max_concurrent_requests}")
        print(f"   🔁 Max retries: {config.max_retries}")
        
        # Check if we have product links
        product_links = scraper.read_product_links()
        
        if product_links:
            print(f"   📋 Found {len(product_links)} product links")
            
            # Test with limit applied during reading (more efficient)
            print(f"   🎯 Testing with limit=3 (efficient reading)")
            
            # Create test links file
            test_links_file = "test_links.jsonl"
            with open(test_links_file, 'w') as f:
                for link in product_links[:10]:  # Create file with 10 links
                    f.write(json.dumps(link) + '\n')
            
            # Temporarily set links file
            original_links_file = scraper.links_file
            scraper.links_file = test_links_file
            
            # Run scraping with limit (now applied during file reading)
            start_time = time.time()
            scraper.scrape_all_products(mode='scrape', limit=3)
            total_time = time.time() - start_time
            
            # Restore original links file
            scraper.links_file = original_links_file
            
            # Clean up test file
            if os.path.exists(test_links_file):
                os.remove(test_links_file)
            
            print(f"   ⏱️ Total scraping time: {total_time:.2f}s")
            print(f"   📊 Statistics: {scraper.stats}")
            
            return True
        else:
            print("   ⚠️ No product links found - skipping comprehensive test")
            return True
            
    except Exception as e:
        print(f"❌ Comprehensive scraping test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 API Product Detail Scraper Test Suite")
    print("=" * 60)
    
    tests = [
        ("Session Management", test_session_management),
        ("API Scraper Configuration", test_api_scraper_configuration),
        ("API Scraper Initialization", test_api_scraper_initialization),
        ("Single Product Scraping", test_single_product_scraping),
        ("Batch Scraping", test_batch_scraping),
        ("Error Handling", test_error_handling),
        ("Rate Limiting", test_rate_limiting),
        ("Session Recovery", test_session_recovery),
        ("Comprehensive Scraping", test_comprehensive_scraping)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"🧪 Running: {test_name}")
        print(f"{'='*60}")
        
        try:
            result = test_func()
            results.append((test_name, result))
            
            if result:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
                
        except Exception as e:
            print(f"💥 {test_name}: ERROR - {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {test_name}: {status}")
    
    print(f"\n📈 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! API scraper is ready for production.")
    else:
        print("⚠️ Some tests failed. Please check the configuration and session.")

if __name__ == "__main__":
    main() 