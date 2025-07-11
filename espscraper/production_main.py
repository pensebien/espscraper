#!/usr/bin/env python3
"""
Production entry point for ESP Scraper
"""

import sys
import os
import logging
import argparse
import traceback
from datetime import datetime
from pathlib import Path

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from espscraper.session_manager import SessionManager
from espscraper.scrape_product_details import ProductDetailScraper
from espscraper.api_scraper import ApiScraper
from production_config import validate_production_config, get_production_config, get_chrome_options

def setup_logging(log_file=None, log_level='INFO'):
    """Setup logging for production"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Create log directory
    log_dir = Path('log')
    log_dir.mkdir(exist_ok=True)
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format=log_format,
        handlers=[
            logging.FileHandler(log_file or 'log/scraper.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

def create_directories():
    """Create necessary directories"""
    directories = ['espscraper/data', 'tmp', 'log']
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

def validate_environment():
    """Validate environment and configuration"""
    try:
        validate_production_config()
        create_directories()
        return True
    except Exception as e:
        print(f"❌ Environment validation failed: {e}")
        return False

def is_github_actions():
    """Detect if running inside GitHub Actions."""
    return os.getenv("GITHUB_ACTIONS") == "true"

def validate_env_vars(required_vars):
    """Validate required environment variables. Strict in GitHub Actions, warn otherwise."""
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        msg = f"Missing required environment variables: {', '.join(missing)}"
        if is_github_actions():
            raise RuntimeError(msg)
        else:
            print(f"⚠️ {msg} (not fatal in manual/dev mode)")

def run_scraper(args):
    """Run the scraper with production settings"""
    logger = logging.getLogger(__name__)
    config = get_production_config()
    
    try:
        # Setup session manager
        session_manager = SessionManager(
            cookie_file='tmp/session_cookies.json',
            state_file='tmp/session_state.json',
            headless=config['HEADLESS']
        )
        
        # Always collect latest product links before scraping
        logger.info("Starting link collection (always-on)...")
        api_scraper = ApiScraper(session_manager)
        status = api_scraper.collect_product_links(
            force_relogin=args.force_relogin,
            limit=args.limit,
            new_only=False,  # We'll filter after collecting
            detail_output_file=args.output_file
        )
        if status:
            logger.info(f"Link collection completed: {status}")
        
        # Setup detail scraper
        scraper = ProductDetailScraper(
            session_manager,
            headless=config['HEADLESS'],
            limit=args.limit,
            output_file=args.output_file,
            links_file=args.links_file,
            aggressive_cleanup=config['AGGRESSIVE_CLEANUP'],
            max_retries=config['MAX_RETRIES'],
            batch_retry_limit=config['BATCH_RETRY_LIMIT'],
            debug_mode=config['DEBUG_MODE']
        )
        
        # Run scraping with mode
        logger.info(f"Starting product detail scraping in mode: {args.mode}")
        scraper.scrape_all_details(force_relogin=args.force_relogin, mode=args.mode)
        logger.info("Scraping completed successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Main entry point for production"""
    parser = argparse.ArgumentParser(description="ESP Scraper - Production Version")
    parser.add_argument('--limit', type=int, default=None, help='Limit number of products to scrape')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--force-relogin', action='store_true', help='Force fresh login')
    parser.add_argument('--output-file', type=str, default=None, help='Output file for scraped details')
    parser.add_argument('--links-file', type=str, default=None, help='Input links file')
    parser.add_argument('--collect-links', action='store_true', help='Collect new links before scraping')
    parser.add_argument('--new-only', action='store_true', help='Only collect links for new products')
    parser.add_argument('--log-file', type=str, default=None, help='Log file path')
    parser.add_argument('--log-level', type=str, default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    parser.add_argument('--validate-only', action='store_true', help='Only validate configuration')
    parser.add_argument('--mode', type=str, default='scrape', choices=['scrape', 'override', 'sync'], help='Smart scraping mode: scrape (new only), override (all), sync (new+updates)')
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.log_file, args.log_level)
    logger.info("ESP Scraper starting...")
    
    # Conditionally validate environment variables
    required_vars = [
        "ESP_USERNAME", "ESP_PASSWORD", "PRODUCTS_URL"
    ]
    # WordPress variables are optional for now
    optional_vars = ["WP_API_URL", "WP_API_KEY"]
    try:
        validate_env_vars(required_vars)
    except RuntimeError as e:
        logger.error(str(e))
        sys.exit(1)
    
    if args.validate_only:
        logger.info("Configuration validation completed successfully")
        return
    
    # Run scraper
    start_time = datetime.now()
    success = run_scraper(args)
    end_time = datetime.now()
    
    duration = end_time - start_time
    logger.info(f"Scraping completed in {duration}")
    
    if success:
        logger.info("✅ Scraping completed successfully")
        sys.exit(0)
    else:
        logger.error("❌ Scraping failed")
        sys.exit(1)

if __name__ == "__main__":
    main() 