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
from lxml import html, etree

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


class ProductDetailScraper(BaseScraper):
    def __init__(
        self,
        session_manager,
        headless=False,
        limit=None,
        output_file=None,
        links_file=None,
        aggressive_cleanup=True,
        max_retries=5,
        batch_retry_limit=2,
        debug_mode=False,
    ):
        super().__init__(session_manager)
        # Don't load .env file in production - use environment variables directly
        # self.load_env()
        self.USERNAME = os.getenv("ESP_USERNAME")
        self.PASSWORD = os.getenv("ESP_PASSWORD")
        self.PRODUCTS_URL = os.getenv("PRODUCTS_URL")
        # Ensure data directory exists
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(data_dir, exist_ok=True)
        self.OUTPUT_FILE = output_file or os.getenv(
            "DETAILS_OUTPUT_FILE", os.path.join(data_dir, "final_product_details.jsonl")
        )
        self.LINKS_FILE = links_file or os.getenv(
            "DETAILS_LINKS_FILE", os.path.join(data_dir, "api_scraped_links.jsonl")
        )
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
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        if not self.headless:
            options.add_argument("--start-maximized")

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_page_load_timeout(30)  # Increased from 15 to 30 seconds
        self.driver.implicitly_wait(10)  # Increased from 5 to 10 seconds

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
            logging.info(
                "✅ Loaded session state from file, attempting to use existing session."
            )
            # Load cookies into the current driver
            self._load_cookies_into_driver(cookies)

            # Check if session validation passed
            if hasattr(self, "_session_validated") and self._session_validated:
                logging.info("✅ Existing session is valid, skipping login.")
                return
            else:
                logging.warning(
                    "⚠️ Existing session appears to be expired, performing fresh login."
                )

        logging.info("🤖 Launching simple Selenium for login...")
        options = Options()
        if self.headless:
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
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )
        try:
            driver.get(self.PRODUCTS_URL)
            time.sleep(3)
            logging.info("🔒 Login page detected. Logging in...")
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "asilogin_UserName"))
            )
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
            WebDriverWait(driver, 40).until(
                EC.presence_of_element_located((By.ID, "hdnPageStateKey"))
            )
            cookies = driver.get_cookies()
            with open(self.session_manager.cookie_file, "w") as f:
                import json

                json.dump(cookies, f)
            page_key = driver.find_element(By.ID, "hdnPageStateKey").get_attribute(
                "value"
            )
            current_url = driver.current_url
            import urllib.parse

            parsed_url = urllib.parse.urlparse(current_url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            search_id = (
                query_params["SearchID"][0] if "SearchID" in query_params else None
            )
            self.session_manager.save_state(cookies, page_key, search_id)
            logging.info(
                f"✅ Selenium login complete. pageKey: {page_key}, searchId: {search_id}"
            )

            # Load cookies into the current driver
            self._load_cookies_into_driver(cookies)

        except Exception as e:
            logging.error(f"❌ Selenium login failed: {e}")
        finally:
            driver.quit()
            logging.info("🤖 Selenium browser closed.")


    def _load_cookies_into_driver(self, cookies):
        """Load cookies into the current driver and validate session"""
        try:
            # First navigate to the domain to set cookies
            self.driver.get(self.PRODUCTS_URL)
            time.sleep(2)

            # Add cookies to the driver
            for cookie in cookies:
                try:
                    # Remove problematic attributes that Selenium doesn't like
                    cookie_dict = {
                        "name": cookie["name"],
                        "value": cookie["value"],
                        "domain": cookie.get("domain", ""),
                        "path": cookie.get("path", "/"),
                    }
                    self.driver.add_cookie(cookie_dict)
                except Exception as e:
                    logging.warning(
                        f"⚠️ Could not add cookie {cookie.get('name', 'unknown')}: {e}"
                    )

            logging.info(f"✅ Loaded {len(cookies)} cookies into driver")

            # Validate session by checking if we're still logged in
            self._validate_session()

        except Exception as e:
            logging.error(f"⚠️ Error loading cookies into driver: {e}")

    def _validate_session(self):
        """Validate that the session is still active"""
        try:
            # Refresh the page to see if we're still logged in
            self.driver.refresh()
            time.sleep(3)

            # Check if we're redirected to login page
            current_url = self.driver.current_url
            if "login" in current_url.lower() or "asilogin" in current_url.lower():
                logging.warning("⚠️ Session expired - redirected to login page")
                self._session_validated = False
                return False

            # Check for login form elements
            try:
                login_form = self.driver.find_element(By.ID, "asilogin_UserName")
                if login_form:
                    logging.warning("⚠️ Session expired - login form detected")
                    self._session_validated = False
                    return False
            except:
                pass

            # Check for authenticated page elements
            try:
                # Look for elements that indicate we're logged in
                authenticated_elements = [
                    "hdnPageStateKey",
                    "productDetailsMain",
                    "product-list",
                    "search-results",
                ]

                for element_id in authenticated_elements:
                    try:
                        self.driver.find_element(By.ID, element_id)
                        logging.info("✅ Session validated successfully")
                        self._session_validated = True
                        return True
                    except:
                        continue

                # If we can't find authenticated elements, check if we're on a product page
                if "productID=" in current_url:
                    logging.info("✅ Session validated - on product page")
                    self._session_validated = True
                    return True

                logging.warning("⚠️ Session validation inconclusive")
                self._session_validated = True  # Assume valid if we can't determine
                return True

            except Exception as e:
                logging.warning(f"⚠️ Error during session validation: {e}")
                self._session_validated = True  # Assume valid on error
                return True

        except Exception as e:
            logging.error(f"❌ Session validation failed: {e}")
            self._session_validated = False
            return False

    def read_product_links(self):
        import json

        links = []
        if not os.path.exists(self.LINKS_FILE):
            return links

        def extract_json_objects(text):
            decoder = json.JSONDecoder()
            idx = 0
            length = len(text)
            while idx < length:
                try:
                    obj, end = decoder.raw_decode(text, idx)
                    yield obj
                    idx = end
                    while idx < length and text[idx] in " \r\n\t":
                        idx += 1
                except json.JSONDecodeError:
                    break

        with open(self.LINKS_FILE, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                try:
                    links.append(json.loads(line))
                except Exception as e:
                    # Fallback: try to extract multiple JSON objects from the line
                    found_any = False
                    for obj in extract_json_objects(line):
                        links.append(obj)
                        found_any = True
                    if found_any:
                        import logging

                        logging.warning(
                            f"Line {i} in {self.LINKS_FILE} contained multiple JSON objects. Used fallback parser."
                        )
                    else:
                        import logging

                        logging.error(
                            f"Skipping invalid JSON line {i} in {self.LINKS_FILE}: {e} | Content: {line.strip()}"
                        )
        return links

    def get_related_products(self, product_id, soup=None):
        """Try API first, fallback to HTML only if API fails or is empty. Never print errors, always return a list."""
        api_url = f"https://api.asicentral.com/v1/products/{product_id}/suggestions.json?page=1&rpp=5"
        try:
            resp = requests.get(api_url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                related = []
                for item in data.get("Results", []):
                    pid = item.get("Id")
                    name = item.get("Name")
                    image = item.get("ImageUrl")
                    if image and not image.startswith("http"):
                        image = f"https://api.asicentral.com/v1/{image.lstrip('/')}"
                    url = self.build_product_url(pid) if pid else ""
                    related.append({"Name": name, "URL": url, "Image": image})
                if related:
                    return related
        except Exception:
            pass
        # Only try HTML if API failed or returned no results
        related = []
        if soup:
            for item in soup.find_all("div", class_=re.compile(r"product-list-item")):
                name_tag = item.select_one(".prod-name a")
                name = name_tag.text.strip() if name_tag else "N/A"
                img_tag = item.select_one(".prod-img-inner img")
                image = img_tag["src"] if img_tag and img_tag.has_attr("src") else ""
                pid_match = re.search(r"/([0-9]+)(?:\?|$)", image)
                pid = pid_match.group(1) if pid_match else None
                url = self.build_product_url(pid) if pid else ""
                related.append({"Name": name, "URL": url, "Image": image})
        return related

    def build_product_url(self, product_id):
        return f"https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductDetails&productID={product_id}&autoLaunchVS=0&tab=list"

    def scrape_product_detail_page(self):
        """
        Scrapes product details from the currently opened product detail page.
        """
        try:
            # Use LXML for better performance
            detail_soup = BeautifulSoup(self.driver.page_source, "lxml")

            # --- Product Name (updated selectors) ---
            name = "N/A"
            try:
                # Try multiple selectors for product name
                name_selectors = [
                    "#productDetailsMain h3.text-primary",
                    "h1.product-title",
                    ".product-name h1",
                    "h1[data-product-name]",
                    ".product-header h1",
                    "h1",
                ]
                for selector in name_selectors:
                    name_elem = detail_soup.select_one(selector)
                    if name_elem and name_elem.text.strip():
                        name = name_elem.text.strip()
                        break
            except:
                pass

            # Product Number (SKU) - updated selectors based on actual HTML structure
            sku = "N/A"
            try:
                sku_selectors = [
                    "span.product-number.ng-binding",  # Direct product number span
                    "span.product-number",  # Fallback to any product-number
                    ".product-sku",
                    "[data-product-sku]",
                    ".product-id",
                    'span[translate*="PRODUCT_NO"]',  # Translate attribute approach
                ]
                for selector in sku_selectors:
                    sku_elem = detail_soup.select_one(selector)
                    if sku_elem:
                        sku_text = sku_elem.text.strip()
                        # Clean up the text (remove "Product #:" prefix)
                        if "Product #:" in sku_text:
                            sku = sku_text.replace("Product #:", "").strip()
                        else:
                            sku = sku_text
                        break
            except:
                pass

            # Short Description - updated selectors
            short_description = "N/A"
            try:
                desc_selectors = [
                    "#productDetailsMain div.product-info p.ng-binding",
                    ".product-description p",
                    ".product-summary p",
                    "[data-product-description]",
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
                    ".product-images img",
                    ".variant-images img",
                    "img[data-product-image]",
                ]
                for selector in img_selectors:
                    images = detail_soup.select(selector)
                    if images:
                        for img in images:
                            src = img.get("src", "")
                            if src and src not in variant_images:
                                variant_images.append(src)
                        break
            except:
                pass

            # Main Image URL
            image_url = variant_images[0] if variant_images else "N/A"

            # Price Range - updated selectors based on actual HTML structure
            price = "N/A"
            try:
                price_selectors = [
                    ".product-price a.ng-binding",  # Direct price link
                    '.product-price a[ng-click*="scrollTo"]',  # Price with ng-click
                    ".product-price .ng-binding",  # Any ng-binding in price div
                    ".product-price strong + a",  # Link after "Price" label
                    "[data-product-price]",
                    ".price-range",
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
                    'span:-soup-contains("Colors") + span',
                    ".product-colors span",
                    "[data-product-colors]",
                ]
                for selector in color_selectors:
                    color_elem = detail_soup.select_one(selector)
                    if color_elem:
                        color_text = color_elem.get_text(strip=True)
                        if color_text and color_text != "N/A":
                            colors = [
                                c.strip() for c in color_text.split(",") if c.strip()
                            ]
                            break
            except:
                pass

            # --- ProductID from URL ---
            product_id = None
            try:
                parsed_url = urllib.parse.urlparse(self.driver.current_url)
                for part in urllib.parse.parse_qsl(parsed_url.query):
                    if part[0].lower() == "productid":
                        product_id = part[1]
                        break
            except:
                pass

            # --- UpdateDate and ProductURL ---
            update_date = None
            product_url = None
            try:
                # Try to extract from JS context
                product_json = self.driver.execute_script(
                    "return (typeof Product !== 'undefined') ? JSON.stringify(Product) : null;"
                )
                if product_json:
                    import json as _json

                    product_js = _json.loads(product_json)
                    update_date = product_js.get("UpdateDate")
                    product_url = product_js.get("ProductURL")
            except:
                pass

            # Fallback to HTML if not found
            if not update_date:
                try:
                    update_selectors = [
                        "span.text-light-2.text-medium.ng-binding",
                        ".last-updated",
                        "[data-last-updated]",
                    ]
                    for selector in update_selectors:
                        update_elem = detail_soup.select_one(selector)
                        if update_elem and "Last updated" in update_elem.text:
                            update_date = update_elem.text.replace(
                                "Last updated:", ""
                            ).strip()
                            break
                except:
                    pass

            # --- Comprehensive AngularJS Data Extraction ---
            angular_data = self.get_angular_product_data()

            # --- Enhanced Imprint Section with Charges ---
            imprint_info = self.extract_comprehensive_imprint(detail_soup, angular_data)

            # --- Enhanced Production Info ---
            production_info = self.extract_comprehensive_production_info(
                detail_soup, angular_data
            )

            # --- Shipping Information ---
            shipping_info = self.extract_shipping_info(detail_soup, angular_data)

            # --- Safety & Compliance ---
            safety_info = self.extract_safety_compliance(detail_soup, angular_data)

            # --- Supplier Information with ASINumber ---
            supplier_info = self.extract_supplier_info(detail_soup, angular_data)

            # --- Production Time and Supplier ---
            production_time = "N/A"
            supplier = "N/A"
            try:
                production_elem = detail_soup.find(
                    "span", string=lambda s: s and "Production Time" in s
                )
                if production_elem:
                    production_time_elem = production_elem.find_next(
                        "span", class_="ng-binding"
                    )
                    if production_time_elem:
                        production_time = production_time_elem.text.strip()
            except:
                pass

            try:
                supplier_elem = detail_soup.find(
                    "span", string=lambda s: s and "Supplier" in s
                )
                if supplier_elem:
                    supplier_elem = supplier_elem.find_next("span", class_="ng-binding")
                    if supplier_elem:
                        supplier = supplier_elem.text.strip()
            except:
                pass

            # --- ProductCPN ---
            product_cpn = None
            try:
                cpn_selectors = [
                    "div.product-cpn.ng-binding",
                    ".product-cpn",
                    "[data-product-cpn]",
                ]
                for selector in cpn_selectors:
                    cpn_elem = detail_soup.select_one(selector)
                    if cpn_elem:
                        product_cpn = cpn_elem.text.strip()
                        break
            except:
                pass

            # --- Comprehensive Pricing Tables ---
            pricing_table = self.extract_comprehensive_pricing(
                detail_soup, angular_data
            )

            # --- Related Products (simplified) ---
            related_products = []
            if product_id:
                try:
                    related_products = self.get_related_products(
                        product_id, soup=detail_soup
                    )
                except Exception as e:
                    logging.warning(f"[RelatedProduct] Error: {e}")

            # Get current URL
            current_url = self.driver.current_url

            # --- ProductNumber extraction (from HTML) ---
            product_number = ""
            try:
                product_number_elem = detail_soup.select_one(
                    "span.product-number[translate-values]"
                )
                if product_number_elem:
                    attr = product_number_elem.get("translate-values", "")
                    # Try to parse as JSON/dict
                    import json
                    import re

                    attr_fixed = attr.replace("'", '"')
                    try:
                        d = json.loads(attr_fixed)
                        product_number = d.get("productno", "")
                    except Exception:
                        # Fallback: try to extract number from text
                        match = re.search(r"(\\d+)", product_number_elem.text)
                        if match:
                            product_number = match.group(1)
                # If still not found, fallback to SKU if numeric
                if not product_number and sku and sku.isdigit():
                    product_number = sku
            except Exception:
                pass

            # --- ProductURL and ProductArtURL construction ---
            product_url = (
                f"https://www.hitpromo.net/product/show/{product_number}"
                if product_number
                else ""
            )
            product_art_url = (
                f"https://www.hitpromo.net/fs/artTemplates/{product_number}/{product_number}.pdf"
                if product_number
                else ""
            )

            # Add scraped date
            scraped_date = time.strftime("%Y-%m-%d %H:%M:%S")

            return {
                "ProductID": product_id,
                "UpdateDate": update_date,
                "ProductURL": product_url,
                "ProductCPN": product_cpn,
                "URL": current_url,
                "Name": name,
                "SKU": sku,
                "ProductNumber": product_number,
                "ShortDescription": short_description,
                "ImageURL": image_url,
                "VariantImages": variant_images,
                "Price": price,  # Added price field
                "PricingTable": pricing_table,
                "Colors": colors,
                "ProductionTime": production_time,
                "Supplier": supplier,
                "RelatedProduct": related_products,
                "Imprint": imprint_info,
                "ProductionInfo": production_info,
                "Shipping": shipping_info,
                "SafetyAndCompliance": safety_info,
                "SupplierInfo": supplier_info,
                "ProductArtURL": product_art_url,
                "ScrapedDate": scraped_date,
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
                "#pnlPricing",
                ".pricing-section",
                '[id*="pricing"]',
                '[class*="pricing"]',
            ]

            for selector in pricing_selectors:
                try:
                    pricing_section = WebDriverWait(
                        self.driver, 10
                    ).until(  # Increased from 3 to 10
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if pricing_section:
                        break
                except:
                    continue

            if not pricing_section:
                logging.warning("⚠️ No pricing section found, skipping pricing table")
                return []

            pricing_soup = BeautifulSoup(
                pricing_section.get_attribute("innerHTML"), "lxml"
            )
            table = pricing_soup.find("table")

            if not table:
                logging.warning(
                    "⚠️ Pricing table element not found within pricing section."
                )
                return []

            rows = table.find_all("tr")
            if not rows or len(rows) < 2:
                logging.warning("⚠️ Pricing table has no header or data rows.")
                return []

            # Find the header row with quantities and create a column map {index: quantity}
            header_row = rows[0]
            quantity_map = {}
            for i, th in enumerate(header_row.find_all(["th", "td"])):
                if i == 0:
                    continue  # Skip the first column
                try:
                    quantity = int(re.sub(r"[^0-9]", "", th.text))
                    if quantity > 0:
                        quantity_map[i] = quantity
                except (ValueError, TypeError):
                    continue

            if not quantity_map:
                logging.warning(
                    "⚠️ Could not parse quantities from the pricing table header."
                )
                return []

            # Process data rows
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
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

                        dc_elem = cell.find("small", class_="price-code") or cell.find(
                            "span", class_="price-code"
                        )
                        if dc_elem:
                            discount_code = dc_elem.get_text(strip=True).strip("()")

                        price_match = re.search(r"[\d.,]+\d", price_str)
                        if price_match:
                            try:
                                price = float(price_match.group().replace(",", ""))
                                breaks.append(
                                    {
                                        "quantity": quantity,
                                        "price": price,
                                        "discount_code": discount_code,
                                    }
                                )
                            except (ValueError, TypeError):
                                continue

                if breaks:
                    pricing_table.append({"type": row_label, "breaks": breaks})

            if not pricing_table:
                logging.warning(
                    "⚠️ Pricing table was parsed, but no valid data was extracted."
                )

            return pricing_table

        except Exception as e:
            logging.warning(f"⚠️ Error in extract_pricing_table: {e}")
            return []

    def get_angular_product_data(self):
        """Extract complete product data from AngularJS with enhanced script execution and waiting"""
        try:
            # First, ensure all scripts are executed and AngularJS is fully loaded
            logging.info("🔄 Ensuring all JavaScript scripts are executed...")

            # Wait for AngularJS to be fully loaded and trigger digest cycles
            self.driver.execute_script(
                """
                // Wait for AngularJS to be available
                if (typeof angular !== 'undefined') {
                    // Trigger multiple digest cycles to ensure all data is populated
                    var $rootScope = angular.element(document.body).scope();
                    if ($rootScope) {
                        // Force multiple digest cycles
                        for (var i = 0; i < 3; i++) {
                            $rootScope.$apply();
                            $rootScope.$digest();
                        }

                        // Wait for any pending async operations
                        if ($rootScope.$$phase) {
                            $rootScope.$evalAsync(function() {});
                        }
                    }

                    // Trigger any pending timeouts or intervals
                    if (window.setTimeout) {
                        // Force execution of any pending timeouts
                        var originalSetTimeout = window.setTimeout;
                        window.setTimeout = function(fn, delay) {
                            if (delay === 0) {
                                fn();
                            } else {
                                originalSetTimeout(fn, delay);
                            }
                        };
                    }

                    // Execute any pending scripts
                    var scripts = document.querySelectorAll('script');
                    for (var i = 0; i < scripts.length; i++) {
                        var script = scripts[i];
                        if (script.type === 'text/javascript' || !script.type) {
                            try {
                                if (script.innerHTML) {
                                    eval(script.innerHTML);
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

                // Wait for any dynamic content to load
                return new Promise(function(resolve) {
                    setTimeout(function() {
                        resolve('Scripts executed and AngularJS ready');
                    }, 2000);
                });
            """
            )

            # Wait for the script execution to complete
            time.sleep(3)

            # Now extract the AngularJS data with enhanced methods
            angular_data = self.driver.execute_script(
                """
                // Enhanced AngularJS data extraction with multiple fallback strategies
                var productData = {};
                var scopeFound = false;

                // Method 1: Try to find the ProductDetailCtrl controller scope (most reliable)
                if (typeof angular !== 'undefined') {
                    try {
                        // Find the ProductDetailCtrl controller
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

                // Method 2: Try to find any controller with vm.product
                if (!scopeFound && typeof angular !== 'undefined') {
                    try {
                        var controllers = document.querySelectorAll('[ng-controller]');
                        for (var i = 0; i < controllers.length; i++) {
                            var controllerScope = angular.element(controllers[i]).scope();
                            if (controllerScope && controllerScope.vm && controllerScope.vm.product) {
                                var vm = controllerScope.vm;
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

                // Method 3: Try to find any scope with product data
                if (!scopeFound && typeof angular !== 'undefined') {
                    try {
                        // Try multiple elements to find the scope
                        var elements = [
                            document.body,
                            document.querySelector('#productDetailsMain'),
                            document.querySelector('.product-details'),
                            document.querySelector('[ng-controller]'),
                            document.querySelector('[ng-model]')
                        ];

                        for (var i = 0; i < elements.length; i++) {
                            if (elements[i]) {
                                var scope = angular.element(elements[i]).scope();
                                if (scope && scope.product) {
                                    productData = {
                                        product: scope.product || {},
                                        pricing: scope.product.Prices || [],
                                        variants: scope.product.Variants || [],
                                        imprinting: scope.product.Imprinting || {},
                                        shipping: scope.product.Shipping || {},
                                        supplier: scope.product.Supplier || {},
                                        attributes: scope.product.Attributes || {},
                                        warnings: scope.product.Warnings || [],
                                        certifications: scope.product.Certifications || []
                                    };
                                    scopeFound = true;
                                    break;
                                }
                            }
                        }
                    } catch (e) {
                        // Continue to next method
                    }
                }

                // Method 4: Try to extract from ng-model attributes (enhanced)
                if (!scopeFound) {
                    var ngModels = document.querySelectorAll('[ng-model]');
                    for (var i = 0; i < ngModels.length; i++) {
                        var model = ngModels[i].getAttribute('ng-model');
                        if (model && (model.includes('product') || model.includes('vm') || model.includes('pricing'))) {
                            // Try to evaluate the model
                            try {
                                var modelValue = eval(model);
                                if (modelValue && typeof modelValue === 'object') {
                                    productData = {
                                        product: modelValue || {},
                                        pricing: modelValue.Prices || [],
                                        variants: modelValue.Variants || [],
                                        imprinting: modelValue.Imprinting || {},
                                        shipping: modelValue.Shipping || {},
                                        supplier: modelValue.Supplier || {},
                                        attributes: modelValue.Attributes || {},
                                        warnings: modelValue.Warnings || [],
                                        certifications: modelValue.Certifications || []
                                    };
                                    scopeFound = true;
                                    break;
                                }
                            } catch (e) {
                                // Continue to next model
                            }
                        }
                    }
                }

                // Method 5: Try to extract from data attributes
                if (!scopeFound) {
                    var dataElements = document.querySelectorAll('[data-product]');
                    if (dataElements.length > 0) {
                        try {
                            var dataProduct = JSON.parse(dataElements[0].getAttribute('data-product'));
                            if (dataProduct) {
                                productData = {
                                    product: dataProduct || {},
                                    pricing: dataProduct.Prices || [],
                                    variants: dataProduct.Variants || [],
                                    imprinting: dataProduct.Imprinting || {},
                                    shipping: dataProduct.Shipping || {},
                                    supplier: dataProduct.Supplier || {},
                                    attributes: dataProduct.Attributes || {},
                                    warnings: dataProduct.Warnings || [],
                                    certifications: dataProduct.Certifications || []
                                };
                                scopeFound = true;
                            }
                        } catch (e) {
                            // Continue to next method
                        }
                    }
                }

                // Method 6: Try to extract from window object (some apps expose data here)
                if (!scopeFound) {
                    if (window.productData || window.Product || window.product) {
                        var windowData = window.productData || window.Product || window.product;
                        if (windowData && typeof windowData === 'object') {
                            productData = {
                                product: windowData || {},
                                pricing: windowData.Prices || [],
                                variants: windowData.Variants || [],
                                imprinting: windowData.Imprinting || {},
                                shipping: windowData.Shipping || {},
                                supplier: windowData.Supplier || {},
                                attributes: windowData.Attributes || {},
                                warnings: windowData.Warnings || [],
                                certifications: windowData.Certifications || []
                            };
                            scopeFound = true;
                        }
                    }
                }

                // Method 7: Enhanced - Try to extract from any AngularJS scope with product data
                if (!scopeFound && typeof angular !== 'undefined') {
                    try {
                        // Get all AngularJS scopes
                        var allScopes = [];
                        function collectAllScopes(scope) {
                            if (scope) {
                                allScopes.push(scope);
                                if (scope.$$childHead) {
                                    collectAllScopes(scope.$$childHead);
                                }
                                if (scope.$$nextSibling) {
                                    collectAllScopes(scope.$$nextSibling);
                                }
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

                return {
                    data: productData,
                    scopeFound: scopeFound,
                    availableScopes: {
                        angular: typeof angular !== 'undefined',
                        windowProduct: !!(window.productData || window.Product || window.product),
                        totalScopes: allScopes ? allScopes.length : 0
                    }
                };
            """
            )

            if angular_data.get("scopeFound"):
                logging.info("✅ Extracted AngularJS product data successfully")
                return angular_data.get("data", {})
            else:
                logging.warning(
                    f"⚠️ No AngularJS scope found. Available: {angular_data.get('availableScopes', {})}"
                )
                return {}

        except Exception as e:
            logging.warning(f"⚠️ Failed to extract AngularJS data: {e}")
            return {}

    def extract_comprehensive_pricing(self, detail_soup, angular_data):
        """Extract all pricing tables including variants and nested charges"""
        pricing_tables = []

        try:
            # Method 1: Extract from AngularJS data (preferred)
            if angular_data.get("pricing"):
                main_pricing = self.parse_angular_pricing(
                    angular_data["pricing"], "main"
                )
                pricing_tables.extend(main_pricing)

            # Extract variant pricing from AngularJS
            if angular_data.get("variants"):
                for variant in angular_data["variants"]:
                    if variant.get("Prices"):
                        variant_pricing = self.parse_angular_pricing(
                            variant["Prices"],
                            f"variant_{variant.get('Number', 'unknown')}",
                        )
                        pricing_tables.extend(variant_pricing)

            # Method 2: Extract from HTML pricing sections
            if not pricing_tables:
                pricing_tables = self.extract_pricing_from_html(detail_soup)

            # Method 3: Fallback to original table extraction
            if not pricing_tables:
                pricing_tables = self.extract_pricing_table()

            logging.info(f"✅ Extracted {len(pricing_tables)} pricing tables")
            return pricing_tables

        except Exception as e:
            logging.warning(f"⚠️ Error extracting comprehensive pricing: {e}")
            return self.extract_pricing_table()  # Fallback to original method

    def extract_pricing_from_html(self, detail_soup):
        """Extract pricing from HTML sections including AngularJS components"""
        pricing_tables = []

        try:
            # Method 1: Extract directly from AngularJS scope (preferred)
            pricing_data = self.driver.execute_script(
                """
                var pricing_tables = [];

                // Extract main product pricing
                if (typeof vm !== 'undefined' && vm && vm.product && vm.product.Prices) {
                    pricing_tables.push({
                        type: 'main_product',
                        data: vm.product.Prices
                    });
                }

                // Extract variant pricing
                if (typeof vm !== 'undefined' && vm && vm.product && vm.product.Variants) {
                    for (var i = 0; i < vm.product.Variants.length; i++) {
                        var variant = vm.product.Variants[i];
                        if (variant.Prices) {
                            pricing_tables.push({
                                type: 'variant_' + (variant.Number || i),
                                data: variant.Prices
                            });
                        }
                    }
                }

                return pricing_tables;
            """
            )

            if pricing_data:
                for table_info in pricing_data:
                    if table_info.get("data"):
                        parsed_pricing = self.parse_angular_pricing(
                            table_info["data"], table_info["type"]
                        )
                        pricing_tables.extend(parsed_pricing)

            # Method 2: Extract from rendered HTML components
            if not pricing_tables:
                pricing_sections = detail_soup.select(
                    '#pnlPricing, .pricing-section, [id*="pricing"], [class*="pricing"]'
                )

                for section in pricing_sections:
                    # Look for product-table-charges components
                    product_tables = section.select(
                        'product-table-charges, [ng-model*="Prices"], [ng-model*="pricing"]'
                    )

                    for table in product_tables:
                        # Extract data from ng-model attributes
                        ng_model = table.get("ng-model", "")
                        if "Prices" in ng_model or "pricing" in ng_model:
                            try:
                                # Execute JavaScript to get the data
                                pricing_data = self.driver.execute_script(
                                    f"""
                                    try {{
                                        return {ng_model} || [];
                                    }} catch(e) {{
                                        return [];
                                    }}
                                """
                                )

                                if pricing_data:
                                    model_name = ng_model.replace(
                                        "vm.product.", ""
                                    ).replace("vm.", "")
                                    parsed_pricing = self.parse_angular_pricing(
                                        pricing_data, f"html_{model_name}"
                                    )
                                    pricing_tables.extend(parsed_pricing)

                            except Exception as e:
                                logging.warning(
                                    f"⚠️ Could not extract pricing from {ng_model}: {e}"
                                )

                    # Also look for standard tables as fallback
                    tables = section.select("table")
                    for table in tables:
                        table_pricing = self.parse_html_table_pricing(table)
                        if table_pricing:
                            pricing_tables.extend(table_pricing)

            return pricing_tables

        except Exception as e:
            logging.warning(f"⚠️ Error extracting pricing from HTML: {e}")
            return []

    def parse_html_table_pricing(self, table):
        """Parse standard HTML table for pricing data"""
        pricing_tables = []

        try:
            rows = table.find_all("tr")
            if not rows or len(rows) < 2:
                return []

            # Find the header row with quantities
            header_row = rows[0]
            quantity_map = {}
            for i, th in enumerate(header_row.find_all(["th", "td"])):
                if i == 0:
                    continue  # Skip the first column
                try:
                    quantity = int(re.sub(r"[^0-9]", "", th.text))
                    if quantity > 0:
                        quantity_map[i] = quantity
                except (ValueError, TypeError):
                    continue

            if not quantity_map:
                return []

            # Process data rows
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
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

                        dc_elem = cell.find("small", class_="price-code") or cell.find(
                            "span", class_="price-code"
                        )
                        if dc_elem:
                            discount_code = dc_elem.get_text(strip=True).strip("()")

                        price_match = re.search(r"[\d.,]+\d", price_str)
                        if price_match:
                            try:
                                price = float(price_match.group().replace(",", ""))
                                breaks.append(
                                    {
                                        "quantity": quantity,
                                        "price": price,
                                        "discount_code": discount_code,
                                    }
                                )
                            except (ValueError, TypeError):
                                continue

                if breaks:
                    pricing_tables.append({"type": row_label, "breaks": breaks})

            return pricing_tables

        except Exception as e:
            logging.warning(f"⚠️ Error parsing HTML table pricing: {e}")
            return []

    def parse_angular_pricing(self, prices_data, table_type):
        """Parse AngularJS pricing data into structured format"""
        pricing_tables = []

        try:
            for price_item in prices_data:
                if isinstance(price_item, dict):
                    pricing_table = {
                        "type": price_item.get("Type", table_type),
                        "breaks": [],
                    }

                    # Extract price breaks
                    if price_item.get("Breaks"):
                        for break_item in price_item["Breaks"]:
                            if isinstance(break_item, dict):
                                pricing_table["breaks"].append(
                                    {
                                        "quantity": break_item.get("Quantity", 0),
                                        "price": break_item.get("Price", 0),
                                        "discount_code": break_item.get("DiscountCode"),
                                    }
                                )

                    pricing_tables.append(pricing_table)

            return pricing_tables
        except Exception as e:
            logging.warning(f"⚠️ Error parsing AngularJS pricing: {e}")
            return []

    def extract_comprehensive_imprint(self, detail_soup, angular_data):
        """Extract comprehensive imprint information including nested charges"""
        imprint_info = {"General": {}, "Methods": {}, "Services": {}, "Other": {}}

        try:
            # Method 1: Extract directly from AngularJS scope (preferred)
            imprint_data = self.driver.execute_script(
                """
                var imprint_info = {};

                if (typeof vm !== 'undefined' && vm && vm.product && vm.product.Imprinting) {
                    var imprinting = vm.product.Imprinting;

                    // Extract general info
                    imprint_info.General = {
                        Colors: imprinting.Colors || [],
                        Sizes: imprinting.Sizes || [],
                        Locations: imprinting.Locations || [],
                        FullColorProcess: imprinting.FullColorProcess,
                        Personalization: imprinting.Personalization,
                        SoldUnimprinted: imprinting.SoldUnimprinted
                    };

                    // Extract methods with charges
                    if (imprinting.Methods && imprinting.Methods.Values) {
                        imprint_info.Methods = {};
                        for (var i = 0; i < imprinting.Methods.Values.length; i++) {
                            var method = imprinting.Methods.Values[i];
                            imprint_info.Methods[method.Name || 'Method_' + i] = {
                                Description: method.Description || '',
                                Charges: method.Charges || []
                            };
                        }
                    }

                    // Extract services with nested charges
                    if (imprinting.Services && imprinting.Services.Values) {
                        imprint_info.Services = {};
                        for (var i = 0; i < imprinting.Services.Values.length; i++) {
                            var service = imprinting.Services.Values[i];
                            imprint_info.Services[service.Name || 'Service_' + i] = {
                                Description: service.Description || '',
                                Charges: service.Charges || []
                            };
                        }
                    }
                }

                return imprint_info;
            """
            )

            if imprint_data:
                imprint_info.update(imprint_data)

            # Method 2: Extract from AngularJS data (fallback)
            if not imprint_info["Methods"] and angular_data.get("imprinting"):
                imprint_data = angular_data["imprinting"]

                # Extract methods
                if imprint_data.get("Methods"):
                    for method in imprint_data["Methods"]:
                        method_name = method.get("Name", "Unknown Method")
                        imprint_info["Methods"][method_name] = {
                            "Description": method.get("Description", ""),
                            "Charges": self.extract_charges_from_angular(
                                method.get("Charges", [])
                            ),
                        }

                # Extract services with nested charges
                if imprint_data.get("Services", {}).get("Values"):
                    for service in imprint_data["Services"]["Values"]:
                        service_name = service.get("Name", "Unknown Service")
                        imprint_info["Services"][service_name] = {
                            "Description": service.get("Description", ""),
                            "Charges": self.extract_charges_from_angular(
                                service.get("Charges", [])
                            ),
                        }

                # Extract general info
                general_fields = [
                    "Colors",
                    "Sizes",
                    "Locations",
                    "FullColorProcess",
                    "Personalization",
                    "SoldUnimprinted",
                ]
                for field in general_fields:
                    if imprint_data.get(field):
                        imprint_info["General"][field] = imprint_data[field]

            # Method 3: Fallback to HTML extraction
            if not imprint_info["Methods"]:
                imprint_section = detail_soup.select_one("#pnlImprint")
                if imprint_section:
                    imprint_info = self.extract_imprint_from_html(imprint_section)

            logging.info("✅ Extracted comprehensive imprint information")
            return imprint_info

        except Exception as e:
            logging.warning(f"⚠️ Error extracting comprehensive imprint: {e}")
            return imprint_info

    def extract_charges_from_angular(self, charges_data):
        """Extract charge information from AngularJS data"""
        charges = []

        try:
            for charge in charges_data:
                if isinstance(charge, dict):
                    charges.append(
                        {
                            "name": charge.get("Name", ""),
                            "price": charge.get("Price", ""),
                            "description": charge.get("Description", ""),
                        }
                    )

            return charges
        except Exception as e:
            logging.warning(f"⚠️ Error extracting charges: {e}")
            return charges

    def extract_imprint_from_html(self, imprint_section):
        """Extract imprint information from HTML as fallback"""
        imprint_info = {"General": {}, "Methods": {}, "Services": {}, "Other": {}}

        try:
            # Extract basic imprint info
            for attr_div in imprint_section.select("div.product-attribute"):
                header_elem = attr_div.select_one(
                    "span.attribute-header, span.property-label"
                )
                if header_elem:
                    key = header_elem.get_text(strip=True).replace(":", "")
                    values = [
                        span.get_text(strip=True)
                        for span in attr_div.select("span.ng-binding")
                        if span.get_text(strip=True)
                    ]
                    if key and values:
                        imprint_info["General"][key] = (
                            values if len(values) > 1 else values[0]
                        )

            return imprint_info
        except Exception as e:
            logging.warning(f"⚠️ Error extracting imprint from HTML: {e}")
            return imprint_info

    def extract_comprehensive_production_info(self, detail_soup, angular_data):
        """Extract comprehensive production information"""
        production_info = {}

        try:
            # Extract from AngularJS data first
            if angular_data.get("product"):
                product_data = angular_data["product"]

                # Extract all available fields
                fields_to_extract = [
                    "Description",
                    "AdditionalInfo",
                    "TradeNames",
                    "Weight",
                    "Upc",
                    "IsAssembled",
                    "BatteryInfo",
                    "WarrantyInfo",
                    "Samples",
                ]

                for field in fields_to_extract:
                    if product_data.get(field):
                        production_info[field] = product_data[field]

                # Extract attributes (Colors, Sizes, Materials, etc.)
                if product_data.get("Attributes"):
                    for attr_type, attr_data in product_data["Attributes"].items():
                        if attr_data and attr_data.get("Values"):
                            production_info[f"{attr_type}"] = attr_data["Values"]

            # Fallback to HTML extraction
            options_section = detail_soup.select_one("#pnlOptions")
            if options_section:
                production_info.update(
                    self.extract_production_from_html(options_section)
                )

            logging.info("✅ Extracted comprehensive production information")
            return production_info

        except Exception as e:
            logging.warning(f"⚠️ Error extracting comprehensive production info: {e}")
            return {}

    def extract_production_from_html(self, options_section):
        """Extract production information from HTML as fallback"""
        production_info = {}

        try:
            for attr_div in options_section.select("div.product-attribute"):
                header_elem = attr_div.select_one("span.attribute-header")
                if header_elem:
                    key = header_elem.get_text(strip=True)
                    values = [
                        span.get_text(strip=True)
                        for span in attr_div.select("span.ng-binding")
                        if span.get_text(strip=True)
                    ]
                    if key and values:
                        production_info[key] = values if len(values) > 1 else values[0]

            return production_info
        except Exception as e:
            logging.warning(f"⚠️ Error extracting production from HTML: {e}")
            return production_info

    def extract_shipping_info(self, detail_soup, angular_data):
        """Extract shipping information"""
        shipping_info = {}

        try:
            # Extract from AngularJS data
            if angular_data.get("shipping"):
                shipping_data = angular_data["shipping"]

                # Extract shipping fields
                shipping_fields = [
                    "FOBPoints",
                    "Weight",
                    "PackageUnit",
                    "Options",
                    "Dimensions",
                ]
                for field in shipping_fields:
                    if shipping_data.get(field):
                        shipping_info[field] = shipping_data[field]

                # Extract package info
                if shipping_data.get("ItemsPerPackage"):
                    shipping_info["ItemsPerPackage"] = shipping_data["ItemsPerPackage"]

                # Extract plain box info
                if "PackageInPlainBox" in shipping_data:
                    shipping_info["PackageInPlainBox"] = shipping_data[
                        "PackageInPlainBox"
                    ]

            # Extract from HTML as fallback
            shipping_section = detail_soup.select_one("#pnlShipping")
            if shipping_section:
                shipping_info.update(self.extract_shipping_from_html(shipping_section))

            logging.info("✅ Extracted shipping information")
            return shipping_info

        except Exception as e:
            logging.warning(f"⚠️ Error extracting shipping info: {e}")
            return {}

    def extract_shipping_from_html(self, shipping_section):
        """Extract shipping information from HTML"""
        shipping_info = {}

        try:
            # Extract production time
            production_time_elem = shipping_section.select_one(
                'div[ng-repeat*="ProductionTime"]'
            )
            if production_time_elem:
                shipping_info["ProductionTime"] = production_time_elem.get_text(
                    strip=True
                )

            # Extract rush service
            rush_elem = shipping_section.select_one('p[ng-if*="HasRushService"]')
            if rush_elem:
                shipping_info["RushService"] = "Yes"

            # Extract country of origin
            origin_elem = shipping_section.select_one('p[ng-if*="Origin"]')
            if origin_elem:
                shipping_info["CountryOfOrigin"] = origin_elem.get_text(strip=True)

            return shipping_info
        except Exception as e:
            logging.warning(f"⚠️ Error extracting shipping from HTML: {e}")
            return shipping_info

    def extract_safety_compliance(self, detail_soup, angular_data):
        """Extract safety and compliance information"""
        safety_info = {}

        try:
            # Extract from AngularJS data
            if angular_data.get("warnings"):
                safety_info["Warnings"] = angular_data["warnings"]

            if angular_data.get("certifications"):
                safety_info["Certifications"] = angular_data["certifications"]

            # Extract from HTML as fallback
            safety_section = detail_soup.select_one("#pnlSafety")
            if safety_section:
                safety_info.update(self.extract_safety_from_html(safety_section))

            logging.info("✅ Extracted safety and compliance information")
            return safety_info

        except Exception as e:
            logging.warning(f"⚠️ Error extracting safety info: {e}")
            return {}

    def extract_safety_from_html(self, safety_section):
        """Extract safety information from HTML"""
        safety_info = {}

        try:
            # Extract Prop 65 warnings
            prop_warnings = safety_section.select('p[ng-repeat*="PROP"]')
            if prop_warnings:
                safety_info["Prop65Warnings"] = [
                    w.get_text(strip=True) for w in prop_warnings
                ]

            # Extract safety warnings
            safety_warnings = safety_section.select('p[ng-repeat*="SWCH"]')
            if safety_warnings:
                safety_info["SafetyWarnings"] = [
                    w.get_text(strip=True) for w in safety_warnings
                ]

            # Extract certifications
            cert_elem = safety_section.select_one('p[ng-if*="Certifications"]')
            if cert_elem:
                safety_info["Certifications"] = cert_elem.get_text(strip=True)

            return safety_info
        except Exception as e:
            logging.warning(f"⚠️ Error extracting safety from HTML: {e}")
            return safety_info

    def extract_supplier_info(self, detail_soup, angular_data):
        """Extract supplier information including ASINumber"""
        supplier_info = {}

        try:
            # Extract from AngularJS data
            if angular_data.get("supplier"):
                supplier_data = angular_data["supplier"]
                supplier_info.update(
                    {
                        "Name": supplier_data.get("Name", ""),
                        "Rating": supplier_data.get("Rating", ""),
                        "Email": supplier_data.get("Email", ""),
                        "Website": supplier_data.get("Website", ""),
                    }
                )

            # Extract from HTML (including ASINumber)
            supplier_section = detail_soup.select_one("#pnlSupplierInfo")
            if supplier_section:
                supplier_info.update(self.extract_supplier_from_html(supplier_section))

            logging.info("✅ Extracted supplier information")
            return supplier_info

        except Exception as e:
            logging.warning(f"⚠️ Error extracting supplier info: {e}")
            return {}

    def extract_supplier_from_html(self, supplier_section):
        """Extract supplier information from HTML including ASINumber"""
        supplier_info = {}

        try:
            # Extract supplier name
            name_elem = supplier_section.select_one(".supplier-name")
            if name_elem:
                supplier_info["Name"] = name_elem.get_text(strip=True)

            # Extract ASINumber
            asi_elem = supplier_section.select_one(".asi-num")
            if asi_elem:
                asi_text = asi_elem.get_text(strip=True)
                # Extract ASI number from "asi/61125" format
                asi_match = re.search(r"asi/(\d+)", asi_text)
                if asi_match:
                    supplier_info["ASINumber"] = asi_match.group(1)

            # Extract phone number
            phone_elem = supplier_section.select_one(".col-xs-6.text-right div")
            if phone_elem:
                supplier_info["Phone"] = phone_elem.get_text(strip=True)

            # Extract website
            website_elem = supplier_section.select_one('a[href*="http"]')
            if website_elem:
                supplier_info["Website"] = website_elem.get("href", "")

            # Extract fax
            fax_elem = supplier_section.select_one('div:-soup-contains("Fax:")')
            if fax_elem:
                fax_text = fax_elem.get_text(strip=True)
                fax_match = re.search(r"Fax:\s*([^)]+)", fax_text)
                if fax_match:
                    supplier_info["Fax"] = fax_match.group(1).strip()

            return supplier_info
        except Exception as e:
            logging.warning(f"⚠️ Error extracting supplier from HTML: {e}")
            return supplier_info

    def is_price(self, text):
        # Matches $7.88, 7.88, 2.70, etc.
        return bool(re.match(r"^\$?\d+(\.\d+)?$", text.strip()))

    def get_scraped_ids(self):
        scraped_ids = set()

        # Check the main output file
        if os.path.exists(self.OUTPUT_FILE):
            with open(self.OUTPUT_FILE, "r") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        # Try multiple ID fields to be more robust
                        if "ProductID" in data and data["ProductID"]:
                            scraped_ids.add(str(data["ProductID"]))
                        elif "id" in data and data["id"]:
                            scraped_ids.add(str(data["id"]))
                        elif "SourceURL" in data and data["SourceURL"]:
                            # Extract product ID from URL as fallback
                            import re

                            url_match = re.search(r"productID=(\d+)", data["SourceURL"])
                            if url_match:
                                scraped_ids.add(url_match.group(1))
                    except Exception:
                        continue

        # Also check the product index file if it exists
        index_file = os.path.join(
            os.path.dirname(self.OUTPUT_FILE), "product_index.json"
        )
        if os.path.exists(index_file):
            try:
                with open(index_file, "r") as f:
                    index_data = json.load(f)
                    for product_id in index_data.keys():
                        scraped_ids.add(str(product_id))
            except Exception as e:
                logging.warning(f"⚠️ Could not read product index: {e}")

        return scraped_ids

    def post_single_product_to_wordpress(self, product, api_url, api_key):
        """
        Send a single product immediately to WordPress for live streaming.
        """
        if not product:
            return
        if not api_url or not api_key:
            return
        # Prepare single product as JSONL
        jsonl_data = json.dumps(product) + "\n"
        files = {"file": ("single_product.jsonl", jsonl_data)}
        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            response = requests.post(api_url, files=files, headers=headers, timeout=10)
            response.raise_for_status()
            logging.info(f"✅ Live streamed single product to WordPress.")
        except Exception as e:
            logging.error(f"❌ Failed to live stream product to WordPress: {e}")

    def post_batch_to_wordpress(self, batch, api_url, api_key):
        """
        Send a batch of products to the WordPress REST API endpoint.
        """
        if not batch:
            return
        if not api_url or not api_key:
            logging.info(
                f"⚠️ WordPress integration not configured - saving {len(batch)} products locally only"
            )
            return
        # Prepare the batch as JSONL
        jsonl_data = "\n".join([json.dumps(product) for product in batch])
        files = {"file": ("batch.jsonl", jsonl_data)}
        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            response = requests.post(api_url, files=files, headers=headers, timeout=30)
            response.raise_for_status()
            logging.info(
                f"✅ Successfully posted batch of {len(batch)} products to WordPress."
            )
        except Exception as e:
            logging.error(f"❌ Failed to post batch to WordPress: {e}")

    def fetch_existing_products(self, api_url, api_key):
        """
        Fetch the list of existing products from the WordPress plugin.
        Returns a set of product_ids and a set of skus.
        Supports optional HTTP Basic Auth if WP_BASIC_AUTH_USER and WP_BASIC_AUTH_PASS are set.
        Uses WP_BASE_URL as the base for constructing endpoints if needed.
        """
        import os
        from requests.auth import HTTPBasicAuth

        wp_base_url = os.getenv("WP_BASE_URL")
        headers = {"X-API-Key": api_key}
        username = os.getenv("WP_BASIC_AUTH_USER")
        password = os.getenv("WP_BASIC_AUTH_PASS")
        auth = HTTPBasicAuth(username, password) if username and password else None
        # If api_url is not provided, construct it from WP_BASE_URL
        if not api_url and wp_base_url:
            api_url = (
                wp_base_url.rstrip("/")
                + "/wp-json/promostandards-importer/v1/existing-products"
            )
        try:
            resp = requests.get(api_url, headers=headers, auth=auth, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            product_ids = set()
            skus = set()
            for prod in data.get("products", []):
                if prod.get("product_id"):
                    product_ids.add(str(prod["product_id"]))
                if prod.get("sku"):
                    skus.add(str(prod["sku"]))
            return product_ids, skus
        except Exception as e:
            logging.error(f"Failed to fetch existing products: {e}")
            return set(), set()

    def scrape_all_details(self, force_relogin=False, mode="scrape"):
        self.login(force_relogin=force_relogin)
        product_links = self.read_product_links()
        scraped_ids = self.get_scraped_ids()
        # Heartbeat file logic
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        heartbeat_file = os.path.join(data_dir, "scraper_heartbeat.txt")

        def update_heartbeat(status_text):
            with open(heartbeat_file, "w") as hb:
                hb.write(json.dumps({"status": status_text, "timestamp": time.time()}))

        update_heartbeat("running: start")  # Initial heartbeat
        last_heartbeat = time.time()

        # --- Smart Filtering: Fetch existing products from WP if configured ---
        api_url = os.getenv("WP_API_URL")
        api_key = os.getenv("WP_API_KEY")
        existing_product_ids = set()
        existing_skus = set()
        if api_url and api_key:
            # Use /existing-products endpoint
            if api_url.endswith("/upload"):
                existing_url = api_url.replace("/upload", "/existing-products")
            else:
                existing_url = api_url.rstrip("/") + "/existing-products"
            logging.info(f"Fetching existing products from {existing_url}")
            existing_product_ids, existing_skus = self.fetch_existing_products(
                existing_url, api_key
            )

        # --- Filter links based on mode ---
        links_to_process = []
        skipped_duplicates = 0
        for link in product_links:
            product_id = str(link.get("id"))
            # Always skip if already scraped in this run
            if product_id in scraped_ids:
                skipped_duplicates += 1
                continue
            if mode == "scrape":
                # Only scrape if not in store
                if product_id not in existing_product_ids:
                    links_to_process.append(link)
                else:
                    skipped_duplicates += 1
            elif mode == "override":
                # Scrape all
                links_to_process.append(link)
            elif mode == "sync":
                # --- Sync mode: check last_modified ---
                # Find the store's last_modified for this product
                store_last_modified = None
                # We'll need to fetch the last_modified from the store's /existing-products
                # For efficiency, build a dict of product_id -> last_modified at fetch time
                if not hasattr(self, "_existing_products_meta"):
                    # Build a dict for quick lookup
                    self._existing_products_meta = {}
                    api_url = os.getenv("WP_API_URL")
                    api_key = os.getenv("WP_API_KEY")
                    if api_url and api_key:
                        if api_url.endswith("/upload"):
                            existing_url = api_url.replace(
                                "/upload", "/existing-products"
                            )
                        else:
                            existing_url = api_url.rstrip("/") + "/existing-products"
                        headers = {"Authorization": f"Bearer {api_key}"}
                        try:
                            resp = requests.get(
                                existing_url, headers=headers, timeout=30
                            )
                            resp.raise_for_status()
                            data = resp.json()
                            for prod in data.get("products", []):
                                pid = str(prod.get("product_id"))
                                if pid:
                                    self._existing_products_meta[pid] = prod.get(
                                        "last_modified"
                                    )
                        except Exception as e:
                            logging.error(
                                f"Failed to fetch existing products for sync mode: {e}"
                            )
                store_last_modified = self._existing_products_meta.get(product_id)
                # Get the candidate's last_modified (if available in link)
                candidate_last_modified = link.get("last_modified")
                if store_last_modified and candidate_last_modified:
                    # Compare ISO8601 strings
                    if candidate_last_modified > store_last_modified:
                        links_to_process.append(link)
                    else:
                        skipped_duplicates += 1
                else:
                    # Fallback: if not in store, add; else skip
                    if product_id not in existing_product_ids:
                        links_to_process.append(link)
                    else:
                        skipped_duplicates += 1
            else:
                # Default: behave like scrape
                if product_id not in existing_product_ids:
                    links_to_process.append(link)
                else:
                    skipped_duplicates += 1

        if self.limit:
            original_count = len(links_to_process)
            links_to_process = links_to_process[: self.limit]

        logging.info(
            f"🚀 Starting to scrape {len(links_to_process)} products (skipped {skipped_duplicates} duplicates, mode={mode})..."
        )

        # --- Hardcoded Robust Rate Limiting ---
        max_requests_per_minute = 25
        # Smaller batch size for GitHub Actions to ensure batch files are created
        batch_size = 5 if os.getenv("GITHUB_ACTIONS") == "true" else 15
        batch_pause = 5
        min_delay = 1.5
        request_times = collections.deque()

        batch = []
        api_url = os.getenv("WP_API_URL")  # Optional - can be empty
        api_key = os.getenv("WP_API_KEY")  # Optional - can be empty

        # Log WordPress integration status
        if api_url and api_key:
            logging.info("✅ WordPress integration configured")
        else:
            logging.info(
                "⚠️ WordPress integration not configured - data will be saved locally only"
            )

        def rate_limit_pause():
            now = time.time()
            # Remove requests older than 60 seconds
            while request_times and now - request_times[0] > 60:
                request_times.popleft()
            if len(request_times) >= max_requests_per_minute:
                wait_time = 60 - (now - request_times[0])
                if wait_time > 0 and wait_time < 30:  # never sleep too long
                    time.sleep(wait_time)
            # Enforce minimum delay between requests
            if request_times and now - request_times[-1] < min_delay:
                delay = min_delay - (now - request_times[-1])
                if delay > 0 and delay < 10:
                    time.sleep(delay)
            request_times.append(time.time())

        def save_batch_to_file(batch_data, batch_num=None):
            """Save batch to file with better naming"""
            if not batch_data:
                return

            timestamp = int(time.time())
            if batch_num is None:
                batch_num = timestamp

            batch_filename = f"batch_{batch_num}_{len(batch_data)}.jsonl"
            try:
                with open(batch_filename, "w", encoding="utf-8") as batch_file:
                    for product in batch_data:
                        batch_file.write(json.dumps(product) + "\n")

                # Also save to data directory for backup
                data_batch_filename = os.path.join("espscraper/data", batch_filename)
                with open(data_batch_filename, "w", encoding="utf-8") as batch_file:
                    for product in batch_data:
                        batch_file.write(json.dumps(product) + "\n")

            except Exception as e:
                logging.error(f"❌ Failed to save batch file: {e}")

        # Open file in append mode to add new products to the end
        with open(self.OUTPUT_FILE, "a", encoding="utf-8") as f_out:
            batch_counter = 0
            products_scraped = 0
            for i, link_info in enumerate(links_to_process):
                url = link_info.get("url")
                product_id = link_info.get("id")
                if not url or not product_id:
                    continue
                # Update heartbeat every 20 seconds
                if time.time() - last_heartbeat > 20:
                    update_heartbeat(
                        f"running: product {i+1} of {len(links_to_process)}"
                    )
                    last_heartbeat = time.time()

                logging.info(
                    f"--- ({i+1}/{len(links_to_process)}) Processing Product ID: {product_id}"
                )

                # --- Rate limiting before each request ---
                rate_limit_pause()

                # Simple scraping without window switching
                try:
                    # Load the product page directly
                    self.driver.get(url)
                    # Wait for the page to load with a more flexible approach
                    try:
                        WebDriverWait(self.driver, 30).until(  # Increased from 15 to 30
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "#productDetailsMain")
                            )
                        )
                    except Exception as e:
                        # Try alternative selectors
                        alternative_selectors = [
                            "h3.text-primary",
                            ".product-info",
                            "span.product-number",
                            "body",
                        ]
                        element_found = False
                        for selector in alternative_selectors:
                            try:
                                WebDriverWait(
                                    self.driver, 10
                                ).until(  # Increased from 5 to 10
                                    EC.presence_of_element_located(
                                        (By.CSS_SELECTOR, selector)
                                    )
                                )
                                element_found = True
                                break
                            except:
                                continue
                        if not element_found:
                            continue

                    scraped_data = self.scrape_product_detail_page()
                    scraped_data["SourceURL"] = url

                    # Append to the main output file (adds to end of file)
                    f_out.write(json.dumps(scraped_data) + "\n")
                    f_out.flush()  # Ensure data is written immediately
                    products_scraped += 1
                    batch.append(scraped_data)
                    logging.info(f"   ✅ Scraped: {scraped_data.get('Name', 'N/A')}")

                    # LIVE STREAMING: Send immediately to WordPress
                    if api_url and api_key:
                        self.post_single_product_to_wordpress(
                            scraped_data, api_url, api_key
                        )
                        logging.info(f"   🚀 Live streamed to WordPress")

                    # Create batch files more frequently
                    if len(batch) >= batch_size:
                        batch_counter += 1
                        save_batch_to_file(batch, batch_counter)

                        # Post batch to WordPress (as backup)
                        self.post_batch_to_wordpress(batch, api_url, api_key)
                        batch = []

                except Exception as e:
                    logging.error(
                        f"❌ FAILED to scrape page for Product ID {product_id}. Error: {e}"
                    )
                    # Simple error recovery - just restart the driver
                    try:
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
                    logging.info(f"⏸️ Batch pause after {batch_size} products...")
                    time.sleep(batch_pause)

            # Save final batch if any products remain
            if batch:
                batch_counter += 1
                save_batch_to_file(batch, batch_counter)

                # Post final batch to WordPress (as backup, since products were already live streamed)
                self.post_batch_to_wordpress(batch, api_url, api_key)
        # Final heartbeat update
        update_heartbeat("finished")

        # Log final summary
        logging.info(
            f"✅ Scraping completed: {products_scraped} new products added to {self.OUTPUT_FILE}"
        )

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

                product_links_map = {
                    str(link.get("id")): link for link in product_links
                }
                scraped_ids = self.get_scraped_ids()

                with open(self.OUTPUT_FILE, "a", encoding="utf-8") as f_out:
                    for product_id in failed_ids:
                        if product_id in scraped_ids:
                            continue

                        link_info = product_links_map.get(product_id)
                        if not link_info:
                            continue

                        url = link_info.get("url")

                        try:
                            self.driver.get(url)

                            # Wait for page load with better error handling
                            try:
                                WebDriverWait(
                                    self.driver, 30
                                ).until(  # Increased from 15 to 30
                                    EC.presence_of_element_located(
                                        (By.CSS_SELECTOR, "#productDetailsMain")
                                    )
                                )
                            except Exception as e:
                                # Try alternative selectors
                                alternative_selectors = [
                                    "h3.text-primary",
                                    ".product-info",
                                    "span.product-number",
                                    "body",
                                ]
                                element_found = False
                                for selector in alternative_selectors:
                                    try:
                                        WebDriverWait(
                                            self.driver, 10
                                        ).until(  # Increased from 5 to 10
                                            EC.presence_of_element_located(
                                                (By.CSS_SELECTOR, selector)
                                            )
                                        )
                                        element_found = True
                                        break
                                    except:
                                        continue
                                if not element_found:
                                    continue

                            scraped_data = self.scrape_product_detail_page()
                            if scraped_data:
                                scraped_data["SourceURL"] = url
                                f_out.write(json.dumps(scraped_data) + "\n")
                                f_out.flush()
                        except Exception as e:
                            logging.error(
                                f"❌ [RETRY] FAILED to scrape page for Product ID {product_id}. Error: {e}"
                            )

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
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of products to scrape.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chrome in headless mode (no window).",
    )
    parser.add_argument(
        "--force-relogin",
        action="store_true",
        help="Force update session/cookies with fresh login.",
    )
    parser.add_argument(
        "--output-file", type=str, default=None, help="Output file for scraped details."
    )
    parser.add_argument(
        "--links-file", type=str, default=None, help="Input links file (JSONL)."
    )
    parser.add_argument(
        "--overwrite-output",
        action="store_true",
        help="Overwrite output file before scraping (do not resume).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Number of products to process in this batch.",
    )
    parser.add_argument(
        "--batch-number", type=int, default=None, help="Batch number (0-based)."
    )
    parser.add_argument(
        "--no-aggressive-cleanup",
        action="store_true",
        help="Disable aggressive Chrome process cleanup (keeps your browser windows open).",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=5,
        help="Maximum number of retries for individual product scraping (default: 5)",
    )
    parser.add_argument(
        "--batch-retry-limit",
        type=int,
        default=2,
        help="Maximum number of batch retry attempts for failed products (default: 2)",
    )
    parser.add_argument(
        "--debug-mode",
        action="store_true",
        help="Enable real-time connection monitoring.",
    )
    args = parser.parse_args()
    if args.overwrite_output:
        output_file = args.output_file or os.getenv(
            "DETAILS_OUTPUT_FILE", "final_product_details.jsonl"
        )
        open(output_file, "w").close()  # Truncate the file
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
        debug_mode=args.debug_mode,
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
        logging.info(
            f"🔢 Processing batch {args.batch_number} (products {start} to {end-1})"
        )
    scraper.scrape_all_details(force_relogin=args.force_relogin)


if __name__ == "__main__":
    main()
