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
from espscraper.selenium_resilient_manager import SeleniumResilientManager
import requests
import collections
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

class ProductDetailScraper(BaseScraper):
    def __init__(self, session_manager, headless=False, limit=None, output_file=None, links_file=None, aggressive_cleanup=True, max_retries=5, batch_retry_limit=2, debug_mode=False):
        super().__init__(session_manager)
        # Don't load .env file in production - use environment variables directly
        # self.load_env()
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
        self.max_retries = max_retries
        self.batch_retry_limit = batch_retry_limit
        self.debug_mode = debug_mode
        self.headless_failed = False  # Track if headless mode failed
        
        # Use simple Selenium driver instead of resilient manager
        self.driver = None
        self._setup_simple_driver()

    def _setup_simple_driver(self):
        """Setup a simple Selenium driver without the resilient manager"""
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium import webdriver
        
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")  # Reduce memory usage
        options.add_argument("--disable-web-security")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--disable-ipc-flooding-protection")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-client-side-phishing-detection")
        options.add_argument("--disable-component-extensions-with-background-pages")
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-domain-reliability")
        options.add_argument("--disable-features=TranslateUI")
        options.add_argument("--disable-hang-monitor")
        options.add_argument("--disable-prompt-on-repost")
        options.add_argument("--disable-sync")
        options.add_argument("--force-color-profile=srgb")
        options.add_argument("--metrics-recording-only")
        options.add_argument("--no-first-run")
        options.add_argument("--safebrowsing-disable-auto-update")
        options.add_argument("--enable-automation")
        options.add_argument("--password-store=basic")
        options.add_argument("--use-mock-keychain")
        options.add_argument("--memory-pressure-off")
        options.add_argument("--max_old_space_size=2048")
        options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        if not self.headless:
            options.add_argument("--start-maximized")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_page_load_timeout(15)
        self.driver.implicitly_wait(5)
        
        # Remove webdriver property to avoid detection
        try:
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": """
                        Object.defineProperty(navigator, 'webdriver', {get: () => undefined})
                    """
                },
            )
        except Exception:
            pass
        
        logging.info("✅ Simple Chrome driver started successfully")

    def setup_selenium(self, driver=None):
        # This method is now only used as a callback if needed for custom setup after driver creation
        pass

    def login(self, force_relogin=False):
        # Use a simple Selenium driver for login and cookie loading
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium import webdriver
        import time
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        # If session is valid and not force_relogin, skip login
        cookies, page_key, search_id = self.session_manager.load_state()
        if cookies and page_key and search_id and not force_relogin:
            logging.info("✅ Loaded session state from file, skipping login.")
            # Load cookies into the current driver
            self._load_cookies_into_driver(cookies)
            return

        logging.info("🤖 Launching simple Selenium for login...")
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        try:
            driver.get(self.PRODUCTS_URL)
            time.sleep(3)
            logging.info("🔒 Login page detected. Logging in...")
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "asilogin_UserName")))
            driver.find_element(By.ID, "asilogin_UserName").send_keys(self.USERNAME)
            driver.find_element(By.ID, "asilogin_Password").send_keys(self.PASSWORD)
            driver.find_element(By.ID, "btnLogin").click()
            try:
                logging.info("⏳ Waiting for potential login alert...")
                WebDriverWait(driver, 10).until(EC.alert_is_present())
                alert = driver.switch_to.alert
                logging.warning(f"⚠️ Alert detected: {alert.text}")
                alert.accept()
                logging.info("✅ Alert accepted.")
            except Exception:
                logging.info("ℹ️ No login alert appeared, continuing.")
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "hdnPageStateKey")))
            cookies = driver.get_cookies()
            with open(self.session_manager.cookie_file, 'w') as f:
                import json
                json.dump(cookies, f)
            page_key = driver.find_element(By.ID, "hdnPageStateKey").get_attribute('value')
            current_url = driver.current_url
            import urllib.parse
            parsed_url = urllib.parse.urlparse(current_url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            search_id = query_params['SearchID'][0] if 'SearchID' in query_params else None
            self.session_manager.save_state(cookies, page_key, search_id)
            logging.info(f"✅ Selenium login complete. pageKey: {page_key}, searchId: {search_id}")
            
            # Load cookies into the current driver
            self._load_cookies_into_driver(cookies)
            
        except Exception as e:
            logging.error(f"❌ Selenium login failed: {e}")
        finally:
            driver.quit()
            logging.info("🤖 Selenium browser closed.")

    def _load_cookies_into_driver(self, cookies):
        """Load cookies into the current driver"""
        try:
            # First navigate to the domain to set cookies
            self.driver.get(self.PRODUCTS_URL)
            time.sleep(2)
            
            # Add cookies to the driver
            for cookie in cookies:
                try:
                    # Remove problematic attributes that Selenium doesn't like
                    cookie_dict = {
                        'name': cookie['name'],
                        'value': cookie['value'],
                        'domain': cookie.get('domain', ''),
                        'path': cookie.get('path', '/')
                    }
                    self.driver.add_cookie(cookie_dict)
                except Exception as e:
                    logging.warning(f"⚠️ Could not add cookie {cookie.get('name', 'unknown')}: {e}")
            
            logging.info(f"✅ Loaded {len(cookies)} cookies into driver")
        except Exception as e:
            logging.error(f"⚠️ Error loading cookies into driver: {e}")

    def read_product_links(self):
        links = []
        if os.path.exists(self.LINKS_FILE):
            with open(self.LINKS_FILE, 'r') as f:
                for line in f:
                    links.append(json.loads(line))
            logging.info(f"📄 Read {len(links)} product links from {self.LINKS_FILE}.")
        else:
            logging.error(f"❌ ERROR: Links file not found at {self.LINKS_FILE}")
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
            
            # --- Product Name (updated selectors) ---
            name = "N/A"
            try:
                # Try multiple selectors for product name
                name_selectors = [
                    '#productDetailsMain h3.text-primary',
                    'h1.product-title',
                    '.product-name h1',
                    'h1[data-product-name]',
                    '.product-header h1',
                    'h1'
                ]
                for selector in name_selectors:
                    name_elem = detail_soup.select_one(selector)
                    if name_elem and name_elem.text.strip():
                        name = name_elem.text.strip()
                        break
            except:
                pass

            # Product Number (SKU) - updated selectors
            sku = "N/A"
            try:
                sku_selectors = [
                    'span.product-number',
                    '.product-sku',
                    '[data-product-sku]',
                    '.product-id'
                ]
                for selector in sku_selectors:
                    sku_elem = detail_soup.select_one(selector)
                    if sku_elem:
                        sku = sku_elem.text.strip().replace('Product #:', '').strip()
                        break
            except:
                pass

            # Short Description - updated selectors
            short_description = "N/A"
            try:
                desc_selectors = [
                    '#productDetailsMain div.product-info p.ng-binding',
                    '.product-description p',
                    '.product-summary p',
                    '[data-product-description]'
                ]
                for selector in desc_selectors:
                    desc_elem = detail_soup.select_one(selector)
                    if desc_elem and desc_elem.text.strip():
                        short_description = desc_elem.text.strip()
                        break
            except:
                pass

            # --- Variant Images (simplified) ---
            variant_images = []
            try:
                # Try multiple image selectors
                img_selectors = [
                    '#productImages input[type="image"]',
                    '.product-images img',
                    '.variant-images img',
                    'img[data-product-image]'
                ]
                for selector in img_selectors:
                    images = detail_soup.select(selector)
                    if images:
                        for img in images:
                            src = img.get('src', '')
                            if src and src not in variant_images:
                                variant_images.append(src)
                        break
            except:
                pass

            # Main Image URL
            image_url = variant_images[0] if variant_images else "N/A"

            # Price Range - updated selectors
            price = "N/A"
            try:
                price_selectors = [
                    '#productDetailsMain div.product-price a.ng-binding',
                    '.product-price',
                    '[data-product-price]',
                    '.price-range'
                ]
                for selector in price_selectors:
                    price_elem = detail_soup.select_one(selector)
                    if price_elem and price_elem.text.strip():
                        price = price_elem.text.strip()
                        break
            except:
                pass

            # Colors - updated selectors
            colors = []
            try:
                color_selectors = [
                    'span:contains("Colors") + span',
                    '.product-colors span',
                    '[data-product-colors]'
                ]
                for selector in color_selectors:
                    color_elem = detail_soup.select_one(selector)
                    if color_elem:
                        color_text = color_elem.get_text(strip=True)
                        if color_text and color_text != "N/A":
                            colors = [c.strip() for c in color_text.split(',') if c.strip()]
                            break
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

            # --- UpdateDate and ProductURL ---
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
                    update_selectors = [
                        'span.text-light-2.text-medium.ng-binding',
                        '.last-updated',
                        '[data-last-updated]'
                    ]
                    for selector in update_selectors:
                        update_elem = detail_soup.select_one(selector)
                        if update_elem and 'Last updated' in update_elem.text:
                            update_date = update_elem.text.replace('Last updated:', '').strip()
                            break
                except:
                    pass

            # --- Simplified Imprint Section ---
            imprint_info = {
                'General': {},
                'Methods': {},
                'Services': {},
                'Other': {}
            }
            try:
                imprint_section = detail_soup.select_one('#pnlImprint')
                if imprint_section:
                    # Extract basic imprint info
                    for attr_div in imprint_section.select('div.product-attribute'):
                        header_elem = attr_div.select_one('span.attribute-header, span.property-label')
                        if header_elem:
                            key = header_elem.get_text(strip=True).replace(':', '')
                            values = [span.get_text(strip=True) for span in attr_div.select('span.ng-binding') if span.get_text(strip=True)]
                            if key and values:
                                imprint_info['General'][key] = values if len(values) > 1 else values[0]
            except Exception as e:
                logging.warning(f"⚠️ Error extracting imprint info: {e}")

            # --- Simplified Production Info ---
            production_info = {}
            try:
                options_section = detail_soup.select_one('#pnlOptions')
                if options_section:
                    for attr_div in options_section.select('div.product-attribute'):
                        header_elem = attr_div.select_one('span.attribute-header')
                        if header_elem:
                            key = header_elem.get_text(strip=True)
                            values = [span.get_text(strip=True) for span in attr_div.select('span.ng-binding') if span.get_text(strip=True)]
                            if key and values:
                                production_info[key] = values if len(values) > 1 else values[0]
            except:
                pass

            # --- Production Time and Supplier ---
            production_time = "N/A"
            supplier = "N/A"
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
                cpn_selectors = [
                    'div.product-cpn.ng-binding',
                    '.product-cpn',
                    '[data-product-cpn]'
                ]
                for selector in cpn_selectors:
                    cpn_elem = detail_soup.select_one(selector)
                    if cpn_elem:
                        product_cpn = cpn_elem.text.strip()
                        break
            except:
                pass

            # --- Pricing Table (simplified) ---
            pricing_table = self.extract_pricing_table()

            # --- Related Products (simplified) ---
            related_products = []
            if product_id:
                try:
                    related_products = self.get_related_products(product_id, soup=detail_soup)
                except Exception as e:
                    logging.warning(f"[RelatedProduct] Error: {e}")

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
                "Shipping": {},
                "SafetyAndCompliance": {},
                "SupplierInfo": {}
            }

        except Exception as e:
            logging.error(f"❌ Error scraping product detail page: {e}")
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
                logging.warning('⚠️ No pricing section found, skipping pricing table')
                return []

            pricing_soup = BeautifulSoup(pricing_section.get_attribute('innerHTML'), 'html.parser')
            table = pricing_soup.find('table')

            if not table:
                logging.warning('⚠️ Pricing table element not found within pricing section.')
                return []

            rows = table.find_all('tr')
            if not rows or len(rows) < 2:
                logging.warning('⚠️ Pricing table has no header or data rows.')
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
                logging.warning('⚠️ Could not parse quantities from the pricing table header.')
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
                logging.warning('⚠️ Pricing table was parsed, but no valid data was extracted.')
            
            return pricing_table

        except Exception as e:
            logging.warning(f'⚠️ Error in extract_pricing_table: {e}')
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
                        if 'id' in data and data['id']:
                            scraped_ids.add(str(data['id']))
                        elif 'ProductID' in data and data['ProductID']:
                            scraped_ids.add(str(data['ProductID']))
                        elif 'url' in data and data['url']:
                            scraped_ids.add(str(data['url']))
                    except Exception:
                        continue
        return scraped_ids
    
    def post_batch_to_wordpress(batch, api_url, api_key):
        """
        Send a batch of products to the WordPress REST API endpoint.
        """
        if not batch:
            return
        # Prepare the batch as JSONL
        jsonl_data = '\n'.join([json.dumps(product) for product in batch])
        files = {'file': ('batch.jsonl', jsonl_data)}
        headers = {'Authorization': f'Bearer {api_key}'}
        try:
            response = requests.post(api_url, files=files, headers=headers, timeout=30)
            response.raise_for_status()
            logging.info(f"✅ Successfully posted batch of {len(batch)} products to WordPress.")
        except Exception as e:
            logging.error(f"❌ Failed to post batch to WordPress: {e}")

    def scrape_all_details(self, force_relogin=False):
        self.login(force_relogin=force_relogin)
        product_links = self.read_product_links()
        scraped_ids = self.get_scraped_ids()
        links_to_process = [link for link in product_links if str(link.get('id')) not in scraped_ids]
        if self.limit:
            links_to_process = links_to_process[:self.limit]
        logging.info(f"🚀 Starting to scrape {len(links_to_process)} product pages (skipping {len(scraped_ids)} already scraped)...")

        # --- Hardcoded Robust Rate Limiting ---
        max_requests_per_minute = 25
        batch_size = 15
        batch_pause = 5
        min_delay = 1.5
        request_times = collections.deque()

        batch = []
        api_url = os.getenv("WP_API_URL")  # Set this in your GitHub Action env
        api_key = os.getenv("WP_API_KEY")  # Set this in your GitHub Action env/secrets

        def rate_limit_pause():
            now = time.time()
            # Remove requests older than 60 seconds
            while request_times and now - request_times[0] > 60:
                request_times.popleft()
            if len(request_times) >= max_requests_per_minute:
                wait_time = 60 - (now - request_times[0])
                if wait_time > 0 and wait_time < 30:  # never sleep too long
                    logging.info(f"⏸️ [RateLimit] Waiting {wait_time:.1f} seconds to respect per-minute limit...")
                    time.sleep(wait_time)
            # Enforce minimum delay between requests
            if request_times and now - request_times[-1] < min_delay:
                delay = min_delay - (now - request_times[-1])
                if delay > 0 and delay < 10:
                    logging.info(f"⏸️ [MinDelay] Waiting {delay:.2f} seconds...")
                    time.sleep(delay)
            request_times.append(time.time())

        with open(self.OUTPUT_FILE, 'a', encoding='utf-8') as f_out:
            for i, link_info in enumerate(links_to_process):
                url = link_info.get('url')
                product_id = link_info.get('id')
                if not url or not product_id:
                    logging.warning(f"--- ({i+1}/{len(links_to_process)}) Skipping product with missing URL or ID.")
                    continue
                logging.info(f"--- ({i+1}/{len(links_to_process)}) Loading Product ID: {product_id}...")

                # --- Rate limiting before each request ---
                rate_limit_pause()

                # Simple scraping without window switching
                try:
                    # Load the product page directly
                    self.driver.get(url)
                    # Wait for the page to load with a more flexible approach
                    try:
                        WebDriverWait(self.driver, 15).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "#productDetailsMain"))
                        )
                    except Exception as e:
                        logging.warning(f"   ⚠️ Timeout waiting for product details, trying alternative selectors...")
                        # Try alternative selectors
                        alternative_selectors = [
                            "h3.text-primary",
                            ".product-info",
                            "span.product-number",
                            "body"
                        ]
                        element_found = False
                        for selector in alternative_selectors:
                            try:
                                WebDriverWait(self.driver, 5).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                                )
                                element_found = True
                                logging.info(f"   ✅ Found element with selector: {selector}")
                                break
                            except:
                                continue
                        if not element_found:
                            logging.warning(f"   ❌ Could not find any expected elements on page")
                            continue
                    logging.info(f"   ✅ Successfully loaded page for Product ID: {product_id}")
                    scraped_data = self.scrape_product_detail_page()
                    scraped_data['SourceURL'] = url
                    f_out.write(json.dumps(scraped_data) + '\n')
                    f_out.flush()
                    batch.append(scraped_data)
                    logging.info(f"   ✅ Scraped: {scraped_data.get('Name', 'N/A')}")

                    # POST batch if batch_size reached
                    if len(batch) >= batch_size:
                        self.post_batch_to_wordpress(batch, api_url, api_key)
                        batch = []
                except Exception as e:
                    logging.error(f"❌ FAILED to scrape page for Product ID {product_id}. Error: {e}")
                    # Simple error recovery - just restart the driver
                    try:
                        logging.info("🔄 Restarting driver due to error...")
                        self.driver.quit()
                        time.sleep(3)
                        self._setup_simple_driver()
                        # Re-login if needed
                        self.login(force_relogin=False)
                    except Exception as restart_e:
                        logging.warning(f"⚠️ Could not restart driver: {restart_e}")
                    # Log the failed product ID for later retry
                    try:
                        with open("failed_products.txt", "a") as fail_log:
                            fail_log.write(f"{product_id}\n")
                    except Exception as log_e:
                        logging.warning(f"⚠️ Could not log failed product ID: {log_e}")
                    # Add delay before continuing to next product
                    time.sleep(3)
                    continue

                # --- Batch pause after every batch_size products ---
                if (i + 1) % batch_size == 0 and (i + 1) < len(links_to_process):
                    logging.info(f"⏸️ [BatchPause] Pausing for {batch_pause} seconds after {batch_size} products...")
                    time.sleep(batch_pause)

                if batch:
                    self.post_batch_to_wordpress(batch, api_url, api_key)
                    

        # Clean up
        try:
            self.driver.quit()
        except:
            pass
        logging.info("✅ Done!")

        # Simple retry for failed products
        if os.path.exists("failed_products.txt"):
            logging.info(f"🔄 Retrying failed products...")
            with open("failed_products.txt", "r") as f:
                failed_ids = [line.strip() for line in f if line.strip()]
            
            if failed_ids:
                logging.info(f"🔄 Retrying {len(failed_ids)} failed products...")
                # Re-setup driver for retry
                try:
                    self.driver.quit()
                except:
                    pass
                self._setup_simple_driver()
                self.login(force_relogin=False)
                
                product_links_map = {str(link.get('id')): link for link in product_links}
                scraped_ids = self.get_scraped_ids()
                
                with open(self.OUTPUT_FILE, 'a', encoding='utf-8') as f_out:
                    for product_id in failed_ids:
                        if product_id in scraped_ids:
                            logging.warning(f"⚠️ Product ID {product_id} already scraped, skipping retry.")
                            continue
                        
                        link_info = product_links_map.get(product_id)
                        if not link_info:
                            logging.warning(f"⚠️ Could not find link info for failed product ID {product_id}, skipping.")
                            continue
                        
                        url = link_info.get('url')
                        logging.info(f"🔄 Retrying Product ID: {product_id}")
                        
                        try:
                            self.driver.get(url)
                            
                            # Wait for page load with better error handling
                            try:
                                WebDriverWait(self.driver, 15).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, "#productDetailsMain"))
                                )
                            except Exception as e:
                                logging.warning(f"   ⚠️ Timeout waiting for product details, trying alternative selectors...")
                                # Try alternative selectors
                                alternative_selectors = [
                                    "h3.text-primary",
                                    ".product-info",
                                    "span.product-number",
                                    "body"
                                ]
                                element_found = False
                                for selector in alternative_selectors:
                                    try:
                                        WebDriverWait(self.driver, 5).until(
                                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                                        )
                                        element_found = True
                                        logging.info(f"   ✅ Found element with selector: {selector}")
                                        break
                                    except:
                                        continue
                                if not element_found:
                                    logging.warning(f"   ❌ Could not find any expected elements on page")
                                    continue
                            
                            scraped_data = self.scrape_product_detail_page()
                            if scraped_data:
                                scraped_data['SourceURL'] = url
                                f_out.write(json.dumps(scraped_data) + '\n')
                                f_out.flush()
                                logging.info(f"   ✅ [RETRY] Scraped: {scraped_data.get('Name', 'N/A')}")
                            else:
                                logging.warning(f"   ❌ [RETRY] Failed to extract data for Product ID {product_id}")
                        except Exception as e:
                            logging.error(f"❌ [RETRY] FAILED to scrape page for Product ID {product_id}. Error: {e}")
                        
                        time.sleep(2)
                
                # Clean up retry driver
                try:
                    self.driver.quit()
                except:
                    pass
            
            # Remove the failed products file
            try:
                os.remove("failed_products.txt")
            except:
                pass

    def fallback_to_headful(self):
        """Fallback to headful mode if headless mode is failing"""
        if self.headless and not self.headless_failed:
            logging.info("🔄 Headless mode failing, switching to headful mode...")
            self.headless_failed = True
            self.headless = False
            try:
                self.driver.quit()
                self.driver = None
                self._setup_simple_driver()
                logging.info("✅ Switched to headful mode successfully")
                return True
            except Exception as e:
                logging.error(f"❌ Failed to switch to headful mode: {e}")
                return False
        return False


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
    parser.add_argument('--no-aggressive-cleanup', action='store_true', help='Disable aggressive Chrome process cleanup (keeps your browser windows open).')
    parser.add_argument('--max-retries', type=int, default=5, help='Maximum number of retries for individual product scraping (default: 5)')
    parser.add_argument('--batch-retry-limit', type=int, default=2, help='Maximum number of batch retry attempts for failed products (default: 2)')
    parser.add_argument('--debug-mode', action='store_true', help='Enable real-time connection monitoring.')
    args = parser.parse_args()
    if args.overwrite_output:
        output_file = args.output_file or os.getenv("DETAILS_OUTPUT_FILE", "final_product_details.jsonl")
        open(output_file, 'w').close()  # Truncate the file
        logging.warning(f"⚠️ Output file '{output_file}' has been cleared.")
    session_manager = SessionManager()
    scraper = ProductDetailScraper(
        session_manager,
        headless=args.headless,
        limit=args.limit,
        output_file=args.output_file,
        links_file=args.links_file,
        aggressive_cleanup=not args.no_aggressive_cleanup,
        max_retries=args.max_retries,
        batch_retry_limit=args.batch_retry_limit,
        debug_mode=args.debug_mode
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
        logging.info(f"🔢 Processing batch {args.batch_number} (products {start} to {end-1})")
    scraper.scrape_all_details(force_relogin=args.force_relogin)

if __name__ == "__main__":
    main()