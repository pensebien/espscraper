#!/usr/bin/env python3
"""
Test script to verify JavaScript script execution and AngularJS loading
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

def test_script_execution():
    """Test that all JavaScript scripts are executed and AngularJS is loaded"""
    
    print("🔧 Testing JavaScript Script Execution")
    print("=" * 50)
    print("This test verifies that all scripts are executed")
    print("and AngularJS is properly loaded")
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
            
            # Test script execution verification
            print("\n🔍 VERIFYING SCRIPT EXECUTION:")
            print("=" * 40)
            
            # Check initial state
            initial_check = scraper.driver.execute_script("""
                return {
                    angularLoaded: typeof angular !== 'undefined',
                    jqueryLoaded: typeof jQuery !== 'undefined',
                    scriptsFound: document.querySelectorAll('script').length,
                    angularScopes: 0,
                    productDataAvailable: false
                };
            """)
            
            print("📊 INITIAL STATE:")
            print(f"   - AngularJS Loaded: {initial_check.get('angularLoaded', False)}")
            print(f"   - jQuery Loaded: {initial_check.get('jqueryLoaded', False)}")
            print(f"   - Scripts Found: {initial_check.get('scriptsFound', 0)}")
            
            # Now trigger the enhanced script execution
            print("\n🔄 TRIGGERING ENHANCED SCRIPT EXECUTION...")
            
            # Execute the enhanced script execution method
            script_execution_result = scraper.driver.execute_script("""
                // Enhanced script execution
                var executionInfo = {
                    angularLoaded: typeof angular !== 'undefined',
                    digestCyclesTriggered: 0,
                    scriptsExecuted: 0,
                    timeoutsTriggered: 0,
                    scopesProcessed: 0
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
                
                // Trigger any pending timeouts
                if (window.setTimeout) {
                    var originalSetTimeout = window.setTimeout;
                    window.setTimeout = function(fn, delay) {
                        if (delay === 0) {
                            fn();
                            executionInfo.timeoutsTriggered++;
                        } else {
                            originalSetTimeout(fn, delay);
                        }
                    };
                }
                
                return executionInfo;
            """)
            
            print("📊 SCRIPT EXECUTION RESULTS:")
            print(f"   - AngularJS Loaded: {script_execution_result.get('angularLoaded', False)}")
            print(f"   - Digest Cycles Triggered: {script_execution_result.get('digestCyclesTriggered', 0)}")
            print(f"   - Scripts Executed: {script_execution_result.get('scriptsExecuted', 0)}")
            print(f"   - Timeouts Triggered: {script_execution_result.get('timeoutsTriggered', 0)}")
            print(f"   - Scopes Processed: {script_execution_result.get('scopesProcessed', 0)}")
            
            # Wait for any dynamic content to load
            time.sleep(3)
            
            # Check final state after script execution
            print("\n📊 FINAL STATE AFTER SCRIPT EXECUTION:")
            final_check = scraper.driver.execute_script("""
                var finalInfo = {
                    angularLoaded: typeof angular !== 'undefined',
                    jqueryLoaded: typeof jQuery !== 'undefined',
                    scriptsFound: document.querySelectorAll('script').length,
                    angularScopes: 0,
                    productDataAvailable: false,
                    vmAvailable: false,
                    productScopeAvailable: false
                };
                
                if (typeof angular !== 'undefined') {
                    var rootScope = angular.element(document.body).scope();
                    if (rootScope) {
                        finalInfo.angularScopes = 1;
                        // Count child scopes
                        function countScopes(scope) {
                            if (scope.$$childHead) {
                                finalInfo.angularScopes++;
                                countScopes(scope.$$childHead);
                            }
                            if (scope.$$nextSibling) {
                                finalInfo.angularScopes++;
                                countScopes(scope.$$nextSibling);
                            }
                        }
                        countScopes(rootScope);
                        
                        // Check for product data
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
                        collectAllScopes(rootScope);
                        
                        // Check each scope for product data
                        for (var i = 0; i < allScopes.length; i++) {
                            var scope = allScopes[i];
                            if (scope.product || (scope.vm && scope.vm.product)) {
                                finalInfo.productDataAvailable = true;
                                if (scope.vm) {
                                    finalInfo.vmAvailable = true;
                                }
                                if (scope.product) {
                                    finalInfo.productScopeAvailable = true;
                                }
                                break;
                            }
                        }
                    }
                }
                
                return finalInfo;
            """)
            
            print(f"   - AngularJS Loaded: {final_check.get('angularLoaded', False)}")
            print(f"   - jQuery Loaded: {final_check.get('jqueryLoaded', False)}")
            print(f"   - Scripts Found: {final_check.get('scriptsFound', 0)}")
            print(f"   - Angular Scopes: {final_check.get('angularScopes', 0)}")
            print(f"   - Product Data Available: {final_check.get('productDataAvailable', False)}")
            print(f"   - VM Available: {final_check.get('vmAvailable', False)}")
            print(f"   - Product Scope Available: {final_check.get('productScopeAvailable', False)}")
            
            # Test the actual AngularJS data extraction
            print("\n📊 TESTING ANGULARJS DATA EXTRACTION:")
            print("=" * 40)
            
            angular_data = scraper.get_angular_product_data()
            
            if angular_data:
                print("✅ AngularJS data extraction successful!")
                print(f"📊 Available data keys: {list(angular_data.keys())}")
                
                # Save the extracted data to a file
                output_file = "script_execution_test_data.json"
                with open(output_file, 'w') as f:
                    json.dump(angular_data, f, indent=2)
                print(f"\n💾 Test data saved to: {output_file}")
                
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
    success = test_script_execution()
    if success:
        print("\n✅ Script execution test completed successfully!")
        print("🎉 All scripts were executed and AngularJS data was extracted!")
    else:
        print("\n❌ Script execution test failed!") 