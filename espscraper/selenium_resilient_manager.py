from selenium import webdriver
from selenium.common.exceptions import WebDriverException, TimeoutException, SessionNotCreatedException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging
import psutil
import os
import signal
import traceback
from datetime import datetime

class SeleniumResilientManager:
    def __init__(self, headless=False, setup_callback=None, max_retries=3, connection_timeout=30, aggressive_cleanup=True):
        self.headless = headless
        self.setup_callback = setup_callback  # Function to call for custom setup (e.g., cookies)
        self.max_retries = max_retries
        self.connection_timeout = connection_timeout
        self.aggressive_cleanup = aggressive_cleanup  # Whether to kill Chrome processes
        self.driver = None
        self.driver_pid = None
        self.chrome_pids = set()  # Track Chrome PIDs created by this instance
        self._start_driver()

    def _kill_chrome_processes(self):
        """Kill only Chrome processes created by this WebDriver instance, not user browser windows"""
        try:
            # First, kill tracked Chrome PIDs from this instance
            for pid in self.chrome_pids.copy():
                try:
                    proc = psutil.Process(pid)
                    if proc.is_running() and 'chrome' in proc.name().lower():
                        print(f"🧹 Cleaning up tracked Chrome process (PID: {pid})")
                        proc.terminate()
                        time.sleep(0.5)
                        if proc.is_running():
                            proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
                finally:
                    self.chrome_pids.discard(pid)
            
            # Also kill any orphaned WebDriver Chrome processes (fallback)
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and 'chrome' in proc.info['name'].lower():
                        # Only kill Chrome processes that are likely WebDriver instances
                        cmdline = proc.info.get('cmdline', [])
                        if any(arg in ' '.join(cmdline).lower() for arg in [
                            '--remote-debugging-port',
                            '--disable-web-security',
                            '--disable-features=vizdisplaycompositor',
                            '--disable-ipc-flooding-protection',
                            '--disable-renderer-backgrounding',
                            '--disable-background-timer-throttling',
                            '--disable-backgrounding-occluded-windows',
                            '--disable-client-side-phishing-detection',
                            '--disable-component-extensions-with-background-pages',
                            '--disable-default-apps',
                            '--disable-domain-reliability',
                            '--disable-features=translateui',
                            '--disable-hang-monitor',
                            '--disable-prompt-on-repost',
                            '--disable-sync',
                            '--force-color-profile=srgb',
                            '--metrics-recording-only',
                            '--no-first-run',
                            '--safebrowsing-disable-auto-update',
                            '--enable-automation',
                            '--password-store=basic',
                            '--use-mock-keychain',
                            '--memory-pressure-off',
                            '--max_old_space_size=4096'
                        ]):
                            if proc.pid != os.getpid():  # Don't kill ourselves
                                print(f"🧹 Cleaning up orphaned WebDriver Chrome process (PID: {proc.pid})")
                                proc.terminate()
                                time.sleep(0.5)
                                if proc.is_running():
                                    proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except Exception as e:
            print(f"⚠️ Warning: Could not clean up WebDriver Chrome processes: {e}")

    def _start_driver(self):
        """Start a new Chrome driver with enhanced stability options"""
        try:
            # Kill any existing Chrome processes first (only if aggressive cleanup is enabled)
            if self.aggressive_cleanup:
                self._kill_chrome_processes()
            
            options = Options()
            options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                                 "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Enhanced stability options
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins")
            options.add_argument("--disable-images")  # Reduce memory usage
            # options.add_argument("--disable-javascript")  # Temporarily disable JS if needed
            options.add_argument("--disable-web-security")
            options.add_argument("--allow-running-insecure-content")
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
            
            # Enhanced headless mode options for better compatibility
            if self.headless:
                options.add_argument("--headless=new")  # Use new headless mode
                options.add_argument("--window-size=1920,1080")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--remote-debugging-port=9222")
                # Stealth options to avoid detection
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)
                # Additional stealth options
                options.add_argument("--disable-web-security")
                options.add_argument("--allow-running-insecure-content")
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
            else:
                options.add_argument("--start-maximized")
            
            # Set memory limits
            options.add_argument("--memory-pressure-off")
            options.add_argument("--max_old_space_size=4096")
            
            # Create service with timeout
            service = Service(ChromeDriverManager().install())
            service.start_error_message = "ChromeDriver failed to start"
            
            # Create driver with timeout
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # Store the driver PID for cleanup
            if hasattr(self.driver, 'service') and hasattr(self.driver.service, 'process'):
                self.driver_pid = self.driver.service.process.pid
                # Track Chrome processes created by this WebDriver instance
                try:
                    for proc in psutil.process_iter(['pid', 'ppid', 'name']):
                        if (proc.info['name'] and 'chrome' in proc.info['name'].lower() and 
                            proc.info['ppid'] == self.driver_pid):
                            self.chrome_pids.add(proc.pid)
                except Exception:
                    pass
            
            # Set page load timeout
            self.driver.set_page_load_timeout(self.connection_timeout)
            self.driver.implicitly_wait(10)
            
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
                
            print("✅ Chrome driver started successfully")
            
        except Exception as e:
            print(f"❌ Failed to start Chrome driver: {e}")
            self._kill_chrome_processes()
            raise

    def _is_driver_alive(self):
        """Check if the driver is still responsive"""
        try:
            if not self.driver:
                return False
            # Try a simple command to test if driver is alive
            self.driver.current_url
            return True
        except (WebDriverException, Exception):
            return False

    def get_driver(self):
        """Get the current driver, restart if dead"""
        if not self._is_driver_alive():
            print("⚠️ Driver is dead, restarting...")
            self.restart_driver()
        return self.driver

    def restart_driver(self):
        """Safely restart the driver with cleanup"""
        try:
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass
                self.driver = None
        except Exception:
            pass
        
        # Kill any remaining Chrome processes (only if aggressive cleanup is enabled)
        if self.aggressive_cleanup:
            self._kill_chrome_processes()
        
        # Wait a bit before restarting
        time.sleep(2)
        
        # Start new driver
        self._start_driver()

    def resilient_action(self, action, *args, **kwargs):
        """
        Runs the given action(driver, *args, **kwargs) with enhanced retry logic.
        If the driver crashes, it restarts and retries.
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                # Ensure driver is alive before each attempt
                if not self._is_driver_alive():
                    print(f"⚠️ Driver dead on attempt {attempt+1}, restarting...")
                    self.restart_driver()
                    time.sleep(3)  # Give more time for restart
                
                return action(self.driver, *args, **kwargs)
                
            except (WebDriverException, TimeoutException, SessionNotCreatedException) as e:
                last_exception = e
                print(f"⚠️ Selenium driver error on attempt {attempt+1}/{self.max_retries}: {e}")
                
                # Log detailed error information for debugging
                error_info = self._log_connection_error(e, attempt+1, f"resilient_action_attempt_{attempt+1}")
                
                # More aggressive cleanup on connection errors
                if ("Connection refused" in str(e) or 
                    "Failed to establish a new connection" in str(e) or
                    "timeout: Timed out receiving message from renderer" in str(e) or
                    "ERR_CONNECTION_REFUSED" in str(e) or
                    "ERR_NAME_NOT_RESOLVED" in str(e)):
                    print("🔧 Connection error detected - performing aggressive cleanup...")
                    if self.aggressive_cleanup:
                        self._kill_chrome_processes()
                    time.sleep(5)  # Longer wait for connection issues
                
                if attempt < self.max_retries - 1:
                    print(f"🔄 Restarting driver and retrying...")
                    self.restart_driver()
                    time.sleep(3)
                else:
                    print(f"❌ All retry attempts exhausted")
                    
            except Exception as e:
                last_exception = e
                print(f"⚠️ Unexpected error on attempt {attempt+1}/{self.max_retries}: {e}")
                # Log unexpected errors too
                self._log_connection_error(e, attempt+1, f"unexpected_error_attempt_{attempt+1}")
                if attempt < self.max_retries - 1:
                    self.restart_driver()
                    time.sleep(2)
        
        raise RuntimeError(f"Selenium driver failed after {self.max_retries} retries. Last error: {last_exception}")

    def quit(self):
        """Safely quit the driver and cleanup processes"""
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass
        finally:
            self.driver = None
            if self.aggressive_cleanup:
                self._kill_chrome_processes()

    def _log_connection_error(self, error, attempt, context=""):
        """Log detailed information about connection errors for debugging"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_info = {
            'timestamp': timestamp,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'attempt': attempt,
            'context': context,
            'driver_alive': self._is_driver_alive(),
            'chrome_processes': self._get_chrome_process_info()
        }
        
        # Log to file for analysis
        with open("connection_errors.log", "a") as f:
            f.write(f"=== CONNECTION ERROR ===\n")
            f.write(f"Time: {error_info['timestamp']}\n")
            f.write(f"Error Type: {error_info['error_type']}\n")
            f.write(f"Error Message: {error_info['error_message']}\n")
            f.write(f"Attempt: {error_info['attempt']}\n")
            f.write(f"Context: {error_info['context']}\n")
            f.write(f"Driver Alive: {error_info['driver_alive']}\n")
            f.write(f"Chrome Processes: {error_info['chrome_processes']}\n")
            f.write(f"Traceback:\n{traceback.format_exc()}\n")
            f.write(f"======================\n\n")
        
        print(f"🔍 Connection error logged to connection_errors.log")
        return error_info

    def _get_chrome_process_info(self):
        """Get information about Chrome processes for debugging"""
        chrome_info = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info']):
                try:
                    if proc.info['name'] and 'chrome' in proc.info['name'].lower():
                        cmdline = ' '.join(proc.info.get('cmdline', []))
                        memory = proc.info.get('memory_info', {})
                        chrome_info.append({
                            'pid': proc.pid,
                            'name': proc.info['name'],
                            'cmdline': cmdline[:200] + '...' if len(cmdline) > 200 else cmdline,
                            'memory_mb': memory.get('rss', 0) / 1024 / 1024 if memory else 0
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception:
            pass
        return chrome_info 