#!/usr/bin/env python3
"""
API-Based Product Detail Scraper

This module implements a robust API-based scraper following Google's crawler expertise:
1. Intelligent session management with automatic recovery
2. Parallel processing with controlled concurrency
3. Robust error handling and retry mechanisms
4. Rate limiting and throttling
5. Comprehensive logging and monitoring
6. Graceful degradation and fallback strategies
"""

import os
import sys
import time
import json
import requests
import logging
import collections
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
import hashlib
import signal
import traceback

# Add the espscraper directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'espscraper'))

from espscraper.session_manager import SessionManager
from espscraper.base_scraper import BaseScraper
from espscraper.batch_processor import BatchProcessor
from espscraper.product_data import ProductData

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler('api_product_scraper.log'),
        logging.StreamHandler()
    ]
)

@dataclass
class ScrapingConfig:
    """Configuration for API product scraping"""
    # Rate limiting
    max_requests_per_minute: int = 25
    min_delay: float = 1.5
    max_concurrent_requests: int = 3
    
    # Retry settings
    max_retries: int = 3
    retry_delay: float = 2.0
    exponential_backoff: bool = True
    
    # Timeout settings
    request_timeout: int = 30
    session_timeout: int = 300  # 5 minutes
    
    # Batch processing
    batch_size: int = 15
    batch_pause: int = 5
    
    # Session management
    session_refresh_interval: int = 1800  # 30 minutes
    auto_relogin: bool = True
    
    # Error handling
    max_consecutive_failures: int = 10
    circuit_breaker_enabled: bool = True
    
    # Monitoring
    enable_heartbeat: bool = True
    heartbeat_interval: int = 60  # seconds
    log_detailed_stats: bool = True



class RateLimiter:
    """Intelligent rate limiter with adaptive throttling"""
    
    def __init__(self, max_requests_per_minute: int, min_delay: float = 1.5):
        self.max_requests_per_minute = max_requests_per_minute
        self.min_delay = min_delay
        self.request_times = collections.deque()
        self.lock = threading.Lock()
        self.failure_count = 0
        self.last_failure_time = 0
        
    def wait_if_needed(self):
        """Wait if rate limit is exceeded with adaptive throttling"""
        with self.lock:
            now = time.time()
            
            # Adaptive throttling based on failures
            if self.failure_count > 5:
                # Increase delay if many failures
                adaptive_delay = self.min_delay * (1 + (self.failure_count - 5) * 0.5)
                if now - self.last_failure_time < 60:
                    time.sleep(adaptive_delay)
            
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
    
    def record_failure(self):
        """Record a failure for adaptive throttling"""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
    
    def record_success(self):
        """Record a success to reduce throttling"""
        with self.lock:
            if self.failure_count > 0:
                self.failure_count = max(0, self.failure_count - 1)

class ApiProductDetailScraper(BaseScraper):
    """API-based product detail scraper using browser session management"""
    
    def __init__(self, session_manager: SessionManager, config: ScrapingConfig = None):
        super().__init__(session_manager)
        self.config = config or ScrapingConfig()
        self.rate_limiter = RateLimiter(
            self.config.max_requests_per_minute,
            self.config.min_delay
        )
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'start_time': time.time(),
            'last_heartbeat': time.time()
        }
        self.consecutive_failures = 0
        self.circuit_breaker_open = False
        self.circuit_breaker_open_time = 0
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Load environment variables
        self.load_env()
        self.PRODUCT_API_URL = os.getenv("PRODUCT_API_URL")
        self.PRODUCT_URL_TEMPLATE = os.getenv("PRODUCT_URL_TEMPLATE")
        self.OUTPUT_FILE = os.getenv("PRODUCT_OUTPUT_FILE", "api_scraped_product_data.jsonl")
        
        # Enhanced indexing and resume tracking
        self.checkpoint_file = self.OUTPUT_FILE.replace('.jsonl', '.checkpoint.txt')
        self.progress_file = self.OUTPUT_FILE.replace('.jsonl', '.progress.json')
        self.scraped_index = set()
        self.current_batch = []
        self.batch_start_time = time.time()
        
        # Initialize batch processor
        self.batch_processor = BatchProcessor(
            batch_size=self.config.batch_size,
            batch_dir="batch",
            main_output_file=self.OUTPUT_FILE
        )
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(self.OUTPUT_FILE) if os.path.dirname(self.OUTPUT_FILE) else '.', exist_ok=True)
        
        # Load existing progress
        self._load_progress()
        
        logging.info("🚀 API Product Detail Scraper initialized")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logging.info("🛑 Received shutdown signal, saving stats...")
        self._save_stats()
        sys.exit(0)
    
    def _save_stats(self):
        """Save current statistics"""
        stats_file = self.OUTPUT_FILE.replace('.jsonl', '.stats.json')
        with open(stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)
        logging.info(f"📊 Stats saved to {stats_file}")
    
    def _load_progress(self):
        """Load existing progress and scraped index with auto-repair"""
        # Validate and repair output file before loading
        if os.path.exists(self.OUTPUT_FILE):
            if not self._validate_and_repair_jsonl(self.OUTPUT_FILE):
                logging.error(f"❌ Failed to validate/repair {self.OUTPUT_FILE}")
                return
        
        # Load scraped product IDs from output file
        if os.path.exists(self.OUTPUT_FILE):
            try:
                with open(self.OUTPUT_FILE, 'r') as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())
                            product_id = data.get('product_id') or data.get('productId') or data.get('id')
                            if product_id:
                                self.scraped_index.add(str(product_id))
                        except json.JSONDecodeError:
                            continue
                logging.info(f"📊 Loaded {len(self.scraped_index)} already scraped products")
            except Exception as e:
                logging.warning(f"⚠️ Error loading scraped index: {e}")
        
        # Load progress file if exists
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    progress_data = json.load(f)
                    self.current_batch = progress_data.get('current_batch', [])
                    self.batch_start_time = progress_data.get('batch_start_time', time.time())
                    logging.info(f"📈 Resuming from batch with {len(self.current_batch)} products")
            except Exception as e:
                logging.warning(f"⚠️ Error loading progress: {e}")
    
    def _save_progress(self):
        """Save current progress to file"""
        try:
            progress_data = {
                'current_batch': self.current_batch,
                'batch_start_time': self.batch_start_time,
                'scraped_count': len(self.scraped_index),
                'timestamp': datetime.now().isoformat()
            }
            with open(self.progress_file, 'w') as f:
                json.dump(progress_data, f, indent=2)
        except Exception as e:
            logging.warning(f"⚠️ Error saving progress: {e}")
    
    def _update_checkpoint(self, product_id: str):
        """Update checkpoint with current product ID"""
        try:
            with open(self.checkpoint_file, 'w') as f:
                f.write(product_id)
        except Exception as e:
            logging.warning(f"⚠️ Error updating checkpoint: {e}")
    
    def _get_resume_position(self, product_ids: List[str]) -> int:
        """Get the position to resume from based on checkpoint"""
        if not os.path.exists(self.checkpoint_file):
            return 0
        
        try:
            with open(self.checkpoint_file, 'r') as f:
                last_product_id = f.read().strip()
            
            if last_product_id in product_ids:
                resume_index = product_ids.index(last_product_id) + 1
                logging.info(f"🔄 Resuming from position {resume_index} (product {last_product_id})")
                return resume_index
            else:
                logging.info("🔄 Checkpoint product not found in current list, starting from beginning")
                return 0
        except Exception as e:
            logging.warning(f"⚠️ Error reading checkpoint: {e}")
            return 0
    
    def _update_heartbeat(self):
        """Update heartbeat for monitoring"""
        if self.config.enable_heartbeat:
            now = time.time()
            if now - self.stats['last_heartbeat'] > self.config.heartbeat_interval:
                self.stats['last_heartbeat'] = now
                logging.info(f"💓 Heartbeat: {self.stats['successful_requests']} successful, {self.stats['failed_requests']} failed")
    
    def _handle_failure(self):
        """Handle request failure"""
        self.stats['failed_requests'] += 1
        self.consecutive_failures += 1
        self.rate_limiter.record_failure()
        
        if (self.config.circuit_breaker_enabled and 
            self.consecutive_failures >= self.config.max_consecutive_failures):
            self.circuit_breaker_open = True
            self.circuit_breaker_open_time = time.time()
            logging.warning("🚨 Circuit breaker opened due to consecutive failures")
    
    def scrape_product_api(self, product_id: str) -> Optional[ProductData]:
        """Scrape a single product using API with session management"""
        if self.circuit_breaker_open:
            if time.time() - self.circuit_breaker_open_time < 60:
                logging.warning("🚨 Circuit breaker open, skipping request")
                return None
            else:
                self.circuit_breaker_open = False
                logging.info("✅ Circuit breaker closed, resuming requests")
        
        self.rate_limiter.wait_if_needed()
        
        # Get authenticated session from session manager
        try:
            session = self.session_manager.get_authenticated_session()
        except FileNotFoundError:
            logging.warning("⚠️ No session found, attempting login...")
            if self.session_manager.login():
                session = self.session_manager.get_authenticated_session()
            else:
                logging.error("❌ Failed to login")
                return None
        
        # Setup headers for API request
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json;charset=UTF-8',
            'Referer': os.getenv("PRODUCTS_URL"),
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        session.headers.update(headers)
        
        # Prepare API URL with product ID
        api_url = self.PRODUCT_API_URL.format(product_id=product_id)
        
        extraction_start = time.time()
        retry_count = 0
        
        while retry_count <= self.config.max_retries:
            try:
                self.stats['total_requests'] += 1
                
                response = session.get(
                    api_url,
                    timeout=self.config.request_timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    extraction_time = time.time() - extraction_start
                    
                    if data:
                        # Get related products
                        related_products = self._get_related_products(product_id, session)
                        
                        product_data = self._extract_product_data(data, product_id, extraction_time, related_products)
                        self.stats['successful_requests'] += 1
                        self.consecutive_failures = 0
                        self.rate_limiter.record_success()
                        
                        if self.config.log_detailed_stats:
                            logging.info(f"✅ Product {product_id} scraped successfully in {extraction_time:.2f}s")
                        
                        return product_data
                    else:
                        logging.warning(f"⚠️ Empty response for product {product_id}")
                        self._handle_failure()
                        
                elif response.status_code == 401:
                    logging.warning(f"🔐 Authentication failed for product {product_id}, attempting relogin...")
                    if self.session_manager.login():
                        session = self.session_manager.get_authenticated_session()
                        session.headers.update(headers)
                        retry_count += 1
                        continue
                    else:
                        logging.error("❌ Relogin failed")
                        self._handle_failure()
                        break
                        
                elif response.status_code == 429:
                    logging.warning(f"⏸️ Rate limited for product {product_id}, waiting...")
                    time.sleep(self.config.retry_delay * (2 ** retry_count))
                    retry_count += 1
                    continue
                    
                else:
                    logging.warning(f"⚠️ HTTP {response.status_code} for product {product_id}")
                    self._handle_failure()
                    
            except requests.exceptions.Timeout:
                logging.warning(f"⏰ Timeout for product {product_id} (attempt {retry_count + 1})")
                self._handle_failure()
                
            except requests.exceptions.RequestException as e:
                logging.warning(f"🌐 Request error for product {product_id}: {e}")
                self._handle_failure()
                
            except Exception as e:
                logging.error(f"❌ Unexpected error for product {product_id}: {e}")
                self._handle_failure()
            
            retry_count += 1
            if retry_count <= self.config.max_retries:
                delay = self.config.retry_delay
                if self.config.exponential_backoff:
                    delay *= (2 ** (retry_count - 1))
                logging.info(f"🔄 Retrying product {product_id} in {delay:.1f}s (attempt {retry_count + 1})")
                time.sleep(delay)
        
        logging.error(f"❌ Failed to scrape product {product_id} after {self.config.max_retries} attempts")
        return None
    
    def _get_related_products(self, product_id: str, session: requests.Session) -> List[Dict]:
        """Get related products for a given product ID"""
        try:
            api_url = f"https://api.asicentral.com/v1/products/{product_id}/suggestions.json?page=1&rpp=5"
            response = session.get(api_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                related = []
                
                for item in data.get('Results', []):
                    pid = item.get('Id')
                    name = item.get('Name')
                    image = item.get('ImageUrl')
                    
                    # Build proper image URL
                    if image and not image.startswith('http'):
                        image = f"https://api.asicentral.com/v1/{image.lstrip('/')}"
                    
                    # Build product URL
                    url = self._build_product_url(pid) if pid else ''
                    
                    related.append({
                        'id': pid,
                        'name': name,
                        'image_url': image,
                        'product_url': url
                    })
                
                return related
        except Exception as e:
            logging.warning(f"⚠️ Failed to get related products for {product_id}: {e}")
        
        return []
    
    def _build_product_url(self, product_id: str) -> str:
        """Build product URL for WordPress import"""
        return f"https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductDetails&productID={product_id}&autoLaunchVS=0&tab=list"
    
    def _build_image_url(self, image_path: str) -> str:
        """Build proper image URL for WordPress import"""
        if not image_path:
            return ""
        
        if image_path.startswith('http'):
            return image_path
        
        # Remove leading slash and build full URL
        clean_path = image_path.lstrip('/')
        return f"https://api.asicentral.com/v1/{clean_path}"
    
    def _extract_product_data(self, data: Dict, product_id: str, extraction_time: float, related_products: List[Dict] = None) -> ProductData:
        """Extract structured product data from API response with enhanced image handling"""
        
        # Build proper image URLs
        main_image_url = self._build_image_url(data.get('ImageUrl', ''))
        
        # Process variants with proper image URLs
        variants = data.get('Variants', [])
        processed_variants = []
        for variant in variants:
            processed_variant = variant.copy()
            processed_variant['image_url'] = self._build_image_url(variant.get('ImageUrl', ''))
            processed_variants.append(processed_variant)
        
        # Process images array
        images = data.get('Images', [])
        processed_images = []
        for image in images:
            if isinstance(image, dict):
                processed_image = image.copy()
                processed_image['url'] = self._build_image_url(image.get('url', image.get('Url', '')))
                processed_images.append(processed_image)
            elif isinstance(image, str):
                processed_images.append({
                    'url': self._build_image_url(image),
                    'type': 'product_image'
                })
        
        # Process virtual sample images
        virtual_samples = data.get('VirtualSampleImages', [])
        processed_virtual_samples = []
        for sample in virtual_samples:
            if isinstance(sample, dict):
                processed_sample = sample.copy()
                processed_sample['url'] = self._build_image_url(sample.get('url', sample.get('Url', '')))
                processed_virtual_samples.append(processed_sample)
            elif isinstance(sample, str):
                processed_virtual_samples.append({
                    'url': self._build_image_url(sample),
                    'type': 'virtual_sample'
                })
        
        return ProductData(
            product_id=product_id,
            name=data.get('Name', 'N/A'),
            sku=data.get('SKU', 'N/A'),
            description=data.get('Description', ''),
            short_description=data.get('ShortDescription', ''),
            image_url=main_image_url,
            product_url=data.get('ProductUrl', ''),
            supplier_info=self._extract_supplier_info(data),
            pricing_info=self._extract_pricing_info(data),
            production_info=self._extract_production_info(data),
            attributes=self._extract_attributes(data),
            imprinting=self._extract_imprinting_info(data),
            shipping=self._extract_shipping_info(data),
            variants=processed_variants,
            warnings=data.get('Warnings', []),
            services=data.get('Services', []),
            images=processed_images,
            virtual_samples=processed_virtual_samples,
            related_products=related_products or [],
            raw_data=data,
            extraction_time=extraction_time,
            scraped_date=datetime.now().isoformat()
        )
    
    def _extract_supplier_info(self, data: Dict) -> Dict:
        """Extract supplier information"""
        supplier = data.get('Supplier', {})
        return {
            'supplier_name': supplier.get('Name', ''),
            'supplier_id': supplier.get('Id', ''),
            'supplier_rating': supplier.get('Rating', {}).get('Rating', ''),
            'supplier_location': supplier.get('Location', ''),
            'asi_number': supplier.get('AsiNumber', ''),
            'email': supplier.get('Email', ''),
            'phone': supplier.get('Phone', {}).get('Primary', ''),
            'websites': supplier.get('Websites', [])
        }
    
    def _extract_pricing_info(self, data: Dict) -> Dict:
        """Extract pricing information"""
        return {
            'base_price': data.get('LowestPrice', ''),
            'discount_price': data.get('HighestPrice', ''),
            'bulk_pricing': data.get('Prices', []),
            'currency': data.get('Currency', 'USD')
        }
    
    def _extract_production_info(self, data: Dict) -> Dict:
        """Extract production information"""
        return {
            'production_time': data.get('ProductionTime', []),
            'minimum_order': data.get('MinimumOrder', ''),
            'maximum_order': data.get('MaximumOrder', ''),
            'production_methods': data.get('ProductionMethods', []),
            'origin': data.get('Origin', []),
            'trade_names': data.get('TradeNames', [])
        }
    
    def _extract_attributes(self, data: Dict) -> Dict:
        """Extract product attributes"""
        attributes = data.get('Attributes', {})
        return {
            'category': data.get('Category', ''),
            'subcategory': data.get('Subcategory', ''),
            'tags': data.get('Tags', []),
            'features': data.get('Features', []),
            'colors': attributes.get('Colors', {}).get('Values', []),
            'sizes': attributes.get('Sizes', {}).get('Values', []),
            'materials': attributes.get('Materials', {}).get('Values', [])
        }
    
    def _extract_imprinting_info(self, data: Dict) -> Dict:
        """Extract imprinting information"""
        imprinting = data.get('Imprinting', {})
        return {
            'imprinting_methods': imprinting.get('Methods', {}).get('Values', []),
            'imprinting_locations': imprinting.get('Locations', {}).get('Values', []),
            'imprinting_colors': imprinting.get('Colors', {}).get('Values', []),
            'setup_charges': imprinting.get('Services', {}).get('Values', [])
        }
    
    def _extract_shipping_info(self, data: Dict) -> Dict:
        """Extract shipping information"""
        shipping = data.get('Shipping', {})
        return {
            'shipping_methods': shipping.get('Methods', {}).get('Values', []),
            'shipping_time': shipping.get('Time', ''),
            'shipping_cost': shipping.get('Cost', ''),
            'free_shipping_threshold': shipping.get('FreeThreshold', ''),
            'weight_unit': shipping.get('WeightUnit', ''),
            'weight_per_package': shipping.get('WeightPerPackage', ''),
            'package_unit': shipping.get('PackageUnit', ''),
            'items_per_package': shipping.get('ItemsPerPackage', ''),
            'fob_points': shipping.get('FOBPoints', {}).get('Values', [])
        }
    
    def read_product_ids(self, limit: int = None) -> List[str]:
        """Read product IDs from JSONL file with optional limit"""
        product_ids = []
        input_file = os.getenv("API_SCRAPED_LINKS_FILE", "api_scraped_links.jsonl")
        
        if not os.path.exists(input_file):
            logging.error(f"❌ Input file {input_file} not found")
            return product_ids
        
        try:
            with open(input_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    if limit and len(product_ids) >= limit:
                        break
                    
                    try:
                        data = json.loads(line.strip())
                        product_id = data.get('id') or data.get('productId') or data.get('ProductID')
                        if product_id:
                            product_ids.append(str(product_id))
                    except json.JSONDecodeError as e:
                        logging.warning(f"⚠️ Invalid JSON on line {line_num}: {e}")
                        continue
            
            logging.info(f"📖 Read {len(product_ids)} product IDs from {input_file}")
            return product_ids
            
        except Exception as e:
            logging.error(f"❌ Error reading product IDs: {e}")
            return product_ids
    
    def scrape_all_products(self, mode: str = 'scrape', limit: int = None):
        """Scrape all products with enhanced indexing and resume capabilities"""
        logging.info(f"🚀 Starting product scraping in {mode} mode")
        
        # Read product IDs
        product_ids = self.read_product_ids(limit)
        if not product_ids:
            logging.error("❌ No product IDs found")
            return
        
        # Filter products based on mode
        filtered_ids = self._filter_products(product_ids, mode)
        if not filtered_ids:
            logging.info("ℹ️ No products to scrape after filtering")
            return
        
        # Get resume position
        resume_position = self._get_resume_position(filtered_ids)
        products_to_scrape = filtered_ids[resume_position:]
        
        logging.info(f"🎯 Scraping {len(products_to_scrape)} products (resuming from position {resume_position})")
        
        try:
            # Process products with enhanced indexing
            self._process_products_with_indexing(products_to_scrape)
            
            # Finalize batch processing
            self._finalize_batches()
            
            # Save final stats and clean up
            self._save_stats()
            self._save_progress()
            
            # Clean up checkpoint file on successful completion
            if os.path.exists(self.checkpoint_file):
                os.remove(self.checkpoint_file)
                logging.info("🧹 Cleaned up checkpoint file")
            
            logging.info("✅ Product scraping completed")
            
        except KeyboardInterrupt:
            logging.info("🛑 Scraping interrupted by user")
            self._finalize_batches()
            self._save_progress()
            self._save_stats()
            logging.info("💾 Progress and stats saved")
            raise
        except Exception as e:
            logging.error(f"❌ Unexpected error during scraping: {e}")
            self._finalize_batches()
            self._save_progress()
            self._save_stats()
            raise
    
    def _filter_products(self, product_ids: List[str], mode: str) -> List[str]:
        """Filter products based on mode and already scraped data"""
        if mode == 'scrape':
            return product_ids
        
        # Load already scraped IDs
        scraped_ids = self._load_scraped_ids()
        
        if mode == 'new':
            filtered = [pid for pid in product_ids if pid not in scraped_ids]
            logging.info(f"🔍 Filtered to {len(filtered)} new products (excluded {len(scraped_ids)} already scraped)")
            return filtered
        
        elif mode == 'missing':
            filtered = [pid for pid in product_ids if pid not in scraped_ids]
            logging.info(f"🔍 Filtered to {len(filtered)} missing products")
            return filtered
        
        return product_ids
    
    def _load_scraped_ids(self) -> Set[str]:
        """Load already scraped product IDs"""
        scraped_ids = set()
        
        if os.path.exists(self.OUTPUT_FILE):
            try:
                with open(self.OUTPUT_FILE, 'r') as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())
                            product_id = data.get('product_id') or data.get('productId') or data.get('id')
                            if product_id:
                                scraped_ids.add(str(product_id))
                        except json.JSONDecodeError:
                            continue
                
                logging.info(f"📊 Loaded {len(scraped_ids)} already scraped product IDs")
            except Exception as e:
                logging.warning(f"⚠️ Error loading scraped IDs: {e}")
        
        return scraped_ids
    
    def _process_products_with_indexing(self, product_ids: List[str]):
        """Process products with enhanced indexing and resume capabilities"""
        total_products = len(product_ids)
        completed = 0
        failed = 0
        
        logging.info(f"📊 Starting processing of {total_products} products")
        
        for i, product_id in enumerate(product_ids):
            try:
                # Update checkpoint
                self._update_checkpoint(product_id)
                
                # Check if already scraped
                if product_id in self.scraped_index:
                    logging.info(f"⏭️ Skipping already scraped product {product_id}")
                    completed += 1
                    continue
                
                # Scrape product
                product_data = self.scrape_product_api(product_id)
                
                if product_data:
                    # Save product and update index
                    self._save_single_product(product_data)
                    self.scraped_index.add(product_id)
                    completed += 1
                    
                    # Update progress every 10 products
                    if completed % 10 == 0:
                        self._save_progress()
                        logging.info(f"📈 Progress: {completed}/{total_products} completed ({completed/total_products*100:.1f}%)")
                else:
                    failed += 1
                    logging.warning(f"⚠️ Failed to scrape product {product_id}")
                
                # Update heartbeat
                self._update_heartbeat()
                
                # Batch pause if configured
                if self.config.batch_pause > 0 and (i + 1) % self.config.batch_size == 0:
                    logging.info(f"⏸️ Batch pause for {self.config.batch_pause}s")
                    time.sleep(self.config.batch_pause)
                
            except KeyboardInterrupt:
                logging.info("🛑 Interrupted by user, saving progress...")
                self._save_progress()
                raise
            except Exception as e:
                failed += 1
                logging.error(f"❌ Error processing product {product_id}: {e}")
        
        logging.info(f"✅ Completed {completed}/{total_products} products ({failed} failed)")
    
    def _process_products_parallel(self, product_ids: List[str]):
        """Process products in parallel with session management (legacy method)"""
        with ThreadPoolExecutor(max_workers=self.config.max_concurrent_requests) as executor:
            futures = []
            
            for product_id in product_ids:
                future = executor.submit(self.scrape_product_api, product_id)
                futures.append((product_id, future))
            
            completed = 0
            for product_id, future in futures:
                try:
                    product_data = future.result()
                    if product_data:
                        self._save_single_product(product_data)
                        completed += 1
                    
                    # Update heartbeat
                    self._update_heartbeat()
                    
                except Exception as e:
                    logging.error(f"❌ Error processing product {product_id}: {e}")
            
            logging.info(f"✅ Completed {completed}/{len(product_ids)} products")
    
    def _validate_and_repair_jsonl(self, filename):
        """Validate and repair JSONL file if needed"""
        if not os.path.exists(filename):
            return True
        
        try:
            valid_lines = []
            invalid_count = 0
            
            with open(filename, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        json.loads(line)
                        valid_lines.append(line)
                    except json.JSONDecodeError as e:
                        invalid_count += 1
                        logging.warning(f"⚠️ Found invalid JSON on line {line_num}: {e}")
            
            if invalid_count > 0:
                logging.warning(f"🔧 Repairing {filename}: removing {invalid_count} invalid lines")
                
                # Create backup
                backup_file = filename + '.backup'
                import shutil
                shutil.copy2(filename, backup_file)
                logging.info(f"📋 Created backup: {backup_file}")
                
                # Write repaired file
                temp_file = filename + '.repaired'
                with open(temp_file, 'w') as f:
                    for line in valid_lines:
                        f.write(line + '\n')
                
                # Atomic move
                shutil.move(temp_file, filename)
                logging.info(f"✅ Repaired {filename}: kept {len(valid_lines)} valid lines")
                
                return True
            else:
                logging.debug(f"✅ {filename} is valid")
                return True
                
        except Exception as e:
            logging.error(f"❌ Error validating/repairing {filename}: {e}")
            return False
    
    def _save_single_product(self, product_data: ProductData):
        """Save a single product using batch processing"""
        try:
            # Add product to batch processor
            if not self.batch_processor.add_product(product_data):
                logging.error(f"❌ Failed to add product {product_data.product_id} to batch")
                return False
            
            return True
            
        except Exception as e:
            logging.error(f"❌ Error saving product {product_data.product_id}: {e}")
            return False
    
    def _finalize_batches(self):
        """Finalize batch processing by flushing and merging"""
        try:
            logging.info("🔄 Finalizing batch processing...")
            
            # Flush any remaining products in current batch
            if not self.batch_processor.flush_batch():
                logging.error("❌ Failed to flush final batch")
                return False
            
            # Get batch statistics
            stats = self.batch_processor.get_batch_stats()
            logging.info(f"📊 Batch stats: {stats['batch_count']} batches, {stats['total_products']} products")
            
            # Merge batches to main output file
            if stats['batch_count'] > 0:
                if not self.batch_processor.merge_batches_to_main():
                    logging.error("❌ Failed to merge batches to main output")
                    return False
                
                logging.info("✅ Successfully merged all batches to main output")
                
                # Optionally cleanup batch files (keep them for now)
                # self.batch_processor.cleanup_batches()
            
            return True
            
        except Exception as e:
            logging.error(f"❌ Error finalizing batches: {e}")
            return False

def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='API Product Detail Scraper')
    parser.add_argument('--mode', choices=['scrape', 'new', 'missing'], default='scrape',
                       help='Scraping mode')
    parser.add_argument('--limit', type=int, help='Limit number of products to scrape')
    parser.add_argument('--config', type=str, help='Path to config file')
    
    args = parser.parse_args()
    
    # Initialize session manager
    session_manager = SessionManager()
    
    # Initialize scraper
    config = ScrapingConfig()
    if args.config and os.path.exists(args.config):
        with open(args.config, 'r') as f:
            config_data = json.load(f)
            for key, value in config_data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
    
    scraper = ApiProductDetailScraper(session_manager, config)
    
    # Start scraping
    scraper.scrape_all_products(args.mode, args.limit)

if __name__ == "__main__":
    main() 