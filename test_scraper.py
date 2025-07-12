#!/usr/bin/env python3
"""
Simple test script to test product detail scraping locally.
"""

import os
import sys
import json
import time
from espscraper.scrape_product_details import ProductDetailScraper
from espscraper.session_manager import SessionManager
from dotenv import load_dotenv
load_dotenv()

def test_single_product():
    """Test scraping a single product detail page."""
    
    print("🧪 Testing Product Detail Scraper...")
    
    # Initialize session manager and scraper
    session_manager = SessionManager()
    scraper = ProductDetailScraper(
        session_manager,
        headless=False,  # Set to True if you want headless mode
        limit=1,
        debug_mode=True
    )
    
    try:
        # Login first
        print("🔐 Logging in...")
        scraper.login(force_relogin=True)
        
        # Test with a single product URL
        test_url = "https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductDetails&productID=12345&autoLaunchVS=0&tab=list"
        
        print(f"🌐 Loading test product page: {test_url}")
        scraper.driver.get(test_url)
        
        # Wait for page to load
        time.sleep(5)
        
        # Scrape the product details
        print("📝 Scraping product details...")
        product_data = scraper.scrape_product_detail_page()
        
        if product_data:
            print("✅ Successfully scraped product data!")
            print("\n📊 Product Data Summary:")
            print(f"  ProductID: {product_data.get('ProductID', 'N/A')}")
            print(f"  Name: {product_data.get('Name', 'N/A')}")
            print(f"  SKU: {product_data.get('SKU', 'N/A')}")
            print(f"  ProductNumber: {product_data.get('ProductNumber', 'N/A')}")
            print(f"  ASINumber: {product_data.get('ASINumber', 'N/A')}")
            print(f"  UpdateDate: {product_data.get('UpdateDate', 'N/A')}")
            print(f"  ProductURL: {product_data.get('ProductURL', 'N/A')}")
            print(f"  ProductArtURL: {product_data.get('ProductArtURL', 'N/A')}")
            print(f"  ScrapedDate: {product_data.get('ScrapedDate', 'N/A')}")
            print(f"  ImageURL: {product_data.get('ImageURL', 'N/A')}")
            print(f"  Price: {product_data.get('PricingTable', 'N/A')}")
            
            # Save to test file
            test_file = "test_product_output.json"
            with open(test_file, 'w') as f:
                json.dump(product_data, f, indent=2)
            print(f"\n💾 Saved detailed output to: {test_file}")
            
        else:
            print("❌ Failed to scrape product data")
            
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up
        try:
            scraper.driver.quit()
            print("🧹 Cleaned up driver")
        except:
            pass

def test_with_real_product_id():
    """Test with a real product ID if you have one."""
    
    print("\n🧪 Testing with real product ID...")
    
    # You can change this to a real product ID you know exists
    real_product_id = "12345"  # Change this to a real product ID
    
    session_manager = SessionManager()
    scraper = ProductDetailScraper(
        session_manager,
        headless=False,
        limit=1,
        debug_mode=True
    )
    
    try:
        # Login
        print("🔐 Logging in...")
        scraper.login(force_relogin=True)
        
        # Build real product URL
        real_url = f"https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductDetails&productID={real_product_id}&autoLaunchVS=0&tab=list"
        
        print(f"🌐 Loading real product page: {real_url}")
        scraper.driver.get(real_url)
        
        # Wait for page to load
        time.sleep(5)
        
        # Scrape
        print("📝 Scraping product details...")
        product_data = scraper.scrape_product_detail_page()
        
        if product_data:
            print("✅ Successfully scraped real product data!")
            print(f"  ProductID: {product_data.get('ProductID', 'N/A')}")
            print(f"  Name: {product_data.get('Name', 'N/A')}")
            print(f"  ProductNumber: {product_data.get('ProductNumber', 'N/A')}")
            print(f"  UpdateDate: {product_data.get('UpdateDate', 'N/A')}")
            
            # Save to test file
            test_file = f"test_real_product_{real_product_id}.json"
            with open(test_file, 'w') as f:
                json.dump(product_data, f, indent=2)
            print(f"💾 Saved to: {test_file}")
            
        else:
            print("❌ Failed to scrape real product data")
            
    except Exception as e:
        print(f"❌ Error during real product testing: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        try:
            scraper.driver.quit()
        except:
            pass

if __name__ == "__main__":
    print("🚀 Starting Product Detail Scraper Test")
    print("=" * 50)
    
    # Check if environment variables are set
    required_vars = ["ESP_USERNAME", "ESP_PASSWORD", "PRODUCTS_URL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these environment variables before running the test.")
        sys.exit(1)
    
    # Run basic test
    test_single_product()
    
    # Ask if user wants to test with real product ID
    print("\n" + "=" * 50)
    response = input("Do you want to test with a real product ID? (y/n): ").lower().strip()
    
    if response == 'y':
        real_id = input("Enter a real product ID to test: ").strip()
        if real_id:
            # Update the test function to use the provided ID
            def test_with_real_product_id():
                session_manager = SessionManager()
                scraper = ProductDetailScraper(
                    session_manager,
                    headless=False,
                    limit=1,
                    debug_mode=True
                )
                
                try:
                    print("🔐 Logging in...")
                    scraper.login(force_relogin=True)
                    
                    real_url = f"https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductDetails&productID={real_id}&autoLaunchVS=0&tab=list"
                    
                    print(f"🌐 Loading real product page: {real_url}")
                    scraper.driver.get(real_url)
                    
                    time.sleep(5)
                    
                    print("📝 Scraping product details...")
                    product_data = scraper.scrape_product_detail_page()
                    
                    if product_data:
                        print("✅ Successfully scraped real product data!")
                        print(f"  ProductID: {product_data.get('ProductID', 'N/A')}")
                        print(f"  Name: {product_data.get('Name', 'N/A')}")
                        print(f"  ProductNumber: {product_data.get('ProductNumber', 'N/A')}")
                        print(f"  UpdateDate: {product_data.get('UpdateDate', 'N/A')}")
                        
                        test_file = f"test_real_product_{real_id}.json"
                        with open(test_file, 'w') as f:
                            json.dump(product_data, f, indent=2)
                        print(f"💾 Saved to: {test_file}")
                        
                    else:
                        print("❌ Failed to scrape real product data")
                        
                except Exception as e:
                    print(f"❌ Error during real product testing: {e}")
                    import traceback
                    traceback.print_exc()
                    
                finally:
                    try:
                        scraper.driver.quit()
                    except:
                        pass
            
            test_with_real_product_id()
    
    print("\n✅ Test completed!") 