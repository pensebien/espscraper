#!/usr/bin/env python3
"""
Production entry point for ESP Scraper - Synchronized API and Product Detail Scraping

Coordinates API scraper (link collection) and product detail scraper (data processing)
with configurable batch sizes and retry limits.
"""

import sys
import os
import logging
import argparse
import traceback
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from espscraper.session_manager import SessionManager
from espscraper.api_scraper import ApiScraper
from espscraper.api_product_detail_scraper import ApiProductDetailScraper, ScrapingConfig

def setup_logging(log_file=None, log_level='INFO'):
    """Setup logging for production"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Create logs directory
    logs_dir = Path('logs')
    logs_dir.mkdir(exist_ok=True)
    
    # Default log file if none specified
    if not log_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = logs_dir / f'production_scraper_{timestamp}.log'
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format=log_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"🚀 Production Scraper Started")
    logger.info(f"📝 Log file: {log_file}")
    
    return logger

def validate_environment():
    """Validate required environment variables"""
    required_vars = [
        'ESP_USERNAME',
        'ESP_PASSWORD',
        'PRODUCTS_URL',
        'SEARCH_API_URL',
        'GOTO_PAGE_API_URL',
        'API_SCRAPED_LINKS_FILE',
        'PRODUCT_OUTPUT_FILE'
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

def create_directories():
    """Create necessary directories"""
    directories = ['logs', 'espscraper/data', 'tmp']
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

def check_link_collection_needed(logger, args):
    """Check if link collection is needed based on file age and arguments"""
    links_file = os.getenv('API_SCRAPED_LINKS_FILE')
    
    if not os.path.exists(links_file):
        logger.info("📄 Links file not found, link collection required")
        return True
    
    if args.force_link_collection:
        logger.info("🔄 Force link collection requested")
        return True
    
    # Check file age
    file_age = time.time() - os.path.getmtime(links_file)
    max_age_hours = args.max_link_age or 24  # Default 24 hours
    
    if file_age > (max_age_hours * 3600):
        logger.info(f"⏰ Links file is {file_age/3600:.1f} hours old (max: {max_age_hours}h), link collection needed")
        return True
    
    logger.info(f"✅ Links file is fresh ({file_age/3600:.1f}h old), skipping link collection")
    return False

def collect_links_phase(logger, session_manager, args):
    """Phase 1: Collect product links using API scraper"""
    logger.info("🔗 PHASE 1: Collecting Product Links")
    logger.info("=" * 50)
    
    try:
        # Initialize API scraper
        api_scraper = ApiScraper(session_manager)
        
        # Collect links with specified parameters
        logger.info(f"📊 Starting link collection with batch_size={args.batch_size}, max_retries={args.max_retries}")
        
        result = api_scraper.collect_product_links(
            force_relogin=args.force_relogin,
            pages=args.pages,
            limit=args.link_limit,
            new_only=args.new_only,
            detail_output_file=os.getenv('PRODUCT_OUTPUT_FILE'),
            resume_missing=args.resume_missing
        )
        
        if result:
            new_links = result.get('new_links_collected', 0)
            if new_links > 0:
                logger.info(f"✅ Link collection completed successfully")
                logger.info(f"📊 New links collected: {new_links}")
            else:
                logger.warning("⚠️ Link collection completed with no new links")
            return True
        else:
            logger.warning("⚠️ Link collection completed with no new links")
            return True
            
    except Exception as e:
        logger.error(f"❌ Link collection failed: {e}")
        return False

def process_products_phase(logger, session_manager, args):
    """Phase 2: Process product details using product detail scraper"""
    logger.info("📦 PHASE 2: Processing Product Details")
    logger.info("=" * 50)
    
    try:
        # Create scraping configuration
        detail_config = ScrapingConfig(
            max_requests_per_minute=20,
            min_delay=2.0,
            max_concurrent_requests=3,
            max_retries=args.max_retries,
            retry_delay=3.0,
            exponential_backoff=True,
            request_timeout=30,
            session_timeout=1800,
            batch_size=args.batch_size,
            batch_pause=10,
            session_refresh_interval=1800,
            auto_relogin=True,
            max_consecutive_failures=15,
            circuit_breaker_enabled=True,
            enable_heartbeat=True,
            heartbeat_interval=120,
            log_detailed_stats=True
        )
        
        # Initialize product detail scraper
        detail_scraper = ApiProductDetailScraper(session_manager, detail_config)
        
        # Process products with specified parameters
        logger.info(f"📊 Starting product processing with batch_size={detail_config.batch_size}, max_retries={detail_config.max_retries}")
        
        detail_scraper.scrape_all_products(
            mode=args.mode,
            limit=args.product_limit
        )
        
        logger.info("✅ Product processing completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Product processing failed: {e}")
        return False

def run_synchronized_scraping(args):
    """Run synchronized scraping process"""
    # Setup logging
    logger = setup_logging(args.log_file, args.log_level)
    
    try:
        # Validate environment
        logger.info("🔍 Validating production environment...")
        validate_environment()
        logger.info("✅ Environment validation passed")
        
        # Create directories
        logger.info("📁 Creating directories...")
        create_directories()
        
        # Initialize session manager
        logger.info("🔐 Initializing session manager...")
        session_manager = SessionManager()
        
        # Test login
        logger.info("🔑 Testing authentication...")
        if not session_manager.login():
            raise Exception("Failed to authenticate with ESP")
        logger.info("✅ Authentication successful")
        
        start_time = time.time()
        
        # Phase 1: Link Collection (if needed)
        if check_link_collection_needed(logger, args):
            link_success = collect_links_phase(logger, session_manager, args)
            if not link_success:
                if args.fail_on_link_collection:
                    logger.error("❌ Link collection phase failed and --fail-on-link-collection is set")
                    return False
                else:
                    logger.warning("⚠️ Link collection failed, but continuing with existing links")
                    logger.info("📄 Using existing links file for product processing")
            else:
                logger.info("✅ Link collection completed successfully")
        else:
            logger.info("⏭️ Skipping link collection phase")
        
        # Phase 2: Product Processing
        product_success = process_products_phase(logger, session_manager, args)
        if not product_success:
            logger.error("❌ Product processing phase failed")
            return False
        
        # Calculate completion statistics
        end_time = time.time()
        total_time = end_time - start_time
        actual_time = timedelta(seconds=total_time)
        
        logger.info("=" * 60)
        logger.info("🎉 SYNCHRONIZED SCRAPING COMPLETED")
        logger.info("=" * 60)
        logger.info(f"⏱️ Total completion time: {actual_time}")
        logger.info(f"📊 Configuration: batch_size={args.batch_size}, max_retries={args.max_retries}")
        
        logger.info("✅ Synchronized scraping completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Synchronized scraping failed: {e}")
        logger.exception("Full error details:")
        return False

def main():
    """Main entry point for production"""
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
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("🧪 DRY RUN MODE - Configuration test only")
        print(f"📊 Batch size: {args.batch_size}")
        print(f"📊 Max retries: {args.max_retries}")
        print(f"📊 Link collection: {'forced' if args.force_link_collection else 'conditional'}")
        print(f"📊 Product mode: {args.mode}")
        print("✅ Configuration test completed successfully")
        return
    
    if args.validate_only:
        try:
            validate_environment()
            create_directories()
            print("✅ Configuration validation completed successfully")
            return
        except Exception as e:
            print(f"❌ Configuration validation failed: {e}")
            sys.exit(1)
    
    # Run synchronized scraping
    success = run_synchronized_scraping(args)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 