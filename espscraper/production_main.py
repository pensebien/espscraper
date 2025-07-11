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
import json

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from espscraper.session_manager import SessionManager
from espscraper.scrape_product_details import ProductDetailScraper
from espscraper.api_scraper import ApiScraper
from espscraper.checkpoint_manager import CheckpointManager
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
    """Run the scraper: collect all product data, no deduplication or import."""
    logger = logging.getLogger(__name__)
    config = get_production_config()
    try:
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
            new_only=False,  # Always collect all links
            detail_output_file=args.output_file
        )
        if status:
            logger.info(f"Link collection completed: {status}")
        # Scrape all product details (no deduplication, just collect data)
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
        logger.info("Starting product detail scraping (data collection only)...")
        scraper.scrape_all_details(force_relogin=args.force_relogin, mode='override')
        logger.info("Scraping completed successfully (data collection only)")
        return True
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        logger.error(traceback.format_exc())
        return False

def run_import(args):
    """Run the import: compare canonical data to store and upload missing/updated products."""
    logger = logging.getLogger(__name__)
    config = get_production_config()
    try:
        # Load canonical product details
        details_file = args.output_file or os.path.join(os.path.dirname(__file__), 'data', 'final_product_details.jsonl')
        checkpoint_manager = CheckpointManager(details_file, id_fields=['ProductID'])
        scraped_ids, last_valid_id, last_valid_line = checkpoint_manager.get_scraped_ids_and_checkpoint()
        # Fetch existing products from store
        api_url = os.getenv("WP_API_URL")
        api_key = os.getenv("WP_API_KEY")
        session_manager = SessionManager(
            cookie_file='tmp/session_cookies.json',
            state_file='tmp/session_state.json',
            headless=config['HEADLESS']
        )
        scraper = ProductDetailScraper(session_manager)
        if api_url and api_key:
            if api_url.endswith('/upload'):
                existing_url = api_url.replace('/upload', '/existing-products')
            else:
                existing_url = api_url.rstrip('/') + '/existing-products'
            logger.info(f"Fetching existing products from {existing_url}")
            existing_product_ids, _ = scraper.fetch_existing_products(existing_url, api_key)
        else:
            logger.error("WordPress integration not configured. Cannot import.")
            return False
        # Compare and upload missing/updated products
        to_import = []
        with open(details_file, 'r') as f:
            for line in f:
                try:
                    product = json.loads(line)
                    pid = product.get('ProductID')
                    if pid and pid not in existing_product_ids:
                        to_import.append(product)
                except Exception:
                    continue
        logger.info(f"Importing {len(to_import)} products to WordPress...")
        for product in to_import:
            scraper.post_single_product_to_wordpress(product, api_url, api_key)
        logger.info("Import completed.")
        return True
    except Exception as e:
        logger.error(f"Import failed: {e}")
        logger.error(traceback.format_exc())
        return False

def run_final_import(args):
    """Import all products from final_product_details.jsonl to WordPress, deduplicating by ProductID and last-modified."""
    logger = logging.getLogger(__name__)
    details_file = args.output_file or os.path.join(os.path.dirname(__file__), 'data', 'final_product_details.jsonl')
    checkpoint_manager = CheckpointManager(details_file, id_fields=['ProductID'])
    api_url = os.getenv("WP_API_URL")
    api_key = os.getenv("WP_API_KEY")
    if not api_url or not api_key:
        logger.error("WordPress integration not configured. Cannot import.")
        return False

    session_manager = SessionManager()
    scraper = ProductDetailScraper(session_manager)
    # Fetch existing products from store
    if api_url.endswith('/upload'):
        existing_url = api_url.replace('/upload', '/existing-products')
    else:
        existing_url = api_url.rstrip('/') + '/existing-products'
    logger.info(f"Fetching existing products from {existing_url}")
    existing_product_ids, _ = scraper.fetch_existing_products(existing_url, api_key)

    # Import missing/updated products
    to_import = []
    with open(details_file, 'r') as f:
        for line in f:
            try:
                product = json.loads(line)
                pid = product.get('ProductID')
                if pid and pid not in existing_product_ids:
                    to_import.append(product)
            except Exception:
                continue
    logger.info(f"Final import: {len(to_import)} products to import to WordPress...")
    batch_size = 10
    for i in range(0, len(to_import), batch_size):
        batch = to_import[i:i+batch_size]
        scraper.post_batch_to_wordpress(batch, api_url, api_key)
    logger.info("Final import pass complete.")
    return True

def main():
    parser = argparse.ArgumentParser(description="ESP Scraper - Production Version (separated scrape/import)")
    subparsers = parser.add_subparsers(dest='command', required=True)
    # Scrape command
    scrape_parser = subparsers.add_parser('scrape', help='Collect all product data (no import)')
    scrape_parser.add_argument('--limit', type=int, default=None)
    scrape_parser.add_argument('--headless', action='store_true')
    scrape_parser.add_argument('--force-relogin', action='store_true')
    scrape_parser.add_argument('--output-file', type=str, default=None)
    scrape_parser.add_argument('--links-file', type=str, default=None)
    # Import command
    import_parser = subparsers.add_parser('import', help='Import missing/updated products to WordPress')
    import_parser.add_argument('--output-file', type=str, default=None)
    parser.add_argument('--final-import', action='store_true', help='Run final import pass to WordPress after scraping')
    args = parser.parse_args()
    logger = setup_logging(None, 'INFO')
    if args.command == 'scrape':
        run_scraper(args)
    elif args.command == 'import':
        run_import(args)
    if args.final_import:
        run_final_import(args)

if __name__ == "__main__":
    main() 