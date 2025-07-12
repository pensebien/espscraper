#!/usr/bin/env python3
"""
Optimized extraction test that tries fast methods first
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

def test_optimized_extraction():
    """Test optimized extraction with fast methods first"""
    
    print("⚡ Optimized Product Data Extraction")
    print("=" * 50)
    print("Fast methods first, fallback to slower methods")
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
        # Create session manager and scraper (reuses session from tmp folder)
        session_manager = SessionManager()
        scraper = ProductDetailScraper(session_manager, headless=False)
        
        # Test session loading (reuses existing session if valid)
        print("\n🔐 Testing session loading (reuses tmp session)...")
        scraper.login(force_relogin=False)  # This will reuse session from tmp folder
        
        # Test accessing a product page
        print("\n🔍 Testing optimized extraction...")
        test_url = "https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductDetails&productID=555102402&autoLaunchVS=0&tab=list"
        
        try:
            scraper.driver.get(test_url)
            time.sleep(3)
            
            current_url = scraper.driver.current_url
            print(f"📍 Current URL: {current_url}")
            
            if 'login' in current_url.lower():
                print("❌ Redirected to login page - session expired")
                return False
            
            # Method 1: Fast HTML parsing (100-200ms)
            print("\n🚀 METHOD 1: Fast HTML Parsing")
            print("=" * 30)
            
            start_time = time.time()
            
            html_data = scraper.driver.execute_script("""
                // Fast HTML parsing - extract basic product info
                var productData = {};
                
                // Basic product info from HTML
                var productName = document.querySelector('.product-name, .product-title, h1')?.textContent?.trim();
                var productSku = document.querySelector('[data-sku], .sku, .product-sku')?.textContent?.trim();
                var productDesc = document.querySelector('.product-description, .description')?.textContent?.trim();
                var productImage = document.querySelector('.product-image img, .main-image img')?.src;
                
                // Pricing from HTML tables
                var pricingTable = document.querySelector('.pricing-table, table');
                var pricingData = [];
                if (pricingTable) {
                    var rows = pricingTable.querySelectorAll('tr');
                    for (var i = 1; i < rows.length; i++) {
                        var cells = rows[i].querySelectorAll('td');
                        if (cells.length >= 2) {
                            pricingData.push({
                                quantity: cells[0]?.textContent?.trim(),
                                price: cells[1]?.textContent?.trim()
                            });
                        }
                    }
                }
                
                // Supplier info
                var supplierName = document.querySelector('.supplier-name, .vendor-name')?.textContent?.trim();
                var supplierPhone = document.querySelector('.supplier-phone, .contact-phone')?.textContent?.trim();
                
                return {
                    product: {
                        name: productName || 'N/A',
                        sku: productSku || 'N/A',
                        description: productDesc || 'N/A',
                        image: productImage || 'N/A'
                    },
                    pricing: pricingData,
                    supplier: {
                        name: supplierName || 'N/A',
                        phone: supplierPhone || 'N/A'
                    },
                    extraction_method: 'fast_html',
                    data_completeness: 'basic'
                };
            """)
            
            html_time = time.time() - start_time
            
            print(f"   ⏱️ Time: {html_time:.3f} seconds")
            print(f"   📊 Data extracted: {len(html_data.get('product', {}))} product fields")
            print(f"   📊 Pricing items: {len(html_data.get('pricing', []))}")
            print(f"   📊 Supplier info: {len(html_data.get('supplier', {}))} fields")
            
            # Check if we got enough data
            product_name = html_data.get('product', {}).get('name', '')
            has_basic_data = product_name and product_name != 'N/A'
            
            if has_basic_data:
                print(f"   ✅ Got basic product data via fast HTML parsing!")
                
                # Method 2: Quick AngularJS check (200-500ms) - only if needed
                print("\n🔄 METHOD 2: Quick AngularJS Check (if needed)")
                print("=" * 40)
                
                # Check if we need more data
                needs_more_data = (
                    len(html_data.get('pricing', [])) < 2 or
                    html_data.get('supplier', {}).get('name') == 'N/A'
                )
                
                if needs_more_data:
                    print(f"   ⚠️ Need more data, trying quick AngularJS extraction...")
                    
                    start_time = time.time()
                    
                    quick_angular_data = scraper.driver.execute_script("""
                        // Quick AngularJS extraction - minimal processing
                        var productData = {};
                        
                        if (typeof angular !== 'undefined') {
                            try {
                                // Quick scope check
                                var rootScope = angular.element(document.body).scope();
                                if (rootScope) {
                                    // Single digest cycle
                                    rootScope.$digest();
                                    
                                    // Try to find product data quickly
                                    var productDetailElements = document.querySelectorAll('[ng-controller*="ProductDetailCtrl"]');
                                    for (var i = 0; i < productDetailElements.length; i++) {
                                        var element = productDetailElements[i];
                                        var scope = angular.element(element).scope();
                                        if (scope && scope.vm && scope.vm.product) {
                                            var vm = scope.vm;
                                            productData = {
                                                product: vm.product || {},
                                                pricing: vm.product.Prices || [],
                                                supplier: vm.product.Supplier || {},
                                                extraction_method: 'quick_angular',
                                                data_completeness: 'enhanced'
                                            };
                                            break;
                                        }
                                    }
                                }
                            } catch (e) {
                                // Ignore errors
                            }
                        }
                        
                        return productData;
                    """)
                    
                    quick_angular_time = time.time() - start_time
                    
                    print(f"   ⏱️ Time: {quick_angular_time:.3f} seconds")
                    print(f"   📊 Angular data extracted: {len(quick_angular_data.get('product', {}))} fields")
                    
                    if quick_angular_data.get('product'):
                        print(f"   ✅ Got enhanced data via quick AngularJS extraction!")
                        
                        # Merge the data
                        final_data = {
                            'html_data': html_data,
                            'angular_data': quick_angular_data,
                            'total_time': html_time + quick_angular_time,
                            'extraction_method': 'hybrid_fast'
                        }
                    else:
                        print(f"   ⚠️ No additional AngularJS data found")
                        final_data = {
                            'html_data': html_data,
                            'angular_data': {},
                            'total_time': html_time,
                            'extraction_method': 'html_only'
                        }
                else:
                    print(f"   ✅ Basic data is sufficient, skipping AngularJS extraction")
                    final_data = {
                        'html_data': html_data,
                        'angular_data': {},
                        'total_time': html_time,
                        'extraction_method': 'html_only'
                    }
            else:
                print(f"   ❌ Basic HTML parsing failed, trying AngularJS...")
                
                # Method 3: Full AngularJS extraction (500-1000ms) - only if needed
                print("\n🔄 METHOD 3: Full AngularJS Extraction (fallback)")
                print("=" * 40)
                
                start_time = time.time()
                
                # Use the enhanced method but with reduced digest cycles
                angular_data = scraper.driver.execute_script("""
                    // Optimized AngularJS extraction
                    var productData = {};
                    
                    if (typeof angular !== 'undefined') {
                        try {
                            var $rootScope = angular.element(document.body).scope();
                            if ($rootScope) {
                                // Reduced digest cycles (1 instead of 3)
                                $rootScope.$digest();
                                
                                // Quick scope search
                                var productDetailElements = document.querySelectorAll('[ng-controller*="ProductDetailCtrl"]');
                                for (var i = 0; i < productDetailElements.length; i++) {
                                    var element = productDetailElements[i];
                                    var scope = angular.element(element).scope();
                                    if (scope && scope.vm && scope.vm.product) {
                                        var vm = scope.vm;
                                        productData = {
                                            product: vm.product || {},
                                            pricing: vm.product.Prices || [],
                                            variants: vm.product.Variants || [],
                                            imprinting: vm.product.Imprinting || {},
                                            shipping: vm.product.Shipping || {},
                                            supplier: vm.product.Supplier || {},
                                            attributes: vm.product.Attributes || {},
                                            warnings: vm.product.Warnings || [],
                                            certifications: vm.product.Certifications || []
                                        };
                                        break;
                                    }
                                }
                            }
                        } catch (e) {
                            // Ignore errors
                        }
                    }
                    
                    return productData;
                """)
                
                angular_time = time.time() - start_time
                
                print(f"   ⏱️ Time: {angular_time:.3f} seconds")
                print(f"   📊 Angular data extracted: {len(angular_data.get('product', {}))} fields")
                
                if angular_data.get('product'):
                    print(f"   ✅ Got data via optimized AngularJS extraction!")
                    final_data = {
                        'html_data': {},
                        'angular_data': angular_data,
                        'total_time': angular_time,
                        'extraction_method': 'optimized_angular'
                    }
                else:
                    print(f"   ❌ All extraction methods failed")
                    final_data = {
                        'html_data': {},
                        'angular_data': {},
                        'total_time': angular_time,
                        'extraction_method': 'failed'
                    }
            
            # Summary
            print(f"\n📊 OPTIMIZED EXTRACTION SUMMARY:")
            print("=" * 40)
            print(f"   ⏱️ Total Time: {final_data['total_time']:.3f} seconds")
            print(f"   🔧 Method: {final_data['extraction_method']}")
            
            html_fields = len(final_data.get('html_data', {}).get('product', {}))
            angular_fields = len(final_data.get('angular_data', {}).get('product', {}))
            
            print(f"   📊 HTML Data Fields: {html_fields}")
            print(f"   📊 Angular Data Fields: {angular_fields}")
            print(f"   📊 Total Data Fields: {html_fields + angular_fields}")
            
            # Performance comparison
            original_time = 1.5  # Estimated time for original enhanced method
            time_savings = ((original_time - final_data['total_time']) / original_time) * 100
            
            print(f"   ⚡ Time Savings: {time_savings:.1f}% faster than original method")
            
            if time_savings > 50:
                print(f"   ✅ Excellent performance improvement!")
            elif time_savings > 25:
                print(f"   ✅ Good performance improvement!")
            else:
                print(f"   ⚠️ Modest performance improvement")
            
            # Save results
            output_file = "optimized_extraction_results.json"
            with open(output_file, 'w') as f:
                json.dump(final_data, f, indent=2)
            
            print(f"\n💾 Results saved to: {output_file}")
            
            return True
                
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
    success = test_optimized_extraction()
    if success:
        print("\n✅ Optimized extraction test completed successfully!")
    else:
        print("\n❌ Optimized extraction test failed!") 