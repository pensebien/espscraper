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
   - By default, output, checkpoint, and metadata files are saved in `espscraper/data/`.
3. **Run the scraper:**
   ```bash
   python -m espscraper --limit 100 --headless --log-file scraper.log
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
- `DETAILS_OUTPUT_FILE` (default: `espscraper/data/final_product_details.jsonl`)
- `DETAILS_LINKS_FILE` (default: `espscraper/data/api_scraped_links.jsonl`)

## Batching Example

To process 500 products per batch (8 batches for 4000 products):
```bash
python -m espscraper --batch-size 500 --batch-number 0
python -m espscraper  --batch-size 500 --batch-number 1
# ... up to batch-number 7
```

## Resume & Overwrite
- By default, the scraper resumes from where it left off (skips already-scraped products).
- Use `--overwrite-output` to start from scratch.

## Logging
- Use `--log-file` to log output to a file for cron/production use.
- If you provide just a filename (e.g., `--log-file scraper.log`), the log will be placed in the `log/` folder by default. The `log` folder is created automatically if it does not exist.

## Temp/Session Files
- Session/cookie files are stored in `tmp/`.
- Use `--clear-session` to clear session/cache before running.

## Output, Metadata, and Checkpoint Files

- **Output links file:** Default is `espscraper/data/api_scraped_links.jsonl` (can be changed with `OUTPUT_FILE` or `DETAILS_LINKS_FILE` env var)
- **Product details output file:** Default is `espscraper/data/final_product_details.jsonl` (can be changed with `DETAILS_OUTPUT_FILE` env var)
- **Metadata file:** `espscraper/data/api_scraped_links.meta.json` (contains `ResultsPerPage`, `resultsTotal`, and `totalPages`)
- **Checkpoint file:** `espscraper/data/api_scraped_links.checkpoint.txt` (tracks last completed page for resuming)

All files are created if they do not exist. The scraper is robust to missing files and will use sensible defaults if metadata is missing.

## Dynamic Paging

The scraper automatically determines the number of pages to scrape based on the first search response (`ResultsPerPage` and `resultsTotal`). You do not need to specify the number of pages unless you want to override it with `--pages`.

## Running Only Link Scraper or Product Detail Scraper

You can run each part of the scraper independently:

### 1. Run Only the Link Scraper
Collect product links and save them to the data folder:

```bash
python -m espscraper.api_scraper
```

**Options:**
- `--pages N` — Limit the number of pages to scrape
- `--limit N` — Limit the number of product links to collect
- `--new-only` — Only collect links for products not already scraped (based on your detail output file)

**Example:**
```bash
python -m espscraper.api_scraper --limit 50 --new-only
```

### 2. Run Only the Product Detail Scraper
Read the links file and scrape product details:

```bash
python -m espscraper
```

**Options:**
- `--limit N` — Limit the number of product details to scrape
- `--headless` — Run the browser in headless mode
- `--log-file mylog.log` — Save logs to a file

**Example:**
```bash
python -m espscraper --limit 50 --headless --log-file details.log
```

### 3. Run Both in Sequence
To run both link collection and detail scraping in one command:

```bash
python -m espscraper --collect-links --limit 50 --new-only --headless
```

## License
MIT 