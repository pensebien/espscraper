#!/usr/bin/env python3
"""
Automated ESP Product Scraper

This module handles automated scraping on a schedule, independent of WordPress user actions.
The scraping process runs in the background and updates product data files that WordPress
users can then import or sync against.
"""

import os
import sys
import time
import json
import logging
import schedule
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import threading
import signal

# Add the espscraper directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'espscraper'))

from espscraper.session_manager import SessionManager
from espscraper.api_scraper import APIScraper, ScrapingConfig, ProductData

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler('automated_scraper.log'),
        logging.StreamHandler()
    ]
)

@dataclass
class AutomatedScrapingConfig:
    """Configuration for automated scraping"""
    # Scheduling
    scrape_interval_hours: int = 6  # Scrape every 6 hours
    scrape_time: str = "02:00"      # Start scraping at 2 AM
    max_products_per_run: int = 1000  # Maximum products to scrape per run
    
    # Scraping settings
    batch_size: int = 15
    max_requests_per_minute: int = 25
    batch_pause: int = 5
    min_delay: float = 1.5
    max_retries: int = 3
    timeout: int = 30
    
    # File management
    data_directory: str = "data"
    backup_old_files: bool = True
    max_backup_files: int = 10
    
    # Monitoring
    enable_heartbeat: bool = True
    heartbeat_interval: int = 60  # seconds
    log_scraping_stats: bool = True

class AutomatedScraper:
    """Automated scraper that runs on a schedule"""
    
    def __init__(self, config: AutomatedScrapingConfig = None):
        self.config = config or AutomatedScrapingConfig()
        self.session_manager = SessionManager()
        self.scraper = None
        self.running = False
        self.last_scrape_time = None
        self.scraping_stats = {
            'total_runs': 0,
            'total_products_scraped': 0,
            'last_run_products': 0,
            'last_run_duration': 0,
            'last_run_success': False
        }
        
        # Ensure data directory exists
        os.makedirs(self.config.data_directory, exist_ok=True)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logging.info("🛑 Received shutdown signal, stopping automated scraper...")
        self.stop()
    
    def start(self):
        """Start the automated scraper"""
        logging.info("🚀 Starting automated ESP scraper...")
        
        # Setup scraping schedule
        schedule.every(self.config.scrape_interval_hours).hours.do(self.run_scraping_job)
        schedule.every().day.at(self.config.scrape_time).do(self.run_scraping_job)
        
        # Run initial scrape if needed
        if self._should_run_initial_scrape():
            logging.info("🔄 Running initial scrape...")
            self.run_scraping_job()
        
        self.running = True
        
        # Start heartbeat monitoring
        if self.config.enable_heartbeat:
            heartbeat_thread = threading.Thread(target=self._heartbeat_monitor, daemon=True)
            heartbeat_thread.start()
        
        logging.info(f"✅ Automated scraper started. Scraping every {self.config.scrape_interval_hours} hours at {self.config.scrape_time}")
        
        # Main loop
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logging.info("🛑 Keyboard interrupt received")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the automated scraper"""
        logging.info("🛑 Stopping automated scraper...")
        self.running = False
        schedule.clear()
    
    def _should_run_initial_scrape(self) -> bool:
        """Check if we should run an initial scrape"""
        # Check if we have recent data
        latest_file = self._get_latest_product_file()
        if not latest_file:
            return True
        
        # Check if file is older than scrape interval
        file_age = time.time() - os.path.getmtime(latest_file)
        max_age = self.config.scrape_interval_hours * 3600
        
        return file_age > max_age
    
    def _get_latest_product_file(self) -> Optional[str]:
        """Get the latest product data file"""
        data_dir = self.config.data_directory
        if not os.path.exists(data_dir):
            return None
        
        files = [f for f in os.listdir(data_dir) if f.startswith('api_product_details_') and f.endswith('.jsonl')]
        if not files:
            return None
        
        # Sort by modification time
        files.sort(key=lambda f: os.path.getmtime(os.path.join(data_dir, f)), reverse=True)
        return os.path.join(data_dir, files[0])
    
    def run_scraping_job(self):
        """Run a scraping job"""
        if not self.running:
            return
        
        start_time = time.time()
        logging.info("🔄 Starting scraping job...")
        
        try:
            # Initialize scraper
            scraping_config = ScrapingConfig(
                max_requests_per_minute=self.config.max_requests_per_minute,
                batch_size=self.config.batch_size,
                batch_pause=self.config.batch_pause,
                min_delay=self.config.min_delay,
                max_retries=self.config.max_retries,
                timeout=self.config.timeout,
                enable_streaming=False,  # No streaming in automated mode
                enable_batching=True,
                enable_deduplication=True,
                enable_wordpress_integration=False  # No direct WordPress integration
            )
            
            self.scraper = APIScraper(self.session_manager, scraping_config)
            
            # Get product links
            product_links = self.scraper.read_product_links()
            if not product_links:
                logging.warning("⚠️ No product links found")
                return
            
            # Limit products for this run
            if len(product_links) > self.config.max_products_per_run:
                product_links = product_links[:self.config.max_products_per_run]
                logging.info(f"📦 Limited to {self.config.max_products_per_run} products for this run")
            
            # Create output file with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(self.config.data_directory, f"api_product_details_{timestamp}.jsonl")
            
            # Run scraping
            products_scraped = self._scrape_products(product_links, output_file)
            
            # Update stats
            duration = time.time() - start_time
            self.scraping_stats['total_runs'] += 1
            self.scraping_stats['total_products_scraped'] += products_scraped
            self.scraping_stats['last_run_products'] = products_scraped
            self.scraping_stats['last_run_duration'] = duration
            self.scraping_stats['last_run_success'] = True
            self.last_scrape_time = datetime.now()
            
            # Create latest symlink
            latest_file = os.path.join(self.config.data_directory, "api_product_details_latest.jsonl")
            if os.path.exists(latest_file):
                os.remove(latest_file)
            os.symlink(output_file, latest_file)
            
            # Backup old files
            if self.config.backup_old_files:
                self._cleanup_old_files()
            
            logging.info(f"✅ Scraping job completed: {products_scraped} products in {duration:.1f}s")
            
        except Exception as e:
            logging.error(f"❌ Scraping job failed: {e}")
            self.scraping_stats['last_run_success'] = False
    
    def _scrape_products(self, product_links: List[Dict], output_file: str) -> int:
        """Scrape products and save to file"""
        products_scraped = 0
        
        with open(output_file, 'w', encoding='utf-8') as f_out:
            for i, link_info in enumerate(product_links):
                product_id = str(link_info.get('id'))
                url = link_info.get('url')
                
                if not product_id or not url:
                    continue
                
                if i % 100 == 0:
                    logging.info(f"📦 Progress: {i}/{len(product_links)} products processed")
                
                # Scrape product
                product_data = self.scraper.scrape_product_api(product_id)
                
                if product_data:
                    # Convert to dict format
                    product_dict = self._convert_to_dict_format(product_data)
                    
                    # Write to file
                    f_out.write(json.dumps(product_dict) + '\n')
                    f_out.flush()
                    
                    products_scraped += 1
                    
                    # Mark as scraped
                    self.scraper.deduplicator.mark_as_scraped(product_id)
                else:
                    logging.warning(f"⚠️ Failed to scrape product {product_id}")
        
        return products_scraped
    
    def _convert_to_dict_format(self, product_data: ProductData) -> Dict:
        """Convert ProductData to dictionary format"""
        return {
            "ProductID": product_data.product_id,
            "Name": product_data.name,
            "SKU": product_data.sku,
            "ShortDescription": product_data.short_description,
            "ImageURL": product_data.image_url,
            "ProductURL": product_data.product_url,
            "SupplierInfo": product_data.supplier_info,
            "PricingTable": product_data.pricing_info,
            "ProductionInfo": product_data.production_info,
            "Attributes": product_data.attributes,
            "Imprint": product_data.imprinting,
            "Shipping": product_data.shipping,
            "Variants": product_data.variants,
            "Warnings": product_data.warnings,
            "Services": product_data.services,
            "Images": product_data.images,
            "VirtualSampleImages": product_data.virtual_samples,
            "ExtractionMethod": product_data.extraction_method,
            "ExtractionTime": product_data.extraction_time,
            "ScrapedDate": datetime.now().isoformat()
        }
    
    def _cleanup_old_files(self):
        """Clean up old product files"""
        data_dir = self.config.data_directory
        files = [f for f in os.listdir(data_dir) if f.startswith('api_product_details_') and f.endswith('.jsonl')]
        
        # Sort by modification time
        files.sort(key=lambda f: os.path.getmtime(os.path.join(data_dir, f)), reverse=True)
        
        # Keep only the most recent files
        for old_file in files[self.config.max_backup_files:]:
            file_path = os.path.join(data_dir, old_file)
            try:
                os.remove(file_path)
                logging.info(f"🗑️ Removed old file: {old_file}")
            except Exception as e:
                logging.warning(f"⚠️ Failed to remove old file {old_file}: {e}")
    
    def _heartbeat_monitor(self):
        """Monitor heartbeat for the scraper"""
        heartbeat_file = os.path.join(self.config.data_directory, 'scraper_heartbeat.txt')
        
        while self.running:
            try:
                heartbeat_data = {
                    'status': 'running',
                    'last_scrape_time': self.last_scrape_time.isoformat() if self.last_scrape_time else None,
                    'total_runs': self.scraping_stats['total_runs'],
                    'total_products_scraped': self.scraping_stats['total_products_scraped'],
                    'last_run_products': self.scraping_stats['last_run_products'],
                    'last_run_duration': self.scraping_stats['last_run_duration'],
                    'last_run_success': self.scraping_stats['last_run_success'],
                    'timestamp': time.time()
                }
                
                with open(heartbeat_file, 'w') as f:
                    json.dump(heartbeat_data, f)
                
                time.sleep(self.config.heartbeat_interval)
                
            except Exception as e:
                logging.error(f"❌ Heartbeat error: {e}")
                time.sleep(self.config.heartbeat_interval)
    
    def get_scraping_stats(self) -> Dict:
        """Get scraping statistics"""
        return {
            'running': self.running,
            'last_scrape_time': self.last_scrape_time.isoformat() if self.last_scrape_time else None,
            'next_scheduled_scrape': schedule.next_run().isoformat() if schedule.jobs else None,
            'stats': self.scraping_stats.copy()
        }

def main():
    """Main function for automated scraper"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Automated ESP Product Scraper")
    parser.add_argument('--config-file', help='Configuration file (JSON)')
    parser.add_argument('--scrape-now', action='store_true', help='Run a scraping job immediately')
    parser.add_argument('--interval-hours', type=int, default=6, help='Scraping interval in hours')
    parser.add_argument('--max-products', type=int, default=1000, help='Maximum products per run')
    parser.add_argument('--batch-size', type=int, default=15, help='Batch size for processing')
    
    args = parser.parse_args()
    
    # Load configuration
    config = AutomatedScrapingConfig()
    
    if args.config_file and os.path.exists(args.config_file):
        with open(args.config_file, 'r') as f:
            config_data = json.load(f)
            for key, value in config_data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
    
    # Override with command line arguments
    if args.interval_hours:
        config.scrape_interval_hours = args.interval_hours
    if args.max_products:
        config.max_products_per_run = args.max_products
    if args.batch_size:
        config.batch_size = args.batch_size
    
    # Create and start scraper
    scraper = AutomatedScraper(config)
    
    if args.scrape_now:
        # Run immediate scrape
        scraper.run_scraping_job()
    else:
        # Start automated mode
        scraper.start()

if __name__ == "__main__":
    main() 