#!/usr/bin/env python3
"""
Cleanup Duplicate Batch Files Script

This script analyzes and cleans up duplicate batch files by:
1. Identifying files with identical content
2. Consolidating small files into larger ones
3. Removing duplicate products within files
4. Keeping only unique, consolidated files
"""

import os
import json
import logging
import shutil
import hashlib
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple
import argparse


class BatchFileCleaner:
    """Clean up duplicate batch files and consolidate them"""
    
    def __init__(self, batch_dir: str = "batch", backup_dir: str = "batch_backup"):
        self.batch_dir = batch_dir
        self.backup_dir = backup_dir
        self.stats = {
            "total_files": 0,
            "duplicate_files": 0,
            "consolidated_files": 0,
            "removed_files": 0,
            "total_products": 0,
            "unique_products": 0,
            "duplicate_products": 0
        }
        
        # Ensure directories exist
        os.makedirs(self.batch_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s"
        )
        
    def analyze_batch_files(self) -> Dict:
        """Analyze all batch files and return analysis results"""
        logging.info(f"🔍 Analyzing batch files in: {self.batch_dir}")
        
        batch_files = []
        for filename in os.listdir(self.batch_dir):
            if filename.startswith("batch_") and filename.endswith(".jsonl"):
                filepath = os.path.join(self.batch_dir, filename)
                batch_files.append(filepath)
        
        self.stats["total_files"] = len(batch_files)
        logging.info(f"📁 Found {len(batch_files)} batch files")
        
        if not batch_files:
            return {}
        
        # Analyze each file
        file_analysis = {}
        all_products = {}
        file_hashes = {}
        
        for filepath in batch_files:
            analysis = self._analyze_single_file(filepath)
            file_analysis[filepath] = analysis
            
            # Track all products for deduplication
            for product_id, product_data in analysis["products"].items():
                if product_id not in all_products:
                    all_products[product_id] = product_data
                else:
                    self.stats["duplicate_products"] += 1
            
            # Track file content hash
            file_hash = self._get_file_hash(filepath)
            if file_hash in file_hashes:
                file_hashes[file_hash].append(filepath)
            else:
                file_hashes[file_hash] = [filepath]
        
        self.stats["total_products"] = sum(len(analysis["products"]) for analysis in file_analysis.values())
        self.stats["unique_products"] = len(all_products)
        
        return {
            "file_analysis": file_analysis,
            "all_products": all_products,
            "file_hashes": file_hashes,
            "stats": self.stats.copy()
        }
    
    def _analyze_single_file(self, filepath: str) -> Dict:
        """Analyze a single batch file"""
        filename = os.path.basename(filepath)
        products = {}
        product_count = 0
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        product = json.loads(line)
                        product_id = (
                            product.get("product_id") 
                            or product.get("productId") 
                            or product.get("id")
                        )
                        
                        if product_id:
                            products[str(product_id)] = product
                        
                        product_count += 1
                        
                    except json.JSONDecodeError as e:
                        logging.warning(f"⚠️ JSON error in {filename} line {line_num}: {e}")
                        continue
            
            return {
                "filename": filename,
                "filepath": filepath,
                "total_products": product_count,
                "unique_products": len(products),
                "products": products,
                "file_size": os.path.getsize(filepath),
                "last_modified": datetime.fromtimestamp(os.path.getmtime(filepath))
            }
            
        except Exception as e:
            logging.error(f"❌ Error analyzing {filename}: {e}")
            return {
                "filename": filename,
                "filepath": filepath,
                "total_products": 0,
                "unique_products": 0,
                "products": {},
                "file_size": 0,
                "last_modified": None,
                "error": str(e)
            }
    
    def _get_file_hash(self, filepath: str) -> str:
        """Get content hash of a file"""
        try:
            with open(filepath, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""
    
    def remove_duplicate_files(self, analysis: Dict) -> bool:
        """Remove files with identical content"""
        logging.info("🗑️ Removing duplicate files...")
        
        file_hashes = analysis["file_hashes"]
        removed_count = 0
        
        for file_hash, filepaths in file_hashes.items():
            if len(filepaths) > 1:
                # Keep the first file, remove the rest
                keep_file = filepaths[0]
                remove_files = filepaths[1:]
                
                logging.info(f"🔄 Found {len(filepaths)} identical files, keeping {os.path.basename(keep_file)}")
                
                for filepath in remove_files:
                    try:
                        # Move to backup instead of deleting
                        backup_path = os.path.join(self.backup_dir, os.path.basename(filepath))
                        shutil.move(filepath, backup_path)
                        removed_count += 1
                        logging.info(f"   📦 Moved {os.path.basename(filepath)} to backup")
                    except Exception as e:
                        logging.error(f"   ❌ Error moving {filepath}: {e}")
        
        self.stats["removed_files"] = removed_count
        logging.info(f"✅ Removed {removed_count} duplicate files")
        return True
    
    def consolidate_small_files(self, analysis: Dict, target_size: int = 50) -> bool:
        """Consolidate small files into larger ones"""
        logging.info(f"🔄 Consolidating files smaller than {target_size} products...")
        
        file_analysis = analysis["file_analysis"]
        small_files = []
        large_files = []
        
        # Separate small and large files
        for filepath, analysis_data in file_analysis.items():
            if os.path.exists(filepath):  # Check if file still exists after deduplication
                if analysis_data["unique_products"] < target_size:
                    small_files.append((filepath, analysis_data))
                else:
                    large_files.append((filepath, analysis_data))
        
        if not small_files:
            logging.info("ℹ️ No small files to consolidate")
            return True
        
        logging.info(f"📁 Found {len(small_files)} small files to consolidate")
        
        # Group small files for consolidation
        consolidated_groups = []
        current_group = []
        current_size = 0
        
        for filepath, analysis_data in small_files:
            if current_size + analysis_data["unique_products"] <= target_size * 2:
                current_group.append((filepath, analysis_data))
                current_size += analysis_data["unique_products"]
            else:
                if current_group:
                    consolidated_groups.append(current_group)
                current_group = [(filepath, analysis_data)]
                current_size = analysis_data["unique_products"]
        
        # Add the last group
        if current_group:
            consolidated_groups.append(current_group)
        
        # Consolidate each group
        consolidated_count = 0
        for i, group in enumerate(consolidated_groups):
            if len(group) > 1:  # Only consolidate if multiple files
                if self._consolidate_group(group, i + 1):
                    consolidated_count += len(group)
        
        self.stats["consolidated_files"] = consolidated_count
        logging.info(f"✅ Consolidated {consolidated_count} files into larger batches")
        return True
    
    def _consolidate_group(self, group: List[Tuple[str, Dict]], group_id: int) -> bool:
        """Consolidate a group of files into one"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            consolidated_filename = f"batch_consolidated_{timestamp}_group_{group_id}.jsonl"
            consolidated_path = os.path.join(self.batch_dir, consolidated_filename)
            
            # Collect all unique products from the group
            all_products = {}
            for filepath, analysis_data in group:
                all_products.update(analysis_data["products"])
            
            # Write consolidated file
            with open(consolidated_path, "w", encoding="utf-8") as f:
                for product in all_products.values():
                    json_line = json.dumps(product, ensure_ascii=False, separators=(",", ":")) + "\n"
                    f.write(json_line)
            
            # Move original files to backup
            for filepath, _ in group:
                try:
                    backup_path = os.path.join(self.backup_dir, os.path.basename(filepath))
                    shutil.move(filepath, backup_path)
                    logging.debug(f"   📦 Moved {os.path.basename(filepath)} to backup")
                except Exception as e:
                    logging.warning(f"   ⚠️ Could not move {filepath}: {e}")
            
            logging.info(f"✅ Consolidated {len(group)} files into {consolidated_filename} ({len(all_products)} unique products)")
            return True
            
        except Exception as e:
            logging.error(f"❌ Error consolidating group: {e}")
            return False
    
    def remove_duplicate_products(self) -> bool:
        """Remove duplicate products from remaining files"""
        logging.info("🔄 Removing duplicate products from files...")
        
        # Get all remaining batch files
        batch_files = []
        for filename in os.listdir(self.batch_dir):
            if filename.startswith("batch_") and filename.endswith(".jsonl"):
                filepath = os.path.join(self.batch_dir, filename)
                batch_files.append(filepath)
        
        if not batch_files:
            logging.info("ℹ️ No batch files to process")
            return True
        
        processed_files = 0
        total_duplicates_removed = 0
        
        for filepath in batch_files:
            try:
                # Read all products from file
                products = {}
                duplicate_count = 0
                
                with open(filepath, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        
                        try:
                            product = json.loads(line)
                            product_id = (
                                product.get("product_id") 
                                or product.get("productId") 
                                or product.get("id")
                            )
                            
                            if product_id:
                                product_id = str(product_id)
                                if product_id not in products:
                                    products[product_id] = product
                                else:
                                    duplicate_count += 1
                            else:
                                # Product without ID, keep it
                                products[f"no_id_{len(products)}"] = product
                                
                        except json.JSONDecodeError:
                            continue
                
                if duplicate_count > 0:
                    # Rewrite file with unique products only
                    temp_path = filepath + ".tmp"
                    with open(temp_path, "w", encoding="utf-8") as f:
                        for product in products.values():
                            json_line = json.dumps(product, ensure_ascii=False, separators=(",", ":")) + "\n"
                            f.write(json_line)
                    
                    # Atomic move
                    shutil.move(temp_path, filepath)
                    total_duplicates_removed += duplicate_count
                    logging.info(f"✅ Removed {duplicate_count} duplicates from {os.path.basename(filepath)}")
                
                processed_files += 1
                
            except Exception as e:
                logging.error(f"❌ Error processing {filepath}: {e}")
        
        logging.info(f"✅ Processed {processed_files} files, removed {total_duplicates_removed} duplicate products")
        return True
    
    def print_final_stats(self):
        """Print final statistics"""
        logging.info("📊 Final Cleanup Statistics:")
        logging.info(f"   Total files processed: {self.stats['total_files']}")
        logging.info(f"   Duplicate files removed: {self.stats['removed_files']}")
        logging.info(f"   Files consolidated: {self.stats['consolidated_files']}")
        logging.info(f"   Total products: {self.stats['total_products']:,}")
        logging.info(f"   Unique products: {self.stats['unique_products']:,}")
        logging.info(f"   Duplicate products: {self.stats['duplicate_products']:,}")
        
        # Count remaining files
        remaining_files = len([f for f in os.listdir(self.batch_dir) 
                             if f.startswith("batch_") and f.endswith(".jsonl")])
        logging.info(f"   Remaining batch files: {remaining_files}")
        
        # Count backup files
        backup_files = len([f for f in os.listdir(self.backup_dir) 
                          if f.startswith("batch_") and f.endswith(".jsonl")])
        logging.info(f"   Files in backup: {backup_files}")
    
    def cleanup(self, target_size: int = 50) -> bool:
        """Perform complete cleanup process"""
        logging.info("🚀 Starting batch file cleanup process...")
        
        try:
            # Step 1: Analyze all files
            analysis = self.analyze_batch_files()
            if not analysis:
                logging.info("ℹ️ No batch files found")
                return True
            
            # Step 2: Remove duplicate files
            self.remove_duplicate_files(analysis)
            
            # Step 3: Re-analyze after removing duplicates
            analysis = self.analyze_batch_files()
            
            # Step 4: Consolidate small files
            self.consolidate_small_files(analysis, target_size)
            
            # Step 5: Remove duplicate products from remaining files
            self.remove_duplicate_products()
            
            # Step 6: Print final statistics
            self.print_final_stats()
            
            logging.info("✅ Batch file cleanup completed successfully!")
            return True
            
        except Exception as e:
            logging.error(f"❌ Error during cleanup: {e}")
            return False


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Clean up duplicate batch files")
    parser.add_argument("--batch-dir", default="batch", help="Batch directory")
    parser.add_argument("--backup-dir", default="batch_backup", help="Backup directory")
    parser.add_argument("--target-size", type=int, default=50, help="Target size for consolidation")
    parser.add_argument("--dry-run", action="store_true", help="Analyze only, don't make changes")
    
    args = parser.parse_args()
    
    cleaner = BatchFileCleaner(args.batch_dir, args.backup_dir)
    
    if args.dry_run:
        logging.info("🔍 DRY RUN MODE - Analyzing only")
        analysis = cleaner.analyze_batch_files()
        cleaner.print_final_stats()
    else:
        cleaner.cleanup(args.target_size)


if __name__ == "__main__":
    main()
