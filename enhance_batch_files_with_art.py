#!/usr/bin/env python3
"""
Simplified Batch File Processor with Art Template Integration

This script enhances batch files by:
1. Adding product art URLs to all product data
2. Downloading art templates from Hit Promotional Products
3. Creating FPD configurations based on product data imprint information
"""

import os
import json
import re
import requests
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
import time
from pathlib import Path

# BeautifulSoup for HTML parsing
try:
    from bs4 import BeautifulSoup

    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    print("⚠️ BeautifulSoup not available. Install with: pip install beautifulsoup4")


@dataclass
class ImprintMethod:
    """Represents an imprint method with its locations and sizes"""

    name: str
    code: str
    locations: List[Dict]  # List of location options
    sizes: List[Dict]  # List of size options
    charges: List[Dict]  # List of charges


@dataclass
class ImprintLocation:
    """Represents an imprint location with its dimensions"""

    name: str
    vendor_code: str
    method: str
    width_inches: float
    height_inches: float


@dataclass
class FPDConfig:
    """FPD configuration based on product data imprint information"""

    stage_width: int = 800
    stage_height: int = 600
    views: List[Dict] = None
    imprint_areas: List[Dict] = None
    design_elements: List[Dict] = None
    restrictions: Dict = None
    product_type: str = "catalog"
    enable_fpd: bool = True
    create_design_areas: bool = True


class ArtTemplateProcessor:
    """Processes art templates - downloads only, no OCR processing"""

    def __init__(
        self,
        base_url: str = "https://www.hitpromo.net",
        cache_dir: str = "art_templates",
    ):
        self.base_url = base_url
        self.cache_dir = cache_dir
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )

        # Create art_templates directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
        logging.info(f"📁 Art templates directory: {self.cache_dir}")

    def get_art_templates_info(self) -> Dict:
        """Get information about downloaded art templates"""
        try:
            if not os.path.exists(self.cache_dir):
                return {
                    "art_templates_dir": self.cache_dir,
                    "total_files": 0,
                    "total_size": 0,
                    "file_types": {},
                }

            total_files = 0
            total_size = 0
            file_types = {}

            for file in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, file)
                if os.path.isfile(file_path):
                    total_files += 1
                    total_size += os.path.getsize(file_path)

                    # Count file types
                    file_ext = os.path.splitext(file)[1].lower()
                    file_types[file_ext] = file_types.get(file_ext, 0) + 1

            return {
                "art_templates_dir": self.cache_dir,
                "total_files": total_files,
                "total_size": total_size,
                "file_types": file_types,
            }
        except Exception as e:
            logging.error(f"❌ Error getting art templates info: {e}")
            return {
                "art_templates_dir": self.cache_dir,
                "total_files": 0,
                "total_size": 0,
                "file_types": {},
            }

    def clear_art_templates(self) -> bool:
        """Clear all downloaded art templates"""
        try:
            if os.path.exists(self.cache_dir):
                for file in os.listdir(self.cache_dir):
                    file_path = os.path.join(self.cache_dir, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                logging.info(f"🗑️ Cleared all art templates from {self.cache_dir}")
            return True
        except Exception as e:
            logging.error(f"❌ Error clearing art templates: {e}")
            return False

    def _get_cached_file_path(self, url: str, product_number: str) -> str:
        """Get the cached file path for a given URL and product number"""
        try:
            # Parse the URL to get the file extension
            parsed_url = urlparse(url)
            path = parsed_url.path
            filename = os.path.basename(path)

            # If no filename or extension, create one based on product number
            if not filename or "." not in filename:
                # Try to determine file type from URL
                if "pdf" in url.lower():
                    filename = f"{product_number}.pdf"
                elif "ai" in url.lower():
                    filename = f"{product_number}.ai"
                elif "eps" in url.lower():
                    filename = f"{product_number}.eps"
                else:
                    filename = f"{product_number}.pdf"  # Default to PDF

            return os.path.join(self.cache_dir, filename)
        except Exception as e:
            logging.error(f"❌ Error getting cached file path: {e}")
            return os.path.join(self.cache_dir, f"{product_number}.pdf")

    def get_product_art_url(self, product_number: str) -> Optional[str]:
        """Get the art template URL for a product number"""
        try:
            # Construct the product page URL
            product_url = f"{self.base_url}/product/show/{product_number}"

            logging.info(f"🔍 Fetching art template URL for product {product_number}")

            # Fetch the product page
            response = self.session.get(product_url, timeout=30)
            response.raise_for_status()

            html_content = response.text

            # Extract art template URL using regex
            art_url = self._extract_art_url_regex(html_content, product_number)

            if art_url:
                logging.info(f"✅ Found art template URL: {art_url}")
                return art_url
            else:
                logging.warning(
                    f"⚠️ No art template URL found for product {product_number}"
                )
            return None

        except Exception as e:
            logging.error(
                f"❌ Error getting art template URL for {product_number}: {e}"
            )
            return None

    def _extract_art_url_regex(
        self, html_content: str, product_number: str
    ) -> Optional[str]:
        """Extract art template URL using regex patterns"""
        try:
            # Pattern to find art template URLs
            patterns = [
                rf'https://www\.hitpromo\.net/fs/artTemplates/{product_number}/[^"\s]+',
                rf'https://www\.hitpromo\.net/artTemplates/{product_number}/[^"\s]+',
                rf'https://www\.hitpromo\.net/fs/artTemplates/[^"\s]*{product_number}[^"\s]*',
            ]

            for pattern in patterns:
                matches = re.findall(pattern, html_content)
            if matches:
                return matches[0]

            return None
        except Exception as e:
            logging.error(f"❌ Error extracting art URL with regex: {e}")
            return None

    def download_art_template(self, art_url: str, product_number: str) -> Optional[str]:
        """Download art template file"""
        try:
            # Get cached file path
            cached_path = self._get_cached_file_path(art_url, product_number)

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

    def extract_imprint_structure_from_product_data(
        self, product_data: Dict
    ) -> List[ImprintLocation]:
        """Extract complete imprint structure from product data - UNIQUE LOCATIONS = UNIQUE VIEWS"""
        imprint_locations = []
        unique_locations = set()  # Track unique location names

        try:
            imprinting = product_data.get("imprinting", {})
            imprinting_methods = imprinting.get("imprinting_methods", [])

            for method in imprinting_methods:
                method_name = method.get("Name", "")
                method_code = method.get("Code", "")

                # Get locations and sizes for this method
                options = method.get("Options", [])
                locations = []
                sizes = []

                for option in options:
                    option_type = option.get("Type", "")
                    values = option.get("Values", [])

                    if option_type == "Imprint Location":
                        locations = values
                    elif option_type == "Imprint Size":
                        sizes = values

                # Create imprint locations for each UNIQUE location only
                # ONE VIEW PER LOCATION: Each unique location gets one view, regardless of method or size
                for location in locations:
                    location_name = location.get("Name", "")
                    vendor_code = location.get("VendorCode", "")

                    # Only create a view if this location hasn't been seen before
                    if location_name not in unique_locations:
                        unique_locations.add(location_name)

                        # Use the first available size for this location (or default if none)
                        if sizes:
                            size_info = sizes[0]  # Use first size as representative
                            size_name = size_info.get("Name", "")
                            size_code = size_info.get("Code", "")

                            # Parse dimensions from size name (e.g., "2.5000\"H x 2.5000\"W")
                            dimensions = self._parse_imprint_dimensions(size_name)

                            if dimensions:
                                imprint_location = ImprintLocation(
                                    name=location_name,
                                    vendor_code=vendor_code,
                                    method=method_name,
                                    width_inches=dimensions["width"],
                                    height_inches=dimensions["height"],
                                )
                                imprint_locations.append(imprint_location)

                                logging.info(
                                    f"📐 Found imprint location: {location_name} ({method_name}) - {dimensions['width']}\" x {dimensions['height']}\""
                                )

        except Exception as e:
            logging.error(f"❌ Error extracting imprint structure: {e}")

        return imprint_locations

    def _parse_imprint_dimensions(self, size_name: str) -> Optional[Dict]:
        """Parse imprint dimensions from size name"""
        try:
            # Pattern to match dimensions like "2.5000\"H x 2.5000\"W"
            pattern = r'(\d+\.?\d*)"H\s*x\s*(\d+\.?\d*)"W'
            match = re.search(pattern, size_name)

            if match:
                height = float(match.group(1))
                width = float(match.group(2))
                return {"width": width, "height": height}

            return None
        except Exception as e:
            logging.error(f"❌ Error parsing imprint dimensions: {e}")
            return None

    def create_fpd_config_from_product_data(self, product_data: Dict) -> FPDConfig:
        """Create FPD configuration from product data - MULTIPLE METHODS = MULTIPLE VIEWS"""
        try:
            # Extract product dimensions for stage size
            product_dimensions = self._extract_product_dimensions(product_data)

            # Extract imprint structure to get imprint area dimensions
            imprint_locations = self.extract_imprint_structure_from_product_data(
                product_data
            )

            # Calculate stage size with priority: product dimensions > imprint area dimensions > default
            dpi = 150
            stage_width = 1160  # Default
            stage_height = 1500  # Default

            if product_dimensions["width"] and product_dimensions["height"]:
                # Use product dimensions with padding
                stage_width = (
                    int(product_dimensions["width"] * dpi) + 200
                )  # More padding for better design
                stage_height = int(product_dimensions["height"] * dpi) + 200
                logging.info(
                    f"🎨 Stage size from product dimensions: {stage_width}x{stage_height}px"
                )
            elif imprint_locations:
                # Use imprint area dimensions with padding
                max_imprint_width = 0
                max_imprint_height = 0

                for imprint_location in imprint_locations:
                    imprint_width_pixels = int(imprint_location.width_inches * dpi)
                    imprint_height_pixels = int(imprint_location.height_inches * dpi)
                    max_imprint_width = max(max_imprint_width, imprint_width_pixels)
                    max_imprint_height = max(max_imprint_height, imprint_height_pixels)

                    # Add padding around imprint area (at least 200px on each side)
                    stage_width = max_imprint_width + 400
                    stage_height = max_imprint_height + 400
                    logging.info(
                        f"🎨 Stage size from imprint area dimensions: {stage_width}x{stage_height}px"
                        )
                else:
                    logging.warning(
                    f"⚠️ Using default stage size - no product or imprint dimensions found"
                        )

            # imprint_locations already extracted above for stage size calculation

            # Create views for each imprint method and location
            views = []

            # Group imprint locations by method for better organization
            method_groups = {}
            for imprint_location in imprint_locations:
                method = imprint_location.method
                if method not in method_groups:
                    method_groups[method] = []
                method_groups[method].append(imprint_location)

            # Create views for each method and location
            view_index = 0
            for method_name, locations in method_groups.items():
                for imprint_location in locations:
                    # Convert imprint dimensions to pixels
                    dpi = 150
                    width_pixels = int(imprint_location.width_inches * dpi)
                    height_pixels = int(imprint_location.height_inches * dpi)

                    # Calculate position (center the design area)
                    x = (stage_width - width_pixels) // 2
                    y = (stage_height - height_pixels) // 2

                    # Get view-specific image
                    view_image = self._get_view_specific_image(
                        product_data, view_index, len(imprint_locations)
                    )

                    # Create view with elements
                    view = {
                        "title": imprint_location.name,
                        "elements": [
                            # View-specific product image
                            {
                                "type": "image",
                                "source": view_image,
                                "title": f"Base Image - {imprint_location.name}",
                            },
                            # Design area for this imprint method/location
                            {
                                "type": "design",
                                "title": f"Design Area - {imprint_location.method}",
                                "x": x,
                                "y": y,
                                "width": width_pixels,
                                "height": height_pixels,
                                "parameters": {
                                    "z": 10,
                                    "method": imprint_location.method,
                                    "location": imprint_location.name,
                                },
                            },
                        ],
                    }
                    views.append(view)

                    logging.info(
                        f"🎨 Created view: {imprint_location.name} - {width_pixels}x{height_pixels}px at ({x},{y})"
                    )
                    view_index += 1

            # Create FPD config in the simpler format
            fpd_config = FPDConfig(
                stage_width=stage_width,
                stage_height=stage_height,
                views=views,
                imprint_areas=[],  # Not used in this format
                design_elements=[],  # Not used in this format
                restrictions={
                    "allow_text": True,
                    "allow_images": True,
                    "allow_shapes": True,
                },
                product_type="catalog",
                enable_fpd=True,
                create_design_areas=True,
            )

            logging.info(f"✅ Created FPD config with {len(views)} views")
            return fpd_config

        except Exception as e:
            logging.error(f"❌ Error creating FPD config: {e}")
            return FPDConfig()

    def _extract_product_size(self, product_data: Dict) -> str:
        """Extract product size"""
        try:
            sizes = product_data.get("attributes", {}).get("sizes", [])
            if sizes:
                return sizes[0].get("Name", "")
            return ""
        except Exception as e:
            logging.error(f"❌ Error extracting product size: {e}")
            return ""

    def _get_view_specific_image(
        self, product_data: Dict, view_index: int, total_views: int
    ) -> str:
        """Get the most appropriate image for a specific view"""
        try:
            # Priority order: virtual_samples > images array > main image
            available_images = []

            # 1. Add virtual samples (often show different angles)
            virtual_samples = product_data.get("virtual_samples", [])
            for sample in virtual_samples:
                if isinstance(sample, dict):
                    image_url = sample.get("url", "")
                    if not image_url and sample.get("ImageUrl"):
                        # Convert relative URL to full URL
                        image_url = (
                            f"https://api.asicentral.com/v1/{sample['ImageUrl']}"
                        )
                    if image_url:
                        # Convert to larger image URL
                        large_image_url = self._get_large_image_url(image_url)
                        available_images.append(
                            {
                                "url": large_image_url,
                                "type": "virtual_sample",
                                "description": sample.get("Description", ""),
                                "is_primary": sample.get("IsPrimary", False),
                            }
                        )

            # 2. Add images from images array
            images = product_data.get("images", [])
            for img in images:
                if isinstance(img, dict):
                    image_url = img.get("url", "")
                    if image_url:
                        # Convert to larger image URL
                        large_image_url = self._get_large_image_url(image_url)
                        available_images.append(
                            {
                                "url": large_image_url,
                                "type": "product_image",
                                "description": img.get("description", ""),
                                "is_primary": False,
                            }
                        )

            # 3. Add main image as fallback
            main_image = product_data.get("image_url", "")
            if main_image:
                # Convert to larger image URL
                large_main_image = self._get_large_image_url(main_image)
                available_images.append(
                    {
                        "url": large_main_image,
                        "type": "main_image",
                        "description": "Main Product Image",
                        "is_primary": True,
                    }
                )

            # If no images available, return empty string
            if not available_images:
                logging.warning(
                    f"⚠️ No images available for product {product_data.get('product_id', 'unknown')}"
                )
                return ""

            # Select image based on view index and available images
            if len(available_images) == 1:
                # Only one image available, use it for all views
                selected_image = available_images[0]["url"]
                logging.info(f"🎨 Using single image for all views: {selected_image}")
            else:
                # Multiple images available, distribute them across views
                image_index = view_index % len(available_images)
                selected_image = available_images[image_index]["url"]
                image_type = available_images[image_index]["type"]
                logging.info(
                    f"🎨 View {view_index + 1}/{total_views}: Using {image_type} image: {selected_image}"
                )

            return selected_image

        except Exception as e:
            logging.error(f"❌ Error getting view-specific image: {e}")
            # Fallback to main image
            main_image = product_data.get("image_url", "")
            if main_image:
                return self._get_large_image_url(main_image)
            return ""

    def _get_large_image_url(self, original_url: str) -> str:
        """Convert a small image URL to a larger, higher-quality version"""
        if not original_url:
            return ""

        try:
            # If it's already a large image URL, return as-is
            if "large" in original_url.lower() or "high" in original_url.lower():
                return original_url

            # Handle different URL patterns
            if "api.asicentral.com" in original_url:
                # API URLs - try to get larger version
                # Remove any size parameters and add large size
                base_url = original_url.split("?")[0]  # Remove query parameters

                # Try different large image URL patterns
                large_urls_to_try = [
                    f"{base_url}?size=large",
                    f"{base_url}?size=800x800",
                    f"{base_url}?size=1024x1024",
                    f"{base_url}?width=800&height=800",
                    f"{base_url}?width=1024&height=1024",
                    # Try replacing common small image patterns
                    original_url.replace("thumb", "large"),
                    original_url.replace("small", "large"),
                    original_url.replace("150x150", "800x800"),
                    original_url.replace("300x300", "800x800"),
                    # If no size parameters, add large size
                    (
                        f"{original_url}&size=large"
                        if "?" in original_url
                        else f"{original_url}?size=large"
                    ),
                ]

                # Return the first pattern (we'll let the PHP side handle fallback if needed)
                return large_urls_to_try[0]

            elif "espweb.asicentral.com" in original_url:
                # Web URLs - try to get larger version
                base_url = original_url.split("?")[0]
                large_urls_to_try = [
                    f"{base_url}?size=large",
                    f"{base_url}?size=800x800",
                    f"{base_url}?size=1024x1024",
                    original_url.replace("thumb", "large"),
                    original_url.replace("small", "large"),
                    (
                        f"{original_url}&size=large"
                        if "?" in original_url
                        else f"{original_url}?size=large"
                    ),
                ]
                return large_urls_to_try[0]

            else:
                # Other URLs - try common patterns
                base_url = original_url.split("?")[0]
                large_urls_to_try = [
                    f"{base_url}?size=large",
                    f"{base_url}?size=800x800",
                    f"{base_url}?size=1024x1024",
                    original_url.replace("thumb", "large"),
                    original_url.replace("small", "large"),
                    (
                        f"{original_url}&size=large"
                        if "?" in original_url
                        else f"{original_url}?size=large"
                    ),
                ]
                return large_urls_to_try[0]

        except Exception as e:
            logging.warning(f"⚠️ Error converting to large image URL: {e}")
            return original_url

    def create_optimized_structure(self, product_data: Dict) -> Dict:
        """Create a clean, optimized product structure without repetition"""
        optimized = {
            "product": {
                "id": product_data.get("product_id", ""),
                "name": product_data.get("name", ""),
                "description": product_data.get("description", ""),
                "short_description": product_data.get("short_description", ""),
                "sku": self._extract_primary_sku(product_data),
                "product_number": product_data.get("product_number", ""),
                "featured_image": product_data.get("image_url", ""),
                "gallery_images": self._extract_gallery_images(product_data),
                "virtual_samples": product_data.get("virtual_samples", []),
                "product_url": product_data.get("product_url", ""),
                "extraction_time": product_data.get("extraction_time", 0),
                "extraction_method": product_data.get("extraction_method", ""),
                "scraped_date": product_data.get("scraped_date", ""),
            },
            "pricing": {
                "regular_price": self._extract_base_price(product_data),
                "sale_price": self._extract_sale_price(product_data),
                "currency": product_data.get("pricing_info", {}).get("currency", "USD"),
                "bulk_pricing": self._extract_bulk_pricing(product_data),
                "setup_charges": self._extract_setup_charges(product_data),
            },
            "attributes": {
                "colors": self._extract_colors_optimized(product_data),
                "sizes": self._extract_sizes_optimized(product_data),
                "materials": self._extract_materials_optimized(product_data),
                "features": product_data.get("attributes", {}).get("features", []),
                "tags": product_data.get("attributes", {}).get("tags", []),
            },
            "imprinting": {
                "methods": self._extract_imprint_methods_optimized(product_data),
                "colors": self._extract_imprinting_colors_optimized(product_data),
            },
            "supplier": {
                "name": product_data.get("supplier_info", {}).get("supplier_name", ""),
                "id": product_data.get("supplier_info", {}).get("supplier_id", ""),
                "asi_number": product_data.get("supplier_info", {}).get(
                    "asi_number", ""
                ),
                "email": product_data.get("supplier_info", {}).get("email", ""),
                "phone": product_data.get("supplier_info", {}).get("phone", ""),
                "rating": product_data.get("supplier_info", {}).get(
                    "supplier_rating", ""
                ),
                "websites": product_data.get("supplier_info", {}).get("websites", []),
                "location": product_data.get("supplier_info", {}).get(
                    "supplier_location", ""
                ),
            },
            "production": {
                "production_time": product_data.get("production_info", {}).get(
                    "production_time", []
                ),
                "minimum_order": product_data.get("production_info", {}).get(
                    "minimum_order", ""
                ),
                "maximum_order": product_data.get("production_info", {}).get(
                    "maximum_order", ""
                ),
                "origin": product_data.get("production_info", {}).get("origin", []),
                "trade_names": product_data.get("production_info", {}).get(
                    "trade_names", []
                ),
            },
            "shipping": {
                "weight_unit": product_data.get("shipping", {}).get("weight_unit", ""),
                "weight_per_package": product_data.get("shipping", {}).get(
                    "weight_per_package", ""
                ),
                "package_unit": product_data.get("shipping", {}).get(
                    "package_unit", ""
                ),
                "items_per_package": product_data.get("shipping", {}).get(
                    "items_per_package", ""
                ),
                "fob_points": product_data.get("shipping", {}).get("fob_points", []),
            },
            "specifications": {
                "weight": self._extract_weight(product_data),
                "dimensions": self._extract_dimensions(product_data),
                "materials": product_data.get("attributes", {}).get("materials", []),
                "features": product_data.get("attributes", {}).get("features", []),
            },
            "categories": self._extract_categories(product_data),
            "themes": product_data.get("raw_data", {}).get("Themes", []),
            "related_products": product_data.get("related_products", []),
            "services": product_data.get("services", []),
            "warnings": product_data.get("warnings", []),
            "variants": product_data.get("variants", []),
            "fpd_config": self._create_fpd_config_dict(product_data),
            "art_template": {
                "url": product_data.get("product_art_url", ""),
                "local_file": product_data.get("art_template_local_file", ""),
                "downloaded": bool(product_data.get("art_template_local_file", "")),
            },
            "meta": {
                "vendor_product_id": product_data.get("product_number", ""),
                "vendor_product_url": product_data.get("product_url", ""),
                "supplier_id": product_data.get("supplier_info", {}).get(
                    "supplier_id", ""
                ),
                "supplier_name": product_data.get("supplier_info", {}).get(
                    "supplier_name", ""
                ),
                "asi_number": product_data.get("supplier_info", {}).get(
                    "asi_number", ""
                ),
                "origin": self._extract_origin(product_data),
                "production_time": self._extract_production_time(product_data),
                "minimum_order": self._extract_minimum_order(product_data),
                "weight": self._extract_weight(product_data),
                "dimensions": self._extract_dimensions(product_data),
                "related_products_count": len(product_data.get("related_products", [])),
                "services_count": len(product_data.get("services", [])),
                "warnings_count": len(product_data.get("warnings", [])),
            },
        }

        return optimized

    def _extract_product_dimensions(self, product_data: Dict) -> Dict:
        """Extract product dimensions from product data"""
        dimensions = {"width": None, "height": None, "depth": None, "source": None}

        try:
            # Try to extract from sizes
            sizes = product_data.get("attributes", {}).get("sizes", [])
            if sizes:
                size_info = sizes[0]
                size_name = size_info.get("Name", "")

                # Parse size (e.g., "7.5000 \"")
                pattern = r"(\d+\.?\d*)"
                match = re.search(pattern, size_name)
                if match:
                    dimensions["width"] = float(match.group(1))
                    dimensions["height"] = float(
                        match.group(1)
                    )  # Assume square for now
                    dimensions["source"] = "product_sizes"
                    logging.info(
                        f"📏 Extracted product dimensions: {dimensions['width']} x {dimensions['height']}"
                    )

        except Exception as e:
            logging.error(f"❌ Error extracting product dimensions: {e}")

        return dimensions

    def _create_fpd_config_dict(self, product_data: Dict) -> Dict:
        """Create FPD configuration dictionary matching WordPress FPD plugin structure"""
        try:
            # Get the FPD config object
            fpd_config = self.create_fpd_config_from_product_data(product_data)

            # Convert to dictionary format matching WordPress FPD plugin expectations
            fpd_dict = {
                "product_type": "catalog",
                "enable_fpd": True,
                "create_design_areas": True,
                "stage_config": {
                    "width": fpd_config.stage_width,
                    "height": fpd_config.stage_height,
                },
                "restrictions": fpd_config.restrictions
                or {"allow_text": True, "allow_images": True, "allow_shapes": True},
                "imprint_areas": fpd_config.imprint_areas or [],
                "design_elements": fpd_config.design_elements or [],
                "views": fpd_config.views or [],
                "fpd_product_structure": {
                    "title": "Product Design",
                    "thumbnail": "",
                    "options": {
                        "stageWidth": fpd_config.stage_width,
                        "stageHeight": fpd_config.stage_height,
                    },
                    "views": fpd_config.views or [],
                },
            }

            return fpd_dict

        except Exception as e:
            logging.error(f"❌ Error creating FPD config dict: {e}")
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
                "imprint_areas": [],
                "design_elements": [],
                "views": [],
                "fpd_product_structure": {
                    "title": "Product Design",
                    "thumbnail": "",
                    "options": {"stageWidth": 800, "stageHeight": 600},
                    "views": [],
                },
            }

    def _extract_primary_sku(self, product_data: Dict) -> str:
        """Extract the primary SKU for WooCommerce"""
        sku_data = product_data.get("sku", [])
        if sku_data and len(sku_data) > 0:
            return sku_data[0].get("SKU", "")
        return product_data.get("product_number", "")

    def _extract_gallery_images(self, product_data: Dict) -> List[str]:
        """Extract gallery images"""
        images = product_data.get("images", [])
        return [img.get("url", "") for img in images if img.get("url")]

    def _extract_base_price(self, product_data: Dict) -> float:
        """Extract base price for WooCommerce"""
        pricing = product_data.get("pricing_info", {})
        base_price = pricing.get("base_price", {})
        return base_price.get("Price", 0.0)

    def _extract_sale_price(self, product_data: Dict) -> float:
        """Extract sale price for WooCommerce"""
        pricing = product_data.get("pricing_info", {})
        discount_price = pricing.get("discount_price", {})
        return discount_price.get("Price", 0.0)

    def _extract_bulk_pricing(self, product_data: Dict) -> List[Dict]:
        """Extract bulk pricing for WooCommerce"""
        pricing = product_data.get("pricing_info", {})
        bulk_pricing = pricing.get("bulk_pricing", [])

        return [
            {
                "min_qty": tier.get("Quantity", {}).get("From", 0),
                "max_qty": tier.get("Quantity", {}).get("To", 0),
                "price": tier.get("Price", 0.0),
                "cost": tier.get("Cost", 0.0),
            }
            for tier in bulk_pricing
        ]

    def _extract_woo_attributes(self, product_data: Dict) -> List[Dict]:
        """Extract WooCommerce attributes"""
        attributes = product_data.get("attributes", {})
        woo_attributes = []

        # Colors
        colors = attributes.get("colors", [])
        if colors:
            woo_attributes.append(
                {
                    "name": "Color",
                    "visible": True,
                    "variation": True,
                    "options": [color.get("Name", "") for color in colors],
                }
            )

        # Sizes
        sizes = attributes.get("sizes", [])
        if sizes:
            woo_attributes.append(
                {
                    "name": "Size",
                    "visible": True,
                    "variation": True,
                    "options": [size.get("Name", "") for size in sizes],
                }
            )

        # Materials
        materials = attributes.get("materials", [])
        if materials:
            woo_attributes.append(
                {
                    "name": "Material",
                    "visible": True,
                    "variation": False,
                    "options": [material.get("Name", "") for material in materials],
                }
            )

        return woo_attributes

    def _extract_setup_charges(self, product_data: Dict) -> List[Dict]:
        """Extract setup charges for ACF repeater"""
        setup_charges = []
        imprinting = product_data.get("imprinting", {})

        for method in imprinting.get("imprinting_methods", []):
            charges = method.get("Charges", [])
            for charge in charges:
                if charge.get("Type") == "Set-up Charge":
                    setup_charges.append(
                        {
                            "method_name": method.get("Name", ""),
                            "method_code": method.get("Code", ""),
                            "charge_type": charge.get("Type", ""),
                            "description": charge.get("Description", ""),
                            "price": charge.get("Prices", [{}])[0].get("Price", 0.0),
                            "cost": charge.get("Prices", [{}])[0].get("Cost", 0.0),
                            "usage_level": charge.get("UsageLevel", ""),
                            "is_required": charge.get("IsRequired", False),
                            "vendor_code": charge.get("VendorCode", ""),
                        }
                    )

        return setup_charges

    def _extract_pricing_tiers(self, product_data: Dict) -> List[Dict]:
        """Extract pricing tiers for ACF repeater"""
        pricing = product_data.get("pricing_info", {})
        bulk_pricing = pricing.get("bulk_pricing", [])

        return [
            {
                "min_quantity": tier.get("Quantity", {}).get("From", 0),
                "max_quantity": tier.get("Quantity", {}).get("To", 0),
                "price": tier.get("Price", 0.0),
                "cost": tier.get("Cost", 0.0),
                "discount_code": tier.get("DiscountCode", ""),
                "currency": tier.get("CurrencyCode", "USD"),
            }
            for tier in bulk_pricing
        ]

    def _extract_imprint_methods_complete(self, product_data: Dict) -> List[Dict]:
        """Extract imprint methods for ACF repeater, including all options and charges"""
        imprinting = product_data.get("imprinting", {})
        methods = []

        for method in imprinting.get("imprinting_methods", []):
            method_data = {
                "name": method.get("Name", ""),
                "code": method.get("Code", ""),
                "vendor_code": method.get("VendorCode", ""),
                "locations": [],
                "sizes": [],
                "charges": [],
            }

            # Extract locations and sizes
            for option in method.get("Options", []):
                option_type = option.get("Type", "")
                values = option.get("Values", [])

                if option_type == "Imprint Location":
                    method_data["locations"] = [
                        {
                            "name": val.get("Name", ""),
                            "vendor_code": val.get("VendorCode", ""),
                        }
                        for val in values
                    ]
                elif option_type == "Imprint Size":
                    method_data["sizes"] = [
                        {"name": val.get("Name", ""), "code": val.get("Code", "")}
                        for val in values
                    ]

            # Extract charges
            for charge in method.get("Charges", []):
                method_data["charges"].append(
                    {
                        "type": charge.get("Type", ""),
                        "description": charge.get("Description", ""),
                        "price": charge.get("Prices", [{}])[0].get("Price", 0.0),
                        "cost": charge.get("Prices", [{}])[0].get("Cost", 0.0),
                        "usage_level": charge.get("UsageLevel", ""),
                        "is_required": charge.get("IsRequired", False),
                        "vendor_code": charge.get("VendorCode", ""),
                    }
                )

            methods.append(method_data)

        return methods

    def _extract_supplier_info(self, product_data: Dict) -> Dict:
        """Extract supplier information"""
        supplier = product_data.get("supplier_info", {})
        return {
            "name": supplier.get("supplier_name", ""),
            "id": supplier.get("supplier_id", ""),
            "asi_number": supplier.get("asi_number", ""),
            "email": supplier.get("email", ""),
            "phone": supplier.get("phone", ""),
            "rating": supplier.get("supplier_rating", 0),
            "websites": supplier.get("websites", []),
        }

    def _extract_production_info(self, product_data: Dict) -> Dict:
        """Extract production information"""
        production = product_data.get("production_info", {})
        return {
            "production_time": production.get("production_time", []),
            "minimum_order": production.get("minimum_order", ""),
            "maximum_order": production.get("maximum_order", ""),
            "origin": production.get("origin", []),
            "trade_names": production.get("trade_names", []),
        }

    def _extract_shipping_info(self, product_data: Dict) -> Dict:
        """Extract shipping information"""
        shipping = product_data.get("shipping", {})
        return {
            "weight_unit": shipping.get("weight_unit", ""),
            "weight_per_package": shipping.get("weight_per_package", 0.0),
            "package_unit": shipping.get("package_unit", ""),
            "items_per_package": shipping.get("items_per_package", 0),
            "fob_points": shipping.get("fob_points", []),
        }

    def _extract_specifications(self, product_data: Dict) -> Dict:
        """Extract product specifications"""
        return {
            "weight": self._extract_weight(product_data),
            "dimensions": self._extract_dimensions(product_data),
            "materials": [
                mat.get("Name", "")
                for mat in product_data.get("attributes", {}).get("materials", [])
            ],
            "features": product_data.get("attributes", {}).get("features", []),
        }

    def _extract_origin(self, product_data: Dict) -> List[str]:
        """Extract product origin"""
        return product_data.get("production_info", {}).get("origin", [])

    def _extract_production_time(self, product_data: Dict) -> List[Dict]:
        """Extract production time"""
        return product_data.get("production_info", {}).get("production_time", [])

    def _extract_minimum_order(self, product_data: Dict) -> str:
        """Extract minimum order"""
        return product_data.get("production_info", {}).get("minimum_order", "")

    def _extract_weight(self, product_data: Dict) -> str:
        """Extract product weight"""
        raw_data = product_data.get("raw_data", {})
        weight_data = raw_data.get("Weight", {})
        weight_values = weight_data.get("Values", [])
        if weight_values:
            return weight_values[0]
        return ""

    def _extract_dimensions(self, product_data: Dict) -> Dict:
        """Extract product dimensions"""
        shipping = product_data.get("shipping", {})
        dimensions = shipping.get("Dimensions", {})
        return {
            "length": dimensions.get("Length", ""),
            "width": dimensions.get("Width", ""),
            "height": dimensions.get("Height", ""),
            "description": dimensions.get("Description", ""),
        }

    def _extract_categories(self, product_data: Dict) -> List[Dict]:
        """Extract product categories"""
        categories = []

        # Try different category sources
        if product_data.get("categories"):
            categories = product_data.get("categories", [])
        elif product_data.get("raw_data", {}).get("Categories"):
            categories = product_data.get("raw_data", {}).get("Categories", [])

        return [
            {
                "id": cat.get("id", ""),
                "name": cat.get("name", ""),
                "parent": cat.get("parent", {}),
            }
            for cat in categories
        ]

    def _extract_colors_optimized(self, product_data: Dict) -> List[Dict]:
        """Extract colors in optimized format"""
        try:
            colors = product_data.get("attributes", {}).get("colors", [])
            return [
                {
                    "name": color.get("Name", ""),
                    "code": color.get("Code", ""),
                    "vendor_code": color.get("VendorCode", ""),
                    "image_url": color.get("ImageUrl", ""),
                    "sku": color.get("SKU", ""),
                }
                for color in colors
            ]
        except Exception as e:
            logging.error(f"❌ Error extracting colors: {e}")
            return []

    def _extract_sizes_optimized(self, product_data: Dict) -> List[Dict]:
        """Extract sizes in optimized format"""
        try:
            sizes = product_data.get("attributes", {}).get("sizes", [])
            return [
                {
                    "name": size.get("Name", ""),
                    "code": size.get("Code", ""),
                    "sku": size.get("SKU", ""),
                }
                for size in sizes
            ]
        except Exception as e:
            logging.error(f"❌ Error extracting sizes: {e}")
            return []

    def _extract_materials_optimized(self, product_data: Dict) -> List[Dict]:
        """Extract materials in optimized format"""
        try:
            materials = product_data.get("attributes", {}).get("materials", [])
            return [
                {"name": material.get("Name", ""), "code": material.get("Code", "")}
                for material in materials
            ]
        except Exception as e:
            logging.error(f"❌ Error extracting materials: {e}")
            return []

    def _extract_imprint_methods_optimized(self, product_data: Dict) -> List[Dict]:
        """Extract imprint methods in optimized format"""
        try:
            methods = product_data.get("imprinting", {}).get("imprinting_methods", [])
            optimized_methods = []

            for method in methods:
                method_name = method.get("Name", "")
                method_code = method.get("Code", "")
                vendor_code = method.get("VendorCode", "")

                # Extract locations and sizes
                locations = []
                sizes = []
                charges = []

                for option in method.get("Options", []):
                    if option.get("Type") == "Imprint Location":
                        locations = [
                            {
                                "name": loc.get("Name", ""),
                                "vendor_code": loc.get("VendorCode", ""),
                            }
                            for loc in option.get("Values", [])
                        ]
                    elif option.get("Type") == "Imprint Size":
                        sizes = [
                            {
                                "name": size.get("Name", ""),
                                "code": size.get("Code", ""),
                                "width_inches": (
                                    self._parse_imprint_dimensions(
                                        size.get("Name", "")
                                    ).get("width", 0)
                                    if self._parse_imprint_dimensions(
                                        size.get("Name", "")
                                    )
                                    else 0
                                ),
                                "height_inches": (
                                    self._parse_imprint_dimensions(
                                        size.get("Name", "")
                                    ).get("height", 0)
                                    if self._parse_imprint_dimensions(
                                        size.get("Name", "")
                                    )
                                    else 0
                                ),
                            }
                            for size in option.get("Values", [])
                        ]

                # Extract charges
                for charge in method.get("Charges", []):
                    charges.append(
                        {
                            "type": charge.get("Type", ""),
                            "description": charge.get("Description", ""),
                            "price": (
                                charge.get("Prices", [{}])[0].get("Price", 0)
                                if charge.get("Prices")
                                else 0
                            ),
                            "cost": (
                                charge.get("Prices", [{}])[0].get("Cost", 0)
                                if charge.get("Prices")
                                else 0
                            ),
                            "usage_level": charge.get("UsageLevel", ""),
                            "is_required": charge.get("IsRequired", False),
                            "vendor_code": charge.get("VendorCode", ""),
                        }
                    )

                optimized_methods.append(
                    {
                        "name": method_name,
                        "code": method_code,
                        "vendor_code": vendor_code,
                        "locations": locations,
                        "sizes": sizes,
                        "charges": charges,
                    }
                )

            return optimized_methods
        except Exception as e:
            logging.error(f"❌ Error extracting imprint methods: {e}")
            return []

    def _extract_imprinting_colors_optimized(self, product_data: Dict) -> List[Dict]:
        """Extract imprinting colors in optimized format"""
        try:
            colors = product_data.get("imprinting", {}).get("imprinting_colors", [])
            return [
                {"name": color.get("Name", ""), "code": color.get("Code", "")}
                for color in colors
            ]
        except Exception as e:
            logging.error(f"❌ Error extracting imprinting colors: {e}")
            return []


class BatchFileEnhancer:
    """Enhances batch files with art template information"""

    def __init__(self, art_processor: ArtTemplateProcessor):
        self.art_processor = art_processor
        self.enhanced_count = 0
        self.error_count = 0

    def enhance_batch_file(self, batch_file_path: str, resume: bool = False) -> bool:
        """Enhance a single batch file"""
        try:
            # Validate file exists
            if not os.path.exists(batch_file_path):
                logging.error(f"❌ Batch file not found: {batch_file_path}")
                return False

            # Validate file is readable
            if not os.access(batch_file_path, os.R_OK):
                logging.error(f"❌ Batch file not readable: {batch_file_path}")
                return False

            logging.info(f"🔄 Enhancing batch file: {batch_file_path}")

            # Get base name for state tracking
            base_name = os.path.basename(batch_file_path).replace(".jsonl", "")
            state_file = os.path.join("enhanced", f"{base_name}_enhancement_state.json")

            # Load resume state if requested
            resume_line = 0
            if resume and os.path.exists(state_file):
                try:
                    with open(state_file, "r") as f:
                        state_data = json.load(f)
                        resume_line = state_data.get("last_processed_line", 0)
                        logging.info(f"🔄 Resuming from line {resume_line}")
                except Exception as e:
                    logging.warning(f"⚠️ Could not load state file: {e}")
                    resume_line = 0

            # Read the batch file with validation
            products = []
            try:
                with open(batch_file_path, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        if line.strip():
                            # Skip lines if resuming
                            if resume and line_num <= resume_line:
                                continue

                            try:
                                product = json.loads(line)
                                products.append(product)
                            except json.JSONDecodeError as e:
                                logging.error(
                                    f"❌ Invalid JSON on line {line_num}: {e}"
                                )
                                continue
            except Exception as e:
                logging.error(f"❌ Error reading batch file: {e}")
                return False

            if not products:
                logging.warning(f"⚠️ No valid products found in {batch_file_path}")
                return False

            logging.info(f"📦 Processing {len(products)} products")

            # Enhance each product
            enhanced_products = []
            for i, product in enumerate(products):
                try:
                    enhanced_product = self._enhance_product(product)
                    enhanced_products.append(enhanced_product)

                    if (i + 1) % 10 == 0:
                        logging.info(f"🔄 Enhanced {i + 1}/{len(products)} products")

                except Exception as e:
                    logging.error(f"❌ Error enhancing product {i + 1}: {e}")
                    self.error_count += 1
                    # Keep original product if enhancement fails
                    enhanced_products.append(product)

            # Write enhanced products to new file in 'enhanced' directory
            # Create enhanced directory in the same location as batch directory
            batch_dir = os.path.dirname(batch_file_path)
            enhanced_dir = os.path.join(batch_dir, "..", "enhanced")
            enhanced_dir = os.path.abspath(enhanced_dir)
            os.makedirs(enhanced_dir, exist_ok=True)

            # Also create enhanced directory in current working directory as fallback
            cwd_enhanced_dir = os.path.join(os.getcwd(), "enhanced")
            os.makedirs(cwd_enhanced_dir, exist_ok=True)

            base_name = os.path.basename(batch_file_path).replace(".jsonl", "")
            output_file = os.path.join(enhanced_dir, f"{base_name}_enhanced.jsonl")

            # Log the output location for debugging
            logging.info(f"📁 Enhanced directory: {enhanced_dir}")
            logging.info(f"📁 CWD enhanced directory: {cwd_enhanced_dir}")
            logging.info(f"📄 Output file: {output_file}")

            # Validate output directory is writable
            if not os.access(enhanced_dir, os.W_OK):
                logging.error(f"❌ Output directory not writable: {enhanced_dir}")
                return False

            # Write enhanced products with validation
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    for product in enhanced_products:
                        f.write(json.dumps(product, ensure_ascii=False) + "\n")

                # Verify file was written successfully
                if not os.path.exists(output_file):
                    logging.error(f"❌ Failed to create output file: {output_file}")
                    return False

                file_size = os.path.getsize(output_file)

                if file_size == 0:
                    logging.error(f"❌ Output file is empty: {output_file}")
                    return False

                logging.info(
                    f"✅ Enhanced batch file saved: {output_file} ({file_size} bytes)"
                )

            except Exception as e:
                logging.error(f"❌ Error writing output file: {e}")
                return False

            self.enhanced_count += 1
            return True

        except Exception as e:
            logging.error(f"❌ Error enhancing batch file: {e}")
            return False

    def _enhance_product(self, product: Dict) -> Dict:
        """Enhance a single product"""
        try:
            # Extract product number
            product_number = self._extract_product_number(product)
            if not product_number:
                logging.warning(
                    f"⚠️ No product number found for product {product.get('product_id', 'unknown')}"
                )
                return product

            # Get art template URL
            art_url = self.art_processor.get_product_art_url(product_number)
            if art_url:
                product["product_art_url"] = art_url

                # Download art template
                local_file = self.art_processor.download_art_template(
                    art_url, product_number
                )
                if local_file:
                    product["art_template_local_file"] = local_file

            # Create optimized structure
            optimized_product = self.art_processor.create_optimized_structure(product)

            # Add the optimized structure to the original product
            product["optimized"] = optimized_product

            logging.info(
                f"✅ Enhanced product {product.get('product_id', 'unknown')} with WooCommerce structure"
            )
            return product

        except Exception as e:
            logging.error(f"❌ Error enhancing product: {e}")
            return product

    def _extract_product_number(self, product: Dict) -> Optional[str]:
        """Extract product number from product data"""
        # Try different possible fields
        possible_fields = ["product_number", "numbers", "number", "sku"]

        for field in possible_fields:
            value = product.get(field)
            if value:
                # Clean up the value
                if isinstance(value, list) and len(value) > 0:
                    value = value[0]
                if isinstance(value, dict):
                    value = value.get("SKU", "")

                # Extract numeric part
                if isinstance(value, str):
                    match = re.search(r"(\d+)", value)
                    if match:
                        return match.group(1)

        # Try raw_data.Number (common in ESP data)
        raw_data = product.get("raw_data", {})
        if isinstance(raw_data, dict):
            number = raw_data.get("Number")
            if number:
                return str(number)

        # Try raw_data.Numbers array
        numbers = raw_data.get("Numbers", [])
        if isinstance(numbers, list) and len(numbers) > 0:
            return str(numbers[0])

        return None

    def _fpd_config_to_dict(self, fpd_config: FPDConfig) -> Dict:
        """Convert FPD config to dictionary"""
        return {
            "product_type": fpd_config.product_type,
            "enable_fpd": fpd_config.enable_fpd,
            "create_design_areas": fpd_config.create_design_areas,
            "stage_config": {
                "width": fpd_config.stage_width,
                "height": fpd_config.stage_height,
            },
            "restrictions": fpd_config.restrictions,
            "fpd_product_structure": {
                "title": "Product Design",
                "thumbnail": "",
                "options": {
                    "stageWidth": fpd_config.stage_width,
                    "stageHeight": fpd_config.stage_height,
                },
                "views": fpd_config.views or [],
            },
        }

    def enhance_all_batch_files(
        self,
        batch_dir: str = "batch",
        max_files: int = None,
        dry_run: bool = False,
        force_reprocess: bool = False,
        resume: bool = False,
    ) -> Dict:
        """Enhance all batch files in a directory"""
        start_time = time.time()
        processing_stats = {
            "art_downloads": 0,
            "fpd_views": 0,
            "total_time": 0,
            "avg_file_size_mb": 0,
        }

        try:
            if not os.path.exists(batch_dir):
                logging.error(f"❌ Batch directory not found: {batch_dir}")
                return {"success": False, "error": "Batch directory not found"}

            # Find all batch files
            batch_files = []
            for file in os.listdir(batch_dir):
                if file.startswith("batch_") and file.endswith(".jsonl"):
                    # Include enhanced files if force_reprocess is enabled
                    if force_reprocess or not file.endswith("_enhanced.jsonl"):
                        batch_files.append(os.path.join(batch_dir, file))

            if not batch_files:
                logging.warning(f"⚠️ No batch files found in {batch_dir}")
                return {"success": False, "error": "No batch files found"}

            # Limit files if max_files is specified
            if max_files and len(batch_files) > max_files:
                batch_files = batch_files[:max_files]
                logging.info(
                    f"📁 Processing {len(batch_files)} files (limited by --max-files={max_files})"
                )
            else:
                logging.info(f"📁 Found {len(batch_files)} batch files to enhance")

            if dry_run:
                logging.info("🔍 DRY RUN MODE - No files will be enhanced")
                return {
                    "success": True,
                    "total_files": len(batch_files),
                    "enhanced_files": 0,
                    "error_files": 0,
                    "enhanced_batch_dir": batch_dir,
                    "processing_stats": processing_stats,
                }

            if force_reprocess:
                logging.info(
                    "🔄 FORCE REPROCESS MODE - Will re-enhance already enhanced files"
                )

            if resume:
                logging.info("🔄 RESUME MODE - Will resume from last saved state")

            # Enhance each batch file
            total_file_size = 0
            for i, batch_file in enumerate(batch_files, 1):
                logging.info(
                    f"🔄 Processing file {i}/{len(batch_files)}: {os.path.basename(batch_file)}"
                )

                # Track file size
                file_size = os.path.getsize(batch_file)
                total_file_size += file_size

                success = self.enhance_batch_file(batch_file, resume)
                if success:
                    # Count art downloads and FPD views
                    try:
                        # Try both possible enhanced file locations
                        batch_dir = os.path.dirname(batch_file)
                        enhanced_dir = os.path.abspath(
                            os.path.join(batch_dir, "..", "enhanced")
                        )
                        base_name = os.path.basename(batch_file).replace(".jsonl", "")
                        enhanced_file = os.path.join(
                            enhanced_dir, f"{base_name}_enhanced.jsonl"
                        )

                        # If not found in enhanced directory, check batch directory
                        if not os.path.exists(enhanced_file):
                            enhanced_file = os.path.join(
                                batch_dir, f"{base_name}_enhanced.jsonl"
                            )

                        if os.path.exists(enhanced_file):
                            with open(enhanced_file, "r") as f:
                                for line in f:
                                    if line.strip():
                                        product = json.loads(line)
                                        if product.get("art_template_local_file"):
                                            processing_stats["art_downloads"] += 1
                                        if product.get("fpd_config", {}).get("views"):
                                            processing_stats["fpd_views"] += len(
                                                product["fpd_config"]["views"]
                                            )
                    except Exception as e:
                        logging.warning(
                            f"⚠️ Could not count stats for {batch_file}: {e}"
                        )

                    # Be nice to the server
                    if i < len(batch_files):
                        time.sleep(1)

            # Calculate processing time and stats
            processing_stats["total_time"] = time.time() - start_time
            processing_stats["avg_file_size_mb"] = (
                (total_file_size / len(batch_files)) / 1024 / 1024 if batch_files else 0
            )

            # Summary
            summary = {
                "success": True,
                "total_files": len(batch_files),
                "enhanced_files": self.enhanced_count,
                "error_files": self.error_count,
                "enhanced_batch_dir": os.path.abspath(
                    os.path.join(batch_dir, "..", "enhanced")
                ),
                "processing_stats": processing_stats,
            }

            logging.info(f"✅ Batch enhancement completed:")
            logging.info(f"   📁 Total files: {summary['total_files']}")
            logging.info(f"   ✅ Enhanced: {summary['enhanced_files']}")
            logging.info(f"   ❌ Errors: {summary['error_files']}")
            logging.info(
                f"   ⏱️  Processing time: {processing_stats['total_time']:.2f}s"
            )

            return summary

        except Exception as e:
            logging.error(f"❌ Error enhancing batch files: {e}")
            return {"success": False, "error": str(e)}


def cleanup_duplicate_enhanced_files(batch_dir: str):
    """Clean up duplicate enhanced files"""
    try:
        import glob
        import re

        # Find all files with multiple _enhanced suffixes
        pattern = os.path.join(batch_dir, "*_enhanced_enhanced*.jsonl")
        duplicate_files = glob.glob(pattern)

        if duplicate_files:
            logging.info(
                f"🧹 Cleaning up {len(duplicate_files)} duplicate enhanced files..."
            )
            for file_path in duplicate_files:
                try:
                    os.remove(file_path)
                    logging.info(f"🗑️  Removed: {os.path.basename(file_path)}")
                except Exception as e:
                    logging.error(f"❌ Error removing {file_path}: {e}")
        else:
            logging.info("✨ No duplicate enhanced files found")

    except Exception as e:
        logging.error(f"❌ Error during cleanup: {e}")


def main():
    """Main function to enhance batch files with art template information"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Enhance batch files with art template information"
    )
    parser.add_argument(
        "--batch-dir", default="batch", help="Directory containing batch files"
    )
    parser.add_argument(
        "--base-url",
        default="https://www.hitpromo.net",
        help="Base URL for art templates",
    )
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without actually enhancing",
    )
    parser.add_argument(
        "--max-files", type=int, help="Maximum number of files to process (for testing)"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean up duplicate enhanced files before processing",
    )
    parser.add_argument(
        "--force-reprocess",
        action="store_true",
        help="Force re-enhancement of already enhanced files",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume processing from last saved state",
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # Check dependencies
    if not BS4_AVAILABLE:
        logging.warning(
            "⚠️ BeautifulSoup not available. Install with: pip install beautifulsoup4"
        )

    # Cleanup duplicate files if requested
    if args.cleanup:
        cleanup_duplicate_enhanced_files(args.batch_dir)

    # Create art processor
    art_processor = ArtTemplateProcessor(args.base_url)

    # Show art_templates folder information
    art_info = art_processor.get_art_templates_info()
    print(f"\n📁 Art Templates Folder Information:")
    print(f"   📂 Directory: {art_info['art_templates_dir']}")
    print(f"   📄 Total files: {art_info['total_files']}")
    print(f"   💾 Total size: {art_info['total_size'] / 1024 / 1024:.2f} MB")

    # Create batch enhancer
    enhancer = BatchFileEnhancer(art_processor)

    # Enhance all batch files
    result = enhancer.enhance_all_batch_files(
        args.batch_dir,
        max_files=args.max_files,
        dry_run=args.dry_run,
        force_reprocess=args.force_reprocess,
        resume=args.resume,
    )

    if result["success"]:
        print(f"\n🎉 Batch enhancement completed successfully!")
        print(
            f"   📁 Enhanced {result['enhanced_files']} out of {result['total_files']} files"
        )
        print(f"   📂 Enhanced files saved with '_enhanced.jsonl' suffix")
        print(
            f"   🎨 Art templates saved in '{art_info['art_templates_dir']}/' directory"
        )

        # Show updated art_templates folder information
        updated_art_info = art_processor.get_art_templates_info()
        print(f"\n📁 Updated Art Templates Folder Information:")
        print(f"   📄 Total files: {updated_art_info['total_files']}")
        print(
            f"   💾 Total size: {updated_art_info['total_size'] / 1024 / 1024:.2f} MB"
        )

        # Show processing statistics
        if result.get("processing_stats"):
            stats = result["processing_stats"]
            print(f"\n📊 Processing Statistics:")
            print(f"   ⏱️  Total processing time: {stats.get('total_time', 0):.2f}s")
            print(f"   📥 Art templates downloaded: {stats.get('art_downloads', 0)}")
            print(f"   🎨 FPD views created: {stats.get('fpd_views', 0)}")
            print(f"   💾 Average file size: {stats.get('avg_file_size_mb', 0):.2f} MB")
    else:
        print(f"\n❌ Batch enhancement failed: {result.get('error', 'Unknown error')}")

    return result["success"]


if __name__ == "__main__":
    main()
