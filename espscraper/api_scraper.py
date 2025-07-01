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
from dotenv import load_dotenv
import argparse

# --- CONFIGURATION ---
load_dotenv() # Load variables from .env file

USERNAME = os.getenv("ESP_USERNAME")
PASSWORD = os.getenv("ESP_PASSWORD")

if not USERNAME or not PASSWORD:
    print("❌ Error: ESP_USERNAME and ESP_PASSWORD must be set in the .env file.")
    exit()


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
        self.OUTPUT_FILE = os.getenv("OUTPUT_FILE", "api_scraped_links.jsonl")
        self.TOTAL_PAGES_TO_SCRAPE = int(os.getenv("TOTAL_PAGES_TO_SCRAPE", 100))
        if not all([self.USERNAME, self.PASSWORD, self.SEARCH_API_URL, self.GOTO_PAGE_API_URL, self.PRODUCTS_URL, self.PRODUCT_URL_TEMPLATE]):
            raise ValueError("All required .env variables must be set.")

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

    def collect_product_links(self, force_relogin=False, pages=None):
        page_key, search_id = self.session_manager.selenium_login_and_get_session_data(
            self.USERNAME, self.PASSWORD, self.PRODUCTS_URL, force_relogin=force_relogin
        )
        if not page_key or not search_id:
            print("❌ Could not get pageKey or searchId. Aborting.")
            return
        session = requests.Session()
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json;charset=UTF-8',
            'Referer': self.PRODUCTS_URL,
            'User-Agent': 'Mozilla/5.0',
        }
        session.headers.update(headers)
        cookies, _, _ = self.session_manager.load_state()
        if cookies:
            for cookie in cookies:
                session.cookies.set(cookie['name'], cookie['value'], domain=cookie.get('domain'))
        self.session = session
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
        try:
            response = self.session.post(self.SEARCH_API_URL, json=search_payload, timeout=30)
            response.raise_for_status()
            initial_data = response.json()
            search_state_str = initial_data.get('d', {}).get('SearchState')
            if not search_state_str:
                print("❌ Could not extract SearchState from initial response. Aborting.")
                return
            all_products = self.extract_products_from_json(initial_data)
            seen_ids = {p['id'] for p in all_products}
        except Exception as e:
            print(f"❌ Initial SearchProduct request failed: {e}")
            return
        total_pages = pages if pages is not None else self.TOTAL_PAGES_TO_SCRAPE
        for page_num in range(2, total_pages + 1):
            goto_payload = {
                "page": page_num, "adApplicationCode": "ESPO", "appCode": "WESP", "appVersion": "4.1.0",
                "extraParams": f"SearchId={search_id}", "pageKey": page_key, "searchState": search_state_str,
                "stats": ""
            }
            try:
                response = self.session.post(self.GOTO_PAGE_API_URL, json=goto_payload, timeout=30)
                response.raise_for_status()
                page_data = response.json()
                new_products = self.extract_products_from_json(page_data)
                if not new_products:
                    break
                unique_new_products = []
                for product in new_products:
                    if product['id'] not in seen_ids:
                        unique_new_products.append(product)
                        seen_ids.add(product['id'])
                all_products.extend(unique_new_products)
                time.sleep(1)
            except Exception as e:
                print(f"❌ Request for page {page_num} failed: {e}")
                break
        with open(self.OUTPUT_FILE, 'w') as f_out:
            for product in all_products:
                f_out.write(json.dumps(product) + '\n')
        print(f"✅ Scraping complete. Total unique products found: {len(all_products)}")
        print(f"Data saved to '{self.OUTPUT_FILE}'.")

def get_authenticated_session_data(driver):
    """
    After login, extracts all necessary session data, including the Authorization token.
    """
    print("✅ Login successful. Extracting initial session data...")
    
    # Wait for a key element to ensure the page is loaded
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "hdnPageStateKey")))
    
    # 1. Get Cookies
    cookies = driver.get_cookies()
    requests_cookies = {cookie['name']: cookie['value'] for cookie in cookies}
    print(f"🍪 Extracted {len(requests_cookies)} cookies.")
    
    # 2. Get pageKey
    page_key = driver.find_element(By.ID, "hdnPageStateKey").get_attribute('value')
    print(f"🔑 Extracted pageKey: {page_key}")

    # 3. Get SearchId from the final URL
    search_id = None
    try:
        current_url = driver.current_url
        parsed_url = urllib.parse.urlparse(current_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        if 'SearchID' in query_params:
            search_id = query_params['SearchID'][0]
            print(f"🆔 Extracted SearchID from URL: {search_id}")
    except Exception as e:
        print(f"❌ Error extracting SearchID from URL: {e}")

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
        print(f"❌ Error extracting Auth Token: {e}")

    return requests_cookies, page_key, search_id

def get_authenticated_cookies():
    """
    Uses Selenium to log into the website and returns the session cookies
    and the initial pageKey.
    """
    print("🤖 Launching Selenium to get authenticated session...")
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

        print("🔒 Login page detected. Logging in...")
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "asilogin_UserName")))
        
        driver.find_element(By.ID, "asilogin_UserName").send_keys(USERNAME)
        driver.find_element(By.ID, "asilogin_Password").send_keys(PASSWORD)
        driver.find_element(By.ID, "btnLogin").click()

        # NEW: Handle the "already logged in" alert
        try:
            print("⏳ Waiting for potential login alert...")
            WebDriverWait(driver, 10).until(EC.alert_is_present())
            alert = driver.switch_to.alert
            print(f"⚠️ Alert detected: {alert.text}")
            alert.accept()
            print("✅ Alert accepted.")
        except Exception:
            print("ℹ️ No login alert appeared, continuing.")
        
        # Wait for login to complete by waiting for an element on the products page
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".prod-count")))
        
        return get_authenticated_session_data(driver)

    except Exception as e:
        print(f"❌ Selenium login failed: {e}")
        return None, None, None
    finally:
        driver.quit()
        print("🤖 Selenium browser closed.")

def create_payload_template_if_not_exists():
    """Creates a template for the JSON payload if it doesn't exist."""
    if not os.path.exists(PAYLOAD_TEMPLATE_FILE):
        print(f"📄 Creating '{PAYLOAD_TEMPLATE_FILE}'...")
        template = {
          "page": 1,
          "adApplicationCode": "ESPO",
          "appCode": "WESP",
          "appVersion": "4.1.0",
          "extraParams": "SearchId=782072784",
          "pageKey": "SK-7c4c2a78-93da-438d-a0de-58b983ce41fd",
          "searchState": "{\"SelectedDimensions\":[{\"ID\":\"74\",\"DimensionInput\":\"asi\",\"Dimension\":\"SuppAsiNo\",\"Name\":\"61125\",\"Value\":null,\"Count\":null,\"ImageId\":null,\"MultiSelect\":false,\"Delimiter\":\"^\",\"ReturnAll\":false}],\"PriceType\":0,\"From\":null,\"To\":null,\"Quantity\":null,\"SearchAnyTerms\":null,\"SearchNotTerms\":null,\"SearchPhrase\":null,\"SearchTerms\":null,\"SearchSeqNo\":5,\"Page\":1,\"RecordOffset\":0,\"UniqueID\":\"a5373f10-9a9b-48b3-b223-9969baf6c4d0\",\"SearchId\":832780353,\"IsNewSearch\":false,\"PV\":null,\"PVSelection\":[],\"MarketSegment\":\"USAALL\",\"ProductionTime\":null,\"IncludeRushTime\":false,\"ProductNo\":null,\"ProductList\":null,\"AsiNoList\":null,\"CanadianSuppliers\":false,\"VideoId\":0,\"UiSearchMode\":\"Quick\"}",
          "stats": "tab=list,moduleCode=PRDRES,moduleVersion=5.0.0,moduleVersionId=499,appId=11621,moduleInstance=271774,pageId=128755,referrerModule=,refModSufx=,appVersion=4.1.0,page=ProductResults,referrerPage=ESPHomepage,refPgId=128757"
        }
        with open(PAYLOAD_TEMPLATE_FILE, 'w') as f:
            json.dump(template, f, indent=2)
    else:
        print(f"📄 Using existing '{PAYLOAD_TEMPLATE_FILE}'.")

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
    args = parser.parse_args()
    session_manager = SessionManager()
    scraper = ApiScraper(session_manager)
    scraper.collect_product_links(force_relogin=args.force_relogin, pages=args.pages)

if __name__ == "__main__":
    main() 