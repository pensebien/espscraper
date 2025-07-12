#!/usr/bin/env python3
"""
Performance analysis script to measure the timing impact of enhanced script execution
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

def test_performance_analysis():
    """Test performance impact of enhanced script execution"""
    
    print("⏱️ Performance Analysis of Enhanced Script Execution")
    print("=" * 60)
    print("This test measures the timing impact of the enhanced")
    print("AngularJS extraction method vs basic extraction")
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
            
            # Test 1: Basic AngularJS extraction (original method)
            print("\n📊 TEST 1: Basic AngularJS Extraction (Original Method)")
            print("=" * 50)
            
            start_time = time.time()
            
            # Simulate basic extraction (without enhanced script execution)
            basic_result = scraper.driver.execute_script("""
                var startTime = performance.now();
                
                // Basic AngularJS extraction (simplified version)
                var productData = {};
                var scopeFound = false;
                
                if (typeof angular !== 'undefined') {
                    try {
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
                                scopeFound = true;
                                break;
                            }
                        }
                    } catch (e) {
                        // Continue to next method
                    }
                }
                
                var endTime = performance.now();
                return {
                    data: productData,
                    scopeFound: scopeFound,
                    executionTime: endTime - startTime
                };
            """)
            
            basic_time = time.time() - start_time
            basic_execution_time = basic_result.get('executionTime', 0)
            
            print(f"   ⏱️ Total Time: {basic_time:.3f} seconds")
            print(f"   ⏱️ JavaScript Execution Time: {basic_execution_time:.3f} ms")
            print(f"   ✅ Scope Found: {basic_result.get('scopeFound', False)}")
            print(f"   📊 Data Extracted: {len(basic_result.get('data', {}))} keys")
            
            # Test 2: Enhanced AngularJS extraction (new method)
            print("\n📊 TEST 2: Enhanced AngularJS Extraction (New Method)")
            print("=" * 50)
            
            start_time = time.time()
            
            # Use the enhanced method
            enhanced_result = scraper.driver.execute_script("""
                var startTime = performance.now();
                
                // Enhanced script execution
                var executionInfo = {
                    angularLoaded: typeof angular !== 'undefined',
                    digestCyclesTriggered: 0,
                    scriptsExecuted: 0,
                    timeoutsTriggered: 0,
                    scopesProcessed: 0,
                    executionTime: 0
                };
                
                if (typeof angular !== 'undefined') {
                    // Trigger multiple digest cycles
                    var $rootScope = angular.element(document.body).scope();
                    if ($rootScope) {
                        for (var i = 0; i < 3; i++) {
                            $rootScope.$apply();
                            $rootScope.$digest();
                            executionInfo.digestCyclesTriggered++;
                        }
                        
                        // Wait for any pending async operations
                        if ($rootScope.$$phase) {
                            $rootScope.$evalAsync(function() {});
                        }
                    }
                    
                    // Execute any pending scripts
                    var scripts = document.querySelectorAll('script');
                    for (var i = 0; i < scripts.length; i++) {
                        var script = scripts[i];
                        if (script.type === 'text/javascript' || !script.type) {
                            try {
                                if (script.innerHTML) {
                                    eval(script.innerHTML);
                                    executionInfo.scriptsExecuted++;
                                }
                            } catch (e) {
                                // Ignore script execution errors
                            }
                        }
                    }
                    
                    // Force execution of any AngularJS watchers
                    var allScopes = [];
                    function collectScopes(scope) {
                        allScopes.push(scope);
                        executionInfo.scopesProcessed++;
                        if (scope.$$childHead) {
                            collectScopes(scope.$$childHead);
                        }
                        if (scope.$$nextSibling) {
                            collectScopes(scope.$$nextSibling);
                        }
                    }
                    
                    if ($rootScope) {
                        collectScopes($rootScope);
                        allScopes.forEach(function(scope) {
                            if (scope.$digest) {
                                scope.$digest();
                            }
                        });
                    }
                }
                
                // Now extract data with enhanced methods
                var productData = {};
                var scopeFound = false;
                
                // Method 1: Try to find the ProductDetailCtrl controller scope
                if (typeof angular !== 'undefined') {
                    try {
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
                                scopeFound = true;
                                break;
                            }
                        }
                    } catch (e) {
                        // Continue to next method
                    }
                }
                
                // Method 7: Enhanced - Try to extract from any AngularJS scope with product data
                if (!scopeFound && typeof angular !== 'undefined') {
                    try {
                        var allScopes = [];
                        function collectAllScopes(scope) {
                            allScopes.push(scope);
                            if (scope.$$childHead) {
                                collectAllScopes(scope.$$childHead);
                            }
                            if (scope.$$nextSibling) {
                                collectAllScopes(scope.$$nextSibling);
                            }
                        }
                        
                        var rootScope = angular.element(document.body).scope();
                        if (rootScope) {
                            collectAllScopes(rootScope);
                            
                            // Check each scope for product data
                            for (var i = 0; i < allScopes.length; i++) {
                                var scope = allScopes[i];
                                if (scope.product || (scope.vm && scope.vm.product)) {
                                    var product = scope.product || (scope.vm ? scope.vm.product : null);
                                    if (product) {
                                        productData = {
                                            product: product || {},
                                            pricing: product.Prices || [],
                                            variants: product.Variants || [],
                                            imprinting: product.Imprinting || {},
                                            shipping: product.Shipping || {},
                                            supplier: product.Supplier || {},
                                            attributes: product.Attributes || {},
                                            warnings: product.Warnings || [],
                                            certifications: product.Certifications || []
                                        };
                                        scopeFound = true;
                                        break;
                                    }
                                }
                            }
                        }
                    } catch (e) {
                        // Continue to next method
                    }
                }
                
                var endTime = performance.now();
                executionInfo.executionTime = endTime - startTime;
                
                return {
                    data: productData,
                    scopeFound: scopeFound,
                    executionInfo: executionInfo
                };
            """)
            
            enhanced_time = time.time() - start_time
            enhanced_execution_time = enhanced_result.get('executionInfo', {}).get('executionTime', 0)
            
            print(f"   ⏱️ Total Time: {enhanced_time:.3f} seconds")
            print(f"   ⏱️ JavaScript Execution Time: {enhanced_execution_time:.3f} ms")
            print(f"   ✅ Scope Found: {enhanced_result.get('scopeFound', False)}")
            print(f"   📊 Data Extracted: {len(enhanced_result.get('data', {}))} keys")
            
            # Performance metrics
            execution_info = enhanced_result.get('executionInfo', {})
            print(f"   🔄 Digest Cycles Triggered: {execution_info.get('digestCyclesTriggered', 0)}")
            print(f"   📜 Scripts Executed: {execution_info.get('scriptsExecuted', 0)}")
            print(f"   ⏰ Timeouts Triggered: {execution_info.get('timeoutsTriggered', 0)}")
            print(f"   🔍 Scopes Processed: {execution_info.get('scopesProcessed', 0)}")
            
            # Performance comparison
            print("\n📊 PERFORMANCE COMPARISON:")
            print("=" * 40)
            
            time_difference = enhanced_time - basic_time
            time_increase_percentage = (time_difference / basic_time * 100) if basic_time > 0 else 0
            
            print(f"   ⏱️ Basic Method Time: {basic_time:.3f} seconds")
            print(f"   ⏱️ Enhanced Method Time: {enhanced_time:.3f} seconds")
            print(f"   ⏱️ Time Difference: {time_difference:.3f} seconds")
            print(f"   📈 Time Increase: {time_increase_percentage:.1f}%")
            
            # Data extraction comparison
            basic_data_keys = len(basic_result.get('data', {}))
            enhanced_data_keys = len(enhanced_result.get('data', {}))
            
            print(f"\n📊 DATA EXTRACTION COMPARISON:")
            print(f"   📋 Basic Method Data Keys: {basic_data_keys}")
            print(f"   📋 Enhanced Method Data Keys: {enhanced_data_keys}")
            print(f"   📈 Data Improvement: {enhanced_data_keys - basic_data_keys} additional keys")
            
            # Success rate comparison
            basic_success = basic_result.get('scopeFound', False)
            enhanced_success = enhanced_result.get('scopeFound', False)
            
            print(f"\n📊 SUCCESS RATE COMPARISON:")
            print(f"   ✅ Basic Method Success: {basic_success}")
            print(f"   ✅ Enhanced Method Success: {enhanced_success}")
            
            # Performance recommendations
            print("\n💡 PERFORMANCE RECOMMENDATIONS:")
            print("=" * 40)
            
            if time_increase_percentage < 50:
                print("   ✅ Performance impact is acceptable (< 50% increase)")
                print("   ✅ Enhanced method provides better data extraction")
                print("   ✅ Recommended for production use")
            elif time_increase_percentage < 100:
                print("   ⚠️ Moderate performance impact (50-100% increase)")
                print("   ⚠️ Consider using enhanced method only when needed")
                print("   ⚠️ Could implement fallback to basic method")
            else:
                print("   ❌ High performance impact (> 100% increase)")
                print("   ❌ Consider optimizing the enhanced method")
                print("   ❌ May need to use basic method for bulk scraping")
            
            # Save performance data
            performance_data = {
                "basic_method": {
                    "total_time": basic_time,
                    "js_execution_time": basic_execution_time,
                    "success": basic_success,
                    "data_keys": basic_data_keys
                },
                "enhanced_method": {
                    "total_time": enhanced_time,
                    "js_execution_time": enhanced_execution_time,
                    "success": enhanced_success,
                    "data_keys": enhanced_data_keys,
                    "digest_cycles": execution_info.get('digestCyclesTriggered', 0),
                    "scripts_executed": execution_info.get('scriptsExecuted', 0),
                    "scopes_processed": execution_info.get('scopesProcessed', 0)
                },
                "comparison": {
                    "time_difference": time_difference,
                    "time_increase_percentage": time_increase_percentage,
                    "data_improvement": enhanced_data_keys - basic_data_keys
                }
            }
            
            output_file = "performance_analysis_results.json"
            with open(output_file, 'w') as f:
                json.dump(performance_data, f, indent=2)
            print(f"\n💾 Performance analysis saved to: {output_file}")
            
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
    success = test_performance_analysis()
    if success:
        print("\n✅ Performance analysis completed successfully!")
    else:
        print("\n❌ Performance analysis failed!") 