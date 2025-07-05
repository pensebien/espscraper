#!/usr/bin/env python3
"""
Simple test to compare headful vs headless mode with actual login
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from espscraper.selenium_resilient_manager import SeleniumResilientManager
from espscraper.session_manager import SessionManager
import time

def test_login_performance():
    """Test login performance in both modes"""
    print("🔍 Testing login performance: Headful vs Headless")
    print("=" * 50)
    
    # Test headless mode
    print("\n🧪 Testing HEADLESS mode...")
    try:
        manager_headless = SeleniumResilientManager(headless=True, max_retries=3)
        driver_headless = manager_headless.get_driver()
        
        # Load the login page
        start_time = time.time()
        driver_headless.get("https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductDetails&productID=553467788&autoLaunchVS=0&tab=list")
        
        # Wait for page to load
        time.sleep(5)
        load_time = time.time() - start_time
        
        title = driver_headless.title
        current_url = driver_headless.current_url
        
        print(f"  ✅ Headless: Loaded in {load_time:.2f}s")
        print(f"     Title: {title}")
        print(f"     URL: {current_url}")
        
        manager_headless.quit()
        
    except Exception as e:
        print(f"  ❌ Headless failed: {e}")
    
    # Test headful mode
    print("\n🧪 Testing HEADFUL mode...")
    try:
        manager_headful = SeleniumResilientManager(headless=False, max_retries=3)
        driver_headful = manager_headful.get_driver()
        
        # Load the login page
        start_time = time.time()
        driver_headful.get("https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductDetails&productID=553467788&autoLaunchVS=0&tab=list")
        
        # Wait for page to load
        time.sleep(5)
        load_time = time.time() - start_time
        
        title = driver_headful.title
        current_url = driver_headful.current_url
        
        print(f"  ✅ Headful: Loaded in {load_time:.2f}s")
        print(f"     Title: {title}")
        print(f"     URL: {current_url}")
        
        manager_headful.quit()
        
    except Exception as e:
        print(f"  ❌ Headful failed: {e}")

def test_session_manager():
    """Test session manager in both modes"""
    print("\n🔐 Testing session manager...")
    print("=" * 30)
    
    # Test headless
    print("\n🧪 Testing HEADLESS session...")
    try:
        session_headless = SessionManager(headless=True)
        success = session_headless.login()
        print(f"  {'✅' if success else '❌'} Headless login: {'Success' if success else 'Failed'}")
        session_headless.quit()
    except Exception as e:
        print(f"  ❌ Headless session failed: {e}")
    
    # Test headful
    print("\n🧪 Testing HEADFUL session...")
    try:
        session_headful = SessionManager(headless=False)
        success = session_headful.login()
        print(f"  {'✅' if success else '❌'} Headful login: {'Success' if success else 'Failed'}")
        session_headful.quit()
    except Exception as e:
        print(f"  ❌ Headful session failed: {e}")

def main():
    """Run all tests"""
    print("🔍 ESP Scraper Mode Comparison Test")
    print("=" * 50)
    
    test_login_performance()
    test_session_manager()
    
    print("\n" + "=" * 50)
    print("📊 SUMMARY:")
    print("• If headful mode works better, use --no-headless flag")
    print("• If both work, headless is faster but less stable")
    print("• Consider using headful mode for production scraping")

if __name__ == "__main__":
    main() 