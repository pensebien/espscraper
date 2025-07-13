# Batch Processing Guide

## Overview

The ESP Scraper now uses a sophisticated batch processing system to handle large datasets efficiently. This guide explains how the system works and how to configure it for different scenarios.

## Folder Structure

```
espscraper-project-vscode/
├── espscraper/
│   ├── data/                          # Canonical files
│   │   ├── api_scraped_links.jsonl    # Product links
│   │   └── final_product_details.jsonl # Main product data
│   └── ...
├── batch/                             # Batch files
│   ├── batch_20241201_143022_1.jsonl
│   ├── batch_20241201_143022_2.jsonl
│   └── ...
└── ...
```

### File Organization

- **`espscraper/data/`**: Contains canonical files (main output files)
- **`batch/`**: Contains temporary batch files during processing
- **Batch files**: Named with timestamp and sequence number

## How Product Limit Works

### For 4000 Products

When you set `--product-limit 4000`, the system:

1. **Reads up to 4000 product IDs** from the links file
2. **Processes them in batches** of configurable size (default: 50)
3. **Creates batch files** as products are processed
4. **Merges all batches** into the main output file at completion

### Example: 4000 Products with 50 Batch Size

```
Total Products: 4000
Batch Size: 50
Number of Batches: 80 (4000 ÷ 50)

Files Created:
├── batch/batch_20241201_143022_1.jsonl  (50 products)
├── batch/batch_20241201_143022_2.jsonl  (50 products)
├── ...
├── batch/batch_20241201_143022_80.jsonl (50 products)
└── espscraper/data/final_product_details.jsonl (4000 products)
```

## Configuration Options

### Batch Size
- **Default**: 50 products per batch
- **Range**: 10-200 recommended
- **Impact**: Smaller batches = more files but faster processing

### Product Limit
- **Default**: 4000 products
- **Maximum**: Limited by available product links
- **Usage**: Controls total number of products to process

### Example Configurations

#### Small Dataset (500 products)
```bash
python3 -m espscraper.production_main \
  --batch-size 25 \
  --product-limit 500
```

#### Medium Dataset (2000 products)
```bash
python3 -m espscraper.production_main \
  --batch-size 50 \
  --product-limit 2000
```

#### Large Dataset (4000 products)
```bash
python3 -m espscraper.production_main \
  --batch-size 100 \
  --product-limit 4000
```

## Processing Flow

### 1. Link Collection Phase
```bash
# Collect product links (if needed)
python3 -m espscraper.production_main \
  --force-link-collection \
  --product-limit 4000
```

### 2. Product Processing Phase
```bash
# Process products in batches
python3 -m espscraper.production_main \
  --mode scrape \
  --batch-size 50 \
  --product-limit 4000
```

### 3. Batch Management
- **During Processing**: Products saved to batch files
- **On Completion**: All batches merged to main file
- **On Interruption**: Can resume from last batch

## Resume Capabilities

### Automatic Resume
```bash
# Resume from where it left off
python3 -m espscraper.production_main \
  --mode scrape \
  --batch-size 50 \
  --product-limit 4000
```

### Manual Resume
```bash
# Process only missing products
python3 -m espscraper.production_main \
  --mode missing \
  --batch-size 50 \
  --product-limit 4000
```

## Validation and Monitoring

### Check Batch Statistics
```bash
python3 validate_batches.py --stats-only
```

### Validate Batch Files
```bash
python3 validate_batches.py --validate-only
```

### Monitor Progress
```bash
# Check current progress
ls -la batch/batch_*.jsonl | wc -l
wc -l espscraper/data/final_product_details.jsonl
```

## GitHub Actions Workflow

### API Scraper Workflow
The `api-scraper.yml` workflow handles:

1. **Environment Setup**: Python, Chrome, dependencies
2. **Data Fetching**: Retrieves existing files from artifacts branch
3. **Batch Processing**: Runs scraper with configurable parameters
4. **Validation**: Checks batch file integrity
5. **Artifact Storage**: Saves files to artifacts branch

### Workflow Parameters
- `batch_size`: 50 (default)
- `product_limit`: 4000 (default)
- `mode`: scrape (default)
- `force_link_collection`: false (default)
- `max_link_age`: 48 hours (default)

## Performance Considerations

### For 4000 Products

#### Recommended Settings
```bash
# Optimal for 4000 products
--batch-size 50
--product-limit 4000
--max-retries 3
```

#### Expected Performance
- **Processing Time**: 2-4 hours (depending on rate limits)
- **Batch Files**: 80 files (4000 ÷ 50)
- **Memory Usage**: ~50MB per batch
- **Disk Usage**: ~200MB total

#### Rate Limiting
- **Requests per minute**: 20-25
- **Delay between requests**: 2-3 seconds
- **Batch pause**: 10 seconds between batches

## Error Handling

### Batch Corruption
- **Auto-repair**: Automatically detects and repairs corrupted files
- **Backup creation**: Creates `.backup` files before repairs
- **Validation**: Checks JSON integrity before processing

### Interruption Recovery
- **Checkpoint files**: Track current processing position
- **Progress files**: Save batch and progress information
- **Resume capability**: Skip already processed products

### Network Issues
- **Retry mechanism**: Exponential backoff for failed requests
- **Circuit breaker**: Prevents cascading failures
- **Session management**: Automatic session refresh

## Best Practices

### For Large Datasets (4000+ products)

1. **Start Small**: Begin with 100-500 products to test
2. **Monitor Resources**: Check memory and disk usage
3. **Use Appropriate Batch Size**: 50-100 for most scenarios
4. **Enable Validation**: Always validate batch files
5. **Backup Regularly**: Keep copies of important files

### For Production Use

1. **Test Configuration**: Use `--dry-run` to test settings
2. **Monitor Logs**: Check log files for errors
3. **Validate Results**: Always validate output files
4. **Plan for Interruptions**: Design for resume capability
5. **Set Appropriate Limits**: Don't exceed rate limits

## Troubleshooting

### Common Issues

#### Batch Files Not Created
```bash
# Check if batch directory exists
ls -la batch/

# Check scraper logs
tail -f logs/production_scraper_*.log
```

#### Processing Stuck
```bash
# Check checkpoint file
cat espscraper/data/final_product_details.checkpoint.txt

# Check progress file
cat espscraper/data/final_product_details.progress.json
```

#### Memory Issues
```bash
# Reduce batch size
--batch-size 25

# Check system resources
free -h
df -h
```

#### Rate Limiting
```bash
# Increase delays
--batch-size 25
# (reduces requests per minute)

# Check rate limit logs
grep "Rate limit" logs/production_scraper_*.log
```

## Summary

The batch processing system provides:

✅ **Scalability**: Handle 4000+ products efficiently
✅ **Reliability**: Automatic error recovery and validation
✅ **Resume Capability**: Continue from interruptions
✅ **Monitoring**: Comprehensive progress tracking
✅ **Flexibility**: Configurable batch sizes and limits

For 4000 products, use:
- **Batch Size**: 50-100
- **Product Limit**: 4000
- **Max Retries**: 3
- **Validation**: Always enabled
