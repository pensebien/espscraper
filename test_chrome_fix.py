#!/usr/bin/env python3
"""
Simple test script to verify Chrome user data directory fixes
"""

import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def test_chrome_driver_creation():
    """Test if Chrome driver can be created without user data directory conflicts"""
    print("🧪 Testing Chrome driver creation...")
    
    try:
        # Create Chrome options with our fixes
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")
        options.add_argument("--disable-javascript")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-features=TranslateUI")
        options.add_argument("--disable-ipc-flooding-protection")
        # Don't use user data directory in CI to avoid conflicts
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-sync")
        # Use unique temporary user data directory to avoid conflicts
        import tempfile
        import os
        import time
        
        unique_id = f"{int(time.time())}_{os.getpid()}"
        user_data_dir = os.path.join(tempfile.gettempdir(), f"chrome_temp_{unique_id}")
        options.add_argument(f"--user-data-dir={user_data_dir}")
        options.add_argument("--incognito")
        
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        print(f"📁 Using unique user data directory: {user_data_dir}")
        
        # Create Chrome driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        print("✅ Chrome driver created successfully!")
        
        # Test basic functionality
        driver.get("https://www.google.com")
        print(f"✅ Successfully navigated to: {driver.title}")
        
        # Clean up
        driver.quit()
        print("✅ Chrome driver closed successfully")
        
        # Clean up temporary directory
        try:
            import shutil
            shutil.rmtree(user_data_dir, ignore_errors=True)
            print(f"🧹 Cleaned up temporary directory: {user_data_dir}")
        except Exception as e:
            print(f"⚠️ Warning: Could not clean up directory: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Chrome driver creation failed: {e}")
        return False

def test_multiple_chrome_instances():
    """Test creating multiple Chrome instances to check for conflicts"""
    print("\n🧪 Testing multiple Chrome instances...")
    
    drivers = []
    success_count = 0
    
    try:
        for i in range(3):
            print(f"Creating Chrome instance {i+1}/3...")
            
            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            # Use unique temporary user data directory
            import tempfile
            import os
            import time
            
            unique_id = f"{int(time.time())}_{os.getpid()}_{i}"
            user_data_dir = os.path.join(tempfile.gettempdir(), f"chrome_temp_{unique_id}")
            options.add_argument(f"--user-data-dir={user_data_dir}")
            options.add_argument("--incognito")
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            
            drivers.append((driver, user_data_dir))
            success_count += 1
            print(f"✅ Chrome instance {i+1} created successfully")
            
            # Small delay between creations
            time.sleep(1)
        
        print(f"✅ Successfully created {success_count}/3 Chrome instances")
        
        # Clean up all drivers
        for driver, user_data_dir in drivers:
            try:
                driver.quit()
                import shutil
                shutil.rmtree(user_data_dir, ignore_errors=True)
                print(f"🧹 Cleaned up driver and directory: {user_data_dir}")
            except Exception as e:
                print(f"⚠️ Warning: Could not clean up: {e}")
        
        return success_count == 3
        
    except Exception as e:
        print(f"❌ Multiple Chrome instances test failed: {e}")
        
        # Clean up any created drivers
        for driver, user_data_dir in drivers:
            try:
                driver.quit()
                import shutil
                shutil.rmtree(user_data_dir, ignore_errors=True)
            except:
                pass
        
        return False

if __name__ == "__main__":
    print("🚀 Testing Chrome user data directory fixes...")
    print("=" * 50)
    
    # Test 1: Single Chrome driver creation
    test1_success = test_chrome_driver_creation()
    
    # Test 2: Multiple Chrome instances
    test2_success = test_multiple_chrome_instances()
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"Single Chrome driver: {'✅ PASS' if test1_success else '❌ FAIL'}")
    print(f"Multiple Chrome instances: {'✅ PASS' if test2_success else '❌ FAIL'}")
    
    if test1_success and test2_success:
        print("\n🎉 All tests passed! Chrome user data directory fixes are working.")
    else:
        print("\n⚠️ Some tests failed. Chrome user data directory issues may still exist.")
