from espscraper.base_scraper import BaseScraper
from espscraper.session_manager import SessionManager
import requests
import json
import time
from bs4 import BeautifulSoup
import re
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import urllib.parse
import argparse
import math
import logging

# --- CONFIGURATION ---
# Don't load .env file in production - use environment variables directly
# load_dotenv() # Load variables from .env file

USERNAME = os.getenv("ESP_USERNAME")
PASSWORD = os.getenv("ESP_PASSWORD")

# Don't exit in production - let the validation handle it
# if not USERNAME or not PASSWORD:
#     logging.error("❌ Error: ESP_USERNAME and ESP_PASSWORD must be set in the .env file.")
#     exit()

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


class ApiScraper(BaseScraper):
    def __init__(self, session_manager):
        super().__init__(session_manager)
        self.load_env()
        self.USERNAME = os.getenv("ESP_USERNAME")
        self.PASSWORD = os.getenv("ESP_PASSWORD")
        self.SEARCH_API_URL = os.getenv("SEARCH_API_URL")
        self.GOTO_PAGE_API_URL = os.getenv("GOTO_PAGE_API_URL")
        self.PRODUCTS_URL = os.getenv("PRODUCTS_URL")
        self.PRODUCT_URL_TEMPLATE = os.getenv("PRODUCT_URL_TEMPLATE")
        if not self.PRODUCT_URL_TEMPLATE:
            # Use ESP Web product details URL as default if not set
            self.PRODUCT_URL_TEMPLATE = (
                "https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0"
                "&page=ProductDetails&referrerPage=ProductResults&referrerModule=PRDRES&refModSufx=Generic"
                "&PCUrl=1&productID={product_id}&autoLaunchVS=0&tab=list"
            )
        # Ensure data directory exists
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(data_dir, exist_ok=True)
        self.OUTPUT_FILE = os.getenv("OUTPUT_FILE", os.path.join(data_dir, "api_scraped_links.jsonl"))
        self.TOTAL_PAGES_TO_SCRAPE = int(os.getenv("TOTAL_PAGES_TO_SCRAPE", 100))
        # Improved required variable check
        required_vars = {
            "ESP_USERNAME": self.USERNAME,
            "ESP_PASSWORD": self.PASSWORD,
            "SEARCH_API_URL": self.SEARCH_API_URL,
            "GOTO_PAGE_API_URL": self.GOTO_PAGE_API_URL,
            "PRODUCTS_URL": self.PRODUCTS_URL,
        }
        missing = [k for k, v in required_vars.items() if not v]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    def extract_products_from_json(self, response_data):
        products = []
        if not response_data or 'd' not in response_data:
            return products
        try:
            data_d = response_data['d'] if isinstance(response_data['d'], dict) else json.loads(response_data['d'])
        except (json.JSONDecodeError, TypeError):
            data_d = response_data['d']
        product_results = data_d.get('Results', [])
        for product in product_results:
            product_id = product.get('ProductId') or product.get('Id')
            if product_id:
                product_url = self.PRODUCT_URL_TEMPLATE.format(product_id=product_id)
                products.append({
                    "url": product_url,
                    "id": product_id,
                    "name": product.get("ProductName") or product.get("Name", "N/A"),
                })
        return products

    def collect_product_links(self, force_relogin=False, pages=None, limit=None, new_only=False, detail_output_file=None, resume_missing=False):
        import os
        checkpoint_file = self.OUTPUT_FILE.replace('.jsonl', '.checkpoint.txt')
        metadata_file = self.OUTPUT_FILE.replace('.jsonl', '.meta.json')
        batch_size = 3  # Reduced batch size for better rate limiting
        delay = 2  # Increased delay between page requests
        batch_delay = 5  # Longer delay between batches
        max_requests_per_minute = 20  # Rate limiting
        request_times = []

        def check_rate_limit():
            """Check if we're within rate limits"""
            current_time = time.time()
            # Remove requests older than 1 minute
            request_times[:] = [t for t in request_times if current_time - t < 60]
            if len(request_times) >= max_requests_per_minute:
                wait_time = 60 - (current_time - request_times[0])
                if wait_time > 0:
                    logging.warning(f"⏸️ Rate limit reached. Waiting {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                    return check_rate_limit()  # Recursive check
            return True

        def make_rate_limited_request(session, url, payload):
            """Make a request with rate limiting"""
            check_rate_limit()
            request_times.append(time.time())
            return session.post(url, json=payload, timeout=30)

        def extract_json_objects(text):
            decoder = json.JSONDecoder()
            idx = 0
            length = len(text)
            while idx < length:
                try:
                    obj, end = decoder.raw_decode(text, idx)
                    yield obj
                    idx = end
                    while idx < length and text[idx] in ' \r\n\t':
                        idx += 1
                except json.JSONDecodeError:
                    break
        # Load already-scraped product IDs if new_only is set
        already_scraped_ids = set()
        if new_only and detail_output_file and os.path.exists(detail_output_file):
            with open(detail_output_file, 'r') as f:
                for i, line in enumerate(f, 1):
                    try:
                        data = json.loads(line)
                        pid = data.get('productId') or data.get('ProductID') or data.get('id')
                        if pid:
                            already_scraped_ids.add(str(pid))
                    except Exception as e:
                        found_any = False
                        for obj in extract_json_objects(line):
                            pid = obj.get('productId') or obj.get('ProductID') or obj.get('id')
                            if pid:
                                already_scraped_ids.add(str(pid))
                                found_any = True
                        if found_any:
                            logging.warning(f"Line {i} in {detail_output_file} contained multiple JSON objects. Used fallback parser.")
                        else:
                            logging.error(f"Skipping invalid JSON line {i} in {detail_output_file}: {e} | Content: {line.strip()}")
            logging.info(f"🔎 Loaded {len(already_scraped_ids)} already-scraped product IDs from {detail_output_file}")
        # Load all collected IDs from output file (for deduplication)
        collected_ids = set()
        if os.path.exists(self.OUTPUT_FILE):
            with open(self.OUTPUT_FILE, 'r') as f:
                for i, line in enumerate(f, 1):
                    try:
                        data = json.loads(line)
                        pid = data.get('id') or data.get('productId') or data.get('ProductID')
                        if pid:
                            collected_ids.add(str(pid))
                    except Exception as e:
                        found_any = False
                        for obj in extract_json_objects(line):
                            pid = obj.get('id') or obj.get('productId') or obj.get('ProductID')
                            if pid:
                                collected_ids.add(str(pid))
                                found_any = True
                        if found_any:
                            logging.warning(f"Line {i} in {self.OUTPUT_FILE} contained multiple JSON objects. Used fallback parser.")
                        else:
                            logging.error(f"Skipping invalid JSON line {i} in {self.OUTPUT_FILE}: {e} | Content: {line.strip()}")
        # Always fetch first page for session and ResultsTotal
        def get_session_and_ids():
            cookies, page_key, search_id = self.session_manager.load_state()
            session = requests.Session()
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'application/json;charset=UTF-8',
                'Referer': self.PRODUCTS_URL,
                'User-Agent': 'Mozilla/5.0',
            }
            session.headers.update(headers)
            if cookies:
                for cookie in cookies:
                    session.cookies.set(cookie['name'], cookie['value'], domain=cookie.get('domain'))
            return session, page_key, search_id
        session, page_key, search_id = get_session_and_ids()
        search_payload = {
            "extraParams": f"SearchId={search_id}",
            "type": "SavedSearch",
            "adApplicationCode": "ESPO",
            "appCode": "WESP",
            "appVersion": "4.1.0",
            "pageKey": page_key,
            "searchState": "",
            "stats": ""
        }
        # Fetch first page for ResultsTotal and ResultsPerPage
        try:
            response = make_rate_limited_request(session, self.SEARCH_API_URL, search_payload)
            if response.status_code in (401, 403):
                raise Exception("Session not authenticated (status code)")
            initial_data = response.json()
            logging.info("🔎 First page API response:")
            search_state_str = initial_data.get('d', {}).get('SearchState')
            if not search_state_str:
                raise Exception("No SearchState in response (possible login required)")
            results_per_page = initial_data['d'].get('ResultsPerPage', 22)
            results_total = initial_data['d'].get('ResultsTotal', 0)
            if results_total:
                logging.info(f"📊 Total products available: {results_total}")
            else:
                logging.warning("⚠️ Warning: resultsTotal not found in API response.")
            try:
                total_pages_dynamic = math.ceil(results_total / results_per_page) if results_per_page else 1
            except Exception:
                total_pages_dynamic = self.TOTAL_PAGES_TO_SCRAPE
            # Update metadata file with latest resultsTotal
            try:
                with open(metadata_file, 'w') as meta_f:
                    json.dump({
                        'ResultsPerPage': results_per_page,
                        'resultsTotal': results_total,
                        'totalPages': total_pages_dynamic
                    }, meta_f, indent=2)
            except Exception as meta_e:
                logging.warning(f"⚠️ Could not write metadata file: {meta_e}")
        except Exception as e:
            logging.warning(f"⚠️ Saved session failed or expired: {e}. Launching Selenium login...")
            page_key, search_id = self.session_manager.selenium_login_and_get_session_data(
                self.USERNAME, self.PASSWORD, self.PRODUCTS_URL, force_relogin=True
            )
            if not page_key or not search_id:
                logging.error("❌ Could not get pageKey or searchId after login. Aborting.")
                return
            session, _, _ = get_session_and_ids()
            search_payload["pageKey"] = page_key
            search_payload["extraParams"] = f"SearchId={search_id}"
            try:
                response = make_rate_limited_request(session, self.SEARCH_API_URL, search_payload)
                response.raise_for_status()
                initial_data = response.json()
                logging.info("🔎 First page API response:")
                search_state_str = initial_data.get('d', {}).get('SearchState')
                if not search_state_str:
                    logging.error("❌ Could not extract SearchState from initial response. Aborting.")
                    return
                results_per_page = initial_data['d'].get('ResultsPerPage', 22)
                results_total = initial_data['d'].get('ResultsTotal', 0)
                if results_total:
                    logging.info(f"📊 Total products available: {results_total}")
                else:
                    logging.warning("⚠️ Warning: resultsTotal not found in API response.")
                try:
                    total_pages_dynamic = math.ceil(results_total / results_per_page) if results_per_page else 1
                except Exception:
                    total_pages_dynamic = self.TOTAL_PAGES_TO_SCRAPE
                # Update metadata file with latest resultsTotal
                try:
                    with open(metadata_file, 'w') as meta_f:
                        json.dump({
                            'ResultsPerPage': results_per_page,
                            'resultsTotal': results_total,
                            'totalPages': total_pages_dynamic
                        }, meta_f, indent=2)
                except Exception as meta_e:
                    logging.warning(f"⚠️ Could not write metadata file: {meta_e}")
            except Exception as e2:
                logging.error(f"❌ Initial SearchProduct request failed after login: {e2}")
                return
        # Helper function to fetch and write new links for a page
        def fetch_and_write_page(page_num, total_pages, results_total):
            goto_payload = {
                "page": page_num, "adApplicationCode": "ESPO", "appCode": "WESP", "appVersion": "4.1.0",
                "extraParams": f"SearchId={search_id}", "pageKey": page_key, "searchState": search_state_str,
                "stats": ""
            }
            try:
                response = make_rate_limited_request(session, self.GOTO_PAGE_API_URL, goto_payload)
                response.raise_for_status()
                page_data = response.json()
                new_products = self.extract_products_from_json(page_data)
                if not new_products:
                    return 0
                page_new_links = 0
                for product in new_products:
                    pid = product.get('id') or product.get('productId') or product.get('ProductID')
                    if new_only and pid and str(pid) in already_scraped_ids:
                        continue  # skip already scraped
                    if pid and str(pid) in collected_ids:
                        continue  # skip already collected in output file
                    with open(self.OUTPUT_FILE, 'a') as f_out:
                        f_out.write(json.dumps(product) + '\n')
                    collected_ids.add(str(pid))
                    page_new_links += 1
                logging.info(f"✅ Page {page_num} complete. {page_new_links} new products written. Total collected: {len(collected_ids)}/{results_total}")
                return page_new_links
            except Exception as e:
                logging.error(f"❌ Request for page {page_num} failed: {e}")
                return 0
        # Main collection logic
        new_links_collected = 0
        pages_processed = set()
        total_pages = total_pages_dynamic
        if resume_missing:
            # Resume from checkpoint page + 1
            if os.path.exists(checkpoint_file):
                with open(checkpoint_file, 'r') as f:
                    try:
                        last_page = int(f.read().strip())
                        start_page = last_page + 1
                        logging.info(f"🔄 Resuming from page {start_page} (last completed: {last_page}) [RESUME-MISSING MODE]")
                    except Exception:
                        start_page = 1
            else:
                start_page = 1
            current_page = start_page
            while new_links_collected < (limit if limit is not None else results_total) and current_page <= total_pages:
                batch_end = min(current_page + batch_size, total_pages + 1)
                for page_num in range(current_page, batch_end):
                    if page_num in pages_processed:
                        continue
                    pages_processed.add(page_num)
                    page_new_links = fetch_and_write_page(page_num, total_pages, results_total)
                    new_links_collected += page_new_links
                    time.sleep(delay)
                    # Save checkpoint after each page
                    with open(checkpoint_file, 'w') as f:
                        f.write(str(page_num))
                    if (limit is not None and new_links_collected >= limit) or len(collected_ids) >= results_total:
                        logging.warning(f"⚠️ Limit of {limit} reached, or all products collected.")
                        logging.info(f"✅ Link collection complete up to page {page_num}.")
                        logging.info(f"Links saved to '{self.OUTPUT_FILE}'. Checkpoint saved to '{checkpoint_file}'. Metadata saved to '{metadata_file}'.")
                        logging.info(f"✅ Collected {new_links_collected} new product links.")
                        return {'all_links_collected': False, 'new_links_collected': new_links_collected}
                current_page = batch_end
                time.sleep(batch_delay)
            logging.info(f"✅ Link collection complete up to page {current_page-1}.")
            logging.info(f"Links saved to '{self.OUTPUT_FILE}'. Checkpoint saved to '{checkpoint_file}'. Metadata saved to '{metadata_file}'.")
            logging.info(f"✅ Collected {new_links_collected} new product links.")
            return {'all_links_collected': False, 'new_links_collected': new_links_collected}
        else:
            # Default to new-only mode (fetch from top)
            for page_num in [1, 2]:
                if page_num > total_pages:
                    break
                if page_num in pages_processed:
                    continue
                pages_processed.add(page_num)
                page_new_links = fetch_and_write_page(page_num, total_pages, results_total)
                new_links_collected += page_new_links
                time.sleep(delay)
                # Save checkpoint after each page
                with open(checkpoint_file, 'w') as f:
                    f.write(str(page_num))
                if (limit is not None and new_links_collected >= limit) or len(collected_ids) >= results_total:
                    logging.warning(f"⚠️ Limit of {limit} reached, or all products collected.")
                    logging.info(f"✅ Link collection complete up to page {page_num}.")
                    logging.info(f"Links saved to '{self.OUTPUT_FILE}'. Checkpoint saved to '{checkpoint_file}'. Metadata saved to '{metadata_file}'.")
                    logging.info(f"✅ Collected {new_links_collected} new product links.")
                    return {'all_links_collected': False, 'new_links_collected': new_links_collected}
            current_page = 3
            while new_links_collected < (limit if limit is not None else results_total) and current_page <= total_pages:
                batch_end = min(current_page + batch_size, total_pages + 1)
                for page_num in range(current_page, batch_end):
                    if page_num in pages_processed:
                        continue
                    pages_processed.add(page_num)
                    page_new_links = fetch_and_write_page(page_num, total_pages, results_total)
                    new_links_collected += page_new_links
                    time.sleep(delay)
                    # Save checkpoint after each page
                    with open(checkpoint_file, 'w') as f:
                        f.write(str(page_num))
                    if (limit is not None and new_links_collected >= limit) or len(collected_ids) >= results_total:
                        logging.warning(f"⚠️ Limit of {limit} reached, or all products collected.")
                        logging.info(f"✅ Link collection complete up to page {page_num}.")
                        logging.info(f"Links saved to '{self.OUTPUT_FILE}'. Checkpoint saved to '{checkpoint_file}'. Metadata saved to '{metadata_file}'.")
                        logging.info(f"✅ Collected {new_links_collected} new product links.")
                        return {'all_links_collected': False, 'new_links_collected': new_links_collected}
                current_page = batch_end
                time.sleep(batch_delay)
            logging.info(f"✅ Link collection complete up to page {current_page-1}.")
            logging.info(f"Links saved to '{self.OUTPUT_FILE}'. Checkpoint saved to '{checkpoint_file}'. Metadata saved to '{metadata_file}'.")
            logging.info(f"✅ Collected {new_links_collected} new product links.")
            return {'all_links_collected': False, 'new_links_collected': new_links_collected}

def get_authenticated_session_data(driver):
    """
    After login, extracts all necessary session data, including the Authorization token.
    """
    logging.info("✅ Login successful. Extracting initial session data...")
    
    # Wait for a key element to ensure the page is loaded
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "hdnPageStateKey")))
    
    # 1. Get Cookies
    cookies = driver.get_cookies()
    requests_cookies = {cookie['name']: cookie['value'] for cookie in cookies}
    logging.info(f"🍪 Extracted {len(requests_cookies)} cookies.")
    
    # 2. Get pageKey
    page_key = driver.find_element(By.ID, "hdnPageStateKey").get_attribute('value')
    logging.info(f"🔑 Extracted pageKey: {page_key}")

    # 3. Get SearchId from the final URL
    search_id = None
    try:
        current_url = driver.current_url
        parsed_url = urllib.parse.urlparse(current_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        if 'SearchID' in query_params:
            search_id = query_params['SearchID'][0]
            logging.info(f"🆔 Extracted SearchID from URL: {search_id}")
    except Exception as e:
        logging.error(f"❌ Error extracting SearchID from URL: {e}")

    # 4. Get Authorization Token from JavaScript variable
    auth_token = None
    try:
        # The debug file showed this token in the 'asi.app._tenantToken' variable.
        # Note: This is a different token from the Authorization header, but it's
        # the most likely candidate for a session-specific API token.
        # Let's try extracting the Authorization header directly from the JS context if possible
        # For now, let's assume no extra auth header is needed beyond the cookie.
        # The 'Authorization' header in the text file seems to be a red herring.
        pass
    except Exception as e:
        logging.error(f"❌ Error extracting Auth Token: {e}")

    return requests_cookies, page_key, search_id

def get_authenticated_cookies():
    """
    Uses Selenium to log into the website and returns the session cookies
    and the initial pageKey.
    """
    logging.info("🤖 Launching Selenium to get authenticated session...")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    try:
        driver.get(PRODUCTS_URL)
        time.sleep(3)

        logging.info("🔒 Login page detected. Logging in...")
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "asilogin_UserName")))
        
        driver.find_element(By.ID, "asilogin_UserName").send_keys(USERNAME)
        driver.find_element(By.ID, "asilogin_Password").send_keys(PASSWORD)
        driver.find_element(By.ID, "btnLogin").click()

        # NEW: Handle the "already logged in" alert
        try:
            logging.info("⏳ Waiting for potential login alert...")
            WebDriverWait(driver, 10).until(EC.alert_is_present())
            alert = driver.switch_to.alert
            logging.warning(f"⚠️ Alert detected: {alert.text}")
            alert.accept()
            logging.info("✅ Alert accepted.")
        except Exception:
            logging.info("ℹ️ No login alert appeared, continuing.")
        
        # Wait for login to complete by waiting for an element on the products page
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".prod-count")))
        
        return get_authenticated_session_data(driver)

    except Exception as e:
        logging.error(f"❌ Selenium login failed: {e}")
        return None, None, None
    finally:
        driver.quit()
        logging.info("🤖 Selenium browser closed.")

def extract_links_from_html(html_content):
    """Parses HTML to find product links and update dates."""
    soup = BeautifulSoup(html_content, 'html.parser')
    products = []
    
    # The API returns a list of product divs
    product_divs = soup.select('.prod-container')
    
    for div in product_divs:
        link_tag = div.select_one('.prod-title a')
        update_date_tag = div.select_one('.last-update .ng-binding')
        
        if link_tag and 'href' in link_tag.attrs:
            # Construct the full URL
            base_url = "https://espweb.asicentral.com"
            url = link_tag['href']
            if not url.startswith('http'):
                url = base_url + url
            
            update_date = update_date_tag.text.strip() if update_date_tag else "N/A"
            
            products.append({
                "URL": url,
                "UpdateDate": update_date
            })
    return products

def format_stats_object(stats_obj):
    """Formats the stats dictionary into the required string format."""
    if not isinstance(stats_obj, dict):
        return ""
    # The order might matter, so we should try to match the original order if possible,
    # but for now, this is a good first step.
    return ",".join([f"{key}={value}" for key, value in stats_obj.items()])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pages', type=int, default=None, help='Number of pages to scrape')
    parser.add_argument('--force-relogin', action='store_true', help='Force a fresh Selenium login')
    parser.add_argument('--limit', type=int, default=None, help='Number of product links to collect (not pages)')
    parser.add_argument('--new-only', action='store_true', help='Collect only new product links from the top (pages 1, 2, etc.)')
    parser.add_argument('--resume-missing', action='store_true', help='Resume from checkpoint and continue collecting links from where you left off')
    parser.add_argument('--detail-output-file', help='File containing already scraped product IDs')
    args = parser.parse_args()
    session_manager = SessionManager()
    scraper = ApiScraper(session_manager)
    status = scraper.collect_product_links(
        force_relogin=args.force_relogin,
        pages=args.pages,
        limit=args.limit,
        new_only=args.new_only,
        detail_output_file=args.detail_output_file,
        resume_missing=args.resume_missing
    )
    if status and status.get('all_links_collected'):
        logging.info("All links already collected. You may proceed to detail scraping.")
    elif status:
        logging.info(f"New links collected: {status.get('new_links_collected', 0)}")

if __name__ == "__main__":
    main() 