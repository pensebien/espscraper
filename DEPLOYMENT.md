# ESP Scraper - Production Deployment Guide

## Overview

The ESP Scraper is a synchronized production system that coordinates:
1. **API Scraper**: Collects product links from ESP
2. **Product Detail Scraper**: Processes collected links to extract detailed product data

## Quick Start

### 1. Set Environment Variables
```bash
export ESP_USERNAME="your_esp_username"
export ESP_PASSWORD="your_esp_password"
export PRODUCTS_URL="https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductResults&referrerPage=Home&referrerModule=HOME&refModSufx=Generic&PCUrl=1&SearchID=782072784"
export SEARCH_API_URL="https://espweb.asicentral.com/api/SearchProduct.aspx"
export GOTO_PAGE_API_URL="https://espweb.asicentral.com/api/GotoPage.aspx"
export API_SCRAPED_LINKS_FILE="espscraper/data/api_scraped_links.jsonl"
export PRODUCT_OUTPUT_FILE="espscraper/data/final_product_details.jsonl"
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Scraper
```bash
# Basic run
python3 espscraper/production_main.py

# With custom batch size and retries
python3 espscraper/production_main.py --batch-size 20 --max-retries 3

# Test configuration first
python3 espscraper/production_main.py --dry-run
```

## Command Line Options

### Configuration
- `--batch-size N`: Batch size for both scrapers (default: 20)
- `--max-retries N`: Maximum retries for both scrapers (default: 3)

### Link Collection
- `--force-link-collection`: Force link collection even if file is fresh
- `--max-link-age HOURS`: Maximum age of links file before refresh (default: 24)
- `--link-limit N`: Limit number of links to collect
- `--pages N`: Number of pages to scrape for links
- `--new-only`: Only collect new links not already processed
- `--resume-missing`: Resume link collection from checkpoint
- `--fail-on-link-collection`: Fail entire scraper if link collection fails (default: continue with existing links)

### Product Processing
- `--mode {scrape,new,missing}`: Processing mode (default: scrape)
- `--product-limit N`: Limit number of products to process

### Control
- `--force-relogin`: Force fresh login
- `--dry-run`: Test configuration without scraping
- `--validate-only`: Only validate configuration

### Logging
- `--log-level {DEBUG,INFO,WARNING,ERROR}`: Logging level (default: INFO)
- `--log-file PATH`: Custom log file path

## Production Scenarios

### Initial Full Scrape
```bash
python3 espscraper/production_main.py \
  --force-link-collection \
  --batch-size 20 \
  --max-retries 3 \
  --product-limit 1000
```

### Daily Update
```bash
python3 espscraper/production_main.py \
  --max-link-age 24 \
  --mode new \
  --batch-size 30 \
  --max-retries 3
```

### Incremental Update
```bash
python3 espscraper/production_main.py \
  --mode new \
  --batch-size 20 \
  --max-retries 2
```

## File Structure

```
espscraper-project-vscode/
├── espscraper/
│   ├── production_main.py          # Main entry point
│   ├── api_scraper.py             # API link collection
│   ├── api_product_detail_scraper.py # Product detail processing
│   ├── batch_processor.py         # Batch processing system
│   ├── session_manager.py         # Session management
│   └── data/                      # Canonical files
│       ├── api_scraped_links.jsonl    # Collected product links
│       └── final_product_details.jsonl # Processed product data
├── batch/                         # Batch files (temporary)
│   ├── batch_20241201_143022_1.jsonl
│   ├── batch_20241201_143022_2.jsonl
│   └── ...
├── logs/                          # Log files
├── tmp/                           # Temporary session files
├── requirements.txt               # Python dependencies
├── validate_batches.py           # Batch validation script
└── DEPLOYMENT.md                 # This guide
```

## Monitoring

### Log Files
- Location: `logs/production_scraper_YYYYMMDD_HHMMSS.log`
- Contains detailed progress for both phases

### Checkpoint Files
- Link collection: `espscraper/data/api_scraped_links.checkpoint.txt`
- Product processing: `espscraper/data/final_product_details.checkpoint.txt`
- Product progress: `espscraper/data/final_product_details.progress.json`

### Output Files
- Links: `espscraper/data/api_scraped_links.jsonl`
- Products: `espscraper/data/final_product_details.jsonl`

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   ```bash
   # Clear session and retry
   rm -rf tmp/session_*
   python3 espscraper/production_main.py --force-relogin --batch-size 10
   ```

2. **Rate Limited**
   ```bash
   # Reduce rate limiting
   python3 espscraper/production_main.py --batch-size 10 --max-retries 2
   ```

3. **Resume from Failure**
   ```bash
   # Resume missing products
   python3 espscraper/production_main.py --mode missing --resume-missing
   
   # Resume from interruption (automatic)
   python3 espscraper/production_main.py --mode scrape
   ```

4. **Handle Link Collection Failures**
   ```bash
   # Continue with existing links if link collection fails (default behavior)
   python3 espscraper/production_main.py --batch-size 20 --max-retries 3
   
   # Fail entire scraper if link collection fails
   python3 espscraper/production_main.py --fail-on-link-collection
   ```

### Debug Mode
```bash
python3 espscraper/production_main.py --log-level DEBUG --batch-size 5
```

## Performance Tips

- Start with small batch sizes (10-20) and increase gradually
- Use `--dry-run` to test configuration before full scrape
- Monitor logs for errors and performance metrics
- Use `--max-link-age` to control link collection frequency
- Let the scraper handle session refresh automatically

## Enhanced Indexing & Resume Capabilities

### Automatic Resume
The scraper automatically resumes from where it left off if interrupted:
- **Checkpoint Tracking**: Saves current product ID being processed
- **Progress Indexing**: Maintains index of all scraped products
- **Smart Resume**: Skips already processed products on restart
- **Auto-Repair**: Automatically detects and repairs corrupted JSONL files

### Resume Mechanisms
1. **Checkpoint File**: `final_product_details.checkpoint.txt` - Current product being processed
2. **Progress File**: `final_product_details.progress.json` - Batch and progress information
3. **Output Index**: Scans existing output file for already scraped products
4. **Auto-Repair**: Validates and repairs corrupted JSONL files before processing

### Interruption Handling
```bash
# If scraper is interrupted (Ctrl+C, crash, etc.)
# Simply restart with same command - it will resume automatically
# Auto-repair will handle any corrupted files
python3 espscraper/production_main.py --batch-size 20 --max-retries 3
```

### Manual Resume Control
```bash
# Force fresh start (ignore checkpoints)
rm -f espscraper/data/final_product_details.checkpoint.txt
rm -f espscraper/data/final_product_details.progress.json

# Resume only missing products
python3 espscraper/production_main.py --mode missing
```

### JSONL File Validation & Repair
```bash
# Validate JSONL file integrity
python3 repair_jsonl.py --validate espscraper/data/final_product_details.jsonl

# Repair corrupted JSONL file
python3 repair_jsonl.py espscraper/data/final_product_details.jsonl

# Repair without backup
python3 repair_jsonl.py espscraper/data/final_product_details.jsonl --no-backup
```

**Auto-Repair Integration**: The scraper now automatically validates and repairs corrupted JSONL files:
- **Pre-Write Validation**: Checks file integrity before writing new data
- **Automatic Repair**: Removes invalid JSON lines and creates backups
- **Transparent Operation**: No manual intervention required
- **Backup Creation**: Creates `.backup` files before repairs

## Security

- Never commit environment variables to version control
- Keep `tmp/` directory secure
- Review logs for sensitive information
- Respect ESP's rate limits to avoid IP blocking 




Check the plugin @plugin-scraper.yml file for how we buildthe former github flow. But it this case we want to divide the flow. 

Use a different file. Api_scraper.yml that does the scraping

We are missing something also. All product file should also be saved in batches. Have an indexer that sync batches with the main final file.

importer.yml that helps in the importing to WP.