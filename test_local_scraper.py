#!/usr/bin/env python3
"""
Local Test Script for ESP Scraper

This script loads environment variables from .env and runs the scraper
with all the same functionality as production_main, but using local .env file.
"""

import os
import sys
import logging
import argparse
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(__file__))

def setup_logging(log_level='INFO', log_file=None):
    """Set up logging configuration"""
    level = getattr(logging, log_level.upper())
    
    # Create logs directory if it doesn't exist
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file) if log_file else logging.NullHandler()
        ]
    )

def parse_arguments():
    """Parse command line arguments (same as production_main)"""
    parser = argparse.ArgumentParser(description="ESP Scraper - Synchronized Production Version")
    
    # Link collection arguments
    parser.add_argument('--force-link-collection', action='store_true', 
                       help='Force link collection even if file is fresh')
    parser.add_argument('--max-link-age', type=int, default=24,
                       help='Maximum age of links file in hours before requiring refresh (default: 24)')
    parser.add_argument('--link-limit', type=int, help='Limit number of links to collect')
    parser.add_argument('--pages', type=int, help='Number of pages to scrape for links')
    parser.add_argument('--new-only', action='store_true', 
                       help='Only collect new links not already in output file')
    parser.add_argument('--resume-missing', action='store_true',
                       help='Resume link collection from checkpoint')
    parser.add_argument('--fail-on-link-collection', action='store_true',
                       help='Fail the entire scraper if link collection fails (default: continue with existing links)')
    
    # Product processing arguments
    parser.add_argument('--mode', choices=['scrape', 'new', 'missing'], default='scrape',
                       help='Product processing mode (default: scrape)')
    parser.add_argument('--product-limit', type=int, help='Limit number of products to process')
    
    # Configuration arguments
    parser.add_argument('--batch-size', type=int, default=20, help='Batch size for both scrapers (default: 20)')
    parser.add_argument('--max-retries', type=int, default=3, help='Maximum retries for both scrapers (default: 3)')
    parser.add_argument('--force-relogin', action='store_true', help='Force fresh login')
    
    # Logging arguments
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Logging level')
    parser.add_argument('--log-file', help='Custom log file path')
    parser.add_argument('--dry-run', action='store_true', help='Test configuration without scraping')
    parser.add_argument('--validate-only', action='store_true', help='Only validate configuration')
    
    return parser.parse_args()

def validate_environment():
    """Validate that all required environment variables are loaded"""
    required_vars = [
        'ESP_USERNAME',
        'ESP_PASSWORD', 
        'PRODUCTS_URL',
        'SEARCH_API_URL',
        'GOTO_PAGE_API_URL',
        'API_SCRAPED_LINKS_FILE',
        'PRODUCT_OUTPUT_FILE',
        'PRODUCT_API_URL',
        'PRODUCT_URL_TEMPLATE'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    # Set default values for optional variables
    os.environ.setdefault('PRODUCT_API_URL', 'https://api.asicentral.com/v1/products/{product_id}.json')
    os.environ.setdefault('PRODUCT_URL_TEMPLATE', 'https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductDetails&referrerPage=ProductResults&referrerModule=PRDRES&refModSufx=Generic&PCUrl=1&productID={product_id}&autoLaunchVS=0&tab=list')
    
    return True

def run_synchronized_scraping(args):
    """Run the synchronized scraping process"""
    try:
        # Validate environment
        validate_environment()
        logging.info("✅ Environment validation passed")
        
        # Import the production main module
        from espscraper.production_main import run_synchronized_scraping as run_production
        
        # Run with the same parameters as production_main
        run_production(args)
        
        return True
        
    except Exception as e:
        logging.error(f"❌ Synchronized scraping failed: {e}")
        logging.error("Full error details:", exc_info=True)
        return False

def main():
    """Main function"""
    # Parse arguments
    args = parse_arguments()
    
    # Set up logging
    if not args.log_file:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.log_file = f"logs/test_scraper_{timestamp}.log"
    
    setup_logging(args.log_level, args.log_file)
    
    logging.info("🚀 Local Test Scraper Started")
    logging.info(f"📝 Log file: {args.log_file}")
    
    # Print configuration
    logging.info("📊 Configuration:")
    logging.info(f"  - Batch size: {args.batch_size}")
    logging.info(f"  - Max retries: {args.max_retries}")
    logging.info(f"  - Mode: {args.mode}")
    logging.info(f"  - Force link collection: {args.force_link_collection}")
    logging.info(f"  - Max link age: {args.max_link_age} hours")
    logging.info(f"  - Product limit: {args.product_limit}")
    logging.info(f"  - Dry run: {args.dry_run}")
    logging.info(f"  - Validate only: {args.validate_only}")
    
    # Validate environment
    try:
        validate_environment()
        logging.info("✅ Environment validation passed")
    except ValueError as e:
        logging.error(f"❌ Environment validation failed: {e}")
        return 1
    
    # If validate-only mode, exit here
    if args.validate_only:
        logging.info("✅ Configuration validation completed successfully")
        return 0
    
    # If dry-run mode, just test configuration
    if args.dry_run:
        logging.info("🧪 DRY RUN MODE - Configuration test only")
        logging.info("✅ Configuration test completed successfully")
        return 0
    
    # Run the actual scraping
    if run_synchronized_scraping(args):
        logging.info("✅ Local test completed successfully")
        return 0
    else:
        logging.error("❌ Local test failed")
        return 1

if __name__ == "__main__":
    exit(main()) 