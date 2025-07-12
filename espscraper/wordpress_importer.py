#!/usr/bin/env python3
"""
WordPress/WooCommerce Import Module

This module handles the actual import of scraped product data into WordPress/WooCommerce.
It's separated from the scraping logic to allow for better maintainability and testing.
"""

import os
import sys
import json
import logging
import requests
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import hashlib

# Add the espscraper directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'espscraper'))

@dataclass
class ImportConfig:
    """Configuration for WordPress import"""
    api_url: str
    api_key: str
    base_url: str = None
    basic_auth_user: str = None
    basic_auth_pass: str = None
    batch_size: int = 50
    timeout: int = 30
    retry_attempts: int = 3
    enable_woocommerce_features: bool = True
    create_product_categories: bool = True
    handle_product_images: bool = True
    handle_product_variations: bool = True
    handle_pricing_tables: bool = True
    handle_supplier_info: bool = True
    handle_imprinting_info: bool = True

@dataclass
class ImportResult:
    """Result of an import operation"""
    success: bool
    product_id: str = None
    wordpress_id: int = None
    action: str = None  # 'created', 'updated', 'skipped', 'error'
    error_message: str = None
    processing_time: float = 0.0

class WordPressImporter:
    """Handles WordPress/WooCommerce product imports"""
    
    def __init__(self, config: ImportConfig):
        self.config = config
        self.session = requests.Session()
        self._setup_session()
        
        # Import statistics
        self.stats = {
            'total_processed': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }
    
    def _setup_session(self):
        """Setup requests session with authentication"""
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'ESP-Product-Importer/1.0'
        }
        self.session.headers.update(headers)
        
        # Add basic auth if configured
        if self.config.basic_auth_user and self.config.basic_auth_pass:
            from requests.auth import HTTPBasicAuth
            self.session.auth = HTTPBasicAuth(
                self.config.basic_auth_user,
                self.config.basic_auth_pass
            )
    
    def import_single_product(self, product_data: Dict) -> ImportResult:
        """Import a single product to WordPress"""
        start_time = datetime.now()
        
        try:
            # Validate product data
            if not self._validate_product_data(product_data):
                return ImportResult(
                    success=False,
                    product_id=product_data.get('ProductID'),
                    action='error',
                    error_message='Invalid product data'
                )
            
            # Check if product already exists
            existing_id = self._get_existing_product_id(product_data)
            
            if existing_id and not self.config.force_update:
                return ImportResult(
                    success=True,
                    product_id=product_data.get('ProductID'),
                    wordpress_id=existing_id,
                    action='skipped',
                    processing_time=(datetime.now() - start_time).total_seconds()
                )
            
            # Prepare product data for WordPress
            wp_product_data = self._prepare_wordpress_product_data(product_data)
            
            # Create or update product
            if existing_id:
                result = self._update_product(existing_id, wp_product_data)
                action = 'updated'
            else:
                result = self._create_product(wp_product_data)
                action = 'created'
            
            if result['success']:
                wordpress_id = result.get('id', existing_id)
                
                # Handle additional features
                if self.config.enable_woocommerce_features:
                    self._handle_woocommerce_features(wordpress_id, product_data)
                
                return ImportResult(
                    success=True,
                    product_id=product_data.get('ProductID'),
                    wordpress_id=wordpress_id,
                    action=action,
                    processing_time=(datetime.now() - start_time).total_seconds()
                )
            else:
                return ImportResult(
                    success=False,
                    product_id=product_data.get('ProductID'),
                    action='error',
                    error_message=result.get('error', 'Unknown error'),
                    processing_time=(datetime.now() - start_time).total_seconds()
                )
                
        except Exception as e:
            logging.error(f"❌ Error importing product {product_data.get('ProductID')}: {e}")
            return ImportResult(
                success=False,
                product_id=product_data.get('ProductID'),
                action='error',
                error_message=str(e),
                processing_time=(datetime.now() - start_time).total_seconds()
            )
    
    def import_batch(self, products: List[Dict]) -> List[ImportResult]:
        """Import a batch of products"""
        results = []
        
        for product in products:
            result = self.import_single_product(product)
            results.append(result)
            
            # Update statistics
            self.stats['total_processed'] += 1
            if result.action == 'created':
                self.stats['created'] += 1
            elif result.action == 'updated':
                self.stats['updated'] += 1
            elif result.action == 'skipped':
                self.stats['skipped'] += 1
            elif result.action == 'error':
                self.stats['errors'] += 1
        
        return results
    
    def _validate_product_data(self, product_data: Dict) -> bool:
        """Validate product data has required fields"""
        required_fields = ['ProductID', 'Name']
        return all(field in product_data and product_data[field] for field in required_fields)
    
    def _get_existing_product_id(self, product_data: Dict) -> Optional[int]:
        """Get existing WordPress product ID by external ID or SKU"""
        product_id = product_data.get('ProductID')
        sku = product_data.get('SKU')
        
        # Try to find by external product ID first
        if product_id:
            existing = self._find_product_by_meta('external_product_id', product_id)
            if existing:
                return existing
        
        # Try to find by SKU
        if sku:
            existing = self._find_product_by_meta('_sku', sku)
            if existing:
                return existing
        
        return None
    
    def _find_product_by_meta(self, meta_key: str, meta_value: str) -> Optional[int]:
        """Find product by meta key/value"""
        try:
            # Use WordPress REST API to search by meta
            search_url = f"{self.config.base_url}/wp-json/wp/v2/product"
            params = {
                'meta_key': meta_key,
                'meta_value': meta_value,
                'per_page': 1
            }
            
            response = self.session.get(search_url, params=params, timeout=self.config.timeout)
            if response.status_code == 200:
                products = response.json()
                if products:
                    return products[0]['id']
            
            return None
            
        except Exception as e:
            logging.warning(f"⚠️ Error finding product by meta {meta_key}: {e}")
            return None
    
    def _prepare_wordpress_product_data(self, product_data: Dict) -> Dict:
        """Prepare product data for WordPress REST API"""
        wp_data = {
            'title': product_data.get('Name', 'Imported Product'),
            'content': product_data.get('ShortDescription', ''),
            'excerpt': product_data.get('ShortDescription', ''),
            'status': 'publish',
            'type': 'product',
            'meta': {
                'external_product_id': product_data.get('ProductID'),
                'extraction_method': product_data.get('ExtractionMethod', 'api'),
                'extraction_time': product_data.get('ExtractionTime', 0),
                'scraped_date': product_data.get('ScrapedDate', datetime.now().isoformat())
            }
        }
        
        # Add SKU
        if product_data.get('SKU'):
            wp_data['meta']['_sku'] = product_data['SKU']
        
        # Add product URL
        if product_data.get('ProductURL'):
            wp_data['meta']['product_url'] = product_data['ProductURL']
        
        # Add supplier info
        if product_data.get('SupplierInfo'):
            wp_data['meta']['supplier_info'] = json.dumps(product_data['SupplierInfo'])
        
        # Add production info
        if product_data.get('ProductionInfo'):
            wp_data['meta']['production_info'] = json.dumps(product_data['ProductionInfo'])
        
        # Add imprinting info
        if product_data.get('Imprint'):
            wp_data['meta']['imprinting_info'] = json.dumps(product_data['Imprint'])
        
        # Add shipping info
        if product_data.get('Shipping'):
            wp_data['meta']['shipping_info'] = json.dumps(product_data['Shipping'])
        
        # Add pricing table
        if product_data.get('PricingTable'):
            wp_data['meta']['pricing_table'] = json.dumps(product_data['PricingTable'])
        
        # Add attributes
        if product_data.get('Attributes'):
            wp_data['meta']['product_attributes'] = json.dumps(product_data['Attributes'])
        
        # Add variants
        if product_data.get('Variants'):
            wp_data['meta']['product_variants'] = json.dumps(product_data['Variants'])
        
        # Add warnings
        if product_data.get('Warnings'):
            wp_data['meta']['product_warnings'] = json.dumps(product_data['Warnings'])
        
        # Add services
        if product_data.get('Services'):
            wp_data['meta']['product_services'] = json.dumps(product_data['Services'])
        
        return wp_data
    
    def _create_product(self, product_data: Dict) -> Dict:
        """Create a new product in WordPress"""
        try:
            url = f"{self.config.base_url}/wp-json/wp/v2/product"
            headers = {'Authorization': f'Bearer {self.config.api_key}'}
            
            response = self.session.post(url, json=product_data, headers=headers, timeout=self.config.timeout)
            
            if response.status_code in [201, 200]:
                result = response.json()
                return {
                    'success': True,
                    'id': result.get('id'),
                    'message': 'Product created successfully'
                }
            else:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}: {response.text}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _update_product(self, product_id: int, product_data: Dict) -> Dict:
        """Update an existing product in WordPress"""
        try:
            url = f"{self.config.base_url}/wp-json/wp/v2/product/{product_id}"
            headers = {'Authorization': f'Bearer {self.config.api_key}'}
            
            response = self.session.put(url, json=product_data, headers=headers, timeout=self.config.timeout)
            
            if response.status_code in [200, 201]:
                result = response.json()
                return {
                    'success': True,
                    'id': result.get('id'),
                    'message': 'Product updated successfully'
                }
            else:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}: {response.text}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _handle_woocommerce_features(self, wordpress_id: int, product_data: Dict):
        """Handle WooCommerce-specific features"""
        try:
            # Set product type
            self._set_product_type(wordpress_id, product_data)
            
            # Handle product images
            if self.config.handle_product_images:
                self._handle_product_images(wordpress_id, product_data)
            
            # Handle product variations
            if self.config.handle_product_variations and product_data.get('Variants'):
                self._handle_product_variations(wordpress_id, product_data)
            
            # Handle pricing
            if self.config.handle_pricing_tables and product_data.get('PricingTable'):
                self._handle_pricing_tables(wordpress_id, product_data)
            
            # Handle categories
            if self.config.create_product_categories and product_data.get('ProductionInfo', {}).get('Categories'):
                self._handle_product_categories(wordpress_id, product_data)
            
            # Handle attributes
            if product_data.get('Attributes'):
                self._handle_product_attributes(wordpress_id, product_data)
            
        except Exception as e:
            logging.warning(f"⚠️ Error handling WooCommerce features for product {wordpress_id}: {e}")
    
    def _set_product_type(self, wordpress_id: int, product_data: Dict):
        """Set WooCommerce product type"""
        try:
            # Determine product type based on data
            product_type = 'simple'
            
            if product_data.get('Variants') and len(product_data['Variants']) > 1:
                product_type = 'variable'
            elif product_data.get('ProductURL'):
                product_type = 'external'
            
            # Set product type via meta
            meta_url = f"{self.config.base_url}/wp-json/wp/v2/product/{wordpress_id}"
            headers = {'Authorization': f'Bearer {self.config.api_key}'}
            
            meta_data = {
                'meta': {
                    '_product_type': product_type
                }
            }
            
            response = self.session.put(meta_url, json=meta_data, headers=headers, timeout=self.config.timeout)
            
            if response.status_code not in [200, 201]:
                logging.warning(f"⚠️ Failed to set product type for {wordpress_id}")
                
        except Exception as e:
            logging.warning(f"⚠️ Error setting product type: {e}")
    
    def _handle_product_images(self, wordpress_id: int, product_data: Dict):
        """Handle product images"""
        try:
            images = []
            
            # Add main image
            if product_data.get('ImageURL'):
                images.append(product_data['ImageURL'])
            
            # Add variant images
            if product_data.get('VariantImages'):
                images.extend(product_data['VariantImages'])
            
            # Add virtual sample images
            if product_data.get('VirtualSampleImages'):
                images.extend(product_data['VirtualSampleImages'])
            
            if images:
                # Upload images to WordPress media library
                uploaded_images = []
                for image_url in images[:10]:  # Limit to 10 images
                    try:
                        image_id = self._upload_image(image_url)
                        if image_id:
                            uploaded_images.append(image_id)
                    except Exception as e:
                        logging.warning(f"⚠️ Failed to upload image {image_url}: {e}")
                
                # Set featured image
                if uploaded_images:
                    self._set_featured_image(wordpress_id, uploaded_images[0])
                    
                    # Set gallery images
                    if len(uploaded_images) > 1:
                        self._set_gallery_images(wordpress_id, uploaded_images[1:])
            
        except Exception as e:
            logging.warning(f"⚠️ Error handling product images: {e}")
    
    def _upload_image(self, image_url: str) -> Optional[int]:
        """Upload image to WordPress media library"""
        try:
            # Download image
            response = self.session.get(image_url, timeout=self.config.timeout)
            if response.status_code != 200:
                return None
            
            # Prepare file for upload
            import tempfile
            import mimetypes
            
            content_type = response.headers.get('content-type', 'image/jpeg')
            ext = mimetypes.guess_extension(content_type) or '.jpg'
            
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as temp_file:
                temp_file.write(response.content)
                temp_file_path = temp_file.name
            
            # Upload to WordPress
            upload_url = f"{self.config.base_url}/wp-json/wp/v2/media"
            headers = {'Authorization': f'Bearer {self.config.api_key}'}
            
            with open(temp_file_path, 'rb') as f:
                files = {'file': f}
                response = self.session.post(upload_url, files=files, headers=headers, timeout=self.config.timeout)
            
            # Clean up temp file
            os.unlink(temp_file_path)
            
            if response.status_code in [201, 200]:
                result = response.json()
                return result.get('id')
            
            return None
            
        except Exception as e:
            logging.warning(f"⚠️ Error uploading image {image_url}: {e}")
            return None
    
    def _set_featured_image(self, product_id: int, image_id: int):
        """Set featured image for product"""
        try:
            meta_url = f"{self.config.base_url}/wp-json/wp/v2/product/{product_id}"
            headers = {'Authorization': f'Bearer {self.config.api_key}'}
            
            meta_data = {
                'meta': {
                    '_thumbnail_id': image_id
                }
            }
            
            response = self.session.put(meta_url, json=meta_data, headers=headers, timeout=self.config.timeout)
            
            if response.status_code not in [200, 201]:
                logging.warning(f"⚠️ Failed to set featured image for product {product_id}")
                
        except Exception as e:
            logging.warning(f"⚠️ Error setting featured image: {e}")
    
    def _set_gallery_images(self, product_id: int, image_ids: List[int]):
        """Set gallery images for product"""
        try:
            meta_url = f"{self.config.base_url}/wp-json/wp/v2/product/{product_id}"
            headers = {'Authorization': f'Bearer {self.config.api_key}'}
            
            meta_data = {
                'meta': {
                    '_product_image_gallery': ','.join(map(str, image_ids))
                }
            }
            
            response = self.session.put(meta_url, json=meta_data, headers=headers, timeout=self.config.timeout)
            
            if response.status_code not in [200, 201]:
                logging.warning(f"⚠️ Failed to set gallery images for product {product_id}")
                
        except Exception as e:
            logging.warning(f"⚠️ Error setting gallery images: {e}")
    
    def _handle_product_variations(self, product_id: int, product_data: Dict):
        """Handle product variations"""
        try:
            variants = product_data.get('Variants', [])
            if not variants:
                return
            
            # For now, we'll store variants as meta data
            # In a full implementation, you'd create actual variation products
            meta_url = f"{self.config.base_url}/wp-json/wp/v2/product/{product_id}"
            headers = {'Authorization': f'Bearer {self.config.api_key}'}
            
            meta_data = {
                'meta': {
                    'product_variations': json.dumps(variants)
                }
            }
            
            response = self.session.put(meta_url, json=meta_data, headers=headers, timeout=self.config.timeout)
            
            if response.status_code not in [200, 201]:
                logging.warning(f"⚠️ Failed to set product variations for product {product_id}")
                
        except Exception as e:
            logging.warning(f"⚠️ Error handling product variations: {e}")
    
    def _handle_pricing_tables(self, product_id: int, product_data: Dict):
        """Handle pricing tables"""
        try:
            pricing_table = product_data.get('PricingTable', [])
            if not pricing_table:
                return
            
            # Store pricing table as meta data
            meta_url = f"{self.config.base_url}/wp-json/wp/v2/product/{product_id}"
            headers = {'Authorization': f'Bearer {self.config.api_key}'}
            
            meta_data = {
                'meta': {
                    'pricing_table': json.dumps(pricing_table)
                }
            }
            
            response = self.session.put(meta_url, json=meta_data, headers=headers, timeout=self.config.timeout)
            
            if response.status_code not in [200, 201]:
                logging.warning(f"⚠️ Failed to set pricing table for product {product_id}")
                
        except Exception as e:
            logging.warning(f"⚠️ Error handling pricing tables: {e}")
    
    def _handle_product_categories(self, product_id: int, product_data: Dict):
        """Handle product categories"""
        try:
            categories = product_data.get('ProductionInfo', {}).get('Categories', [])
            if not categories:
                return
            
            # Create or get category terms
            category_ids = []
            for category_name in categories:
                category_id = self._get_or_create_category(category_name)
                if category_id:
                    category_ids.append(category_id)
            
            if category_ids:
                # Set product categories
                categories_url = f"{self.config.base_url}/wp-json/wp/v2/product/{product_id}"
                headers = {'Authorization': f'Bearer {self.config.api_key}'}
                
                category_data = {
                    'product_cat': category_ids
                }
                
                response = self.session.put(categories_url, json=category_data, headers=headers, timeout=self.config.timeout)
                
                if response.status_code not in [200, 201]:
                    logging.warning(f"⚠️ Failed to set categories for product {product_id}")
                    
        except Exception as e:
            logging.warning(f"⚠️ Error handling product categories: {e}")
    
    def _get_or_create_category(self, category_name: str) -> Optional[int]:
        """Get or create a product category"""
        try:
            # Search for existing category
            search_url = f"{self.config.base_url}/wp-json/wp/v2/product_cat"
            params = {'search': category_name, 'per_page': 1}
            
            response = self.session.get(search_url, params=params, timeout=self.config.timeout)
            if response.status_code == 200:
                categories = response.json()
                if categories:
                    return categories[0]['id']
            
            # Create new category
            create_url = f"{self.config.base_url}/wp-json/wp/v2/product_cat"
            headers = {'Authorization': f'Bearer {self.config.api_key}'}
            
            category_data = {
                'name': category_name,
                'slug': category_name.lower().replace(' ', '-')
            }
            
            response = self.session.post(create_url, json=category_data, headers=headers, timeout=self.config.timeout)
            
            if response.status_code in [201, 200]:
                result = response.json()
                return result.get('id')
            
            return None
            
        except Exception as e:
            logging.warning(f"⚠️ Error creating category {category_name}: {e}")
            return None
    
    def _handle_product_attributes(self, product_id: int, product_data: Dict):
        """Handle product attributes"""
        try:
            attributes = product_data.get('Attributes', {})
            if not attributes:
                return
            
            # Store attributes as meta data
            meta_url = f"{self.config.base_url}/wp-json/wp/v2/product/{product_id}"
            headers = {'Authorization': f'Bearer {self.config.api_key}'}
            
            meta_data = {
                'meta': {
                    'product_attributes': json.dumps(attributes)
                }
            }
            
            response = self.session.put(meta_url, json=meta_data, headers=headers, timeout=self.config.timeout)
            
            if response.status_code not in [200, 201]:
                logging.warning(f"⚠️ Failed to set attributes for product {product_id}")
                
        except Exception as e:
            logging.warning(f"⚠️ Error handling product attributes: {e}")
    
    def get_import_statistics(self) -> Dict:
        """Get import statistics"""
        if self.stats['start_time'] and self.stats['end_time']:
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        else:
            duration = 0
        
        return {
            'total_processed': self.stats['total_processed'],
            'created': self.stats['created'],
            'updated': self.stats['updated'],
            'skipped': self.stats['skipped'],
            'errors': self.stats['errors'],
            'duration_seconds': duration,
            'success_rate': (self.stats['created'] + self.stats['updated']) / max(self.stats['total_processed'], 1) * 100
        }
    
    def start_import_session(self):
        """Start an import session"""
        self.stats['start_time'] = datetime.now()
        self.stats['total_processed'] = 0
        self.stats['created'] = 0
        self.stats['updated'] = 0
        self.stats['skipped'] = 0
        self.stats['errors'] = 0
    
    def end_import_session(self):
        """End an import session"""
        self.stats['end_time'] = datetime.now()
        
        stats = self.get_import_statistics()
        logging.info(f"📊 Import session completed:")
        logging.info(f"   📦 Total processed: {stats['total_processed']}")
        logging.info(f"   ✅ Created: {stats['created']}")
        logging.info(f"   🔄 Updated: {stats['updated']}")
        logging.info(f"   ⏭️ Skipped: {stats['skipped']}")
        logging.info(f"   ❌ Errors: {stats['errors']}")
        logging.info(f"   ⏱️ Duration: {stats['duration_seconds']:.1f}s")
        logging.info(f"   📈 Success rate: {stats['success_rate']:.1f}%")

def main():
    """Main function for WordPress importer"""
    import argparse
    
    parser = argparse.ArgumentParser(description="WordPress/WooCommerce Product Importer")
    parser.add_argument('--input-file', required=True, help='Input JSONL file with product data')
    parser.add_argument('--api-url', required=True, help='WordPress API URL')
    parser.add_argument('--api-key', required=True, help='WordPress API key')
    parser.add_argument('--base-url', help='WordPress base URL')
    parser.add_argument('--batch-size', type=int, default=50, help='Batch size for processing')
    parser.add_argument('--force-update', action='store_true', help='Force update existing products')
    
    args = parser.parse_args()
    
    # Create configuration
    config = ImportConfig(
        api_url=args.api_url,
        api_key=args.api_key,
        base_url=args.base_url,
        batch_size=args.batch_size
    )
    
    # Create importer
    importer = WordPressImporter(config)
    
    # Read input file
    products = []
    with open(args.input_file, 'r') as f:
        for line in f:
            try:
                products.append(json.loads(line))
            except Exception as e:
                logging.warning(f"⚠️ Invalid JSON line: {e}")
    
    logging.info(f"📦 Starting import of {len(products)} products")
    
    # Start import session
    importer.start_import_session()
    
    # Process in batches
    for i in range(0, len(products), config.batch_size):
        batch = products[i:i + config.batch_size]
        logging.info(f"🔄 Processing batch {i//config.batch_size + 1}/{(len(products) + config.batch_size - 1)//config.batch_size}")
        
        results = importer.import_batch(batch)
        
        # Log batch results
        batch_stats = {
            'created': sum(1 for r in results if r.action == 'created'),
            'updated': sum(1 for r in results if r.action == 'updated'),
            'skipped': sum(1 for r in results if r.action == 'skipped'),
            'errors': sum(1 for r in results if r.action == 'error')
        }
        
        logging.info(f"   ✅ Created: {batch_stats['created']}")
        logging.info(f"   🔄 Updated: {batch_stats['updated']}")
        logging.info(f"   ⏭️ Skipped: {batch_stats['skipped']}")
        logging.info(f"   ❌ Errors: {batch_stats['errors']}")
    
    # End import session
    importer.end_import_session()

if __name__ == "__main__":
    main() 