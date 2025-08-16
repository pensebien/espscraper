import json
import os
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import urllib.parse
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


class SessionManager:
    def __init__(
        self,
        cookie_file="tmp/session_cookies.json",
        domain=".asicentral.com",
        state_file="tmp/session_state.json",
        headless=False,
    ):
        self.cookie_file = cookie_file
        self.domain = domain
        self.state_file = state_file
        self.headless = headless
        # Ensure tmp directory exists
        tmp_dir = os.path.dirname(self.cookie_file) or "tmp"
        os.makedirs(tmp_dir, exist_ok=True)

    def save_state(self, cookies, page_key, search_id):
        state = {"cookies": cookies, "pageKey": page_key, "searchId": search_id}
        with open(self.state_file, "w") as f:
            json.dump(state, f)
        logging.info(f"✅ Session state saved to {self.state_file}")

    def load_state(self):
        if os.path.exists(self.state_file):
            with open(self.state_file, "r") as f:
                state = json.load(f)
            return state.get("cookies"), state.get("pageKey"), state.get("searchId")
        return None, None, None

    def login_and_save_cookies(self, driver):
        """
        After logging in with Selenium, call this to save cookies to file.
        """
        cookies = driver.get_cookies()
        with open(self.cookie_file, "w") as f:
            json.dump(cookies, f)
        logging.info(f"✅ Cookies saved to {self.cookie_file}")

    def get_authenticated_session(self):
        """
        Returns a requests.Session() with cookies loaded from file.
        """
        session = requests.Session()
        if not os.path.exists(self.cookie_file):
            raise FileNotFoundError(
                f"Cookie file {self.cookie_file} not found. Please run Selenium login first."
            )
        with open(self.cookie_file, "r") as f:
            cookies = json.load(f)
        for cookie in cookies:
            # Only set cookies for the correct domain
            if self.domain in cookie.get("domain", ""):
                session.cookies.set(
                    cookie["name"], cookie["value"], domain=cookie.get("domain")
                )
        return session

    def clear_cookies(self):
        """
        Deletes the cookie file (for forced re-login).
        """
        if os.path.exists(self.cookie_file):
            os.remove(self.cookie_file)
            logging.info(f"🗑️ Deleted cookie file {self.cookie_file}")
        else:
            logging.info(f"No cookie file to delete at {self.cookie_file}")
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
            logging.info(f"🗑️ Deleted state file {self.state_file}")

    def selenium_login_and_get_session_data(
        self,
        username,
        password,
        products_url,
        search_api_url=None,
        force_relogin=False,
        driver=None,
    ):
        """
        Automates Selenium login, saves cookies, and extracts pageKey and searchId.
        Returns (pageKey, searchId). Uses saved state if available and not forced.
        If search_api_url is provided, will check session validity before reusing.
        If driver is provided, uses that driver instead of creating a new one.
        """
        import requests

        if not force_relogin:
            cookies, page_key, search_id = self.load_state()
            if cookies and page_key and search_id:
                # Session validity check
                if search_api_url:
                    session = requests.Session()
                    for cookie in cookies:
                        if self.domain in cookie.get("domain", ""):
                            session.cookies.set(
                                cookie["name"],
                                cookie["value"],
                                domain=cookie.get("domain"),
                            )
                    payload = {
                        "extraParams": f"SearchId={search_id}",
                        "type": "SavedSearch",
                        "adApplicationCode": "ESPO",
                        "appCode": "WESP",
                        "appVersion": "4.1.0",
                        "pageKey": page_key,
                        "searchState": "",
                        "stats": "",
                    }
                    try:
                        resp = session.post(search_api_url, json=payload, timeout=10)
                        if resp.status_code == 200 and "d" in resp.json():
                            with open(self.cookie_file, "w") as f:
                                json.dump(cookies, f)
                            logging.info(
                                f"✅ Loaded and validated session state from {self.state_file}"
                            )
                            return page_key, search_id
                        else:
                            logging.warning("⚠️ Saved session invalid, will relogin.")
                    except Exception as e:
                        logging.warning(
                            f"⚠️ Session validity check failed: {e}. Will relogin."
                        )
                else:
                    with open(self.cookie_file, "w") as f:
                        json.dump(cookies, f)
                    logging.info(f"✅ Loaded session state from {self.state_file}")
                    return page_key, search_id

        # Otherwise, do Selenium login
        logging.info("🤖 Launching Selenium to get authenticated session...")

        # Use provided driver or create new one
        should_quit_driver = False
        if driver is None:
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
            # Use unique user data directory to avoid conflicts in CI
            import tempfile
            import os
            import time

            # Create a more unique identifier with timestamp and process ID
            unique_id = f"{int(time.time())}_{os.getpid()}"
            user_data_dir = os.path.join(
                tempfile.gettempdir(), f"chrome_user_data_{unique_id}"
            )
            options.add_argument(f"--user-data-dir={user_data_dir}")
            options.add_argument(
                "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            # Add retry mechanism for Chrome driver creation
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    driver = webdriver.Chrome(
                        service=Service(ChromeDriverManager().install()), options=options
                    )
                    should_quit_driver = True
                    logging.info(f"✅ Chrome driver created successfully on attempt {attempt + 1}")
                    break
                except Exception as e:
                    if "user data directory is already in use" in str(e) and attempt < max_retries - 1:
                        logging.warning(f"⚠️ Chrome user data directory conflict on attempt {attempt + 1}, retrying...")
                        time.sleep(2)  # Wait before retry
                        # Update user data directory for retry
                        unique_id = f"{int(time.time())}_{os.getpid()}_{attempt}"
                        user_data_dir = os.path.join(tempfile.gettempdir(), f"chrome_user_data_{unique_id}")
                        options.add_argument(f"--user-data-dir={user_data_dir}")
                    else:
                        raise e

        try:
            driver.get(products_url)
            time.sleep(3)
            logging.info("🔒 Login page detected. Logging in...")
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "asilogin_UserName"))
            )
            driver.find_element(By.ID, "asilogin_UserName").send_keys(username)
            driver.find_element(By.ID, "asilogin_Password").send_keys(password)
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
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.ID, "hdnPageStateKey"))
            )
            cookies = driver.get_cookies()
            with open(self.cookie_file, "w") as f:
                json.dump(cookies, f)
            page_key = driver.find_element(By.ID, "hdnPageStateKey").get_attribute(
                "value"
            )
            current_url = driver.current_url
            parsed_url = urllib.parse.urlparse(current_url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            search_id = (
                query_params["SearchID"][0] if "SearchID" in query_params else None
            )
            self.save_state(cookies, page_key, search_id)
            logging.info(
                f"✅ Selenium login complete. pageKey: {page_key}, searchId: {search_id}"
            )
            return page_key, search_id
        except Exception as e:
            logging.exception(f"❌ Selenium login failed: {e}")
            return None, None
        finally:
            if should_quit_driver:
                driver.quit()
                logging.info("🤖 Selenium browser closed.")
                # Clean up temporary user data directory
                try:
                    import shutil

                    if "user_data_dir" in locals():
                        shutil.rmtree(user_data_dir, ignore_errors=True)
                        logging.info(
                            f"🧹 Cleaned up temporary Chrome user data directory: {user_data_dir}"
                        )
                except Exception as e:
                    logging.warning(
                        f"⚠️ Failed to clean up Chrome user data directory: {e}"
                    )

    def login(self):
        """Simple login method for testing"""
        try:
            username = os.getenv("ESP_USERNAME")
            password = os.getenv("ESP_PASSWORD")
            products_url = os.getenv("PRODUCTS_URL")

            if not all([username, password, products_url]):
                logging.warning("❌ Missing environment variables")
                return False

            page_key, search_id = self.selenium_login_and_get_session_data(
                username, password, products_url
            )
            return page_key is not None and search_id is not None
        except Exception as e:
            logging.exception(f"❌ Login failed: {e}")
            return False

    def quit(self):
        """Clean up method"""
        pass
