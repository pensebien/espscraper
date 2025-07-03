# ESP Product Detail Scraper

A robust, production-ready Python scraper for monitoring and extracting product details from ESP Web. Features intelligent deduplication, checkpointing, batching, and automatic error recovery.

## 📁 Project Structure

```
espscraper-project/
├── espscraper/                    # Main scraper package
│   ├── __init__.py               # Package initialization
│   ├── __main__.py               # CLI entry point
│   ├── base_scraper.py           # Base scraper class
│   ├── api_scraper.py            # API-based link collection
│   ├── scrape_product_details.py # Selenium-based detail scraping
│   ├── session_manager.py        # Authentication & session management
│   ├── selenium_resilient_manager.py # Robust Selenium driver management
│   ├── deduplicator.py           # Link deduplication utility
│   ├── merger.py                 # Link file merger utility
│   ├── merger_product_details.py # Product details merger utility
│   └── data/                     # Data storage directory
│       ├── api_scraped_links.jsonl           # Collected product links
│       ├── api_scraped_links.BACKUP.jsonl    # Backup of original links
│       ├── api_scraped_links.deduped.jsonl   # Deduplicated links
│       ├── api_scraped_links.checkpoint.txt  # Page checkpoint for resuming
│       ├── api_scraped_links.meta.json       # API metadata (total pages, etc.)
│       ├── final_product_details.jsonl       # Scraped product details
│       ├── final_product_details_merged.jsonl # Merged product details
│       ├── unified_products.json             # Unified product data
│       ├── to_scrape.jsonl                   # Links pending scraping
│       ├── search_response.json              # Sample API response
│       └── links_checkpoint.txt              # Detail scraping checkpoint
├── tmp/                          # Temporary session files
│   ├── session_cookies.json      # Authentication cookies
│   └── session_state.json        # Session state (pageKey, searchId)
├── log/                          # Log files
│   └── scraper.log               # Scraper execution logs
├── espenv/                       # Python virtual environment
├── requirements.txt              # Python dependencies
├── setup.py                      # Package setup
├── .env                          # Environment variables (create this)
├── .gitignore                    # Git ignore rules
├── failed_products.txt           # Failed product IDs for retry
└── README.md                     # This file
```

## 🚀 Quickstart

1. **Clone the repo and set up a virtual environment:**
   ```bash
   python3 -m venv espenv
   source espenv/bin/activate  # On Windows: espenv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure your `.env` file:**
   ```bash
   ESP_USERNAME=your_username
   ESP_PASSWORD=your_password
   PRODUCTS_URL=https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductResults
   SEARCH_API_URL=https://espweb.asicentral.com/api/SearchProduct
   GOTO_PAGE_API_URL=https://espweb.asicentral.com/api/GotoPage
   PRODUCT_URL_TEMPLATE=https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductDetails&referrerPage=ProductResults&referrerModule=PRDRES&refModSufx=Generic&PCUrl=1&productID={product_id}&autoLaunchVS=0&tab=list
   OUTPUT_FILE=espscraper/data/api_scraped_links.jsonl
   DETAILS_OUTPUT_FILE=espscraper/data/final_product_details.jsonl
   DETAILS_LINKS_FILE=espscraper/data/api_scraped_links.jsonl
   ```

3. **Run the scraper:**
   ```bash
   python -m espscraper --collect-links --limit 100 --headless --log-file scraper.log
   ```

## 🎯 Key Features

### 🔄 **Resume & Recovery**
- **`--new-only`**: Collect only new product links from the top (pages 1, 2, etc.)
- **`--resume-missing`**: Resume from checkpoint and continue collecting links from where you left off
- **Automatic checkpointing**: Saves progress after each page
- **Session persistence**: Maintains authentication across runs
- **Failed product retry**: Automatically retries failed products with exponential backoff

### 🛡️ **Robustness & Error Handling**
- **Selenium crash recovery**: Automatically restarts driver on crashes
- **Network resilience**: Handles timeouts and connection errors
- **Batch retry logic**: Retries failed products in batches
- **Graceful degradation**: Continues scraping even if some products fail

### 📊 **Deduplication & Data Management**
- **In-memory deduplication**: Prevents duplicates during collection
- **Deduplication utility**: `python espscraper/deduplicator.py` to clean existing files
- **Consistent key ordering**: Standardizes JSON output format
- **Merger utilities**: Combine multiple scraped files

### ⚡ **Performance & Scalability**
- **Batching support**: Process products in configurable batches
- **Concurrent-safe**: Can run multiple instances safely
- **Memory efficient**: Streams data to files, doesn't load everything in memory
- **Rate limiting**: Built-in delays to avoid overwhelming the server

## 🖥️ CLI Options

### Main Scraper (`python -m espscraper`)
```bash
# Basic usage
python -m espscraper --collect-links --limit 100 --headless

# Resume from where you left off
python -m espscraper --collect-links --resume-missing --headless

# Only collect new products (skip already scraped)
python -m espscraper --collect-links --new-only --headless

# Process in batches
python -m espscraper --batch-size 500 --batch-number 0

# Force fresh login
python -m espscraper --force-relogin --headless

# Clear session and start fresh
python -m espscraper --clear-session --headless
```

### Link Collection Only (`python -m espscraper.api_scraper`)
```bash
# Collect links with resume support
python -m espscraper.api_scraper --resume-missing --limit 1000

# Collect only new links
python -m espscraper.api_scraper --new-only --limit 500

# Force fresh login
python -m espscraper.api_scraper --force-relogin --limit 200
```

### Detail Scraping Only (`python -m espscraper.scrape_product_details`)
```bash
# Scrape product details
python -m espscraper.scrape_product_details --headless --limit 100

# Overwrite output file
python -m espscraper.scrape_product_details --overwrite-output --headless
```

## 🛠️ Utility Scripts

### Deduplication
```bash
# Deduplicate links file with consistent key ordering
python espscraper/deduplicator.py
```

### Merging
```bash
# Merge link files
python espscraper/merger.py --api-links-file new_links.jsonl

# Merge product detail files
python espscraper/merger_product_details.py --existing existing.jsonl --new new.jsonl --output merged.jsonl
```

## 📈 Advanced Usage Examples

### 1. **Continuous Monitoring (Catch New Products)**
```bash
# Run daily to catch new products added to the top
python -m espscraper --collect-links --new-only --headless --log-file daily.log
```

### 2. **Fill Missing Gaps**
```bash
# Resume from where you left off to fill any gaps
python -m espscraper --collect-links --resume-missing --headless --log-file resume.log
```

### 3. **Large-Scale Processing**
```bash
# Process 10,000 products in batches of 500
for i in {0..19}; do
    python -m espscraper --batch-size 500 --batch-number $i --headless --log-file batch_$i.log
done
```

### 4. **Production Setup with Cron**
```bash
# Add to crontab for daily monitoring
0 2 * * * cd /path/to/espscraper-project && source espenv/bin/activate && python -m espscraper --collect-links --new-only --headless --log-file /var/log/esp_scraper.log
```

## 📊 Data Files Explained

### **Link Collection Files**
- `api_scraped_links.jsonl`: Main product links file (JSONL format)
- `api_scraped_links.checkpoint.txt`: Last completed page number
- `api_scraped_links.meta.json`: API metadata (total products, pages, etc.)
- `api_scraped_links.BACKUP.jsonl`: Backup before deduplication

### **Product Detail Files**
- `final_product_details.jsonl`: Scraped product details
- `failed_products.txt`: Product IDs that failed to scrape (for retry)

### **Session Files**
- `tmp/session_cookies.json`: Authentication cookies
- `tmp/session_state.json`: Session state (pageKey, searchId)

## 🔧 Environment Variables

| Variable               | Required | Description                                                                  |
| ---------------------- | -------- | ---------------------------------------------------------------------------- |
| `ESP_USERNAME`         | ✅        | Your ESP username                                                            |
| `ESP_PASSWORD`         | ✅        | Your ESP password                                                            |
| `PRODUCTS_URL`         | ✅        | ESP products page URL                                                        |
| `SEARCH_API_URL`       | ✅        | ESP search API endpoint                                                      |
| `GOTO_PAGE_API_URL`    | ✅        | ESP pagination API endpoint                                                  |
| `PRODUCT_URL_TEMPLATE` | ✅        | Product detail URL template                                                  |
| `OUTPUT_FILE`          | ❌        | Link output file (default: `espscraper/data/api_scraped_links.jsonl`)        |
| `DETAILS_OUTPUT_FILE`  | ❌        | Details output file (default: `espscraper/data/final_product_details.jsonl`) |
| `DETAILS_LINKS_FILE`   | ❌        | Input links file (default: `espscraper/data/api_scraped_links.jsonl`)        |

## 🐛 Troubleshooting

### **Common Issues**

1. **Authentication Errors**
   ```bash
   # Clear session and force relogin
   python -m espscraper --clear-session --force-relogin --headless
   ```

2. **Driver Crashes**
   - The scraper automatically restarts the driver
   - Check `failed_products.txt` for products that need manual retry

3. **Duplicate Products**
   ```bash
   # Run deduplicator to clean up
   python espscraper/deduplicator.py
   ```

4. **Memory Issues**
   - Use `--limit` to process smaller batches
   - Use `--batch-size` and `--batch-number` for large datasets

### **Log Analysis**
```bash
# Check for errors
grep "ERROR\|FAILED\|❌" log/scraper.log

# Check progress
grep "✅ Page.*complete" log/scraper.log

# Check authentication
grep "login\|session" log/scraper.log
```

## 📝 License
MIT License - see LICENSE file for details.

## 🤝 Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support
For issues and questions:
1. Check the troubleshooting section
2. Review the logs in `log/` directory
3. Open an issue with detailed error information 