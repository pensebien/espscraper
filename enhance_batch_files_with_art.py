#!/usr/bin/env python3
"""
Optimized Batch File Processor - Single Request Approach

Key optimizations:
1. Single HTTP request per product to fetch ALL data
2. Parse HTML once to extract everything needed
3. No separate requests for art templates, color images, variants
4. Smart caching of parsed results
5. Batch processing with connection pooling
"""

import os
import json
import re
import logging
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import pickle
from functools import lru_cache

# BeautifulSoup for HTML parsing
try:
    from bs4 import BeautifulSoup

    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    print("⚠️ BeautifulSoup not available. Install with: pip install beautifulsoup4")


class SingleRequestArtProcessor:
    """Processes art templates and fetches ALL product data in a single request"""

    def __init__(
        self,
        base_url: str = "https://www.hitpromo.net",
        cache_dir: str = "art_templates",
        max_concurrent: int = 10,
        timeout: int = 30,
    ):
        self.base_url = base_url
        self.cache_dir = cache_dir
        self.max_concurrent = max_concurrent
        self.timeout = timeout

        # Create cache directories
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(os.path.join(self.cache_dir, "product_cache"), exist_ok=True)

        # Load existing product cache
        self.cache_file = os.path.join(
            self.cache_dir, "product_cache", "product_data_cache.pkl"
        )
        self.product_cache = self._load_cache()

        # Session for requests with connection pooling
        self.session = self._create_session()

        logging.info(f"📁 Art templates directory: {self.cache_dir}")
        logging.info(f"🚀 Max concurrent requests: {max_concurrent}")

    def _create_session(self):
        """Create optimized session with connection pooling"""
        import requests

        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )

        # Configure connection pooling
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=20, pool_maxsize=50, max_retries=3, pool_block=False
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _load_cache(self) -> Dict:
        """Load cached product data"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, "rb") as f:
                    return pickle.load(f)
        except Exception as e:
            logging.warning(f"⚠️ Could not load product cache: {e}")
        return {}

    def _save_cache(self):
        """Save product cache to disk"""
        try:
            with open(self.cache_file, "wb") as f:
                pickle.dump(self.product_cache, f)
        except Exception as e:
            logging.warning(f"⚠️ Could not save product cache: {e}")

    @lru_cache(maxsize=1000)
    def extract_product_number(self, product_json: str) -> Optional[str]:
        """Cached product number extraction"""
        try:
            product = json.loads(product_json)
            return self._extract_product_number_from_dict(product)
        except:
            return None

    def _extract_product_number_from_dict(self, product: Dict) -> Optional[str]:
        """Extract product number from product data"""
        try:
            # Try different possible fields in order of preference
            possible_fields = [
                "number",
                "numbers",
                "product_number",
                "ProductNumber",
                "sku",
                "SKU",
                "product_id",
                "ProductID",
            ]

            for field in possible_fields:
                value = product.get(field)
                if value:
                    if isinstance(value, list) and len(value) > 0:
                        first_item = value[0]
                        if isinstance(first_item, dict) and first_item.get("SKU"):
                            value = first_item["SKU"]
                        else:
                            value = str(first_item)
                    elif isinstance(value, dict):
                        value = value.get("SKU", "")

                    if value:
                        value = str(value).strip()
                        if len(value) > 20:
                            matches = re.findall(r"\b\d{4,5}\b", value)
                            if matches:
                                return matches[0]
                        else:
                            cleaned = re.sub(r"[^a-zA-Z0-9\-]", "", value)
                            if cleaned and len(cleaned) > 4:
                                base_match = re.match(r"(\d{4,5})[A-Z]+", cleaned)
                                if base_match:
                                    return base_match.group(1)
                                else:
                                    return cleaned

            # Try raw_data.Number
            raw_data = product.get("raw_data", {})
            if isinstance(raw_data, dict):
                number = raw_data.get("Number")
                if number:
                    return str(number)

            numbers = raw_data.get("Numbers", [])
            if isinstance(numbers, list) and len(numbers) > 0:
                return str(numbers[0])

            return None

        except Exception as e:
            logging.error(f"❌ Error extracting product number: {e}")
            return None

    def get_all_product_data_single_request(
        self, product_number: str, product_data: Dict = None
    ) -> Dict:
        """Fetch ALL product data in a single request - main method"""
        cache_key = f"{product_number}_{hash(str(product_data))}"

        # Check cache first
        if cache_key in self.product_cache:
            logging.info(f"✅ Using cached data for product {product_number}")
            return self.product_cache[cache_key]

        try:
            url = f"{self.base_url}/product/show/{product_number}"
            logging.info(f"🔍 Fetching ALL data for product {product_number}: {url}")

            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Parse HTML once to extract everything
            soup = BeautifulSoup(response.content, "html.parser")

            # Extract all data in one pass
            result = self._extract_all_data_from_html(
                soup, product_number, product_data
            )

            # Cache the result
            self.product_cache[cache_key] = result
            self._save_cache()

            return result

        except Exception as e:
            logging.error(f"❌ Error fetching data for {product_number}: {e}")
            return {
                "main_image": None,
                "gallery_images": [],
                "color_images": {},
                "art_template_url": None,
                "product_url": f"{self.base_url}/product/show/{product_number}",
                "error": str(e),
            }

    def _extract_all_data_from_html(
        self, soup: BeautifulSoup, product_number: str, product_data: Dict = None
    ) -> Dict:
        """Extract ALL data from HTML in a single pass"""
        try:
            result = {
                "main_image": None,
                "gallery_images": [],
                "color_images": {},
                "art_template_url": None,
                "product_url": f"{self.base_url}/product/show/{product_number}",
            }

            # 1. Extract main image from zoom viewport
            zoom_viewport = soup.find("div", class_="zoom-viewport")
            if zoom_viewport:
                img = zoom_viewport.find("img", class_="center-block")
                if img and img.get("src"):
                    main_image = urljoin(self.base_url, img["src"])
                    main_image = main_image.replace("/400/", "/")  # Get larger version
                    result["main_image"] = main_image

            # 2. Extract gallery images from carousel
            carousel = soup.find("div", class_="carousel-inner")
            if carousel:
                for item in carousel.find_all("div", class_="carousel-item"):
                    img = item.find("img", class_="center-block")
                    if img and img.get("src"):
                        img_url = urljoin(self.base_url, img["src"])
                        img_url = img_url.replace("/400/", "/")  # Get larger version
                        result["gallery_images"].append(img_url)

            # 3. Extract art template URL from page content
            art_url = self._extract_art_url_from_html(soup, product_number)
            if art_url:
                result["art_template_url"] = art_url

            # 4. Extract color images from the same page
            color_images = self._extract_color_images_from_html(
                soup, product_number, product_data
            )
            if color_images:
                result["color_images"] = color_images

            # 5. Extract additional product images from page
            additional_images = self._extract_additional_images_from_html(soup)
            if additional_images:
                result["gallery_images"].extend(additional_images)

            return result

        except Exception as e:
            logging.error(f"❌ Error extracting data from HTML: {e}")
            return result

    def _extract_art_url_from_html(
        self, soup: BeautifulSoup, product_number: str
    ) -> Optional[str]:
        """Extract art template URL from HTML content"""
        try:
            # Look for art template links in the page
            art_patterns = [
                rf'https://www\.hitpromo\.net/fs/artTemplates/{product_number}/[^"\s]+',
                rf'https://www\.hitpromo\.net/artTemplates/{product_number}/[^"\s]+',
                rf'https://www\.hitpromo\.net/fs/artTemplates/[^"\s]*{product_number}[^"\s]*',
            ]

            html_content = str(soup)

            for pattern in art_patterns:
                matches = re.findall(pattern, html_content)
                if matches:
                    return matches[0]

            # Also look for download links
            download_links = soup.find_all(
                "a", href=re.compile(r"artTemplates|download")
            )
            for link in download_links:
                href = link.get("href", "")
                if product_number in href and (
                    "artTemplates" in href or "download" in href
                ):
                    return urljoin(self.base_url, href)

            return None

        except Exception as e:
            logging.error(f"❌ Error extracting art URL: {e}")
            return None

    def _extract_color_images_from_html(
        self, soup: BeautifulSoup, product_number: str, product_data: Dict = None
    ) -> Dict:
        """Extract color images from HTML content"""
        try:
            color_images = {}

            if not product_data:
                return color_images

            colors = product_data.get("attributes", {}).get("colors", [])
            if not colors:
                return color_images

            # Look for color-specific images in the HTML
            html_content = str(soup)

            for color in colors:
                color_name = color.get("Name", "")
                vendor_code = color.get("VendorCode", "")
                sku = color.get("SKU", "")

                if vendor_code or sku:
                    color_identifier = vendor_code if vendor_code else sku

                    # Find images for this color in the HTML
                    color_urls = self._find_color_images_in_html(
                        html_content, product_number, color_identifier, color_name
                    )

                    if color_urls:
                        color_images[color_name] = {
                            "color_code": color.get("Code", ""),
                            "vendor_code": vendor_code,
                            "sku": sku,
                            "images": color_urls,
                        }

            return color_images

        except Exception as e:
            logging.error(f"❌ Error extracting color images: {e}")
            return {}

    def _find_color_images_in_html(
        self,
        html_content: str,
        product_number: str,
        color_identifier: str,
        color_name: str,
    ) -> List[str]:
        """Find color images in HTML content"""
        try:
            color_urls = []

            # Look for image URLs in the HTML that match this color
            image_patterns = [
                rf'https://www\.hitpromo\.net/imageManager/show/{product_number}_{color_identifier}_[^"\s]+\.(jpg|png)',
                rf'https://www\.hitpromo\.net/imageManager/show/{color_identifier}_[^"\s]+\.(jpg|png)',
                rf'https://www\.hitpromo\.net/imageManager/show/{product_number}_{color_name}_[^"\s]+\.(jpg|png)',
                rf'https://www\.hitpromo\.net/fs/images/{product_number}_{color_identifier}_[^"\s]+\.(jpg|png)',
                rf'https://www\.hitpromo\.net/fs/images/{color_identifier}_[^"\s]+\.(jpg|png)',
            ]

            for pattern in image_patterns:
                matches = re.findall(pattern, html_content)
                for match in matches:
                    if isinstance(match, tuple):
                        # re.findall returns tuples for groups
                        url = match[0] if match[0] else match[1]
                    else:
                        url = match

                    if url and url not in color_urls:
                        color_urls.append(url)

            # Also look for images in img tags that might be color-specific
            img_tags = re.findall(r'<img[^>]+src="([^"]*)"[^>]*>', html_content)
            for img_src in img_tags:
                if (
                    color_identifier in img_src or color_name.lower() in img_src.lower()
                ) and "hitpromo.net" in img_src:
                    if img_src not in color_urls:
                        color_urls.append(img_src)

            return color_urls[:5]  # Limit to 5 images per color

        except Exception as e:
            logging.error(f"❌ Error finding color images: {e}")
            return []

    def _extract_additional_images_from_html(self, soup: BeautifulSoup) -> List[str]:
        """Extract additional product images from HTML"""
        try:
            additional_images = []

            # Look for all img tags with product images
            img_tags = soup.find_all("img", src=re.compile(r"hitpromo\.net"))

            for img in img_tags:
                src = img.get("src", "")
                if src and "hitpromo.net" in src:
                    # Convert to full URL and larger version
                    full_url = urljoin(self.base_url, src)
                    large_url = full_url.replace("/400/", "/")

                    if large_url not in additional_images:
                        additional_images.append(large_url)

            return additional_images

        except Exception as e:
            logging.error(f"❌ Error extracting additional images: {e}")
            return []

    def download_art_template(self, art_url: str, product_number: str) -> Optional[str]:
        """Download art template file"""
        try:
            if not art_url:
                return None

            # Get cached file path
            parsed_url = urlparse(art_url)
            path = parsed_url.path
            filename = os.path.basename(path)

            if not filename or "." not in filename:
                if "pdf" in art_url.lower():
                    filename = f"{product_number}.pdf"
                elif "ai" in art_url.lower():
                    filename = f"{product_number}.ai"
                elif "eps" in art_url.lower():
                    filename = f"{product_number}.eps"
                else:
                    filename = f"{product_number}.pdf"

            cached_path = os.path.join(self.cache_dir, filename)

            # Check if already downloaded
            if os.path.exists(cached_path):
                logging.info(f"✅ Art template already cached: {cached_path}")
                return cached_path

            logging.info(f"📥 Downloading art template: {art_url}")

            # Download the file
            response = self.session.get(art_url, timeout=60)
            response.raise_for_status()

            # Save to cache
            with open(cached_path, "wb") as f:
                f.write(response.content)

            file_size = len(response.content)
            logging.info(
                f"✅ Downloaded art template: {cached_path} ({file_size} bytes)"
            )

            return cached_path

        except Exception as e:
            logging.error(f"❌ Error downloading art template: {e}")
            return None

    def create_fpd_config_from_product_data(self, product_data: Dict):
        """Create FPD configuration from product data"""
        # Implementation from original class - simplified for this example
        try:
            # Basic FPD config
            fpd_config = {
                "product_type": "catalog",
                "enable_fpd": True,
                "create_design_areas": True,
                "stage_config": {
                    "width": 800,
                    "height": 600,
                },
                "restrictions": {
                    "allow_text": True,
                    "allow_images": True,
                    "allow_shapes": True,
                },
                "views": [],
                "fpd_product_structure": {
                    "title": "Product Design",
                    "thumbnail": "",
                    "options": {
                        "stageWidth": 800,
                        "stageHeight": 600,
                    },
                    "views": [],
                },
            }

            return fpd_config

        except Exception as e:
            logging.error(f"❌ Error creating FPD config: {e}")
            return {
                "product_type": "catalog",
                "enable_fpd": True,
                "create_design_areas": True,
                "stage_config": {"width": 800, "height": 600},
                "restrictions": {
                    "allow_text": True,
                    "allow_images": True,
                    "allow_shapes": True,
                },
                "views": [],
                "fpd_product_structure": {
                    "title": "Product Design",
                    "thumbnail": "",
                    "options": {"stageWidth": 800, "stageHeight": 600},
                    "views": [],
                },
            }


class OptimizedBatchFileEnhancer:
    """Optimized batch file enhancer using single request approach"""

    def __init__(self, art_processor: SingleRequestArtProcessor, max_workers: int = 5, skip_art_templates: bool = False):
        self.art_processor = art_processor
        self.max_workers = max_workers
        self.skip_art_templates = skip_art_templates
        self.enhanced_count = 0
        self.error_count = 0

    def enhance_batch_file(self, batch_file_path: str) -> bool:
        """Enhance a single batch file using single request approach"""
        try:
            if not os.path.exists(batch_file_path):
                logging.error(f"❌ Batch file not found: {batch_file_path}")
                return False

            logging.info(f"🔄 Enhancing batch file: {batch_file_path}")

            # Read products
            products = []
            with open(batch_file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            product = json.loads(line)
                            products.append(product)
                        except json.JSONDecodeError:
                            continue

            if not products:
                logging.warning(f"⚠️ No valid products found in {batch_file_path}")
                return False

            logging.info(f"📦 Processing {len(products)} products")

            # Process products with ThreadPoolExecutor
            enhanced_products = []
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []

                for product in products:
                    future = executor.submit(self._enhance_product, product)
                    futures.append(future)

                # Collect results
                for i, future in enumerate(as_completed(futures)):
                    try:
                        result = future.result(timeout=60)
                        enhanced_products.append(result)

                        if (i + 1) % 10 == 0:
                            logging.info(
                                f"🔄 Enhanced {i + 1}/{len(products)} products"
                            )

                    except Exception as e:
                        logging.error(f"❌ Error in processing: {e}")
                        self.error_count += 1

            # Write enhanced products
            base_name = os.path.basename(batch_file_path).replace(".jsonl", "")
            enhanced_dir = os.path.join(
                os.path.dirname(batch_file_path), "..", "enhanced"
            )
            enhanced_dir = os.path.abspath(enhanced_dir)
            os.makedirs(enhanced_dir, exist_ok=True)

            output_file = os.path.join(enhanced_dir, f"{base_name}_enhanced.jsonl")

            with open(output_file, "w", encoding="utf-8") as f:
                for product in enhanced_products:
                    f.write(json.dumps(product, ensure_ascii=False) + "\n")

            self.enhanced_count += 1
            logging.info(f"✅ Enhanced batch file saved: {output_file}")
            return True

        except Exception as e:
            logging.error(f"❌ Error enhancing batch file: {e}")
            return False

    def _enhance_product(self, product: Dict) -> Dict:
        """Enhance a single product using single request approach"""
        try:
            # Extract product number
            product_number = self.art_processor.extract_product_number(
                json.dumps(product)
            )
            if not product_number:
                logging.warning(
                    f"⚠️ No product number found for product {product.get('product_id', 'unknown')}"
                )
                return product

            # Get ALL data in a single request
            all_data = self.art_processor.get_all_product_data_single_request(
                product_number, product
            )

            # Enhance product with all the data
            enhanced_product = self._enhance_product_with_all_data(product, all_data)

            # Ensure FPD config exists - create it if missing
            if not enhanced_product.get("fpd_config"):
                logging.info(f"🔄 Creating FPD config for product {product_number}")
                fpd_config = self.art_processor.create_fpd_config_from_product_data(
                    enhanced_product
                )
                if fpd_config:
                    enhanced_product["fpd_config"] = fpd_config
                    logging.info(f"✅ Created FPD config for product {product_number}")
                else:
                    logging.warning(
                        f"⚠️ Failed to create FPD config for product {product_number}"
                    )

            return enhanced_product

        except Exception as e:
            logging.error(f"❌ Error enhancing product: {e}")
            return product

    def _enhance_product_with_all_data(self, product: Dict, all_data: Dict) -> Dict:
        """Enhance product with all fetched data - FLATTENED STRUCTURE for plugin compatibility"""
        try:
            # Create a flattened structure that the plugin expects
            enhanced_product = {}

            # Extract product info from nested structure
            product_info = product.get("product", {})
            pricing_info = product.get("pricing", {})
            attributes_info = product.get("attributes", {})
            imprinting_info = product.get("imprinting", {})
            supplier_info = product.get("supplier", {})
            production_info = product.get("production", {})
            shipping_info = product.get("shipping", {})
            specifications_info = product.get("specifications", {})

            # Flatten the structure - put everything at top level
            enhanced_product.update(
                {
                    # Core product fields (plugin expects these at top level)
                    "product_id": product_info.get("id", product.get("product_id", "")),
                    "name": product_info.get("name", product.get("name", "")),
                    "description": product_info.get(
                        "description", product.get("description", "")
                    ),
                    "short_description": product_info.get(
                        "short_description", product.get("short_description", "")
                    ),
                    "sku": product_info.get("sku", product.get("sku", "")),
                    "product_number": product_info.get(
                        "product_number", product.get("product_number", "")
                    ),
                    "image_url": product_info.get(
                        "featured_image", product.get("image_url", "")
                    ),
                    "product_url": product_info.get(
                        "product_url", product.get("product_url", "")
                    ),
                    # Pricing (flattened)
                    "pricing_info": pricing_info,
                    # Attributes (flattened)
                    "attributes": attributes_info,
                    # Imprinting (flattened)
                    "imprinting": imprinting_info,
                    # Supplier (flattened)
                    "supplier_info": supplier_info,
                    # Production (flattened)
                    "production_info": production_info,
                    # Shipping (flattened)
                    "shipping": shipping_info,
                    # Specifications (flattened)
                    "specifications": specifications_info,
                    # Other fields from original product
                    "variants": product.get("variants", []),
                    "warnings": product.get("warnings", []),
                    "services": product.get("services", []),
                    "images": product.get("images", []),
                    "virtual_samples": product.get("virtual_samples", []),
                    "raw_data": product.get("raw_data", {}),
                    "extraction_time": product.get("extraction_time", 0),
                    "extraction_method": product.get("extraction_method", ""),
                    "scraped_date": product.get("scraped_date", ""),
                    "related_products": product.get("related_products", []),
                    "categories": product.get("categories", []),
                    "themes": product.get("themes", []),
                    "color_images": product.get("color_images", {}),
                }
            )

            # Add art template info
            art_template = product.get("art_template", {})
            if art_template.get("url"):
                enhanced_product["product_art_url"] = art_template["url"]
            if art_template.get("local_file"):
                enhanced_product["art_template_local_file"] = art_template["local_file"]

            # Add FPD config at TOP LEVEL (this is what the plugin expects)
            fpd_config = product.get("fpd_config", {})
            if fpd_config:
                enhanced_product["fpd_config"] = fpd_config
                logging.info(f"✅ Added FPD config to enhanced product")
            else:
                logging.warning(f"⚠️ No FPD config found in product data")

            # Add meta info
            meta_info = product.get("meta", {})
            if meta_info:
                enhanced_product["meta"] = meta_info

            # Update with HitPromo data if available
            if all_data.get("main_image"):
                enhanced_product["image_url"] = all_data["main_image"]

            if all_data.get("gallery_images"):
                enhanced_product["images"] = [
                    {"url": img, "description": ""}
                    for img in all_data["gallery_images"]
                ]

            if all_data.get("color_images"):
                enhanced_product["color_images"] = all_data["color_images"]

            if all_data.get("art_template_url"):
                enhanced_product["product_art_url"] = all_data["art_template_url"]

                # Download art template only if not skipped
                if not hasattr(self, 'skip_art_templates') or not self.skip_art_templates:
                    local_file = self.art_processor.download_art_template(
                        all_data["art_template_url"],
                        enhanced_product.get("product_number", ""),
                    )
                    if local_file:
                        enhanced_product["art_template_local_file"] = local_file
                else:
                    logging.info(f"⏭️ Skipping art template download for product {enhanced_product.get('product_number', 'unknown')}")

            logging.info(
                f"✅ Enhanced product {enhanced_product.get('product_id', 'unknown')} with flattened structure"
            )
            return enhanced_product

        except Exception as e:
            logging.error(f"❌ Error enhancing product with data: {e}")
            return product

    def enhance_all_batch_files(self, batch_dir: str = "batch", max_batch_files: int = None, 
                               start_batch_index: int = 0, max_time_minutes: int = None,
                               workflow_state_file: str = None) -> Dict:
        """Enhance all batch files in a directory with optional chunking"""
        start_time = time.time()

        try:
            if not os.path.exists(batch_dir):
                logging.error(f"❌ Batch directory not found: {batch_dir}")
                return {"success": False, "error": "Batch directory not found"}

            # Find all batch files
            batch_files = []
            for file in os.listdir(batch_dir):
                if (
                    file.startswith("batch_")
                    and file.endswith(".jsonl")
                    and not file.endswith("_enhanced.jsonl")
                ):
                    batch_files.append(os.path.join(batch_dir, file))

            if not batch_files:
                logging.warning(f"⚠️ No batch files found in {batch_dir}")
                return {"success": False, "error": "No batch files found"}

            # Sort batch files for consistent processing order
            batch_files.sort()

            # Apply chunking parameters
            total_batch_files = len(batch_files)
            end_batch_index = total_batch_files
            
            if max_batch_files:
                end_batch_index = min(start_batch_index + max_batch_files, total_batch_files)
            
            # Get files for this chunk
            chunk_files = batch_files[start_batch_index:end_batch_index]
            
            logging.info(f"📁 Found {total_batch_files} total batch files")
            logging.info(f"🔄 Processing chunk: files {start_batch_index + 1}-{end_batch_index} ({len(chunk_files)} files)")
            logging.info(f"📄 Chunk files: {[os.path.basename(f) for f in chunk_files]}")

            # Enhance each batch file in the chunk
            processed_files = []
            for i, batch_file in enumerate(chunk_files, 1):
                current_time = time.time()
                elapsed_minutes = (current_time - start_time) / 60
                
                # Check time limit
                if max_time_minutes and elapsed_minutes >= max_time_minutes:
                    logging.warning(f"⏰ Time limit reached ({elapsed_minutes:.1f} minutes >= {max_time_minutes} minutes)")
                    logging.info(f"🛑 Stopping processing after {i-1} files in this chunk")
                    break
                
                logging.info(
                    f"🔄 Processing file {start_batch_index + i}/{total_batch_files}: {os.path.basename(batch_file)}"
                )

                success = self.enhance_batch_file(batch_file)
                if success:
                    processed_files.append(os.path.basename(batch_file))
                    # Be nice to the server
                    if i < len(chunk_files):
                        time.sleep(1)

            total_time = time.time() - start_time

            # Create workflow state for chunking
            workflow_state = {
                "total_batch_files": total_batch_files,
                "processed_batch_files": start_batch_index + len(processed_files),
                "current_batch_index": start_batch_index + len(processed_files),
                "elapsed_time_minutes": total_time / 60,
                "max_time_minutes": max_time_minutes,
                "batch_files_per_run": max_batch_files,
                "status": "in_progress" if (start_batch_index + len(processed_files)) < total_batch_files else "completed",
                "remaining_batch_files": [os.path.basename(f) for f in batch_files[start_batch_index + len(processed_files):]],
                "completed_batch_files": [os.path.basename(f) for f in batch_files[:start_batch_index + len(processed_files)]],
                "processed_in_this_run": processed_files,
                "resume_data": {
                    "last_processed_batch": os.path.basename(batch_files[start_batch_index + len(processed_files) - 1]) if processed_files else None,
                    "last_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "next_batch_index": start_batch_index + len(processed_files)
                }
            }

            # Save workflow state if requested
            if workflow_state_file:
                try:
                    os.makedirs(os.path.dirname(workflow_state_file), exist_ok=True)
                    with open(workflow_state_file, 'w') as f:
                        json.dump(workflow_state, f, indent=2)
                    logging.info(f"💾 Workflow state saved to: {workflow_state_file}")
                except Exception as e:
                    logging.error(f"❌ Error saving workflow state: {e}")

            # Summary
            summary = {
                "success": True,
                "total_files": total_batch_files,
                "processed_in_chunk": len(processed_files),
                "enhanced_files": self.enhanced_count,
                "error_files": self.error_count,
                "total_time": total_time,
                "elapsed_minutes": total_time / 60,
                "enhanced_batch_dir": os.path.abspath(
                    os.path.join(batch_dir, "..", "enhanced")
                ),
                "workflow_state": workflow_state,
                "chunking_info": {
                    "start_index": start_batch_index,
                    "end_index": start_batch_index + len(processed_files),
                    "max_batch_files": max_batch_files,
                    "max_time_minutes": max_time_minutes,
                    "time_limit_reached": max_time_minutes and (total_time / 60) >= max_time_minutes
                }
            }

            logging.info(f"✅ Batch enhancement completed:")
            logging.info(f"   📁 Total files: {summary['total_files']}")
            logging.info(f"   🔄 Processed in chunk: {summary['processed_in_chunk']}")
            logging.info(f"   ✅ Enhanced: {summary['enhanced_files']}")
            logging.info(f"   ❌ Errors: {summary['error_files']}")
            logging.info(f"   ⏱️  Processing time: {total_time:.2f}s ({total_time/60:.1f} minutes)")
            
            if workflow_state["status"] == "in_progress":
                logging.info(f"   🔄 More files remaining: {len(workflow_state['remaining_batch_files'])}")
                logging.info(f"   📄 Next batch index: {workflow_state['resume_data']['next_batch_index']}")

            return summary

        except Exception as e:
            logging.error(f"❌ Error enhancing batch files: {e}")
            return {"success": False, "error": str(e)}


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Optimized batch file enhancer - Single Request"
    )
    parser.add_argument(
        "--batch-dir", default="batch", help="Directory containing batch files"
    )
    parser.add_argument("--max-workers", type=int, default=5, help="Max worker threads")
    parser.add_argument(
        "--max-concurrent", type=int, default=10, help="Max concurrent requests"
    )
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    
    # New chunking parameters (backward compatible)
    parser.add_argument(
        "--max-batch-files", type=int, default=None, 
        help="Maximum number of batch files to process per run (for chunking)"
    )
    parser.add_argument(
        "--start-batch-index", type=int, default=0,
        help="Start processing from this batch file index (0-based)"
    )
    parser.add_argument(
        "--max-time-minutes", type=int, default=None,
        help="Maximum processing time in minutes before stopping"
    )
    parser.add_argument(
        "--workflow-state-file", type=str, default=None,
        help="Path to save workflow state for chunking"
    )
    
    # Art template control
    parser.add_argument(
        "--skip-art-templates", action="store_true",
        help="Skip downloading art templates (faster processing)"
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # Create optimized processor
    art_processor = SingleRequestArtProcessor(max_concurrent=args.max_concurrent)

    # Create enhancer
    enhancer = OptimizedBatchFileEnhancer(
        art_processor, 
        max_workers=args.max_workers,
        skip_art_templates=args.skip_art_templates
    )

    # Enhance all batch files with chunking parameters
    result = enhancer.enhance_all_batch_files(
        batch_dir=args.batch_dir,
        max_batch_files=args.max_batch_files,
        start_batch_index=args.start_batch_index,
        max_time_minutes=args.max_time_minutes,
        workflow_state_file=args.workflow_state_file
    )

    if result["success"]:
        print(f"\n🎉 Batch enhancement completed successfully!")
        print(
            f"   📁 Enhanced {result['enhanced_files']} out of {result['total_files']} files"
        )
        print(f"   🔄 Processed in chunk: {result.get('processed_in_chunk', 'N/A')}")
        print(f"   ⏱️  Total time: {result['total_time']:.2f}s ({result.get('elapsed_minutes', 0):.1f} minutes)")
        print(f"   📂 Enhanced files saved with '_enhanced.jsonl' suffix")
        
        # Show chunking info if available
        if 'chunking_info' in result:
            chunk_info = result['chunking_info']
            print(f"   🔄 Chunking: {chunk_info['start_index']}-{chunk_info['end_index']} of {result['total_files']}")
            if chunk_info.get('time_limit_reached'):
                print(f"   ⏰ Time limit reached ({chunk_info['max_time_minutes']} minutes)")
            if result.get('workflow_state', {}).get('status') == 'in_progress':
                print(f"   🔄 More files remaining: {len(result['workflow_state']['remaining_batch_files'])}")
                print(f"   📄 Next batch index: {result['workflow_state']['resume_data']['next_batch_index']}")
    else:
        print(f"\n❌ Batch enhancement failed: {result.get('error', 'Unknown error')}")

    return result["success"]


if __name__ == "__main__":
    main()
