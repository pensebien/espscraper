#!/usr/bin/env python3
"""
API-Based ESP Product Scraper with WordPress Integration

This module provides a comprehensive API-based scraper that:
1. Uses discovered API endpoints for lightning-fast scraping
2. Implements proper batching and streaming
3. Handles WordPress/WooCommerce integration separately
4. Includes robust login, timeout, and throttling
5. Provides deduplication and smart filtering
6. Separates import logic from scraping logic
"""

import os
import sys
import time
import json
import requests
import logging
import collections
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from queue import Queue
import hashlib

# Add the espscraper directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'espscraper'))

from espscraper.session_manager import SessionManager
from espscraper.base_scraper import BaseScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler('api_scraper.log'),
        logging.StreamHandler()
    ]
)

@dataclass
class ScrapingConfig:
    """Configuration for API scraping"""
    max_requests_per_minute: int = 25
    batch_size: int = 15
    batch_pause: int = 5
    min_delay: float = 1.5
    max_retries: int = 3
    timeout: int = 30
    max_workers: int = 3
    enable_streaming: bool = True
    enable_batching: bool = True
    enable_deduplication: bool = True
    enable_wordpress_integration: bool = True

@dataclass
class ProductData:
    """Structured product data from API"""
    product_id: str
    name: str
    sku: str
    description: str
    short_description: str
    image_url: str
    product_url: str
    supplier_info: Dict
    pricing_info: Dict
    production_info: Dict
    attributes: Dict
    imprinting: Dict
    shipping: Dict
    variants: List
    warnings: List
    services: List
    images: List
    virtual_samples: List
    raw_data: Dict
    extraction_time: float
    extraction_method: str = "api"

class RateLimiter:
    """Rate limiter for API requests"""
    
    def __init__(self, max_requests_per_minute: int, min_delay: float = 1.5):
        self.max_requests_per_minute = max_requests_per_minute
        self.min_delay = min_delay
        self.request_times = collections.deque()
        self.lock = threading.Lock()
    
    def wait_if_needed(self):
        """Wait if rate limit is exceeded"""
        with self.lock:
            now = time.time()
            
            # Remove requests older than 60 seconds
            while self.request_times and now - self.request_times[0] > 60:
                self.request_times.popleft()
            
            # Check if we're at the limit
            if len(self.request_times) >= self.max_requests_per_minute:
                wait_time = 60 - (now - self.request_times[0])
                if wait_time > 0 and wait_time < 30:
                    logging.info(f"⏸️ Rate limit reached, waiting {wait_time:.1f}s")
                    time.sleep(wait_time)
            
            # Enforce minimum delay between requests
            if self.request_times and now - self.request_times[-1] < self.min_delay:
                delay = self.min_delay - (now - self.request_times[-1])
                if delay > 0 and delay < 10:
                    time.sleep(delay)
            
            self.request_times.append(time.time())

class WordPressIntegrator:
    """Handles WordPress/WooCommerce integration separately"""
    
    def __init__(self, api_url: str = None, api_key: str = None):
        self.api_url = api_url or os.getenv("WP_API_URL")
        self.api_key = api_key or os.getenv("WP_API_KEY")
        self.base_url = os.getenv("WP_BASE_URL")
        self.basic_auth_user = os.getenv("WP_BASIC_AUTH_USER")
        self.basic_auth_pass = os.getenv("WP_BASIC_AUTH_PASS")
        
        if self.api_url and self.api_key:
            logging.info("✅ WordPress integration configured")
        else:
            logging.info("⚠️ WordPress integration not configured")
    
    def get_existing_products(self) -> Tuple[Set[str], Set[str]]:
        """Fetch existing products from WordPress"""
        if not self.api_url or not self.api_key:
            return set(), set()
        
        try:
            # Construct existing products endpoint
            if self.api_url.endswith('/upload'):
                existing_url = self.api_url.replace('/upload', '/existing-products')
            else:
                existing_url = self.api_url.rstrip('/') + '/existing-products'
            
            headers = {"X-API-Key": self.api_key}
            
            # Add basic auth if configured
            auth = None
            if self.basic_auth_user and self.basic_auth_pass:
                from requests.auth import HTTPBasicAuth
                auth = HTTPBasicAuth(self.basic_auth_user, self.basic_auth_pass)
            
            response = requests.get(existing_url, headers=headers, auth=auth, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            product_ids = set()
            skus = set()
            
            for product in data.get('products', []):
                if product.get('product_id'):
                    product_ids.add(str(product['product_id']))
                if product.get('sku'):
                    skus.add(str(product['sku']))
            
            logging.info(f"📊 Found {len(product_ids)} existing products and {len(skus)} existing SKUs")
            return product_ids, skus
            
        except Exception as e:
            logging.error(f"❌ Failed to fetch existing products: {e}")
            return set(), set()
    
    def stream_single_product(self, product_data: ProductData) -> bool:
        """Stream a single product to WordPress"""
        if not self.api_url or not self.api_key:
            return False
        
        try:
            # Convert ProductData to dict format expected by WordPress
            product_dict = self._convert_to_wordpress_format(product_data)
            
            # Prepare as JSONL
            jsonl_data = json.dumps(product_dict) + '\n'
            files = {'file': ('single_product.jsonl', jsonl_data)}
            headers = {'Authorization': f'Bearer {self.api_key}'}
            
            response = requests.post(self.api_url, files=files, headers=headers, timeout=10)
            response.raise_for_status()
            
            logging.info(f"🚀 Live streamed product {product_data.product_id} to WordPress")
            return True
            
        except Exception as e:
            logging.error(f"❌ Failed to stream product {product_data.product_id}: {e}")
            return False
    
    def stream_batch(self, products: List[ProductData]) -> bool:
        """Stream a batch of products to WordPress"""
        if not self.api_url or not self.api_key or not products:
            return False
        
        try:
            # Convert all products to WordPress format
            product_dicts = [self._convert_to_wordpress_format(p) for p in products]
            
            # Prepare as JSONL
            jsonl_data = '\n'.join([json.dumps(p) for p in product_dicts])
            files = {'file': ('batch.jsonl', jsonl_data)}
            headers = {'Authorization': f'Bearer {self.api_key}'}
            
            response = requests.post(self.api_url, files=files, headers=headers, timeout=30)
            response.raise_for_status()
            
            logging.info(f"✅ Successfully streamed batch of {len(products)} products to WordPress")
            return True
            
        except Exception as e:
            logging.error(f"❌ Failed to stream batch: {e}")
            return False
    
    def _convert_to_wordpress_format(self, product_data: ProductData) -> Dict:
        """Convert ProductData to WordPress-compatible format"""
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

class Deduplicator:
    """Handles product deduplication"""
    
    def __init__(self, output_file: str = None):
        self.output_file = output_file or os.getenv("DETAILS_OUTPUT_FILE", "final_product_details.jsonl")
        self.scraped_ids = self._load_scraped_ids()
        self.wordpress_integrator = WordPressIntegrator()
        self.existing_product_ids, self.existing_skus = self.wordpress_integrator.get_existing_products()
    
    def _load_scraped_ids(self) -> Set[str]:
        """Load already scraped product IDs"""
        scraped_ids = set()
        
        if os.path.exists(self.output_file):
            with open(self.output_file, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        if 'ProductID' in data and data['ProductID']:
                            scraped_ids.add(str(data['ProductID']))
                    except Exception:
                        continue
        
        return scraped_ids
    
    def filter_products(self, product_links: List[Dict], mode: str = 'scrape') -> List[Dict]:
        """Filter products based on deduplication rules"""
        filtered_links = []
        skipped_count = 0
        
        for link in product_links:
            product_id = str(link.get('id'))
            
            # Always skip if already scraped in this run
            if product_id in self.scraped_ids:
                skipped_count += 1
                continue
            
            if mode == 'scrape':
                # Only scrape if not in WordPress store
                if product_id not in self.existing_product_ids:
                    filtered_links.append(link)
                else:
                    skipped_count += 1
            elif mode == 'override':
                # Scrape all
                filtered_links.append(link)
            elif mode == 'sync':
                # Check last_modified for sync mode
                # This would require fetching last_modified from WordPress
                # For now, use simple logic
                if product_id not in self.existing_product_ids:
                    filtered_links.append(link)
                else:
                    skipped_count += 1
            else:
                # Default: behave like scrape
                if product_id not in self.existing_product_ids:
                    filtered_links.append(link)
                else:
                    skipped_count += 1
        
        logging.info(f"🔍 Filtered {len(filtered_links)} products (skipped {skipped_count} duplicates, mode={mode})")
        return filtered_links
    
    def mark_as_scraped(self, product_id: str):
        """Mark a product as scraped"""
        self.scraped_ids.add(product_id)

class APIScraper(BaseScraper):
    """API-based product scraper with comprehensive features"""
    
    def __init__(self, session_manager: SessionManager, config: ScrapingConfig = None):
        super().__init__(session_manager)
        self.config = config or ScrapingConfig()
        self.rate_limiter = RateLimiter(
            self.config.max_requests_per_minute,
            self.config.min_delay
        )
        self.wordpress_integrator = WordPressIntegrator()
        self.deduplicator = Deduplicator()
        self.session = requests.Session()
        self._setup_session()
        
        # Ensure data directory exists
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        self.output_file = os.getenv("DETAILS_OUTPUT_FILE", os.path.join(data_dir, "api_product_details.jsonl"))
        self.links_file = os.getenv("DETAILS_LINKS_FILE", os.path.join(data_dir, "api_scraped_links.jsonl"))
    
    def _setup_session(self):
        """Setup requests session with proper headers and cookies"""
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json;charset=UTF-8',
            'Referer': os.getenv("PRODUCTS_URL"),
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        self.session.headers.update(headers)
        
        # Load session cookies
        cookies, page_key, search_id = self.session_manager.load_state()
        if cookies:
            for cookie in cookies:
                self.session.cookies.set(cookie['name'], cookie['value'], domain=cookie.get('domain'))
            logging.info("✅ Session cookies loaded")
    
    def login(self, force_relogin: bool = False):
        """Login to ESP using Selenium and save session"""
        # Use existing login logic from scrape_product_details.py
        # This is a simplified version - you can enhance it
        logging.info("🔐 Logging in to ESP...")
        
        # For now, assume session is valid if cookies exist
        cookies, page_key, search_id = self.session_manager.load_state()
        if cookies and page_key and search_id and not force_relogin:
            logging.info("✅ Using existing session")
            return True
        
        # If no valid session, you would need to implement Selenium login here
        logging.warning("⚠️ No valid session found - please run the HTML scraper first to create session")
        return False
    
    def scrape_product_api(self, product_id: str) -> Optional[ProductData]:
        """Scrape a single product using API"""
        self.rate_limiter.wait_if_needed()
        
        api_url = f"https://api.asicentral.com/v1/products/{product_id}.json"
        
        try:
            start_time = time.time()
            response = self.session.get(api_url, timeout=self.config.timeout)
            extraction_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract comprehensive product data
                product_data = ProductData(
                    product_id=str(data.get('Id', product_id)),
                    name=data.get('Name', ''),
                    sku=data.get('SKU', ''),
                    description=data.get('Description', ''),
                    short_description=data.get('ShortDescription', ''),
                    image_url=data.get('ImageUrl', ''),
                    product_url=data.get('ProductUrl', ''),
                    supplier_info=self._extract_supplier_info(data),
                    pricing_info=self._extract_pricing_info(data),
                    production_info=self._extract_production_info(data),
                    attributes=self._extract_attributes(data),
                    imprinting=self._extract_imprinting_info(data),
                    shipping=self._extract_shipping_info(data),
                    variants=data.get('Variants', []),
                    warnings=data.get('Warnings', []),
                    services=data.get('Services', []),
                    images=data.get('Images', []),
                    virtual_samples=data.get('VirtualSampleImages', []),
                    raw_data=data,
                    extraction_time=extraction_time
                )
                
                logging.info(f"✅ Scraped product {product_id} in {extraction_time:.3f}s")
                return product_data
                
            else:
                logging.warning(f"⚠️ Failed to scrape product {product_id}: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logging.error(f"❌ Error scraping product {product_id}: {e}")
            return None
    
    def _extract_supplier_info(self, data: Dict) -> Dict:
        """Extract supplier information from API data"""
        supplier_data = data.get('Supplier', {})
        return {
            'id': supplier_data.get('Id'),
            'name': supplier_data.get('Name'),
            'asi_number': supplier_data.get('AsiNumber'),
            'email': supplier_data.get('Email'),
            'phone': supplier_data.get('Phone', {}).get('Primary'),
            'toll_free': supplier_data.get('Phone', {}).get('TollFree'),
            'fax': supplier_data.get('Fax', {}).get('Primary'),
            'websites': supplier_data.get('Websites', []),
            'rating': supplier_data.get('Rating', {}).get('Rating'),
            'companies': supplier_data.get('Rating', {}).get('Companies'),
            'transactions': supplier_data.get('Rating', {}).get('Transactions'),
            'marketing_policy': supplier_data.get('MarketingPolicy'),
            'is_minority_owned': supplier_data.get('IsMinorityOwned'),
            'is_union_available': supplier_data.get('IsUnionAvailable')
        }
    
    def _extract_pricing_info(self, data: Dict) -> Dict:
        """Extract pricing information from API data"""
        return {
            'lowest_price': data.get('LowestPrice'),
            'highest_price': data.get('HighestPrice'),
            'currency': data.get('Currency'),
            'currencies': data.get('Currencies', []),
            'prices': data.get('Prices', [])
        }
    
    def _extract_production_info(self, data: Dict) -> Dict:
        """Extract production information from API data"""
        return {
            'production_time': data.get('ProductionTime', []),
            'origin': data.get('Origin', []),
            'trade_names': data.get('TradeNames', []),
            'categories': data.get('Categories', []),
            'themes': data.get('Themes', []),
            'weight': data.get('Weight'),
            'dimensions': data.get('Dimensions', {}),
            'is_assembled': data.get('IsAssembled'),
            'battery_info': data.get('BatteryInfo'),
            'warranty_info': data.get('WarrantyInfo')
        }
    
    def _extract_attributes(self, data: Dict) -> Dict:
        """Extract product attributes from API data"""
        attributes = data.get('Attributes', {})
        return {
            'colors': attributes.get('Colors', {}).get('Values', []),
            'sizes': attributes.get('Sizes', {}).get('Values', []),
            'materials': attributes.get('Materials', {}).get('Values', []),
            'styles': attributes.get('Styles', {}).get('Values', []),
            'features': attributes.get('Features', {}).get('Values', [])
        }
    
    def _extract_imprinting_info(self, data: Dict) -> Dict:
        """Extract imprinting information from API data"""
        imprinting = data.get('Imprinting', {})
        return {
            'methods': imprinting.get('Methods', {}).get('Values', []),
            'colors': imprinting.get('Colors', {}).get('Values', []),
            'services': imprinting.get('Services', {}).get('Values', []),
            'locations': imprinting.get('Locations', {}).get('Values', []),
            'full_color_process': imprinting.get('FullColorProcess'),
            'personalization': imprinting.get('Personalization'),
            'sold_unimprinted': imprinting.get('SoldUnimprinted')
        }
    
    def _extract_shipping_info(self, data: Dict) -> Dict:
        """Extract shipping information from API data"""
        shipping = data.get('Shipping', {})
        return {
            'weight_unit': shipping.get('WeightUnit'),
            'weight_per_package': shipping.get('WeightPerPackage'),
            'package_unit': shipping.get('PackageUnit'),
            'items_per_package': shipping.get('ItemsPerPackage'),
            'package_in_plain_box': shipping.get('PackageInPlainBox'),
            'fob_points': shipping.get('FOBPoints', {}).get('Values', []),
            'dimensions': shipping.get('Dimensions', {})
        }
    
    def read_product_links(self) -> List[Dict]:
        """Read product links from file"""
        links = []
        if not os.path.exists(self.links_file):
            return links
        
        with open(self.links_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    links.append(json.loads(line))
                except Exception as e:
                    logging.warning(f"⚠️ Invalid JSON line in links file: {e}")
        
        return links
    
    def scrape_all_products(self, mode: str = 'scrape', limit: int = None):
        """Scrape all products using API with comprehensive features"""
        
        # Login first
        if not self.login():
            logging.error("❌ Login failed")
            return
        
        # Read and filter product links
        product_links = self.read_product_links()
        filtered_links = self.deduplicator.filter_products(product_links, mode)
        
        if limit:
            filtered_links = filtered_links[:limit]
        
        logging.info(f"🚀 Starting API scraping of {len(filtered_links)} products (mode={mode})")
        
        # Initialize batch processing
        batch = []
        products_scraped = 0
        
        # Open output file
        with open(self.output_file, 'a', encoding='utf-8') as f_out:
            for i, link_info in enumerate(filtered_links):
                product_id = str(link_info.get('id'))
                url = link_info.get('url')
                
                if not product_id or not url:
                    continue
                
                logging.info(f"--- ({i+1}/{len(filtered_links)}) Processing Product ID: {product_id}")
                
                # Scrape product using API
                product_data = self.scrape_product_api(product_id)
                
                if product_data:
                    # Convert to dict for JSON output
                    product_dict = self.wordpress_integrator._convert_to_wordpress_format(product_data)
                    
                    # Write to file
                    f_out.write(json.dumps(product_dict) + '\n')
                    f_out.flush()
                    
                    # Add to batch
                    batch.append(product_data)
                    products_scraped += 1
                    
                    # Mark as scraped
                    self.deduplicator.mark_as_scraped(product_id)
                    
                    # Stream to WordPress if enabled
                    if self.config.enable_streaming:
                        self.wordpress_integrator.stream_single_product(product_data)
                    
                    # Process batch if full
                    if len(batch) >= self.config.batch_size:
                        self._process_batch(batch)
                        batch = []
                        
                        # Batch pause
                        if (i + 1) < len(filtered_links):
                            logging.info(f"⏸️ Batch pause for {self.config.batch_pause}s...")
                            time.sleep(self.config.batch_pause)
                
                else:
                    logging.warning(f"⚠️ Failed to scrape product {product_id}")
            
            # Process final batch
            if batch:
                self._process_batch(batch)
        
        logging.info(f"✅ API scraping completed: {products_scraped} products processed")
    
    def _process_batch(self, batch: List[ProductData]):
        """Process a batch of products"""
        if not batch:
            return
        
        # Save batch file
        timestamp = int(time.time())
        batch_filename = f"batch_{timestamp}_{len(batch)}.jsonl"
        
        try:
            with open(batch_filename, 'w', encoding='utf-8') as f:
                for product in batch:
                    product_dict = self.wordpress_integrator._convert_to_wordpress_format(product)
                    f.write(json.dumps(product_dict) + '\n')
            
            # Also save to data directory
            data_dir = os.path.join(os.path.dirname(__file__), 'data')
            data_batch_filename = os.path.join(data_dir, batch_filename)
            with open(data_batch_filename, 'w', encoding='utf-8') as f:
                for product in batch:
                    product_dict = self.wordpress_integrator._convert_to_wordpress_format(product)
                    f.write(json.dumps(product_dict) + '\n')
            
            logging.info(f"💾 Batch saved: {batch_filename}")
            
            # Stream to WordPress if enabled
            if self.config.enable_wordpress_integration:
                self.wordpress_integrator.stream_batch(batch)
                
        except Exception as e:
            logging.error(f"❌ Failed to process batch: {e}")

def main():
    """Main function for API scraper"""
    import argparse
    
    parser = argparse.ArgumentParser(description="API-based ESP Product Scraper")
    parser.add_argument('--mode', choices=['scrape', 'override', 'sync'], default='scrape',
                       help='Scraping mode: scrape (skip existing), override (all), sync (check timestamps)')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of products to scrape')
    parser.add_argument('--batch-size', type=int, default=15, help='Batch size for processing')
    parser.add_argument('--max-requests-per-minute', type=int, default=25, help='Rate limit')
    parser.add_argument('--no-streaming', action='store_true', help='Disable live streaming')
    parser.add_argument('--no-wordpress', action='store_true', help='Disable WordPress integration')
    parser.add_argument('--force-relogin', action='store_true', help='Force fresh login')
    
    args = parser.parse_args()
    
    # Create configuration
    config = ScrapingConfig(
        batch_size=args.batch_size,
        max_requests_per_minute=args.max_requests_per_minute,
        enable_streaming=not args.no_streaming,
        enable_wordpress_integration=not args.no_wordpress
    )
    
    # Create session manager and scraper
    session_manager = SessionManager()
    scraper = APIScraper(session_manager, config)
    
    # Run scraping
    scraper.scrape_all_products(mode=args.mode, limit=args.limit)

if __name__ == "__main__":
    main() 