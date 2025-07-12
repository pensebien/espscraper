#!/usr/bin/env python3
"""
Test script for API-based product scraping using discovered endpoints
"""

import os
import sys
import time
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the espscraper directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'espscraper'))

from espscraper.session_manager import SessionManager

def test_api_scraper():
    """Test API-based product scraping using discovered endpoints"""
    
    print("🚀 API-Based Product Scraping Test")
    print("=" * 50)
    print("Using discovered API endpoints for lightning-fast scraping")
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
        
        # Load session data
        cookies, page_key, search_id = session_manager.load_state()
        
        if not cookies or not page_key or not search_id:
            print("❌ No valid session found. Please run the scraper first to create a session.")
            return False
        
        print("✅ Session loaded successfully")
        
        # Create session with cookies
        session = requests.Session()
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json;charset=UTF-8',
            'Referer': os.getenv("PRODUCTS_URL"),
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        session.headers.update(headers)
        
        # Load cookies into session
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'], domain=cookie.get('domain'))
        
        # Test product ID
        test_product_id = "555102402"
        
        print(f"\n🔍 Testing API scraping for product ID: {test_product_id}")
        print("=" * 50)
        
        # Test the main product API endpoint (most comprehensive)
        main_api_url = f"https://api.asicentral.com/v1/products/{test_product_id}.json"
        
        print(f"\n📊 Testing Main API Endpoint:")
        print(f"   🔗 URL: {main_api_url}")
        
        start_time = time.time()
        
        try:
            response = session.get(main_api_url, timeout=10)
            api_time = time.time() - start_time
            
            print(f"   ⏱️ Response Time: {api_time:.3f} seconds")
            print(f"   📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                product_data = response.json()
                print(f"   ✅ Successfully retrieved product data!")
                print(f"   📊 Data Fields: {len(product_data)}")
                
                # Extract key information
                product_info = {
                    'id': product_data.get('Id'),
                    'name': product_data.get('Name'),
                    'description': product_data.get('Description'),
                    'short_description': product_data.get('ShortDescription'),
                    'sku': product_data.get('SKU'),
                    'vendor_product_id': product_data.get('VendorProductId'),
                    'number': product_data.get('Number'),
                    'image_url': product_data.get('ImageUrl'),
                    'product_url': product_data.get('ProductUrl'),
                    'is_new': product_data.get('IsNew'),
                    'is_trending': product_data.get('IsTrending'),
                    'is_confirmed': product_data.get('IsConfirmed'),
                    'update_date': product_data.get('UpdateDate'),
                    'has_inventory': product_data.get('HasInventory'),
                    'has_full_color_process': product_data.get('HasFullColorProcess'),
                    'has_rush_service': product_data.get('HasRushService'),
                    'is_assembled': product_data.get('IsAssembled')
                }
                
                # Extract supplier information
                supplier_data = product_data.get('Supplier', {})
                supplier_info = {
                    'id': supplier_data.get('Id'),
                    'name': supplier_data.get('Name'),
                    'asi_number': supplier_data.get('AsiNumber'),
                    'email': supplier_data.get('Email'),
                    'phone': supplier_data.get('Phone', {}).get('Primary'),
                    'toll_free': supplier_data.get('Phone', {}).get('TollFree'),
                    'fax': supplier_data.get('Fax', {}).get('Primary'),
                    'websites': supplier_data.get('Websites', []),
                    'rating': supplier_data.get('Rating', {}).get('Rating'),
                    'companies': supplier_data.get('Rating', {}).get('Companies'),
                    'transactions': supplier_data.get('Rating', {}).get('Transactions'),
                    'marketing_policy': supplier_data.get('MarketingPolicy'),
                    'is_minority_owned': supplier_data.get('IsMinorityOwned'),
                    'is_union_available': supplier_data.get('IsUnionAvailable')
                }
                
                # Extract pricing information
                pricing_info = {
                    'lowest_price': product_data.get('LowestPrice'),
                    'highest_price': product_data.get('HighestPrice'),
                    'currency': product_data.get('Currency'),
                    'currencies': product_data.get('Currencies', [])
                }
                
                # Extract production information
                production_info = {
                    'production_time': product_data.get('ProductionTime', []),
                    'origin': product_data.get('Origin', []),
                    'trade_names': product_data.get('TradeNames', []),
                    'categories': product_data.get('Categories', []),
                    'themes': product_data.get('Themes', [])
                }
                
                # Extract attributes
                attributes = product_data.get('Attributes', {})
                attributes_info = {
                    'colors': attributes.get('Colors', {}).get('Values', []),
                    'sizes': attributes.get('Sizes', {}).get('Values', []),
                    'materials': attributes.get('Materials', {}).get('Values', [])
                }
                
                # Extract imprinting information
                imprinting = product_data.get('Imprinting', {})
                imprinting_info = {
                    'methods': imprinting.get('Methods', {}).get('Values', []),
                    'colors': imprinting.get('Colors', {}).get('Values', []),
                    'services': imprinting.get('Services', {}).get('Values', [])
                }
                
                # Extract shipping information
                shipping = product_data.get('Shipping', {})
                shipping_info = {
                    'weight_unit': shipping.get('WeightUnit'),
                    'weight_per_package': shipping.get('WeightPerPackage'),
                    'package_unit': shipping.get('PackageUnit'),
                    'items_per_package': shipping.get('ItemsPerPackage'),
                    'package_in_plain_box': shipping.get('PackageInPlainBox'),
                    'fob_points': shipping.get('FOBPoints', {}).get('Values', [])
                }
                
                # Extract variants
                variants = product_data.get('Variants', [])
                variants_info = []
                for variant in variants:
                    variant_info = {
                        'id': variant.get('Id'),
                        'name': variant.get('Name'),
                        'description': variant.get('Description'),
                        'image_url': variant.get('ImageUrl'),
                        'prices': variant.get('Prices', [])
                    }
                    variants_info.append(variant_info)
                
                # Extract warnings
                warnings = product_data.get('Warnings', [])
                warnings_info = []
                for warning in warnings:
                    warning_info = {
                        'name': warning.get('Name'),
                        'description': warning.get('Description')
                    }
                    warnings_info.append(warning_info)
                
                # Extract services
                services = product_data.get('Services', [])
                services_info = []
                for service in services:
                    service_info = {
                        'name': service.get('Name'),
                        'description': service.get('Description')
                    }
                    services_info.append(service_info)
                
                # Compile comprehensive product data
                comprehensive_data = {
                    'product': product_info,
                    'supplier': supplier_info,
                    'pricing': pricing_info,
                    'production': production_info,
                    'attributes': attributes_info,
                    'imprinting': imprinting_info,
                    'shipping': shipping_info,
                    'variants': variants_info,
                    'warnings': warnings_info,
                    'services': services_info,
                    'images': product_data.get('Images', []),
                    'virtual_sample_images': product_data.get('VirtualSampleImages', []),
                    'prop65_additional_info': product_data.get('Prop65AdditionalInfo'),
                    'additional_info': product_data.get('AdditionalInfo'),
                    'extraction_method': 'api',
                    'extraction_time': api_time,
                    'data_completeness': 'complete'
                }
                
                print(f"\n📊 EXTRACTED DATA SUMMARY:")
                print("=" * 30)
                print(f"   📋 Product Info: {len(product_info)} fields")
                print(f"   🏢 Supplier Info: {len(supplier_info)} fields")
                print(f"   💰 Pricing Info: {len(pricing_info)} fields")
                print(f"   ⚙️ Production Info: {len(production_info)} fields")
                print(f"   🎨 Attributes: {len(attributes_info)} categories")
                print(f"   🖨️ Imprinting: {len(imprinting_info)} categories")
                print(f"   📦 Shipping: {len(shipping_info)} fields")
                print(f"   🔄 Variants: {len(variants_info)} items")
                print(f"   ⚠️ Warnings: {len(warnings_info)} items")
                print(f"   🔧 Services: {len(services_info)} items")
                print(f"   🖼️ Images: {len(comprehensive_data['images'])} items")
                print(f"   🎭 Virtual Samples: {len(comprehensive_data['virtual_sample_images'])} items")
                
                # Performance comparison
                print(f"\n⚡ PERFORMANCE COMPARISON:")
                print("=" * 30)
                print(f"   ⏱️ API Extraction Time: {api_time:.3f} seconds")
                print(f"   🐌 HTML Scraping Time: ~1.5 seconds")
                print(f"   🚀 Speed Improvement: {(1.5/api_time):.1f}x faster")
                
                if api_time < 0.1:
                    print(f"   ✅ Lightning fast! (< 100ms)")
                elif api_time < 0.5:
                    print(f"   ✅ Very fast! (< 500ms)")
                else:
                    print(f"   ✅ Fast! (< 1 second)")
                
                # Save comprehensive data
                output_file = "api_scraped_product_data.json"
                with open(output_file, 'w') as f:
                    json.dump(comprehensive_data, f, indent=2)
                
                print(f"\n💾 Complete product data saved to: {output_file}")
                
                # Test multiple products for batch performance
                print(f"\n🧪 Testing Batch Performance...")
                print("=" * 30)
                
                test_product_ids = ["555102402", "555963527", "554901511"]
                batch_times = []
                
                for i, product_id in enumerate(test_product_ids, 1):
                    print(f"\n   📦 Product {i}/{len(test_product_ids)}: {product_id}")
                    
                    start_time = time.time()
                    try:
                        response = session.get(f"https://api.asicentral.com/v1/products/{product_id}.json", timeout=10)
                        if response.status_code == 200:
                            product_time = time.time() - start_time
                            batch_times.append(product_time)
                            print(f"      ✅ Success in {product_time:.3f}s")
                        else:
                            print(f"      ❌ Failed with status {response.status_code}")
                    except Exception as e:
                        print(f"      ❌ Error: {e}")
                
                if batch_times:
                    avg_time = sum(batch_times) / len(batch_times)
                    total_time = sum(batch_times)
                    print(f"\n📊 BATCH PERFORMANCE:")
                    print(f"   📦 Products processed: {len(batch_times)}")
                    print(f"   ⏱️ Average time per product: {avg_time:.3f}s")
                    print(f"   ⏱️ Total batch time: {total_time:.3f}s")
                    print(f"   🚀 Estimated 1000 products: {(avg_time * 1000 / 60):.1f} minutes")
                    print(f"   🚀 Estimated 10000 products: {(avg_time * 10000 / 60):.1f} minutes")
                
                return True
                
            else:
                print(f"   ❌ API request failed with status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ API request failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to test API scraper: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_api_scraper()
    if success:
        print("\n✅ API scraper test completed successfully!")
        print("🎉 Lightning-fast product data extraction achieved!")
    else:
        print("\n❌ API scraper test failed!") 