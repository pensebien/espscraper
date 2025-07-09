#!/usr/bin/env python3
"""
Production configuration for ESP Scraper
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Production settings
PRODUCTION_CONFIG = {
    # Selenium settings
    'HEADLESS': True,  # Always headless in production
    'MAX_RETRIES': 3,  # Reduced retries for faster failure
    'BATCH_RETRY_LIMIT': 1,  # Minimal retry for failed products
    'PAGE_LOAD_TIMEOUT': 30,
    'IMPLICIT_WAIT': 10,
    
    # Memory optimization
    'DISABLE_IMAGES': True,
    'DISABLE_EXTENSIONS': True,
    'DISABLE_PLUGINS': True,
    'MEMORY_LIMIT': '4096',  # 4GB memory limit
    
    # Rate limiting
    'DELAY_BETWEEN_REQUESTS': 2,  # seconds
    'DELAY_BETWEEN_PAGES': 1,  # seconds
    
    # Error handling
    'AGGRESSIVE_CLEANUP': False,  # Don't kill user browsers
    'DEBUG_MODE': False,  # Disable debug in production
    
    # Data settings
    'BATCH_SIZE': 50,  # Process 50 products per batch
    'CHECKPOINT_INTERVAL': 10,  # Save checkpoint every 10 products
    
    # Logging
    'LOG_LEVEL': 'INFO',
    'LOG_FILE': 'log/scraper.log',
    
    # File paths
    'DATA_DIR': 'espscraper/data',
    'TMP_DIR': 'tmp',
    'LOG_DIR': 'log',
    
    # Output files
    'LINKS_FILE': 'espscraper/data/api_scraped_links.jsonl',
    'DETAILS_FILE': 'espscraper/data/final_product_details.jsonl',
    'CHECKPOINT_FILE': 'espscraper/data/api_scraped_links.checkpoint.txt',
    'METADATA_FILE': 'espscraper/data/api_scraped_links.meta.json',
    'FAILED_PRODUCTS_FILE': 'failed_products.txt',
    'CONNECTION_ERRORS_FILE': 'connection_errors.log'
}

# Chrome options for production
PRODUCTION_CHROME_OPTIONS = [
    "--headless=new",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-extensions",
    "--disable-plugins",
    "--disable-images",
    "--disable-web-security",
    "--disable-features=VizDisplayCompositor",
    "--disable-ipc-flooding-protection",
    "--disable-renderer-backgrounding",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-client-side-phishing-detection",
    "--disable-component-extensions-with-background-pages",
    "--disable-default-apps",
    "--disable-domain-reliability",
    "--disable-features=TranslateUI",
    "--disable-hang-monitor",
    "--disable-prompt-on-repost",
    "--disable-sync",
    "--force-color-profile=srgb",
    "--metrics-recording-only",
    "--no-first-run",
    "--safebrowsing-disable-auto-update",
    "--enable-automation",
    "--password-store=basic",
    "--use-mock-keychain",
    "--memory-pressure-off",
    "--max_old_space_size=4096",
    "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

# Environment variables required for production
REQUIRED_ENV_VARS = [
    'ESP_USERNAME',
    'ESP_PASSWORD',
    'PRODUCTS_URL',
    'SEARCH_API_URL',
    'GOTO_PAGE_API_URL'
]

def validate_production_config():
    """Validate that all required environment variables are set"""
    missing_vars = []
    for var in REQUIRED_ENV_VARS:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    print("✅ Production configuration validated")

def get_production_config():
    """Get production configuration"""
    return PRODUCTION_CONFIG

def get_chrome_options():
    """Get Chrome options for production"""
    return PRODUCTION_CHROME_OPTIONS

if __name__ == "__main__":
    validate_production_config()
    print("Production configuration is ready") 