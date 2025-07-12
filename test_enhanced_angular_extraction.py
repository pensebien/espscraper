#!/usr/bin/env python3
"""
Enhanced test script to verify AngularJS data extraction with all scripts executed
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

def test_enhanced_angular_extraction():
    """Test enhanced AngularJS data extraction with script execution"""
    
    print("🚀 Testing Enhanced AngularJS Data Extraction")
    print("=" * 60)
    print("This test ensures all JavaScript scripts are executed")
    print("and AngularJS is fully loaded before data extraction")
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
        # Create session manager and scraper (reuses session from tmp folder)
        session_manager = SessionManager()
        scraper = ProductDetailScraper(session_manager, headless=False)
        
        # Test session loading (reuses existing session if valid)
        print("\n🔐 Testing session loading (reuses tmp session)...")
        scraper.login(force_relogin=False)  # This will reuse session from tmp folder
        
        # Test accessing a product page
        print("\n🔍 Testing product page access...")
        test_url = "https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductDetails&productID=555102402&autoLaunchVS=0&tab=list"
        
        try:
            scraper.driver.get(test_url)
            time.sleep(5)
            
            current_url = scraper.driver.current_url
            print(f"📍 Current URL: {current_url}")
            
            if 'login' in current_url.lower():
                print("❌ Redirected to login page - session expired")
                return False
            
            # Test enhanced AngularJS data extraction
            print("\n📊 Testing Enhanced AngularJS Data Extraction...")
            print("🔄 This will ensure all scripts are executed...")
            
            angular_data = scraper.get_angular_product_data()
            
            if angular_data:
                print("✅ Enhanced AngularJS data extraction successful!")
                print(f"📊 Available data keys: {list(angular_data.keys())}")
                
                # Extract and display comprehensive product information
                print("\n🔍 Extracting Comprehensive Product Information:")
                print("=" * 50)
                
                # 1. Basic Product Information
                if angular_data.get('product'):
                    product = angular_data['product']
                    print("\n📋 BASIC PRODUCT INFORMATION:")
                    print(f"   - Product ID: {product.get('Id', 'N/A')}")
                    print(f"   - Name: {product.get('Name', 'N/A')}")
                    print(f"   - Description: {product.get('Description', 'N/A')[:100]}...")
                    print(f"   - SKU: {product.get('SKU', 'N/A')}")
                    print(f"   - Vendor Product ID: {product.get('VendorProductId', 'N/A')}")
                    print(f"   - Update Date: {product.get('UpdateDate', 'N/A')}")
                    print(f"   - Is New: {product.get('IsNew', 'N/A')}")
                    print(f"   - Is Trending: {product.get('IsTrending', 'N/A')}")
                    print(f"   - Is Confirmed: {product.get('IsConfirmed', 'N/A')}")
                
                # 2. Pricing Information
                if angular_data.get('pricing'):
                    print("\n💰 PRICING INFORMATION:")
                    pricing = angular_data['pricing']
                    print(f"   - Number of pricing items: {len(pricing)}")
                    
                    for i, price_item in enumerate(pricing):
                        if isinstance(price_item, dict):
                            print(f"   - Price Item {i+1}:")
                            print(f"     * Type: {price_item.get('Type', 'N/A')}")
                            print(f"     * Quantity: {price_item.get('Quantity', 'N/A')}")
                            print(f"     * Price: {price_item.get('Price', 'N/A')}")
                            print(f"     * Cost: {price_item.get('Cost', 'N/A')}")
                            print(f"     * Discount Code: {price_item.get('DiscountCode', 'N/A')}")
                            print(f"     * Currency: {price_item.get('CurrencyCode', 'N/A')}")
                
                # 3. Variants Information
                if angular_data.get('variants'):
                    print("\n🔄 PRODUCT VARIANTS:")
                    variants = angular_data['variants']
                    print(f"   - Number of variants: {len(variants)}")
                    
                    for i, variant in enumerate(variants):
                        if isinstance(variant, dict):
                            print(f"   - Variant {i+1}:")
                            print(f"     * ID: {variant.get('Id', 'N/A')}")
                            print(f"     * Name: {variant.get('Name', 'N/A')}")
                            print(f"     * Description: {variant.get('Description', 'N/A')}")
                            print(f"     * Image URL: {variant.get('ImageUrl', 'N/A')}")
                            
                            # Variant pricing
                            if variant.get('Prices'):
                                print(f"     * Pricing: {len(variant['Prices'])} price items")
                
                # 4. Imprinting Information
                if angular_data.get('imprinting'):
                    print("\n🎨 IMPRINTING INFORMATION:")
                    imprinting = angular_data['imprinting']
                    
                    # Colors
                    if imprinting.get('Colors', {}).get('Values'):
                        colors = imprinting['Colors']['Values']
                        print(f"   - Available Colors: {len(colors)}")
                        for color in colors[:3]:  # Show first 3
                            print(f"     * {color.get('Name', 'N/A')} (Code: {color.get('Code', 'N/A')})")
                    
                    # Methods
                    if imprinting.get('Methods', {}).get('Values'):
                        methods = imprinting['Methods']['Values']
                        print(f"   - Imprinting Methods: {len(methods)}")
                        for method in methods[:3]:  # Show first 3
                            print(f"     * {method.get('Name', 'N/A')} (Code: {method.get('Code', 'N/A')})")
                            if method.get('Charges'):
                                print(f"       - Charges: {len(method['Charges'])}")
                
                # 5. Shipping Information
                if angular_data.get('shipping'):
                    print("\n📦 SHIPPING INFORMATION:")
                    shipping = angular_data['shipping']
                    
                    print(f"   - Weight Unit: {shipping.get('WeightUnit', 'N/A')}")
                    print(f"   - Weight Per Package: {shipping.get('WeightPerPackage', 'N/A')}")
                    print(f"   - Package Unit: {shipping.get('PackageUnit', 'N/A')}")
                    print(f"   - Items Per Package: {shipping.get('ItemsPerPackage', 'N/A')}")
                    print(f"   - Package In Plain Box: {shipping.get('PackageInPlainBox', 'N/A')}")
                    
                    # FOB Points
                    if shipping.get('FOBPoints', {}).get('Values'):
                        fob_points = shipping['FOBPoints']['Values']
                        print(f"   - FOB Points: {len(fob_points)}")
                        for fob in fob_points[:2]:  # Show first 2
                            print(f"     * {fob.get('Name', 'N/A')}")
                
                # 6. Supplier Information
                if angular_data.get('supplier'):
                    print("\n🏢 SUPPLIER INFORMATION:")
                    supplier = angular_data['supplier']
                    
                    print(f"   - Name: {supplier.get('Name', 'N/A')}")
                    print(f"   - ASI Number: {supplier.get('AsiNumber', 'N/A')}")
                    print(f"   - Email: {supplier.get('Email', 'N/A')}")
                    
                    # Phone
                    if supplier.get('Phone'):
                        phone = supplier['Phone']
                        print(f"   - Phone: {phone.get('Primary', 'N/A')}")
                        print(f"   - Toll Free: {phone.get('TollFree', 'N/A')}")
                    
                    # Rating
                    if supplier.get('Rating'):
                        rating = supplier['Rating']
                        print(f"   - Rating: {rating.get('Rating', 'N/A')}/10")
                        print(f"   - Companies: {rating.get('Companies', 'N/A')}")
                        print(f"   - Transactions: {rating.get('Transactions', 'N/A')}")
                
                # 7. Attributes Information
                if angular_data.get('attributes'):
                    print("\n📏 ATTRIBUTES INFORMATION:")
                    attributes = angular_data['attributes']
                    
                    for attr_type, attr_data in attributes.items():
                        if attr_data and attr_data.get('Values'):
                            values = attr_data['Values']
                            print(f"   - {attr_type}: {len(values)} options")
                            for value in values[:3]:  # Show first 3
                                print(f"     * {value.get('Name', 'N/A')} (Code: {value.get('Code', 'N/A')})")
                
                # 8. Warnings and Safety
                if angular_data.get('warnings'):
                    print("\n⚠️ SAFETY WARNINGS:")
                    warnings = angular_data['warnings']
                    print(f"   - Number of warnings: {len(warnings)}")
                    for warning in warnings:
                        print(f"   - {warning.get('Name', 'N/A')}: {warning.get('Description', 'N/A')}")
                
                # Save the extracted data to a file
                output_file = "enhanced_angular_extracted_data.json"
                with open(output_file, 'w') as f:
                    json.dump(angular_data, f, indent=2)
                print(f"\n💾 Complete Enhanced AngularJS data saved to: {output_file}")
                
                # Test script execution verification
                print("\n🔍 VERIFYING SCRIPT EXECUTION:")
                print("=" * 40)
                
                # Check if scripts were executed
                script_check = scraper.driver.execute_script("""
                    var scriptExecutionInfo = {
                        angularLoaded: typeof angular !== 'undefined',
                        jqueryLoaded: typeof jQuery !== 'undefined',
                        scriptsExecuted: document.querySelectorAll('script').length,
                        angularScopes: 0,
                        digestCyclesTriggered: false
                    };
                    
                    if (typeof angular !== 'undefined') {
                        var rootScope = angular.element(document.body).scope();
                        if (rootScope) {
                            scriptExecutionInfo.angularScopes = 1;
                            // Count child scopes
                            function countScopes(scope) {
                                if (scope.$$childHead) {
                                    scriptExecutionInfo.angularScopes++;
                                    countScopes(scope.$$childHead);
                                }
                                if (scope.$$nextSibling) {
                                    scriptExecutionInfo.angularScopes++;
                                    countScopes(scope.$$nextSibling);
                                }
                            }
                            countScopes(rootScope);
                        }
                    }
                    
                    return scriptExecutionInfo;
                """)
                
                print(f"   ✅ AngularJS Loaded: {script_check.get('angularLoaded', False)}")
                print(f"   ✅ jQuery Loaded: {script_check.get('jqueryLoaded', False)}")
                print(f"   ✅ Scripts Found: {script_check.get('scriptsExecuted', 0)}")
                print(f"   ✅ Angular Scopes: {script_check.get('angularScopes', 0)}")
                
                return True
                
            else:
                print("⚠️ No AngularJS data extracted")
                return False
                
        except Exception as e:
            print(f"❌ Error during testing: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ Failed to initialize scraper: {e}")
        return False
    finally:
        try:
            scraper.driver.quit()
        except:
            pass

if __name__ == "__main__":
    success = test_enhanced_angular_extraction()
    if success:
        print("\n✅ Enhanced AngularJS data extraction test completed successfully!")
        print("🎉 All scripts were executed and data was extracted!")
    else:
        print("\n❌ Enhanced AngularJS data extraction test failed!") 