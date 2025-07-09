#!/usr/bin/env python3
"""
Test script to check headless mode compatibility with the target website
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from espscraper.selenium_resilient_manager import SeleniumResilientManager
import time

def test_headless_vs_headful():
    """Compare headless vs headful mode behavior"""
    print("🧪 Testing headless vs headful mode compatibility...")
    
    # Test URLs to check
    test_urls = [
        "https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductDetails&productID=553467788&autoLaunchVS=0&tab=list",
        "https://httpbin.org/user-agent",
        "https://httpbin.org/headers"
    ]
    
    for url in test_urls:
        print(f"\n🔍 Testing URL: {url}")
        
        # Test headless mode
        print("  Testing headless mode...")
        try:
            manager_headless = SeleniumResilientManager(headless=True, max_retries=2)
            driver_headless = manager_headless.get_driver()
            
            driver_headless.get(url)
            time.sleep(3)
            
            # Check if page loaded properly
            title_headless = driver_headless.title
            url_headless = driver_headless.current_url
            
            print(f"    ✅ Headless: Title='{title_headless}', URL='{url_headless}'")
            
            # Check for common headless detection
            page_source = driver_headless.page_source.lower()
            if "headless" in page_source or "automation" in page_source:
                print(f"    ⚠️  Headless detection possible in page source")
            
            manager_headless.quit()
            
        except Exception as e:
            print(f"    ❌ Headless failed: {e}")
        
        # Test headful mode
        print("  Testing headful mode...")
        try:
            manager_headful = SeleniumResilientManager(headless=False, max_retries=2)
            driver_headful = manager_headful.get_driver()
            
            driver_headful.get(url)
            time.sleep(3)
            
            title_headful = driver_headful.title
            url_headful = driver_headful.current_url
            
            print(f"    ✅ Headful: Title='{title_headful}', URL='{url_headful}'")
            
            manager_headful.quit()
            
        except Exception as e:
            print(f"    ❌ Headful failed: {e}")

def test_stealth_features():
    """Test if stealth features are working"""
    print("\n🕵️ Testing stealth features...")
    
    try:
        manager = SeleniumResilientManager(headless=True, max_retries=2)
        driver = manager.get_driver()
        
        # Test webdriver property
        webdriver_detected = driver.execute_script("return navigator.webdriver")
        print(f"  WebDriver property: {webdriver_detected}")
        
        # Test user agent
        user_agent = driver.execute_script("return navigator.userAgent")
        print(f"  User Agent: {user_agent}")
        
        # Test automation features
        automation_features = driver.execute_script("""
            return {
                'webdriver': navigator.webdriver,
                'automation': window.navigator.automation,
                'chrome': window.chrome,
                'permissions': navigator.permissions
            }
        """)
        print(f"  Automation features: {automation_features}")
        
        manager.quit()
        
    except Exception as e:
        print(f"  ❌ Stealth test failed: {e}")

def test_connection_stability():
    """Test connection stability in headless mode"""
    print("\n🔗 Testing connection stability...")
    
    try:
        manager = SeleniumResilientManager(headless=True, max_retries=3)
        driver = manager.get_driver()
        
        # Test multiple page loads
        for i in range(5):
            print(f"  Test {i+1}/5: Loading page...")
            driver.get("https://httpbin.org/delay/1")
            time.sleep(2)
            
            # Check if driver is still responsive
            try:
                current_url = driver.current_url
                print(f"    ✅ Page loaded: {current_url}")
            except Exception as e:
                print(f"    ❌ Driver unresponsive: {e}")
                break
        
        manager.quit()
        print("  ✅ Connection stability test completed")
        
    except Exception as e:
        print(f"  ❌ Connection test failed: {e}")

def main():
    """Run all compatibility tests"""
    print("🔍 ESP Scraper Headless Compatibility Tests")
    print("=" * 50)
    
    test_headless_vs_headful()
    test_stealth_features()
    test_connection_stability()
    
    print("\n" + "=" * 50)
    print("✅ Compatibility tests complete!")
    print("\nIf headless mode fails but headful works:")
    print("1. The website may be detecting headless browsers")
    print("2. Try running with --no-aggressive-cleanup")
    print("3. Consider using headful mode for production")

if __name__ == "__main__":
    main() 