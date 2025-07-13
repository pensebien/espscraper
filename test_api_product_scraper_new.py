#!/usr/bin/env python3
"""
Test script for the rewritten API Product Detail Scraper
Tests the new session management integration
"""

import os
import sys
import json
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the espscraper directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'espscraper'))

from espscraper.session_manager import SessionManager
from espscraper.api_product_detail_scraper import ApiProductDetailScraper, ScrapingConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

# Set environment variables for testing
os.environ["API_SCRAPED_LINKS_FILE"] = "espscraper/data/api_scraped_links.jsonl"
os.environ["PRODUCT_OUTPUT_FILE"] = "test_api_scraped_product_data.jsonl"
os.environ["PRODUCT_API_URL"] = "https://api.asicentral.com/v1/products/{product_id}.json"
os.environ["PRODUCT_URL_TEMPLATE"] = "https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductDetails&referrerPage=ProductResults&referrerModule=PRDRES&refModSufx=Generic&PCUrl=1&productID={product_id}&autoLaunchVS=0&tab=list"

def test_session_management():
    """Test that session management works correctly"""
    print("🧪 Testing Session Management...")
    
    # Initialize session manager
    session_manager = SessionManager()
    
    # Test login
    print("🔐 Testing login...")
    login_success = session_manager.login()
    if login_success:
        print("✅ Login successful")
    else:
        print("❌ Login failed")
        return False
    
    # Test getting authenticated session
    print("🔑 Testing authenticated session...")
    try:
        session = session_manager.get_authenticated_session()
        print("✅ Authenticated session obtained")
        
        # Test session state loading
        cookies, page_key, search_id = session_manager.load_state()
        if cookies and page_key and search_id:
            print(f"✅ Session state loaded - pageKey: {page_key}, searchId: {search_id}")
        else:
            print("⚠️ Session state incomplete")
            
    except FileNotFoundError:
        print("❌ No session cookies found")
        return False
    except Exception as e:
        print(f"❌ Error getting authenticated session: {e}")
        return False
    
    return True

def test_product_id_reading():
    """Test reading product IDs from file"""
    print("\n📖 Testing Product ID Reading...")
    
    # Initialize scraper
    session_manager = SessionManager()
    config = ScrapingConfig()
    scraper = ApiProductDetailScraper(session_manager, config)
    
    # Test reading product IDs
    product_ids = scraper.read_product_ids(limit=5)
    
    if product_ids:
        print(f"✅ Read {len(product_ids)} product IDs")
        print(f"📋 Sample IDs: {product_ids[:3]}")
        return product_ids
    else:
        print("❌ No product IDs found")
        return []

def test_single_product_scraping():
    """Test scraping a single product"""
    print("\n🎯 Testing Single Product Scraping...")
    
    # Initialize scraper
    session_manager = SessionManager()
    config = ScrapingConfig(
        max_requests_per_minute=10,
        min_delay=2.0,
        max_concurrent_requests=1
    )
    scraper = ApiProductDetailScraper(session_manager, config)
    
    # Get a test product ID
    product_ids = scraper.read_product_ids(limit=1)
    if not product_ids:
        print("❌ No product IDs available for testing")
        return False
    
    test_product_id = product_ids[0]
    print(f"🧪 Testing with product ID: {test_product_id}")
    
    # Test scraping
    try:
        product_data = scraper.scrape_product_api(test_product_id)
        
        if product_data:
            print("✅ Product scraping successful")
            print(f"📦 Product Name: {product_data.name}")
            print(f"🏷️ SKU: {product_data.sku}")
            print(f"⏱️ Extraction Time: {product_data.extraction_time:.2f}s")
            return True
        else:
            print("❌ Product scraping failed")
            return False
            
    except Exception as e:
        print(f"❌ Error during product scraping: {e}")
        return False

def test_batch_scraping():
    """Test batch scraping with limits"""
    print("\n📦 Testing Batch Scraping...")
    
    # Initialize scraper with conservative settings
    session_manager = SessionManager()
    config = ScrapingConfig(
        max_requests_per_minute=15,
        min_delay=2.0,
        max_concurrent_requests=2,
        batch_size=3,
        max_retries=2
    )
    scraper = ApiProductDetailScraper(session_manager, config)
    
    # Test batch scraping with small limit
    print("🔄 Testing batch scraping with limit=3...")
    try:
        scraper.scrape_all_products(mode='scrape', limit=3)
        print("✅ Batch scraping completed")
        return True
    except Exception as e:
        print(f"❌ Error during batch scraping: {e}")
        return False

def test_session_refresh():
    """Test session refresh functionality"""
    print("\n🔄 Testing Session Refresh...")
    
    session_manager = SessionManager()
    
    # Test session state loading
    cookies, page_key, search_id = session_manager.load_state()
    if cookies and page_key and search_id:
        print("✅ Session state available")
        
        # Test getting session multiple times
        for i in range(3):
            try:
                session = session_manager.get_authenticated_session()
                print(f"✅ Session {i+1} obtained successfully")
            except Exception as e:
                print(f"❌ Error getting session {i+1}: {e}")
                return False
    else:
        print("⚠️ No session state available")
        return False
    
    return True

def main():
    """Run all tests"""
    print("🚀 Starting API Product Scraper Tests")
    print("=" * 50)
    
    tests = [
        ("Session Management", test_session_management),
        ("Product ID Reading", test_product_id_reading),
        ("Single Product Scraping", test_single_product_scraping),
        ("Session Refresh", test_session_refresh),
        ("Batch Scraping", test_batch_scraping)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{status}: {test_name}")
        except Exception as e:
            print(f"❌ ERROR: {test_name} - {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*50)
    print("📊 TEST SUMMARY")
    print("="*50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The rewritten scraper is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the logs above for details.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 