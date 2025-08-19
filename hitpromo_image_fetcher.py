#!/usr/bin/env python3
"""
HitPromo Image Fetcher - Simple Version
"""

import json
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def get_hitpromo_images(product_number):
    """Fetch images from HitPromo product page"""
    try:
        url = f"https://www.hitpromo.net/product/show/{product_number}"
        logging.info(f"🔍 Fetching: {url}")

        response = requests.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        # Get main image
        main_image = None
        zoom_viewport = soup.find("div", class_="zoom-viewport")
        if zoom_viewport:
            img = zoom_viewport.find("img", class_="center-block")
            if img and img.get("src"):
                main_image = urljoin("https://www.hitpromo.net", img["src"])
                main_image = main_image.replace("/400/", "/")  # Get larger version

        # Get gallery images
        gallery_images = []
        carousel = soup.find("div", class_="carousel-inner")
        if carousel:
            for item in carousel.find_all("div", class_="carousel-item"):
                img = item.find("img", class_="center-block")
                if img and img.get("src"):
                    img_url = urljoin("https://www.hitpromo.net", img["src"])
                    img_url = img_url.replace("/400/", "/")  # Get larger version
                    gallery_images.append(img_url)

        return {
            "main_image": main_image,
            "gallery_images": gallery_images,
            "product_url": url,
        }

    except Exception as e:
        logging.error(f"❌ Error for product {product_number}: {e}")
        return {"main_image": None, "gallery_images": [], "error": str(e)}


def update_batch_file(batch_file, max_products=None):
    """Update batch file with HitPromo images"""
    # Create enhanced directory if it doesn't exist
    import os

    enhanced_dir = "enhanced"
    if not os.path.exists(enhanced_dir):
        os.makedirs(enhanced_dir)

    # Get the base filename and save to enhanced folder
    base_name = os.path.basename(batch_file).replace(".jsonl", "")
    output_file = os.path.join(enhanced_dir, f"{base_name}_enhanced.jsonl")

    updated_products = []
    processed = 0

    with open(batch_file, "r") as f:
        for line in f:
            if line.strip():
                product = json.loads(line)

                if max_products and processed >= max_products:
                    break

                # Get product number - try multiple fields and clean them
                product_number = None

                # Try number field first (as specified by user)
                if product.get("number"):
                    product_number = str(product["number"]).strip()
                # Try numbers field (as specified by user)
                elif product.get("numbers"):
                    numbers_data = product["numbers"]
                    if isinstance(numbers_data, list) and len(numbers_data) > 0:
                        product_number = str(numbers_data[0]).strip()
                    else:
                        product_number = str(numbers_data).strip()
                # Try product_number field
                elif product.get("product_number"):
                    product_number = str(product["product_number"]).strip()
                # Try ProductNumber field
                elif product.get("ProductNumber"):
                    product_number = str(product["ProductNumber"]).strip()
                # Try sku field (could be array or string)
                elif product.get("sku"):
                    sku_data = product["sku"]
                    if isinstance(sku_data, list) and len(sku_data) > 0:
                        # If it's an array, get the first SKU
                        first_sku = sku_data[0]
                        if isinstance(first_sku, dict) and first_sku.get("SKU"):
                            product_number = str(first_sku["SKU"]).strip()
                        elif isinstance(first_sku, str):
                            product_number = str(first_sku).strip()
                    elif isinstance(sku_data, str):
                        product_number = str(sku_data).strip()
                # Try SKU field
                elif product.get("SKU"):
                    product_number = str(product["SKU"]).strip()
                # Try product_id field
                elif product.get("product_id"):
                    product_number = str(product["product_id"]).strip()
                # Try ProductID field
                elif product.get("ProductID"):
                    product_number = str(product["ProductID"]).strip()

                # Clean the product number - remove any non-alphanumeric characters except dashes
                if product_number:
                    import re

                    # Remove any complex structures and get just the base product number
                    if isinstance(product_number, str) and len(product_number) > 20:
                        # If it's a complex structure, try to extract a simple product number
                        # Look for patterns like "7645" or "15039" in the string
                        matches = re.findall(r"\b\d{4,5}\b", product_number)
                        if matches:
                            product_number = matches[0]
                        else:
                            # If no simple number found, skip this product
                            product_number = None
                    else:
                        # Clean simple product numbers
                        product_number = re.sub(r"[^a-zA-Z0-9\-]", "", product_number)

                        # Extract base product number from SKU (e.g., "15039BLK" -> "15039")
                        if product_number and len(product_number) > 4:
                            # Look for a number followed by letters
                            base_match = re.match(r"(\d{4,5})[A-Z]+", product_number)
                            if base_match:
                                product_number = base_match.group(1)

                if product_number and len(product_number) > 0:
                    logging.info(f"🔍 Processing product number: {product_number}")
                    hitpromo_images = get_hitpromo_images(product_number)

                    if hitpromo_images.get("main_image"):
                        product["image_url"] = hitpromo_images["main_image"]
                        product["hitpromo_main_image"] = hitpromo_images["main_image"]
                        logging.info(
                            f"✅ Updated main image for product {product_number}"
                        )

                    if hitpromo_images.get("gallery_images"):
                        product["images"] = [
                            {"url": img, "type": "hitpromo_gallery"}
                            for img in hitpromo_images["gallery_images"]
                        ]
                        product["hitpromo_gallery_images"] = hitpromo_images[
                            "gallery_images"
                        ]
                        logging.info(
                            f"✅ Updated gallery images for product {product_number}: {len(hitpromo_images['gallery_images'])} images"
                        )

                    product["hitpromo_updated"] = True
                    product["hitpromo_product_url"] = hitpromo_images.get("product_url")
                    product["hitpromo_product_number"] = product_number
                else:
                    logging.warning(
                        f"⚠️ No valid product number found for product {product.get('product_id', 'unknown')}"
                    )

                updated_products.append(product)
                processed += 1

                if processed % 5 == 0:
                    logging.info(f"📊 Processed {processed} products...")

    with open(output_file, "w") as f:
        for product in updated_products:
            f.write(json.dumps(product, ensure_ascii=False) + "\n")

    logging.info(f"✅ Updated {processed} products")
    logging.info(f"📁 Output: {output_file}")
    return output_file


if __name__ == "__main__":
    import sys

    batch_file = sys.argv[1] if len(sys.argv) > 1 else "batch_test_sample.jsonl"
    max_products = int(sys.argv[2]) if len(sys.argv) > 2 else None

    update_batch_file(batch_file, max_products)
