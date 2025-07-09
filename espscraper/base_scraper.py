import os
# Don't load .env file in production - use environment variables directly
# from dotenv import load_dotenv

class BaseScraper:
    def __init__(self, session_manager=None):
        # load_dotenv()  # Don't load .env in production
        self.session_manager = session_manager
        self.session = None  # For requests.Session or Selenium driver, as needed
        self.verbose = True

    def log(self, message):
        if self.verbose:
            print(message)

    def set_verbose(self, verbose=True):
        self.verbose = verbose

    def load_env(self):
        # load_dotenv()  # Don't load .env in production
        # Optionally, load more config here
        pass 