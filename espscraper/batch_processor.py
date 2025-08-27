#!/usr/bin/env python3
"""
Batch Processor for ESP Product Scraper

Handles saving products in smaller chunks and managing batch files
for better organization and processing.
"""

import os
import json
import logging
import shutil
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import hashlib


@dataclass
class BatchStats:
    """Statistics for batch processing"""
    batch_count: int = 0
    total_products: int = 0
    unique_products: int = 0
    duplicate_products: int = 0
    total_size_bytes: int = 0


class BatchProcessor:
    """Enhanced batch processor with deduplication and consolidation"""

    def __init__(
        self,
        batch_size: int = 100,
        batch_dir: str = "batch",
        main_output_file: str = "final_product_details.jsonl",
        batch_prefix: str = "batch",
        enable_deduplication: bool = True,
        enable_consolidation: bool = True,
    ):
        self.batch_size = batch_size
        self.batch_dir = batch_dir
        self.main_output_file = main_output_file
        self.batch_prefix = batch_prefix
        self.enable_deduplication = enable_deduplication
        self.enable_consolidation = enable_consolidation
        
        # Enhanced tracking
        self.current_batch = []
        self.batch_counter = 0
        self.stats = BatchStats()
        
        # Deduplication tracking
        self.processed_product_ids = set()
        self.batch_product_hashes = {}  # Track product content hashes
        self.existing_batch_products = self._load_existing_batch_products()
        
        # Ensure batch directory exists
        os.makedirs(self.batch_dir, exist_ok=True)
        
        logging.info(
            f"🔧 Enhanced batch processor initialized: batch_size={batch_size}, "
            f"batch_dir={batch_dir}, deduplication={enable_deduplication}, "
            f"consolidation={enable_consolidation}"
        )

    def _load_existing_batch_products(self) -> Dict[str, set]:
        """Load existing products from all batch files to prevent duplicates"""
        existing_products = {}
        
        if not os.path.exists(self.batch_dir):
            return existing_products
            
        for filename in os.listdir(self.batch_dir):
            if filename.startswith(self.batch_prefix) and filename.endswith(".jsonl"):
                filepath = os.path.join(self.batch_dir, filename)
                product_ids = set()
                
                try:
                    with open(filepath, "r") as f:
                        for line in f:
                            try:
                                data = json.loads(line.strip())
                                product_id = (
                                    data.get("product_id") 
                                    or data.get("productId") 
                                    or data.get("id")
                                )
                                if product_id:
                                    product_ids.add(str(product_id))
                            except json.JSONDecodeError:
                                continue
                    
                    existing_products[filename] = product_ids
                    logging.debug(f"📄 Loaded {len(product_ids)} products from {filename}")
                    
                except Exception as e:
                    logging.warning(f"⚠️ Error loading products from {filename}: {e}")
        
        total_existing = sum(len(products) for products in existing_products.values())
        logging.info(f"📊 Loaded {total_existing} existing products from {len(existing_products)} batch files")
        
        return existing_products

    def _get_product_hash(self, product: Dict[str, Any]) -> str:
        """Generate a hash for product content to detect duplicates"""
        # Create a stable representation of the product
        product_copy = product.copy()
        
        # Remove variable fields that shouldn't affect deduplication
        product_copy.pop("extraction_time", None)
        product_copy.pop("scraped_date", None)
        product_copy.pop("SourceURL", None)
        
        # Sort keys for consistent hashing
        sorted_product = json.dumps(product_copy, sort_keys=True, separators=(",", ":"))
        return hashlib.md5(sorted_product.encode()).hexdigest()

    def _is_duplicate_product(self, product: Dict[str, Any]) -> bool:
        """Check if product is a duplicate based on ID and content"""
        if not self.enable_deduplication:
            return False
            
        product_id = (
            product.get("product_id") 
            or product.get("productId") 
            or product.get("id")
        )
        
        if not product_id:
            return False
            
        product_id = str(product_id)
        
        # Check if product ID already processed in this session
        if product_id in self.processed_product_ids:
            logging.debug(f"🔄 Duplicate product ID detected: {product_id}")
            return True
            
        # Check if product exists in any existing batch file
        for filename, product_ids in self.existing_batch_products.items():
            if product_id in product_ids:
                logging.debug(f"🔄 Product {product_id} already exists in {filename}")
                return True
                
        # Check content hash for exact duplicates
        product_hash = self._get_product_hash(product)
        if product_hash in self.batch_product_hashes:
            existing_id = self.batch_product_hashes[product_hash]
            logging.debug(f"🔄 Duplicate content detected: {product_id} matches {existing_id}")
            return True
            
        return False

    def add_product(self, product: Dict[str, Any]) -> bool:
        """Add a product to the current batch with deduplication"""
        try:
            # Check for duplicates
            if self._is_duplicate_product(product):
                self.stats.duplicate_products += 1
                logging.debug(f"⏭️ Skipping duplicate product: {product.get('product_id', 'unknown')}")
                return True  # Return True since we successfully handled it
                
            # Add to current batch
            self.current_batch.append(product)
            
            # Track product
            product_id = (
                product.get("product_id") 
                or product.get("productId") 
                or product.get("id")
            )
            if product_id:
                self.processed_product_ids.add(str(product_id))
                product_hash = self._get_product_hash(product)
                self.batch_product_hashes[product_hash] = str(product_id)
            
            self.stats.unique_products += 1
            self.stats.total_products += 1
            
            # Save batch if it's full
            if len(self.current_batch) >= self.batch_size:
                return self._save_current_batch()
                
            return True
            
        except Exception as e:
            logging.error(f"❌ Error adding product to batch: {e}")
            return False

    def _save_current_batch(self) -> bool:
        """Save the current batch to a file with enhanced naming"""
        if not self.current_batch:
            return True

        try:
            # Create batch filename with product count and timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.batch_counter += 1
            product_count = len(self.current_batch)
            
            # Enhanced filename with product count
            batch_filename = (
                f"{self.batch_prefix}_{timestamp}_{self.batch_counter}_{product_count}.jsonl"
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
                
                # Update stats
                file_size = os.path.getsize(batch_path)
                self.stats.total_size_bytes += file_size
                self.stats.batch_count += 1

                logging.info(
                    f"💾 Saved batch {self.batch_counter}: {product_count} unique products -> {batch_filename} ({file_size:,} bytes)"
                )
                
                # Update existing products tracking
                product_ids = set()
                for product in self.current_batch:
                    product_id = (
                        product.get("product_id") 
                        or product.get("productId") 
                        or product.get("id")
                    )
                    if product_id:
                        product_ids.add(str(product_id))
                self.existing_batch_products[batch_filename] = product_ids

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

    def consolidate_batches(self, target_batch_size: int = 100) -> bool:
        """Consolidate small batch files into larger ones"""
        if not self.enable_consolidation:
            return True
            
        try:
            logging.info(f"🔄 Consolidating batch files to target size: {target_batch_size}")
            
            # Get all batch files
            batch_files = []
            for filename in os.listdir(self.batch_dir):
                if filename.startswith(self.batch_prefix) and filename.endswith(".jsonl"):
                    filepath = os.path.join(self.batch_dir, filename)
                    batch_files.append((filepath, os.path.getctime(filepath)))
            
            if not batch_files:
                logging.info("ℹ️ No batch files to consolidate")
                return True
                
            # Sort by creation time
            batch_files.sort(key=lambda x: x[1])
            
            # Group small files for consolidation
            consolidated_groups = []
            current_group = []
            current_size = 0
            
            for filepath, _ in batch_files:
                try:
                    with open(filepath, "r") as f:
                        product_count = sum(1 for line in f if line.strip())
                    
                    if current_size + product_count <= target_batch_size:
                        current_group.append(filepath)
                        current_size += product_count
                    else:
                        if current_group:
                            consolidated_groups.append(current_group)
                        current_group = [filepath]
                        current_size = product_count
                        
                except Exception as e:
                    logging.warning(f"⚠️ Error reading {filepath}: {e}")
                    continue
            
            # Add the last group
            if current_group:
                consolidated_groups.append(current_group)
            
            # Consolidate each group
            consolidated_count = 0
            for i, group in enumerate(consolidated_groups):
                if len(group) > 1:  # Only consolidate if multiple files
                    if self._consolidate_group(group, i + 1):
                        consolidated_count += len(group)
            
            if consolidated_count > 0:
                logging.info(f"✅ Consolidated {consolidated_count} batch files")
            else:
                logging.info("ℹ️ No consolidation needed")
                
            return True
            
        except Exception as e:
            logging.error(f"❌ Error consolidating batches: {e}")
            return False

    def _consolidate_group(self, filepaths: List[str], group_id: int) -> bool:
        """Consolidate a group of batch files into one"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            consolidated_filename = f"{self.batch_prefix}_consolidated_{timestamp}_group_{group_id}.jsonl"
            consolidated_path = os.path.join(self.batch_dir, consolidated_filename)
            
            # Collect all products from the group
            all_products = []
            for filepath in filepaths:
                try:
                    with open(filepath, "r") as f:
                        for line in f:
                            if line.strip():
                                product = json.loads(line)
                                all_products.append(product)
                except Exception as e:
                    logging.warning(f"⚠️ Error reading {filepath}: {e}")
                    continue
            
            # Remove duplicates based on product ID
            unique_products = {}
            for product in all_products:
                product_id = (
                    product.get("product_id") 
                    or product.get("productId") 
                    or product.get("id")
                )
                if product_id:
                    unique_products[str(product_id)] = product
            
            # Write consolidated file
            with open(consolidated_path, "w") as f:
                for product in unique_products.values():
                    json_line = json.dumps(product, ensure_ascii=False, separators=(",", ":")) + "\n"
                    f.write(json_line)
            
            # Remove original files
            for filepath in filepaths:
                try:
                    os.remove(filepath)
                    logging.debug(f"🗑️ Removed {os.path.basename(filepath)}")
                except Exception as e:
                    logging.warning(f"⚠️ Could not remove {filepath}: {e}")
            
            logging.info(f"✅ Consolidated {len(filepaths)} files into {consolidated_filename} ({len(unique_products)} unique products)")
            return True
            
        except Exception as e:
            logging.error(f"❌ Error consolidating group: {e}")
            return False

    def merge_batches_to_main(self) -> bool:
        """Merge all batch files into the main output file with deduplication"""
        try:
            logging.info("🔄 Merging batch files into main output...")

            # Get all batch files sorted by creation time
            batch_files = []
            for filename in os.listdir(self.batch_dir):
                if filename.startswith(self.batch_prefix) and filename.endswith(".jsonl"):
                    filepath = os.path.join(self.batch_dir, filename)
                    batch_files.append((filepath, os.path.getctime(filepath)))

            batch_files.sort(key=lambda x: x[1])  # Sort by creation time

            if not batch_files:
                logging.warning("⚠️ No batch files found to merge")
                return True

            # Create main output file with atomic write and deduplication
            temp_main = self.main_output_file + ".tmp"
            total_merged = 0
            unique_products = {}
            duplicate_count = 0

            try:
                with open(temp_main, "w") as main_file:
                    for batch_path, _ in batch_files:
                        logging.info(f"📄 Merging {os.path.basename(batch_path)}...")

                        with open(batch_path, "r") as batch_file:
                            for line in batch_file:
                                if line.strip():
                                    try:
                                        product = json.loads(line)
                                        product_id = (
                                            product.get("product_id") 
                                            or product.get("productId") 
                                            or product.get("id")
                                        )
                                        
                                        if product_id:
                                            product_id = str(product_id)
                                            if product_id not in unique_products:
                                                unique_products[product_id] = product
                                                main_file.write(line)
                                                total_merged += 1
                                            else:
                                                duplicate_count += 1
                                        else:
                                            # Product without ID, write it anyway
                                            main_file.write(line)
                                            total_merged += 1
                                            
                                    except json.JSONDecodeError:
                                        logging.warning(f"⚠️ Invalid JSON in {batch_path}")
                                        continue

                # Atomic move
                shutil.move(temp_main, self.main_output_file)

                logging.info(
                    f"✅ Successfully merged {len(batch_files)} batch files into main output: "
                    f"{total_merged} products ({duplicate_count} duplicates removed)"
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

    def cleanup_batches(self, keep_recent: int = 5) -> bool:
        """Clean up old batch files, keeping only the most recent ones"""
        try:
            logging.info(f"🧹 Cleaning up batch files (keeping {keep_recent} most recent)...")
            
            # Get all batch files with creation time
            batch_files = []
            for filename in os.listdir(self.batch_dir):
                if filename.startswith(self.batch_prefix) and filename.endswith(".jsonl"):
                    filepath = os.path.join(self.batch_dir, filename)
                    batch_files.append((filepath, os.path.getctime(filepath)))
            
            if len(batch_files) <= keep_recent:
                logging.info("ℹ️ No cleanup needed")
                return True
            
            # Sort by creation time (oldest first)
            batch_files.sort(key=lambda x: x[1])
            
            # Remove old files
            files_to_remove = batch_files[:-keep_recent]
            removed_count = 0
            
            for filepath, _ in files_to_remove:
                try:
                    os.remove(filepath)
                    removed_count += 1
                    logging.debug(f"🗑️ Removed {os.path.basename(filepath)}")
                except Exception as e:
                    logging.warning(f"⚠️ Could not remove {filepath}: {e}")
            
            logging.info(f"✅ Cleaned up {removed_count} old batch files")
            return True
            
        except Exception as e:
            logging.error(f"❌ Error cleaning up batches: {e}")
            return False

    def get_batch_stats(self) -> Dict[str, Any]:
        """Get comprehensive batch processing statistics"""
        return {
            "batch_count": self.stats.batch_count,
            "total_products": self.stats.total_products,
            "unique_products": self.stats.unique_products,
            "duplicate_products": self.stats.duplicate_products,
            "total_size_bytes": self.stats.total_size_bytes,
            "duplication_rate": (
                (self.stats.duplicate_products / self.stats.total_products * 100)
                if self.stats.total_products > 0 else 0
            ),
            "current_batch_size": len(self.current_batch),
            "processed_product_ids": len(self.processed_product_ids),
            "existing_batch_files": len(self.existing_batch_products)
        }

    def print_stats(self):
        """Print batch processing statistics"""
        stats = self.get_batch_stats()
        logging.info("📊 Batch Processing Statistics:")
        logging.info(f"   Batches created: {stats['batch_count']}")
        logging.info(f"   Total products processed: {stats['total_products']:,}")
        logging.info(f"   Unique products: {stats['unique_products']:,}")
        logging.info(f"   Duplicate products: {stats['duplicate_products']:,}")
        logging.info(f"   Duplication rate: {stats['duplication_rate']:.1f}%")
        logging.info(f"   Total size: {stats['total_size_bytes']:,} bytes")
        logging.info(f"   Current batch size: {stats['current_batch_size']}")
        logging.info(f"   Processed product IDs: {stats['processed_product_ids']:,}")
        logging.info(f"   Existing batch files: {stats['existing_batch_files']}")


def main():
    """Test the enhanced batch processor"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Batch Processor")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size")
    parser.add_argument("--batch-dir", default="batch", help="Batch directory")
    parser.add_argument("--consolidate", action="store_true", help="Consolidate small batches")
    parser.add_argument("--cleanup", action="store_true", help="Clean up old batches")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    
    args = parser.parse_args()
    
    processor = BatchProcessor(
        batch_size=args.batch_size,
        batch_dir=args.batch_dir,
        enable_deduplication=True,
        enable_consolidation=True
    )
    
    if args.consolidate:
        processor.consolidate_batches()
    
    if args.cleanup:
        processor.cleanup_batches()
    
    if args.stats:
        processor.print_stats()


if __name__ == "__main__":
    main()
