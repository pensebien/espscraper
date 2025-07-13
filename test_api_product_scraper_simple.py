#!/usr/bin/env python3
"""
Simple Test for API Product Detail Scraper

This script demonstrates the improved API scraper with efficient product ID reading.
"""

import os
import sys
import time
import logging

# Add the espscraper directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'espscraper'))

from espscraper.session_manager import SessionManager
from espscraper.api_product_detail_scraper import ApiProductDetailScraper, ScrapingConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

def test_efficient_product_id_reading():
    """Test the efficient product ID reading with limit"""
    print("\n🔍 Testing Efficient Product ID Reading")
    print("=" * 50)
    
    try:
        # Create session manager
        session_manager = SessionManager()
        
        # Create configuration
        config = ScrapingConfig(
            max_requests_per_minute=25,
            batch_size=3,
            max_concurrent_requests=2,
            max_retries=3,
            request_timeout=30
        )
        
        # Create scraper
        scraper = ApiProductDetailScraper(session_manager, config)
        
        # Test reading with different limits
        test_limits = [5, 10, 15]
        
        for limit in test_limits:
            print(f"\n📊 Testing with limit: {limit}")
            
            # Read product IDs with limit
            start_time = time.time()
            product_ids = scraper.read_product_links(limit=limit)
            read_time = time.time() - start_time
            
            print(f"   ✅ Read {len(product_ids)} product IDs in {read_time:.3f}s")
            print(f"   📋 First few IDs: {[p['id'] for p in product_ids[:3]]}")
            
            if len(product_ids) != limit:
                print(f"   ⚠️ Expected {limit} but got {len(product_ids)} (file may have fewer entries)")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_single_product_scraping():
    """Test scraping a single product"""
    print("\n🎯 Testing Single Product Scraping")
    print("=" * 50)
    
    try:
        # Create session manager
        session_manager = SessionManager()
        
        # Create configuration
        config = ScrapingConfig(
            max_requests_per_minute=25,
            batch_size=1,
            max_concurrent_requests=1,
            max_retries=3,
            request_timeout=30
        )
        
        # Create scraper
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
            print(f"   ⏱️ Extraction time: {extraction_time:.2f}s")
            return True
        else:
            print("❌ Failed to scrape product")
            return False
            
    except Exception as e:
        print(f"❌ Single product scraping test failed: {e}")
        return False

def test_batch_scraping_with_limit():
    """Test batch scraping with limit"""
    print("\n📦 Testing Batch Scraping with Limit")
    print("=" * 50)
    
    try:
        # Create session manager
        session_manager = SessionManager()
        
        # Create configuration
        config = ScrapingConfig(
            max_requests_per_minute=25,
            batch_size=3,
            max_concurrent_requests=2,
            max_retries=3,
            request_timeout=30
        )
        
        # Create scraper
        scraper = ApiProductDetailScraper(session_manager, config)
        
        # Test with limit
        test_limit = 5
        
        print(f"🎯 Testing batch scraping with limit: {test_limit}")
        print(f"   📦 Batch size: {config.batch_size}")
        print(f"   🔄 Max concurrent: {config.max_concurrent_requests}")
        
        # Run scraping with limit
        start_time = time.time()
        scraper.scrape_all_products(mode='scrape', limit=test_limit)
        total_time = time.time() - start_time
        
        print(f"\n📊 Results:")
        print(f"   ⏱️ Total time: {total_time:.2f}s")
        print(f"   📊 Statistics: {scraper.stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Batch scraping test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Simple API Product Detail Scraper Test")
    print("=" * 60)
    
    tests = [
        ("Efficient Product ID Reading", test_efficient_product_id_reading),
        ("Single Product Scraping", test_single_product_scraping),
        ("Batch Scraping with Limit", test_batch_scraping_with_limit)
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
        print("🎉 All tests passed! API scraper is working efficiently.")
    else:
        print("⚠️ Some tests failed. Please check the configuration and session.")

if __name__ == "__main__":
    main() 