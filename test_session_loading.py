#!/usr/bin/env python3
"""
Test script for session loading and validation
Tests if the scraper properly loads and validates existing sessions
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

def test_session_loading():
    """Test session loading and validation"""
    
    print("🔐 Testing Session Loading and Validation")
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
        # Create session manager
        session_manager = SessionManager()
        
        # Check if session files exist
        cookie_file = session_manager.cookie_file
        state_file = session_manager.state_file
        
        print(f"📁 Cookie file: {cookie_file}")
        print(f"📁 State file: {state_file}")
        
        if os.path.exists(cookie_file):
            print("✅ Cookie file exists")
        else:
            print("⚠️ Cookie file does not exist")
        
        if os.path.exists(state_file):
            print("✅ State file exists")
        else:
            print("⚠️ State file does not exist")
        
        # Create scraper
        print("\n🤖 Creating scraper...")
        scraper = ProductDetailScraper(session_manager, headless=False)
        
        # Test session loading
        print("\n🔐 Testing session loading...")
        scraper.login(force_relogin=False)
        
        # Check if session was validated
        if hasattr(scraper, '_session_validated'):
            if scraper._session_validated:
                print("✅ Session validation passed!")
            else:
                print("❌ Session validation failed - session may be expired")
        else:
            print("⚠️ Session validation not performed")
        
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
            else:
                print("✅ Successfully accessed product page")
                return True
                
        except Exception as e:
            print(f"❌ Error accessing product page: {e}")
            return False
        
    except Exception as e:
        print(f"❌ Error during session test: {e}")
        return False
    
    finally:
        # Clean up
        try:
            scraper.driver.quit()
        except:
            pass

if __name__ == "__main__":
    success = test_session_loading()
    if success:
        print("\n✅ Session loading test completed successfully!")
    else:
        print("\n❌ Session loading test failed!") 