import os
from dotenv import load_dotenv

class BaseScraper:
    def __init__(self, session_manager=None):
        load_dotenv()
        self.session_manager = session_manager
        self.session = None  # For requests.Session or Selenium driver, as needed
        self.verbose = True

    def log(self, message):
        if self.verbose:
            print(message)

    def set_verbose(self, verbose=True):
        self.verbose = verbose

    def load_env(self):
        load_dotenv()
        # Optionally, load more config here 