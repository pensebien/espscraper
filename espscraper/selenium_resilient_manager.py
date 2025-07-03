from selenium import webdriver
from selenium.common.exceptions import WebDriverException, TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

class SeleniumResilientManager:
    def __init__(self, headless=False, setup_callback=None, max_retries=3):
        self.headless = headless
        self.setup_callback = setup_callback  # Function to call for custom setup (e.g., cookies)
        self.max_retries = max_retries
        self.driver = None
        self._start_driver()

    def _start_driver(self):
        options = Options()
        options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        if self.headless:
            options.add_argument("--headless")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
        else:
            options.add_argument("--start-maximized")
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
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
        if self.setup_callback:
            self.setup_callback(self.driver)

    def get_driver(self):
        return self.driver

    def restart_driver(self):
        try:
            self.driver.quit()
        except Exception:
            pass
        self._start_driver()

    def resilient_action(self, action, *args, **kwargs):
        """
        Runs the given action(driver, *args, **kwargs) with retries.
        If the driver crashes, it restarts and retries.
        """
        for attempt in range(self.max_retries):
            try:
                return action(self.driver, *args, **kwargs)
            except (WebDriverException, TimeoutException) as e:
                print(f"⚠️ Selenium driver error: {e}. Restarting driver (attempt {attempt+1}/{self.max_retries})...")
                self.restart_driver()
                time.sleep(2)
        raise RuntimeError("Selenium driver failed after multiple retries.")

    def quit(self):
        try:
            self.driver.quit()
        except Exception:
            pass 