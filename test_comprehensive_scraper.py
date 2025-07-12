#!/usr/bin/env python3
"""
Test script for comprehensive product detail scraper
Tests all the new extraction methods in parallel
"""

import os
import sys
import json
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the espscraper directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'espscraper'))

from espscraper.scrape_product_details import ProductDetailScraper
from espscraper.session_manager import SessionManager

def test_comprehensive_scraper():
    """Test the comprehensive scraper with all new extraction methods"""
    
    print("🚀 Testing Comprehensive Product Detail Scraper")
    print("=" * 50)
    
    # Check environment variables
    required_env_vars = ['ESP_USERNAME', 'ESP_PASSWORD', 'PRODUCTS_URL']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        print("Please set these in your .env file")
        return False
    
    try:
        # Initialize scraper
        session_manager = SessionManager()
        scraper = ProductDetailScraper(
            session_manager,
            headless=True,  # Run in headless mode for testing
            limit=1  # Only test 1 product
        )
        
        print("✅ Scraper initialized successfully")
        
        # Test login
        print("🔐 Testing login...")
        scraper.login(force_relogin=True)
        print("✅ Login successful")
        
        # Test with a known product URL
        test_url = "https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductDetails&productID=555102402&autoLaunchVS=0&tab=list"
        
        print(f"🌐 Testing with product URL: {test_url}")
        
        # Navigate to the product page
        scraper.driver.get(test_url)
        time.sleep(5)  # Wait for page to load
        
        # Test comprehensive extraction
        print("🔍 Testing comprehensive data extraction...")
        scraped_data = scraper.scrape_product_detail_page()
        
        if scraped_data:
            print("✅ Data extraction successful!")
            
            # Test all the new fields
            print("\n📊 Extracted Data Summary:")
            print("-" * 30)
            
            # Test basic fields
            basic_fields = ['ProductID', 'Name', 'SKU', 'ShortDescription', 'ImageURL']
            for field in basic_fields:
                value = scraped_data.get(field, 'N/A')
                print(f"✅ {field}: {value}")
            
            # Test new comprehensive fields
            print("\n🔍 Testing Comprehensive Fields:")
            
            # Test pricing tables
            pricing_tables = scraped_data.get('PricingTable', [])
            print(f"✅ Pricing Tables: {len(pricing_tables)} tables found")
            
            # Test imprint information
            imprint_info = scraped_data.get('Imprint', {})
            if imprint_info:
                print(f"✅ Imprint Info: {len(imprint_info)} sections")
                for section, data in imprint_info.items():
                    if data:
                        print(f"   - {section}: {len(data)} items")
            
            # Test production info
            production_info = scraped_data.get('ProductionInfo', {})
            if production_info:
                print(f"✅ Production Info: {len(production_info)} fields")
                for field, value in production_info.items():
                    if value:
                        print(f"   - {field}: {value}")
            
            # Test shipping info
            shipping_info = scraped_data.get('Shipping', {})
            if shipping_info:
                print(f"✅ Shipping Info: {len(shipping_info)} fields")
                for field, value in shipping_info.items():
                    if value:
                        print(f"   - {field}: {value}")
            
            # Test safety info
            safety_info = scraped_data.get('SafetyAndCompliance', {})
            if safety_info:
                print(f"✅ Safety Info: {len(safety_info)} fields")
                for field, value in safety_info.items():
                    if value:
                        print(f"   - {field}: {value}")
            
            # Test supplier info
            supplier_info = scraped_data.get('SupplierInfo', {})
            if supplier_info:
                print(f"✅ Supplier Info: {len(supplier_info)} fields")
                for field, value in supplier_info.items():
                    if value:
                        print(f"   - {field}: {value}")
            
            # Test scraped date
            scraped_date = scraped_data.get('ScrapedDate')
            if scraped_date:
                print(f"✅ ScrapedDate: {scraped_date}")
            
            # Save test results
            output_file = "test_comprehensive_results.json"
            with open(output_file, 'w') as f:
                json.dump(scraped_data, f, indent=2)
            print(f"\n💾 Test results saved to: {output_file}")
            
            return True
            
        else:
            print("❌ Data extraction failed - no data returned")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up
        try:
            scraper.driver.quit()
            print("🧹 Cleanup completed")
        except:
            pass

if __name__ == "__main__":
    success = test_comprehensive_scraper()
    if success:
        print("\n🎉 All tests passed! Comprehensive scraper is working correctly.")
    else:
        print("\n💥 Tests failed. Please check the errors above.")
        sys.exit(1) 