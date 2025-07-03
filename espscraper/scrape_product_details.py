from espscraper.base_scraper import BaseScraper
from espscraper.session_manager import SessionManager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import json
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import re
from selenium.webdriver.common.keys import Keys
import argparse
import urllib.parse
import random
from dotenv import load_dotenv
from espscraper.selenium_resilient_manager import SeleniumResilientManager
import requests

class ProductDetailScraper(BaseScraper):
    def __init__(self, session_manager, headless=False, limit=None, output_file=None, links_file=None):
        super().__init__(session_manager)
        self.load_env()
        self.USERNAME = os.getenv("ESP_USERNAME")
        self.PASSWORD = os.getenv("ESP_PASSWORD")
        self.PRODUCTS_URL = os.getenv("PRODUCTS_URL")
        # Ensure data directory exists
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(data_dir, exist_ok=True)
        self.OUTPUT_FILE = output_file or os.getenv("DETAILS_OUTPUT_FILE", os.path.join(data_dir, "final_product_details.jsonl"))
        self.LINKS_FILE = links_file or os.getenv("DETAILS_LINKS_FILE", os.path.join(data_dir, "api_scraped_links.jsonl"))
        self.limit = limit
        self.headless = headless
        self.driver_manager = SeleniumResilientManager(headless=self.headless, setup_callback=None)
        self.driver = self.driver_manager.get_driver()

    def setup_selenium(self, driver=None):
        # This method is now only used as a callback if needed for custom setup after driver creation
        pass

    def login(self, force_relogin=False):
        # Use SessionManager to handle login and cookies
        self.session_manager.selenium_login_and_get_session_data(
            self.USERNAME, self.PASSWORD, self.PRODUCTS_URL, force_relogin=force_relogin
        )
        # Load cookies into Selenium driver
        cookies, _, _ = self.session_manager.load_state()
        if cookies:
            self.driver.get(self.PRODUCTS_URL)
            for cookie in cookies:
                cookie_dict = {k: v for k, v in cookie.items() if k in ['name', 'value', 'domain', 'path', 'expiry', 'secure', 'httpOnly']}
                try:
                    self.driver.add_cookie(cookie_dict)
                except Exception:
                    pass
            self.driver.refresh()

    def read_product_links(self):
        links = []
        if os.path.exists(self.LINKS_FILE):
            with open(self.LINKS_FILE, 'r') as f:
                for line in f:
                    links.append(json.loads(line))
            print(f"📄 Read {len(links)} product links from {self.LINKS_FILE}.")
        else:
            print(f"❌ ERROR: Links file not found at {self.LINKS_FILE}")
        return links

    def get_related_products(self, product_id, soup=None):
        """Try API first, fallback to HTML only if API fails or is empty. Never print errors, always return a list."""
        api_url = f"https://api.asicentral.com/v1/products/{product_id}/suggestions.json?page=1&rpp=5"
        try:
            resp = requests.get(api_url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                related = []
                for item in data.get('Results', []):
                    pid = item.get('Id')
                    name = item.get('Name')
                    image = item.get('ImageUrl')
                    if image and not image.startswith('http'):
                        image = f"https://api.asicentral.com/v1/{image.lstrip('/')}"
                    url = self.build_product_url(pid) if pid else ''
                    related.append({'Name': name, 'URL': url, 'Image': image})
                if related:
                    return related
        except Exception:
            pass
        # Only try HTML if API failed or returned no results
        related = []
        if soup:
            for item in soup.find_all('div', class_=re.compile(r'product-list-item')):
                name_tag = item.select_one('.prod-name a')
                name = name_tag.text.strip() if name_tag else 'N/A'
                img_tag = item.select_one('.prod-img-inner img')
                image = img_tag['src'] if img_tag and img_tag.has_attr('src') else ''
                pid_match = re.search(r'/([0-9]+)(?:\?|$)', image)
                pid = pid_match.group(1) if pid_match else None
                url = self.build_product_url(pid) if pid else ''
                related.append({'Name': name, 'URL': url, 'Image': image})
        return related

    def build_product_url(self, product_id):
        return f"https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductDetails&productID={product_id}&autoLaunchVS=0&tab=list"

    def scrape_product_detail_page(self):
        """
        Scrapes product details from the currently opened product detail page.
        """
        try:
            detail_soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            # Initialize all data points to avoid NameError if a section is missing
            imprint_info = {}
            production_time = "N/A"
            supplier = "N/A"
            related_products = []

            # --- Product Name (from main section, not summary) ---
            name = "N/A"
            try:
                name_elem = detail_soup.select_one('#productDetailsMain h3.text-primary')
                if name_elem:
                    name = name_elem.text.strip()
            except:
                pass

            # Product Number (SKU)
            sku = "N/A"
            try:
                sku_elem = detail_soup.select_one('span.product-number')
                if sku_elem:
                    sku = sku_elem.text.strip().replace('Product #:', '').strip()
            except:
                pass

            # Short Description (from main section)
            short_description = "N/A"
            try:
                desc_elem = detail_soup.select_one('#productDetailsMain div.product-info p.ng-binding')
                if desc_elem:
                    short_description = desc_elem.text.strip()
            except:
                pass

            # --- Variant Images ---
            variant_images = []
            try:
                product_images_div = detail_soup.select_one('#productImages')
                if product_images_div:
                    # Only use <input type="image"> tags for variant images
                    for img_input in product_images_div.find_all('input', {'type': 'image'}):
                        if img_input.has_attr('src'):
                            variant_images.append(img_input['src'])
            except:
                pass

            # Main Image URL (first variant or fallback)
            image_url = variant_images[0] if variant_images else "N/A"

            # Price Range (from main section)
            price = "N/A"
            try:
                price_elem = detail_soup.select_one('#productDetailsMain div.product-price a.ng-binding')
                if price_elem:
                    price = price_elem.text.strip()
            except:
                pass

            # Colors
            colors = []
            try:
                color_header = detail_soup.find('span', string=lambda s: s and 'Colors' in s)
                if color_header:
                    color_list = color_header.find_next('span', class_='attribute-list-items')
                    if color_list:
                        for elem in color_list.find_all(['a', 'span'], recursive=False):
                            color_text = elem.get_text(strip=True).rstrip(',')
                            if color_text:
                                colors.append(color_text)
            except:
                pass

            # --- Imprint Section (Definitive Robust Extraction) ---
            imprint_info = {
                'General': {},
                'Methods': {},
                'Services': {},
                'Other': {},
                'Charges': []
            }
            try:
                imprint_section = detail_soup.select_one('#pnlImprint')

                if imprint_section:
                    # 1. General Attribute Lists (e.g., Methods, Sizes, Locations, Colors)
                    for attr_div in imprint_section.select('div.product-attribute'):
                        header_elem = attr_div.select_one('span.attribute-header, span.property-label, div.strong')
                        if not header_elem:
                            continue
                        key = header_elem.get_text(strip=True).replace(':', '')
                        values = [span.get_text(strip=True).replace(',', '') for span in attr_div.select('div.attribute-list-items span.ng-binding, .attribute-list-items span[ng-if]') if span.get_text(strip=True)]
                        if key and values:
                            imprint_info['General'][key] = values if len(values) > 1 else values[0]

                    # 2. Per-Method Nested Details (e.g., "Imprint Methods: Digibrite")
                    for method_block in imprint_section.select('div[ng-if*="value.Options"]'):
                        method_name_elem = method_block.select_one('div.property-label')
                        if not method_name_elem:
                            continue

                        method_name = method_name_elem.get_text(strip=True).replace('Imprint Methods:', '').strip()
                        if method_name not in imprint_info['Methods']:
                             imprint_info['Methods'][method_name] = {}

                        for option in method_block.select('div[ng-repeat="option in vm.options"]'):
                            option_name_elem = option.select_one('div.strong')
                            if not option_name_elem:
                                continue

                            option_name = option_name_elem.get_text(strip=True)
                            
                            # Corrected selector to find the nested value
                            option_values = [val.get_text(strip=True) for val in option.select('product-option-values div.ng-binding')]
                            
                            # Clean up the key name for consistency
                            if 'Imprint Size' in option_name:
                                option_name = 'Size'
                            elif 'Imprint Location' in option_name:
                                option_name = 'Location'

                            imprint_info['Methods'][method_name][option_name] = option_values if len(option_values) > 1 else (option_values[0] if option_values else '')

                    # 3. Standalone Key-Value Pairs (e.g., "Personalization: No")
                    for div in imprint_section.find_all('div', recursive=False):
                        strong_tag = div.select_one('strong')
                        p_tag = div.select_one('p')
                        if strong_tag and p_tag:
                            key = strong_tag.get_text(strip=True)
                            value = p_tag.get_text(strip=True)
                            imprint_info['Other'][key] = value

                    # 4. Charges Extractor (Rewritten for multiple methods)
                    for charges_block in imprint_section.select('div.attribute-charges > div[ng-if*="value.Charges"]'):
                        # Get the method name for this block of charges
                        method_name_text = charges_block.find(string=True, recursive=False)
                        if not method_name_text:
                            continue
                        method_name = method_name_text.strip()

                        if method_name not in imprint_info['Methods']:
                            imprint_info['Methods'][method_name] = {}
                        
                        # Ensure 'Charges' list exists for this method
                        if 'Charges' not in imprint_info['Methods'][method_name]:
                            imprint_info['Methods'][method_name]['Charges'] = []

                        # Find the list of charges within this block
                        charges_ul = charges_block.find('ul')
                        if not charges_ul:
                            continue

                        for charge_li in charges_ul.select('li[product-property-charges]'):
                            charge_data = {}
                            label_elem = charge_li.select_one('.property-label')
                            if not label_elem: continue
                            
                            charge_data['name'] = ' '.join(label_elem.get_text(strip=True).replace('\u2013', '').split())
                            
                            all_prices = charge_li.select('span[asi-price]')
                            charge_data['price'] = all_prices[0].get_text(strip=True) if len(all_prices) > 0 else "N/A"
                            charge_data['cost'] = all_prices[1].get_text(strip=True) if len(all_prices) > 1 else "N/A"
                            
                            imprint_info['Methods'][method_name]['Charges'].append(charge_data)

                # --- Final cleanup to remove the now-redundant top-level 'Charges' list ---
                imprint_info.pop('Charges', None)
            except Exception as e:
                print(f"⚠️ Error extracting imprint info: {e}")

            def extract_section(section):
                info = {}
                try:
                    # Extract div.product-attribute as before
                    for attr in section.find_all('div', class_='product-attribute'):
                        header = attr.select_one('.attribute-header')
                        values = attr.select_one('.attribute-list-items')
                        if header and values:
                            info[header.text.strip()] = [v.text.strip() for v in values.find_all('span', class_='ng-binding') if v.text.strip()]
                    # Extract <p> with <strong> label
                    for p in section.find_all('p'):
                        strong = p.find('strong')
                        if strong:
                            label = strong.text.strip(':').strip()
                            # Get the value: text after <br> or in <span>
                            value = p.get_text(separator=' ', strip=True).replace(strong.text, '').strip(' :\n')
                            if not value:
                                span = p.find('span', class_='ng-binding')
                                value = span.text.strip() if span else ''
                            info[label] = value
                except Exception as e:
                    print(f"⚠️ Error extracting section: {e}")
                return info

            # --- Production Info Section (from Options Section) ---
            production_info = {}
            try:
                options_section = detail_soup.select_one('#pnlOptions')
                if options_section:
                    production_info = extract_section(options_section)
            except:
                pass

            # --- Shipping Section ---
            shipping_info = {}
            try:
                shipping_section = detail_soup.select_one('#pnlShipping')
                if shipping_section:
                    shipping_info = extract_section(shipping_section)
            except:
                pass

            # --- Safety and Compliance Section ---
            safety_info = {}
            try:
                safety_section = detail_soup.select_one('#pnlSafety')
                if safety_section:
                    safety_info = extract_section(safety_section)
            except:
                pass

            # --- Supplier Info Section ---
            supplier_info = {}
            try:
                supplier_section = detail_soup.select_one('#pnlSupplierInfo')
                if supplier_section:
                    # Extract supplier name
                    name_elem = supplier_section.select_one('.supplier-name')
                    if name_elem:
                        supplier_info['Name'] = name_elem.get_text(strip=True)
                    # Extract ASI number
                    asi_elem = supplier_section.select_one('.supplier-asi')
                    if asi_elem:
                        supplier_info['ASI'] = asi_elem.get_text(strip=True)
            except:
                pass

            # --- Production Time and Supplier (from main section) ---
            try:
                production_elem = detail_soup.find('span', string=lambda s: s and 'Production Time' in s)
                if production_elem:
                    production_time_elem = production_elem.find_next('span', class_='ng-binding')
                    if production_time_elem:
                        production_time = production_time_elem.text.strip()
            except:
                pass

            try:
                supplier_elem = detail_soup.find('span', string=lambda s: s and 'Supplier' in s)
                if supplier_elem:
                    supplier_elem = supplier_elem.find_next('span', class_='ng-binding')
                    if supplier_elem:
                        supplier = supplier_elem.text.strip()
            except:
                pass

            # --- ProductCPN ---
            product_cpn = None
            try:
                cpn_elem = detail_soup.select_one('div.product-cpn.ng-binding')
                if cpn_elem:
                    product_cpn = cpn_elem.text.strip()
            except:
                pass

            # --- ProductID from URL ---
            product_id = None
            try:
                parsed_url = urllib.parse.urlparse(self.driver.current_url)
                for part in urllib.parse.parse_qsl(parsed_url.query):
                    if part[0].lower() == 'productid':
                        product_id = part[1]
                        break
            except:
                pass

            # --- UpdateDate and ProductURL (prefer JS variable) ---
            update_date = None
            product_url = None
            try:
                # Try to extract from JS context
                product_json = self.driver.execute_script("return (typeof Product !== 'undefined') ? JSON.stringify(Product) : null;")
                if product_json:
                    import json as _json
                    product_js = _json.loads(product_json)
                    update_date = product_js.get('UpdateDate')
                    product_url = product_js.get('ProductURL')
            except:
                pass
            # Fallback to HTML if not found
            if not update_date:
                try:
                    update_elem = detail_soup.select_one('span.text-light-2.text-medium.ng-binding')
                    if update_elem and 'Last updated' in update_elem.text:
                        update_date = update_elem.text.replace('Last updated:', '').strip()
                except:
                    pass

            # --- Pricing Table (now with better error handling) ---
            pricing_table = self.extract_pricing_table()

            # --- Related Products (API first, fallback to HTML) ---
            if product_id:
                try:
                    related_products = self.get_related_products(product_id, soup=detail_soup)
                except Exception as e:
                    print(f"[RelatedProduct] Error: {e}")

            # Get current URL
            current_url = self.driver.current_url

            return {
                "ProductID": product_id,
                "UpdateDate": update_date,
                "ProductURL": product_url,
                "ProductCPN": product_cpn,
                "URL": current_url,
                "Name": name,
                "SKU": sku,
                "ShortDescription": short_description,
                "ImageURL": image_url,
                "VariantImages": variant_images,
                "PricingTable": pricing_table,
                "Colors": colors,
                "ProductionTime": production_time,
                "Supplier": supplier,
                "RelatedProduct": related_products,
                "Imprint": imprint_info,
                "ProductionInfo": production_info,
                "Shipping": shipping_info,
                "SafetyAndCompliance": safety_info,
                "SupplierInfo": supplier_info
            }

        except Exception as e:
            print(f"❌ Error scraping product detail page: {e}")
            return None

    def extract_pricing_table(self):
        """
        Extracts the pricing table from the product detail page with robust parsing.
        """
        pricing_table = []
        try:
            # Try to find pricing section with multiple selectors
            pricing_section = None
            pricing_selectors = [
                '#pnlPricing',
                '.pricing-section',
                '[id*="pricing"]',
                '[class*="pricing"]'
            ]
            
            for selector in pricing_selectors:
                try:
                    pricing_section = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if pricing_section:
                        break
                except:
                    continue
            
            if not pricing_section:
                print('⚠️ No pricing section found, skipping pricing table')
                return []

            pricing_soup = BeautifulSoup(pricing_section.get_attribute('innerHTML'), 'html.parser')
            table = pricing_soup.find('table')

            if not table:
                print('⚠️ Pricing table element not found within pricing section.')
                return []

            rows = table.find_all('tr')
            if not rows or len(rows) < 2:
                print('⚠️ Pricing table has no header or data rows.')
                return []

            # Find the header row with quantities and create a column map {index: quantity}
            header_row = rows[0]
            quantity_map = {}
            for i, th in enumerate(header_row.find_all(['th', 'td'])):
                if i == 0: continue  # Skip the first column
                try:
                    quantity = int(re.sub(r'[^0-9]', '', th.text))
                    if quantity > 0:
                        quantity_map[i] = quantity
                except (ValueError, TypeError):
                    continue

            if not quantity_map:
                print('⚠️ Could not parse quantities from the pricing table header.')
                return []

            # Process data rows
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                if not cells or len(cells) <= 1:
                    continue

                row_label = cells[0].get_text(strip=True)
                if not row_label or self.is_price(row_label):
                    continue

                breaks = []
                for i, cell in enumerate(cells):
                    if i in quantity_map:
                        quantity = quantity_map[i]
                        price_str = cell.get_text(strip=True)
                        discount_code = None
                        
                        dc_elem = cell.find('small', class_='price-code') or cell.find('span', class_='price-code')
                        if dc_elem:
                            discount_code = dc_elem.get_text(strip=True).strip('()')

                        price_match = re.search(r"[\d.,]+\d", price_str)
                        if price_match:
                            try:
                                price = float(price_match.group().replace(',', ''))
                                breaks.append({"quantity": quantity, "price": price, "discount_code": discount_code})
                            except (ValueError, TypeError):
                                continue
                
                if breaks:
                    pricing_table.append({"type": row_label, "breaks": breaks})
            
            if not pricing_table:
                print('⚠️ Pricing table was parsed, but no valid data was extracted.')
            
            return pricing_table

        except Exception as e:
            print(f'⚠️ Error in extract_pricing_table: {e}')
            return []

    def is_price(self, text):
        # Matches $7.88, 7.88, 2.70, etc.
        return bool(re.match(r'^\$?\d+(\.\d+)?$', text.strip()))

    def get_scraped_ids(self):
        scraped_ids = set()
        if os.path.exists(self.OUTPUT_FILE):
            with open(self.OUTPUT_FILE, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        if 'id' in data:
                            scraped_ids.add(data['id'])
                        elif 'ProductID' in data:
                            scraped_ids.add(data['ProductID'])
                        elif 'url' in data:
                            scraped_ids.add(data['url'])
                    except Exception:
                        continue
        return scraped_ids

    def scrape_all_details(self, force_relogin=False):
        self.login(force_relogin=force_relogin)
        product_links = self.read_product_links()
        scraped_ids = self.get_scraped_ids()
        links_to_process = [link for link in product_links if link.get('id') not in scraped_ids]
        if self.limit:
            links_to_process = links_to_process[:self.limit]
        print(f"🚀 Starting to scrape {len(links_to_process)} product pages (skipping {len(scraped_ids)} already scraped)...")
        original_window = self.driver.current_window_handle
        with open(self.OUTPUT_FILE, 'a', encoding='utf-8') as f_out:
            for i, link_info in enumerate(links_to_process):
                url = link_info.get('url')
                product_id = link_info.get('id')
                if not url or not product_id:
                    print(f"--- ({i+1}/{len(links_to_process)}) Skipping product with missing URL or ID.")
                    continue
                print(f"--- ({i+1}/{len(links_to_process)}) Opening Product ID: {product_id} in a new tab...")
                def scrape_action(driver, url=url, product_id=product_id):
                    driver.execute_script("window.open();")
                    new_window = [window for window in driver.window_handles if window != original_window][0]
                    driver.switch_to.window(new_window)
                    driver.get(url)
                    WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "#productDetailsMain"))
                    )
                    print(f"   ✅ Successfully loaded page for Product ID: {product_id}")
                    scraped_data = self.scrape_product_detail_page()
                    scraped_data['SourceURL'] = url
                    f_out.write(json.dumps(scraped_data) + '\n')
                    f_out.flush()
                    print(f"   ✅ Scraped: {scraped_data.get('Name', 'N/A')}")
                    if len(driver.window_handles) > 1:
                        driver.close()
                        driver.switch_to.window(original_window)
                    time.sleep(2)  # Add delay between requests
                try:
                    self.driver_manager.resilient_action(scrape_action)
                except Exception as e:
                    print(f"❌ FAILED to scrape page for Product ID {product_id}. Error: {e}")
                    # Try to take a screenshot if possible
                    try:
                        if self.driver:
                            self.driver.save_screenshot(f"failure_product_{product_id}.png")
                    except Exception as e2:
                        print("⚠️ Could not take screenshot, driver may be dead.")
                    # Log the failed product ID for later retry
                    try:
                        with open("failed_products.txt", "a") as fail_log:
                            fail_log.write(f"{product_id}\n")
                    except Exception as log_e:
                        print(f"⚠️ Could not log failed product ID: {log_e}")
                    # Ensure the driver is fully restarted
                    try:
                        self.driver_manager.restart_driver()
                        time.sleep(3)  # Give system time to release resources
                        self.driver = self.driver_manager.get_driver()
                    except Exception as restart_e:
                        print(f"⚠️ Could not restart driver: {restart_e}")
                    continue  # Move to the next product
        self.driver_manager.quit()
        print("✅ Done!")

        # Batch retry logic for failed products
        max_retries = 2
        retry_delay = 5
        for attempt in range(1, max_retries + 1):
            if not os.path.exists("failed_products.txt"):
                break
            with open("failed_products.txt", "r") as f:
                failed_ids = [line.strip() for line in f if line.strip()]
            if not failed_ids:
                break
            print(f"🔁 Batch retry attempt {attempt} for {len(failed_ids)} failed products...")
            os.remove("failed_products.txt")  # Remove so we only log new failures
            # Re-read product links to get the full info for failed IDs
            product_links_map = {str(link.get('id')): link for link in product_links}
            scraped_ids = self.get_scraped_ids()  # Refresh scraped IDs before each retry batch
            still_failed = []  # Track products that still fail
            with open(self.OUTPUT_FILE, 'a', encoding='utf-8') as f_out:
                for product_id in failed_ids:
                    if product_id in scraped_ids:
                        print(f"⚠️ Product ID {product_id} already scraped, skipping retry and removing from failed list.")
                        continue
                    link_info = product_links_map.get(product_id)
                    if not link_info:
                        print(f"⚠️ Could not find link info for failed product ID {product_id}, skipping.")
                        continue
                    url = link_info.get('url')
                    print(f"--- [RETRY {attempt}] Retrying Product ID: {product_id}")
                    def scrape_action(driver, url=url, product_id=product_id):
                        driver.execute_script("window.open();")
                        new_window = [window for window in driver.window_handles if window != original_window][0]
                        driver.switch_to.window(new_window)
                        driver.get(url)
                        WebDriverWait(driver, 30).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "#productDetailsMain"))
                        )
                        print(f"   ✅ [RETRY {attempt}] Successfully loaded page for Product ID: {product_id}")
                        scraped_data = self.scrape_product_detail_page()
                        scraped_data['SourceURL'] = url
                        f_out.write(json.dumps(scraped_data) + '\n')
                        f_out.flush()
                        print(f"   ✅ [RETRY {attempt}] Scraped: {scraped_data.get('Name', 'N/A')}")
                        if len(driver.window_handles) > 1:
                            driver.close()
                            driver.switch_to.window(original_window)
                        time.sleep(2)
                    try:
                        self.driver_manager.resilient_action(scrape_action)
                    except Exception as e:
                        print(f"❌ [RETRY {attempt}] FAILED to scrape page for Product ID {product_id}. Error: {e}")
                        try:
                            if self.driver:
                                self.driver.save_screenshot(f"failure_product_{product_id}_retry{attempt}.png")
                        except Exception as e2:
                            print("⚠️ Could not take screenshot, driver may be dead.")
                        still_failed.append(product_id)
                        continue
            # After the batch, write only still-failed IDs back to failed_products.txt
            if still_failed:
                with open("failed_products.txt", "w") as fail_log:
                    for pid in still_failed:
                        fail_log.write(f"{pid}\n")
            print(f"⏳ Waiting {retry_delay} seconds before next retry batch...")
            time.sleep(retry_delay)

def main():
    parser = argparse.ArgumentParser(description="Scrape product data from ESP Web.")
    parser.add_argument('--limit', type=int, default=None, help='Limit the number of products to scrape.')
    parser.add_argument('--headless', action='store_true', help='Run Chrome in headless mode (no window).')
    parser.add_argument('--force-relogin', action='store_true', help='Force update session/cookies with fresh login.')
    parser.add_argument('--output-file', type=str, default=None, help='Output file for scraped details.')
    parser.add_argument('--links-file', type=str, default=None, help='Input links file (JSONL).')
    parser.add_argument('--overwrite-output', action='store_true', help='Overwrite output file before scraping (do not resume).')
    parser.add_argument('--batch-size', type=int, default=None, help='Number of products to process in this batch.')
    parser.add_argument('--batch-number', type=int, default=None, help='Batch number (0-based).')
    args = parser.parse_args()
    if args.overwrite_output:
        output_file = args.output_file or os.getenv("DETAILS_OUTPUT_FILE", "final_product_details.jsonl")
        open(output_file, 'w').close()  # Truncate the file
        print(f"⚠️ Output file '{output_file}' has been cleared.")
    session_manager = SessionManager()
    scraper = ProductDetailScraper(
        session_manager,
        headless=args.headless,
        limit=args.limit,
        output_file=args.output_file,
        links_file=args.links_file
    )
    # Batching logic
    if args.batch_size is not None and args.batch_number is not None:
        all_links = scraper.read_product_links()
        start = args.batch_number * args.batch_size
        end = start + args.batch_size
        batch_links = all_links[start:end]
        # Patch the method to use only the batch
        def batch_read_links():
            return batch_links
        scraper.read_product_links = batch_read_links
        print(f"🔢 Processing batch {args.batch_number} (products {start} to {end-1})")
    scraper.scrape_all_details(force_relogin=args.force_relogin)

if __name__ == "__main__":
    main()