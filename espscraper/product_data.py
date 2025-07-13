#!/usr/bin/env python3
"""
Product Data Models for ESP Scraper

This module contains the data structures used for
product information
to avoid circular imports between modules.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


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
    scraped_date: str = ""
    related_products: List[Dict] = ""
    # Use snake_case for new fields
    product_number: str = ""
    vendor_product_url: str = ""
    product_art_url: str = ""
