#!/usr/bin/env python3
"""
Batch File Duplicate Analyzer
Analyzes batch files to find files with similar or duplicate products.
"""

import os
import json
import glob
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple
import argparse
from datetime import datetime


class BatchAnalyzer:
    def __init__(self, batch_dir: str = "batch"):
        self.batch_dir = batch_dir
        self.product_to_files = defaultdict(set)  # product_id -> set of files
        self.file_to_products = defaultdict(set)  # file -> set of product_ids
        self.file_stats = {}  # file -> stats dict
        
    def analyze_batch_files(self) -> Dict:
        """Analyze all batch files and return analysis results."""
        print(f"🔍 Analyzing batch files in: {self.batch_dir}")
        
        # Find all batch files
        batch_files = glob.glob(os.path.join(self.batch_dir, "*.jsonl"))
        print(f"📁 Found {len(batch_files)} batch files")
        
        if not batch_files:
            print("❌ No batch files found!")
            return {}
        
        # Process each batch file
        for batch_file in batch_files:
            self._process_batch_file(batch_file)
        
        # Generate analysis
        return self._generate_analysis()
    
    def _process_batch_file(self, batch_file: str):
        """Process a single batch file and extract product information."""
        filename = os.path.basename(batch_file)
        print(f"📄 Processing: {filename}")
        
        product_ids = set()
        product_count = 0
        
        try:
            with open(batch_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        product = json.loads(line)
                        product_id = product.get('product_id')
                        
                        if product_id:
                            product_ids.add(product_id)
                            self.product_to_files[product_id].add(filename)
                        
                        product_count += 1
                        
                    except json.JSONDecodeError as e:
                        print(f"⚠️ JSON error in {filename} line {line_num}: {e}")
                        continue
            
            # Store file statistics
            self.file_to_products[filename] = product_ids
            self.file_stats[filename] = {
                'total_products': product_count,
                'unique_products': len(product_ids),
                'file_size': os.path.getsize(batch_file),
                'last_modified': datetime.fromtimestamp(os.path.getmtime(batch_file))
            }
            
        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")
    
    def _generate_analysis(self) -> Dict:
        """Generate comprehensive analysis results."""
        analysis = {
            'summary': self._generate_summary(),
            'duplicate_products': self._find_duplicate_products(),
            'file_similarity': self._find_file_similarity(),
            'product_distribution': self._analyze_product_distribution(),
            'recommendations': self._generate_recommendations()
        }
        return analysis
    
    def _generate_summary(self) -> Dict:
        """Generate summary statistics."""
        total_files = len(self.file_stats)
        total_products = sum(stats['total_products'] for stats in self.file_stats.values())
        unique_products = len(self.product_to_files)
        
        duplicate_products = sum(1 for files in self.product_to_files.values() if len(files) > 1)
        
        return {
            'total_files': total_files,
            'total_products': total_products,
            'unique_products': unique_products,
            'duplicate_products': duplicate_products,
            'duplication_rate': (duplicate_products / unique_products * 100) if unique_products > 0 else 0
        }
    
    def _find_duplicate_products(self) -> List[Dict]:
        """Find products that appear in multiple files."""
        duplicates = []
        
        for product_id, files in self.product_to_files.items():
            if len(files) > 1:
                duplicates.append({
                    'product_id': product_id,
                    'files': sorted(list(files)),
                    'file_count': len(files)
                })
        
        # Sort by number of files (most duplicates first)
        duplicates.sort(key=lambda x: x['file_count'], reverse=True)
        return duplicates
    
    def _find_file_similarity(self) -> List[Dict]:
        """Find files with high product overlap."""
        similarities = []
        
        files = list(self.file_to_products.keys())
        
        for i, file1 in enumerate(files):
            for file2 in files[i+1:]:
                products1 = self.file_to_products[file1]
                products2 = self.file_to_products[file2]
                
                intersection = products1.intersection(products2)
                union = products1.union(products2)
                
                if intersection:  # Only report files with some overlap
                    similarity = len(intersection) / len(union) * 100
                    similarities.append({
                        'file1': file1,
                        'file2': file2,
                        'shared_products': len(intersection),
                        'total_unique_products': len(union),
                        'similarity_percentage': similarity,
                        'shared_product_ids': sorted(list(intersection))
                    })
        
        # Sort by similarity percentage (highest first)
        similarities.sort(key=lambda x: x['similarity_percentage'], reverse=True)
        return similarities
    
    def _analyze_product_distribution(self) -> Dict:
        """Analyze how products are distributed across files."""
        product_counts = Counter(len(files) for files in self.product_to_files.values())
        
        return {
            'products_in_1_file': product_counts[1],
            'products_in_2_files': product_counts[2],
            'products_in_3_files': product_counts[3],
            'products_in_4_plus_files': sum(product_counts[i] for i in range(4, max(product_counts.keys()) + 1)),
            'max_files_per_product': max(product_counts.keys()) if product_counts else 0
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        
        summary = self._generate_summary()
        duplicates = self._find_duplicate_products()
        similarities = self._find_file_similarity()
        
        # Duplication rate recommendations
        if summary['duplication_rate'] > 20:
            recommendations.append(f"⚠️ High duplication rate: {summary['duplication_rate']:.1f}% of products appear in multiple files")
        elif summary['duplication_rate'] > 10:
            recommendations.append(f"⚠️ Moderate duplication rate: {summary['duplication_rate']:.1f}% of products appear in multiple files")
        else:
            recommendations.append(f"✅ Low duplication rate: {summary['duplication_rate']:.1f}% of products appear in multiple files")
        
        # File similarity recommendations
        high_similarity_files = [s for s in similarities if s['similarity_percentage'] > 80]
        if high_similarity_files:
            recommendations.append(f"⚠️ Found {len(high_similarity_files)} pairs of files with >80% similarity")
            for sim in high_similarity_files[:3]:  # Show top 3
                recommendations.append(f"   - {sim['file1']} ↔ {sim['file2']} ({sim['similarity_percentage']:.1f}% similar)")
        
        # Product distribution recommendations
        distribution = self._analyze_product_distribution()
        if distribution['products_in_4_plus_files'] > 0:
            recommendations.append(f"⚠️ {distribution['products_in_4_plus_files']} products appear in 4+ files")
        
        return recommendations
    
    def print_analysis(self, analysis: Dict, detailed: bool = False):
        """Print the analysis results in a formatted way."""
        print("\n" + "="*80)
        print("📊 BATCH FILE ANALYSIS RESULTS")
        print("="*80)
        
        # Summary
        summary = analysis['summary']
        print(f"\n📈 SUMMARY:")
        print(f"   Total batch files: {summary['total_files']}")
        print(f"   Total products: {summary['total_products']:,}")
        print(f"   Unique products: {summary['unique_products']:,}")
        print(f"   Duplicate products: {summary['duplicate_products']:,}")
        print(f"   Duplication rate: {summary['duplication_rate']:.1f}%")
        
        # Product distribution
        distribution = analysis['product_distribution']
        print(f"\n📊 PRODUCT DISTRIBUTION:")
        print(f"   Products in 1 file: {distribution['products_in_1_file']:,}")
        print(f"   Products in 2 files: {distribution['products_in_2_files']:,}")
        print(f"   Products in 3 files: {distribution['products_in_3_files']:,}")
        print(f"   Products in 4+ files: {distribution['products_in_4_plus_files']:,}")
        
        # Top duplicates
        duplicates = analysis['duplicate_products']
        if duplicates:
            print(f"\n🔄 TOP DUPLICATE PRODUCTS:")
            for i, dup in enumerate(duplicates[:10], 1):
                print(f"   {i}. Product {dup['product_id']} appears in {dup['file_count']} files:")
                for file in dup['files']:
                    print(f"      - {file}")
        
        # File similarities
        similarities = analysis['file_similarity']
        if similarities:
            print(f"\n🔗 FILE SIMILARITIES (Top 10):")
            for i, sim in enumerate(similarities[:10], 1):
                print(f"   {i}. {sim['file1']} ↔ {sim['file2']}")
                print(f"      Similarity: {sim['similarity_percentage']:.1f}%")
                print(f"      Shared products: {sim['shared_products']}")
        
        # Recommendations
        recommendations = analysis['recommendations']
        if recommendations:
            print(f"\n💡 RECOMMENDATIONS:")
            for rec in recommendations:
                print(f"   {rec}")
        
        if detailed:
            # Detailed file statistics
            print(f"\n📄 DETAILED FILE STATISTICS:")
            for filename, stats in sorted(self.file_stats.items()):
                print(f"   {filename}:")
                print(f"      Products: {stats['total_products']:,} (unique: {stats['unique_products']:,})")
                print(f"      Size: {stats['file_size']:,} bytes")
                print(f"      Modified: {stats['last_modified'].strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    parser = argparse.ArgumentParser(description="Analyze batch files for duplicates and similarities")
    parser.add_argument("--batch-dir", default="batch", help="Directory containing batch files")
    parser.add_argument("--detailed", action="store_true", help="Show detailed file statistics")
    parser.add_argument("--output", help="Save results to JSON file")
    
    args = parser.parse_args()
    
    # Check if batch directory exists
    if not os.path.exists(args.batch_dir):
        print(f"❌ Batch directory not found: {args.batch_dir}")
        return
    
    # Run analysis
    analyzer = BatchAnalyzer(args.batch_dir)
    analysis = analyzer.analyze_batch_files()
    
    # Print results
    analyzer.print_analysis(analysis, detailed=args.detailed)
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        print(f"\n💾 Results saved to: {args.output}")


if __name__ == "__main__":
    main()
