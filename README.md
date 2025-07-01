# ESP Product Detail Scraper

A robust, production-ready Python scraper for monitoring and extracting product details from ESP Web.

## Quickstart

1. **Clone the repo and set up a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Configure your `.env` file:**
   - `ESP_USERNAME` and `ESP_PASSWORD` (required)
   - `PRODUCTS_URL`, `DETAILS_OUTPUT_FILE`, `DETAILS_LINKS_FILE` (see below)
3. **Run the scraper:**
   ```bash
   python run_scraper.py --limit 100 --headless --log-file scraper.log
   ```

## CLI Options

- `--limit N` : Only scrape the first N products in the batch
- `--headless` : Run Chrome in headless mode
- `--force-relogin` : Force a new login/session
- `--output-file` : Output file for scraped details
- `--links-file` : Input links file (JSONL)
- `--overwrite-output` : Overwrite output file before scraping (do not resume)
- `--batch-size` : Number of products to process in this batch
- `--batch-number` : Batch number (0-based)
- `--log-file` : Log output to a file
- `--clear-session` : Clear session/cache before running

## Environment Variables

- `ESP_USERNAME` (required)
- `ESP_PASSWORD` (required)
- `PRODUCTS_URL` (required)
- `DETAILS_OUTPUT_FILE` (default: `final_product_details.jsonl`)
- `DETAILS_LINKS_FILE` (default: `api_scraped_links_fixed.jsonl`)

## Batching Example

To process 500 products per batch (8 batches for 4000 products):
```bash
python run_scraper.py --batch-size 500 --batch-number 0
python run_scraper.py --batch-size 500 --batch-number 1
# ... up to batch-number 7
```

## Resume & Overwrite
- By default, the scraper resumes from where it left off (skips already-scraped products).
- Use `--overwrite-output` to start from scratch.

## Logging
- Use `--log-file` to log output to a file for cron/production use.

## Temp/Session Files
- Session/cookie files are stored in `tmp/`.
- Use `--clear-session` to clear session/cache before running.

## License
MIT 