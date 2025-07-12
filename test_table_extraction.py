#!/usr/bin/env python3
"""
Test script specifically for table extraction:
- Pricing tables (main product + variants)
- Imprint charges (nested charges)
- AngularJS custom components
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

def test_table_extraction():
    """Test comprehensive table extraction"""
    
    print("📊 Testing Comprehensive Table Extraction")
    print("=" * 50)
    
    # Check environment variables
    required_env_vars = ['ESP_USERNAME', 'ESP_PASSWORD', 'PRODUCTS_URL']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        print("Please set these in your .env file")
        return False
    
    print("✅ Environment variables loaded")
    
    try:
        # Create session manager and scraper
        session_manager = SessionManager()
        scraper = ProductDetailScraper(session_manager, headless=False)
        
        # Test session loading
        print("\n🔐 Testing session loading...")
        scraper.login(force_relogin=False)
        
        # Test accessing a product page
        print("\n🔍 Testing product page access...")
        test_url = "https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductDetails&productID=12345&autoLaunchVS=0&tab=list"
        
        try:
            scraper.driver.get(test_url)
            time.sleep(5)
            
            current_url = scraper.driver.current_url
            print(f"📍 Current URL: {current_url}")
            
            if 'login' in current_url.lower():
                print("❌ Redirected to login page - session expired")
                return False
            
            # Test AngularJS data extraction
            print("\n📊 Testing AngularJS data extraction...")
            angular_data = scraper.get_angular_product_data()
            
            if angular_data:
                print("✅ AngularJS data extraction successful!")
                print(f"📊 Available AngularJS data: {list(angular_data.keys())}")
                
                # Test specific AngularJS data
                if angular_data.get('pricing'):
                    print(f"✅ Pricing data found: {len(angular_data['pricing'])} items")
                else:
                    print("⚠️ No pricing data in AngularJS")
                
                if angular_data.get('variants'):
                    print(f"✅ Variants data found: {len(angular_data['variants'])} items")
                else:
                    print("⚠️ No variants data in AngularJS")
                
                if angular_data.get('imprinting'):
                    print(f"✅ Imprinting data found: {len(angular_data['imprinting'])} fields")
                else:
                    print("⚠️ No imprinting data in AngularJS")
            else:
                print("⚠️ No AngularJS data extracted")
            
            # Test comprehensive product scraping
            print("\n📊 Testing comprehensive product scraping...")
            scraped_data = scraper.scrape_product_detail_page()
            
            if scraped_data:
                print("✅ Product scraping successful!")
                
                # Test pricing tables
                pricing_table = scraped_data.get('PricingTable', [])
                if pricing_table:
                    print(f"✅ Pricing tables found: {len(pricing_table)} tables")
                    for i, table in enumerate(pricing_table):
                        table_type = table.get('type', 'unknown')
                        breaks = table.get('breaks', [])
                        print(f"   📊 Table {i+1}: {table_type} - {len(breaks)} price breaks")
                else:
                    print("⚠️ No pricing tables found")
                
                # Test imprint information
                imprint_info = scraped_data.get('Imprint', {})
                if imprint_info:
                    print(f"✅ Imprint information found: {len(imprint_info)} sections")
                    
                    # Check methods
                    methods = imprint_info.get('Methods', {})
                    if methods:
                        print(f"   📊 Imprint methods: {len(methods)} methods")
                        for method_name, method_data in methods.items():
                            charges = method_data.get('Charges', [])
                            print(f"      📋 {method_name}: {len(charges)} charges")
                    else:
                        print("   ⚠️ No imprint methods found")
                    
                    # Check services
                    services = imprint_info.get('Services', {})
                    if services:
                        print(f"   📊 Imprint services: {len(services)} services")
                        for service_name, service_data in services.items():
                            charges = service_data.get('Charges', [])
                            print(f"      📋 {service_name}: {len(charges)} charges")
                    else:
                        print("   ⚠️ No imprint services found")
                else:
                    print("⚠️ No imprint information found")
                
                # Test other fields
                fields_to_test = [
                    ('Price', 'Price range'),
                    ('SKU', 'Product number'),
                    ('ProductionInfo', 'Production information'),
                    ('Shipping', 'Shipping information'),
                    ('SafetyAndCompliance', 'Safety and compliance'),
                    ('SupplierInfo', 'Supplier information')
                ]
                
                for field_name, description in fields_to_test:
                    field_value = scraped_data.get(field_name)
                    if field_value and field_value != "N/A":
                        if isinstance(field_value, list) and len(field_value) > 0:
                            print(f"✅ {description}: {len(field_value)} items")
                        elif isinstance(field_value, dict) and field_value:
                            print(f"✅ {description}: {len(field_value)} fields")
                        else:
                            print(f"✅ {description}: {field_value}")
                    else:
                        print(f"⚠️ {description}: Not found or empty")
                
                # Save detailed data for inspection
                detailed_file = "detailed_scraped_data.json"
                with open(detailed_file, 'w') as f:
                    json.dump(scraped_data, f, indent=2)
                print(f"\n💾 Detailed data saved to {detailed_file}")
                
                return True
                
            else:
                print("❌ Product scraping failed")
                return False
                
        except Exception as e:
            print(f"❌ Error during test: {e}")
            return False
        
    except Exception as e:
        print(f"❌ Error during test setup: {e}")
        return False
    
    finally:
        # Clean up
        try:
            scraper.driver.quit()
        except:
            pass

if __name__ == "__main__":
    success = test_table_extraction()
    if success:
        print("\n✅ Table extraction test completed successfully!")
    else:
        print("\n❌ Table extraction test failed!") 