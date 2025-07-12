#!/usr/bin/env python3
"""
Comprehensive debug script to understand AngularJS structure on ESP website
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

def debug_angular_structure():
    """Debug the actual AngularJS structure on ESP website"""
    
    print("🔧 Comprehensive AngularJS Structure Debug")
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
        # Create session manager and scraper
        session_manager = SessionManager()
        scraper = ProductDetailScraper(session_manager, headless=True)
        
        # Test session loading
        print("\n🔐 Testing session loading...")
        scraper.login(force_relogin=False)
        
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
            
            # Comprehensive AngularJS structure analysis
            print("\n🔍 Analyzing AngularJS structure...")
            
            # Test 1: Check all global variables
            global_vars = scraper.driver.execute_script("""
                var globals = {};
                var commonVars = ['vm', '$scope', 'angular', 'jQuery', '$', 'Product', 'product', 'productData'];
                
                for (var i = 0; i < commonVars.length; i++) {
                    var varName = commonVars[i];
                    globals[varName] = typeof window[varName] !== 'undefined';
                }
                
                return globals;
            """)
            print(f"✅ Global variables: {global_vars}")
            
            # Test 2: Check all ng-* attributes in the page
            ng_attributes = scraper.driver.execute_script("""
                var ngAttrs = {};
                var elements = document.querySelectorAll('*');
                
                for (var i = 0; i < elements.length; i++) {
                    var element = elements[i];
                    var attrs = element.attributes;
                    
                    for (var j = 0; j < attrs.length; j++) {
                        var attr = attrs[j];
                        if (attr.name.startsWith('ng-')) {
                            if (!ngAttrs[attr.name]) {
                                ngAttrs[attr.name] = [];
                            }
                            ngAttrs[attr.name].push(attr.value);
                        }
                    }
                }
                
                return ngAttrs;
            """)
            print(f"✅ ng-* attributes found: {json.dumps(ng_attributes, indent=2)}")
            
            # Test 3: Check all data-* attributes
            data_attributes = scraper.driver.execute_script("""
                var dataAttrs = {};
                var elements = document.querySelectorAll('*');
                
                for (var i = 0; i < elements.length; i++) {
                    var element = elements[i];
                    var attrs = element.attributes;
                    
                    for (var j = 0; j < attrs.length; j++) {
                        var attr = attrs[j];
                        if (attr.name.startsWith('data-')) {
                            if (!dataAttrs[attr.name]) {
                                dataAttrs[attr.name] = [];
                            }
                            dataAttrs[attr.name].push(attr.value);
                        }
                    }
                }
                
                return dataAttrs;
            """)
            print(f"✅ data-* attributes found: {json.dumps(data_attributes, indent=2)}")
            
            # Test 4: Check all script tags for data
            script_data = scraper.driver.execute_script("""
                var scriptData = [];
                var scripts = document.querySelectorAll('script');
                
                for (var i = 0; i < scripts.length; i++) {
                    var script = scripts[i];
                    var content = script.textContent || script.innerHTML;
                    
                    // Look for common data patterns
                    var patterns = [
                        /var\s+(\w+)\s*=\s*\{/g,
                        /window\.(\w+)\s*=\s*\{/g,
                        /angular\.module\(/g,
                        /\.controller\(/g,
                        /\.service\(/g
                    ];
                    
                    for (var j = 0; j < patterns.length; j++) {
                        var matches = content.match(patterns[j]);
                        if (matches) {
                            scriptData.push({
                                scriptIndex: i,
                                pattern: patterns[j].toString(),
                                matches: matches
                            });
                        }
                    }
                }
                
                return scriptData;
            """)
            print(f"✅ Script data patterns: {json.dumps(script_data, indent=2)}")
            
            # Test 5: Try to find any AngularJS controllers
            controllers = scraper.driver.execute_script("""
                var controllers = [];
                var elements = document.querySelectorAll('[ng-controller]');
                
                for (var i = 0; i < elements.length; i++) {
                    var element = elements[i];
                    var controllerName = element.getAttribute('ng-controller');
                    
                    try {
                        var scope = angular.element(element).scope();
                        controllers.push({
                            controller: controllerName,
                            hasScope: !!scope,
                            scopeKeys: scope ? Object.keys(scope) : []
                        });
                    } catch (e) {
                        controllers.push({
                            controller: controllerName,
                            hasScope: false,
                            error: e.toString()
                        });
                    }
                }
                
                return controllers;
            """)
            print(f"✅ Controllers found: {json.dumps(controllers, indent=2)}")
            
            # Test 6: Check for any JSON data in the page
            json_data = scraper.driver.execute_script("""
                var jsonData = [];
                var elements = document.querySelectorAll('script[type="application/json"], script[type="application/ld+json"]');
                
                for (var i = 0; i < elements.length; i++) {
                    try {
                        var data = JSON.parse(elements[i].textContent);
                        jsonData.push({
                            scriptIndex: i,
                            data: data
                        });
                    } catch (e) {
                        // Not valid JSON
                    }
                }
                
                return jsonData;
            """)
            print(f"✅ JSON data found: {json.dumps(json_data, indent=2)}")
            
            # Test 7: Check for any hidden input fields with data
            hidden_inputs = scraper.driver.execute_script("""
                var hiddenData = [];
                var inputs = document.querySelectorAll('input[type="hidden"]');
                
                for (var i = 0; i < inputs.length; i++) {
                    var input = inputs[i];
                    var name = input.getAttribute('name');
                    var value = input.getAttribute('value');
                    
                    if (name && value && (name.includes('product') || name.includes('data') || value.includes('{'))) {
                        hiddenData.push({
                            name: name,
                            value: value
                        });
                    }
                }
                
                return hiddenData;
            """)
            print(f"✅ Hidden inputs with data: {json.dumps(hidden_inputs, indent=2)}")
            
            # Test 8: Try to extract any data from the page source
            page_data = scraper.driver.execute_script("""
                var pageData = {};
                
                // Try to find any data in the page
                var bodyText = document.body.textContent;
                
                // Look for common data patterns
                var patterns = [
                    /product.*\{[^}]*\}/g,
                    /vm\s*=\s*\{[^}]*\}/g,
                    /scope\s*=\s*\{[^}]*\}/g
                ];
                
                for (var i = 0; i < patterns.length; i++) {
                    var matches = bodyText.match(patterns[i]);
                    if (matches) {
                        pageData['pattern_' + i] = matches;
                    }
                }
                
                return pageData;
            """)
            print(f"✅ Page data patterns: {json.dumps(page_data, indent=2)}")
            
            print("\n✅ Comprehensive AngularJS structure analysis completed!")
            return True
            
        except Exception as e:
            print(f"❌ Error during debugging: {e}")
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
    success = debug_angular_structure()
    if success:
        print("\n✅ AngularJS structure analysis completed successfully!")
    else:
        print("\n❌ AngularJS structure analysis failed!") 