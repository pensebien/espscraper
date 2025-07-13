#!/usr/bin/env python3
"""
Batch Processor for ESP Product Scraper

Handles saving products in smaller chunks and managing batch files
for better organization and processing.
"""

import os
import json
import time
import logging
import shutil
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import asdict

from .product_data import ProductData


class BatchProcessor:
    """Handles batch processing and file management for product scraping"""

    def __init__(
        self,
        batch_size: int = 100,
        batch_dir: str = "batch",
        main_output_file: str = "espscraper/data/final_product_details.jsonl",
        batch_prefix: str = "batch",
    ):

        self.batch_size = batch_size
        self.batch_dir = batch_dir
        self.main_output_file = main_output_file
        self.batch_prefix = batch_prefix

        # Ensure batch directory exists
        os.makedirs(self.batch_dir, exist_ok=True)

        # Initialize batch tracking
        self.current_batch = []
        self.batch_counter = 0
        self.total_products_processed = 0

        # Load existing batch info
        self._load_batch_info()

        logging.info(
            f"🔧 Batch processor initialized: batch_size={batch_size}, batch_dir={batch_dir}"
        )

    def _load_batch_info(self):
        """Load existing batch information"""
        try:
            # Count existing batch files
            existing_batches = [
                f
                for f in os.listdir(self.batch_dir)
                if f.startswith(self.batch_prefix) and f.endswith(".jsonl")
            ]
            self.batch_counter = len(existing_batches)

            # Count total products in existing batches
            total_products = 0
            for batch_file in existing_batches:
                batch_path = os.path.join(self.batch_dir, batch_file)
                try:
                    with open(batch_path, "r") as f:
                        for line in f:
                            if line.strip():
                                total_products += 1
                except Exception as e:
                    logging.warning(f"⚠️ Error reading batch file {batch_file}: {e}")

            self.total_products_processed = total_products
            logging.info(
                f"📊 Loaded batch info: {self.batch_counter} batches, {total_products} products"
            )

        except Exception as e:
            logging.warning(f"⚠️ Error loading batch info: {e}")

    def add_product(self, product_data: ProductData) -> bool:
        """Add a product to the current batch"""
        try:
            # Convert dataclass to dict
            product_dict = asdict(product_data)

            # Add to current batch
            self.current_batch.append(product_dict)
            self.total_products_processed += 1

            # Check if batch is full
            if len(self.current_batch) >= self.batch_size:
                return self._save_current_batch()

            return True

        except Exception as e:
            logging.error(f"❌ Error adding product to batch: {e}")
            return False

    def _save_current_batch(self) -> bool:
        """Save the current batch to a file"""
        if not self.current_batch:
            return True

        try:
            # Create batch filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.batch_counter += 1
            batch_filename = (
                f"{self.batch_prefix}_{timestamp}_{self.batch_counter}.jsonl"
            )
            batch_path = os.path.join(self.batch_dir, batch_filename)

            # Save batch with atomic write
            temp_path = batch_path + ".tmp"
            try:
                with open(temp_path, "w") as f:
                    for product in self.current_batch:
                        json_line = (
                            json.dumps(
                                product, ensure_ascii=False, separators=(",", ":")
                            )
                            + "\n"
                        )
                        f.write(json_line)
                    f.flush()
                    os.fsync(f.fileno())

                # Atomic move
                shutil.move(temp_path, batch_path)

                logging.info(
                    f"💾 Saved batch {self.batch_counter}: {len(self.current_batch)} products -> {batch_filename}"
                )

                # Clear current batch
                self.current_batch = []

                return True

            except Exception as e:
                # Clean up temp file on error
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise e

        except Exception as e:
            logging.error(f"❌ Error saving batch: {e}")
            return False

    def flush_batch(self) -> bool:
        """Force save the current batch even if not full"""
        if self.current_batch:
            return self._save_current_batch()
        return True

    def merge_batches_to_main(self) -> bool:
        """Merge all batch files into the main output file"""
        try:
            logging.info("🔄 Merging batch files into main output...")

            # Get all batch files sorted by creation time
            batch_files = []
            for filename in os.listdir(self.batch_dir):
                if filename.startswith(self.batch_prefix) and filename.endswith(
                    ".jsonl"
                ):
                    filepath = os.path.join(self.batch_dir, filename)
                    batch_files.append((filepath, os.path.getctime(filepath)))

            batch_files.sort(key=lambda x: x[1])  # Sort by creation time

            if not batch_files:
                logging.warning("⚠️ No batch files found to merge")
                return True

            # Create main output file with atomic write
            temp_main = self.main_output_file + ".tmp"
            total_merged = 0

            try:
                with open(temp_main, "w") as main_file:
                    for batch_path, _ in batch_files:
                        logging.info(f"📄 Merging {os.path.basename(batch_path)}...")

                        with open(batch_path, "r") as batch_file:
                            for line in batch_file:
                                if line.strip():
                                    main_file.write(line)
                                    total_merged += 1

                # Atomic move
                shutil.move(temp_main, self.main_output_file)

                logging.info(
                    f"✅ Successfully merged {len(batch_files)} batch files into main output: {total_merged} products"
                )
                return True

            except Exception as e:
                # Clean up temp file on error
                if os.path.exists(temp_main):
                    os.remove(temp_main)
                raise e

        except Exception as e:
            logging.error(f"❌ Error merging batches: {e}")
            return False

    def cleanup_batches(self, keep_main: bool = True) -> bool:
        """Clean up batch files after successful merge"""
        try:
            if not keep_main:
                # Remove main output file if requested
                if os.path.exists(self.main_output_file):
                    os.remove(self.main_output_file)
                    logging.info(f"🗑️ Removed main output file: {self.main_output_file}")

            # Remove all batch files
            removed_count = 0
            for filename in os.listdir(self.batch_dir):
                if filename.startswith(self.batch_prefix) and filename.endswith(
                    ".jsonl"
                ):
                    filepath = os.path.join(self.batch_dir, filename)
                    os.remove(filepath)
                    removed_count += 1

            logging.info(f"🗑️ Cleaned up {removed_count} batch files")
            return True

        except Exception as e:
            logging.error(f"❌ Error cleaning up batches: {e}")
            return False

    def get_batch_stats(self) -> Dict[str, Any]:
        """Get statistics about batches"""
        try:
            batch_files = [
                f
                for f in os.listdir(self.batch_dir)
                if f.startswith(self.batch_prefix) and f.endswith(".jsonl")
            ]

            total_products = 0
            for batch_file in batch_files:
                batch_path = os.path.join(self.batch_dir, batch_file)
                try:
                    with open(batch_path, "r") as f:
                        for line in f:
                            if line.strip():
                                total_products += 1
                except Exception:
                    continue

            return {
                "batch_count": len(batch_files),
                "total_products": total_products,
                "current_batch_size": len(self.current_batch),
                "batch_size_limit": self.batch_size,
                "batch_directory": self.batch_dir,
                "main_output_file": self.main_output_file,
            }

        except Exception as e:
            logging.error(f"❌ Error getting batch stats: {e}")
            return {}

    def validate_batches(self) -> bool:
        """Validate all batch files for JSON integrity"""
        try:
            batch_files = [
                f
                for f in os.listdir(self.batch_dir)
                if f.startswith(self.batch_prefix) and f.endswith(".jsonl")
            ]

            total_invalid = 0
            total_valid = 0

            for batch_file in batch_files:
                batch_path = os.path.join(self.batch_dir, batch_file)
                file_invalid = 0
                file_valid = 0

                try:
                    with open(batch_path, "r") as f:
                        for line_num, line in enumerate(f, 1):
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                json.loads(line)
                                file_valid += 1
                            except json.JSONDecodeError:
                                file_invalid += 1
                                logging.warning(
                                    f"⚠️ Invalid JSON in {batch_file} line {line_num}"
                                )

                    total_valid += file_valid
                    total_invalid += file_invalid

                    if file_invalid > 0:
                        logging.warning(
                            f"⚠️ {batch_file}: {file_invalid} invalid lines, {file_valid} valid lines"
                        )
                    else:
                        logging.debug(f"✅ {batch_file}: {file_valid} valid lines")

                except Exception as e:
                    logging.error(f"❌ Error validating {batch_file}: {e}")
                    total_invalid += 1

            logging.info(
                f"📊 Batch validation complete: {total_valid} valid, {total_invalid} invalid lines across {len(batch_files)} files"
            )
            return total_invalid == 0

        except Exception as e:
            logging.error(f"❌ Error during batch validation: {e}")
            return False


def main():
    """Test the batch processor"""
    import argparse

    parser = argparse.ArgumentParser(description="Batch Processor for ESP Scraper")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size")
    parser.add_argument("--batch-dir", default="batches", help="Batch directory")
    parser.add_argument(
        "--validate", action="store_true", help="Validate existing batches"
    )
    parser.add_argument(
        "--merge", action="store_true", help="Merge batches to main output"
    )
    parser.add_argument(
        "--cleanup", action="store_true", help="Clean up batch files after merge"
    )
    parser.add_argument("--stats", action="store_true", help="Show batch statistics")

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    processor = BatchProcessor(batch_size=args.batch_size, batch_dir=args.batch_dir)

    if args.stats:
        stats = processor.get_batch_stats()
        print("📊 Batch Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

    if args.validate:
        print("🔍 Validating batches...")
        if processor.validate_batches():
            print("✅ All batches are valid")
        else:
            print("❌ Some batches have issues")

    if args.merge:
        print("🔄 Merging batches...")
        if processor.merge_batches_to_main():
            print("✅ Merge completed successfully")
        else:
            print("❌ Merge failed")

    if args.cleanup:
        print("🗑️ Cleaning up batch files...")
        if processor.cleanup_batches():
            print("✅ Cleanup completed")
        else:
            print("❌ Cleanup failed")


if __name__ == "__main__":
    main()
