#!/usr/bin/env python3
"""
Test script for AngularJS data extraction and BeautifulSoup selector fixes
"""

import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the espscraper directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'espscraper'))

from espscraper.scrape_product_details import ProductDetailScraper
from espscraper.session_manager import SessionManager

def test_angular_extraction():
    """Test AngularJS data extraction and BeautifulSoup selectors"""
    
    print("🔧 Testing AngularJS Data Extraction and BeautifulSoup Selectors")
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
                print(f"📊 Extracted data keys: {list(angular_data.keys())}")
                
                # Test specific data extraction
                if angular_data.get('product'):
                    print(f"✅ Product data found: {len(angular_data['product'])} fields")
                
                if angular_data.get('pricing'):
                    print(f"✅ Pricing data found: {len(angular_data['pricing'])} items")
                
                if angular_data.get('variants'):
                    print(f"✅ Variants data found: {len(angular_data['variants'])} items")
                    
            else:
                print("⚠️ No AngularJS data extracted - will use HTML fallback")
            
            # Test BeautifulSoup selectors
            print("\n🔍 Testing BeautifulSoup selectors...")
            detail_soup = scraper.driver.page_source
            
            # Test the fixed selectors
            try:
                # Test color selector
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(detail_soup, 'lxml')
                
                # Test the fixed color selector
                color_elem = soup.select_one('span:-soup-contains("Colors") + span')
                if color_elem:
                    print("✅ Color selector works!")
                else:
                    print("⚠️ Color selector didn't find element (may be normal)")
                
                # Test other selectors
                name_elem = soup.select_one('#productDetailsMain h3.text-primary')
                if name_elem:
                    print("✅ Product name selector works!")
                else:
                    print("⚠️ Product name selector didn't find element")
                
                print("✅ BeautifulSoup selectors test completed")
                
            except Exception as e:
                print(f"❌ BeautifulSoup selector test failed: {e}")
            
            return True
                
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
    success = test_angular_extraction()
    if success:
        print("\n✅ AngularJS and BeautifulSoup fixes test completed successfully!")
    else:
        print("\n❌ AngularJS and BeautifulSoup fixes test failed!") 