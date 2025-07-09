# ESP Scraper - Production Deployment Guide

## 🚀 Quick Start

### 1. **GitHub Secrets Setup**

Add these secrets to your GitHub repository (Settings > Secrets and variables > Actions):

```
ESP_USERNAME=your_username
ESP_PASSWORD=your_password
PRODUCTS_URL=https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductSearch&SearchID=your_search_id
SEARCH_API_URL=https://espweb.asicentral.com/api/SearchProduct
GOTO_PAGE_API_URL=https://espweb.asicentral.com/api/GotoPage
PRODUCT_URL_TEMPLATE=https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductDetails&productID={product_id}&autoLaunchVS=0&tab=list
```

### 2. **Run the Scraper**

#### Option A: GitHub Actions (Recommended)
1. Go to your repository on GitHub
2. Click "Actions" tab
3. Select "ESP Scraper" workflow
4. Click "Run workflow"
5. Configure parameters:
   - **Limit**: Number of products to scrape (default: 10)
   - **Headless**: Run without browser window (default: true)
   - **Force relogin**: Fresh login session (default: false)
   - **Collect links**: Get new product links first (default: true)

#### Option B: Local Production Run
```bash
# Validate configuration
python espscraper/production_main.py --validate-only

# Run scraper
python espscraper/production_main.py --limit 50 --collect-links --headless
```

## 📁 **File Structure**

```
espscraper-project-vscode/
├── .github/workflows/scraper.yml    # GitHub Actions workflow
├── espscraper/
│   ├── __main__.py                  # Main entry point
│   ├── production_main.py           # Production entry point
│   ├── scrape_product_details.py    # Product scraper
│   ├── api_scraper.py              # Link collector
│   ├── session_manager.py          # Session management
│   └── data/                       # Output directory
├── production_config.py             # Production settings
├── requirements.txt                 # Dependencies
└── PRODUCTION_README.md           # This file
```

## ⚙️ **Configuration**

### Production Settings (`production_config.py`)

- **Headless Mode**: Always enabled in production
- **Memory Limit**: 4GB for Chrome
- **Retry Limits**: Reduced for faster failure detection
- **Rate Limiting**: 2-second delays between requests
- **Error Handling**: Non-aggressive cleanup (preserves user browsers)

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ESP_USERNAME` | Your ESP login username | `john.doe@company.com` |
| `ESP_PASSWORD` | Your ESP login password | `your_password` |
| `PRODUCTS_URL` | ESP products page URL | `https://espweb.asicentral.com/...` |
| `SEARCH_API_URL` | Search API endpoint | `https://espweb.asicentral.com/api/SearchProduct` |
| `GOTO_PAGE_API_URL` | Pagination API endpoint | `https://espweb.asicentral.com/api/GotoPage` |
| `PRODUCT_URL_TEMPLATE` | Product detail URL template | `https://espweb.asicentral.com/...productID={product_id}...` |

## 🔧 **Troubleshooting**

### Common Issues

1. **"Connection refused" errors**
   - Solution: Use headless mode (`--headless`)
   - Cause: GUI conflicts in CI environment

2. **"N/A" values in scraped data**
   - Solution: Updated selectors in latest version
   - Cause: Website structure changes

3. **Session timeout**
   - Solution: Use `--force-relogin` flag
   - Cause: Expired authentication

4. **Memory issues**
   - Solution: Reduced batch sizes and memory limits
   - Cause: Large product datasets

### Debug Mode

Enable debug logging:
```bash
python espscraper/production_main.py --log-level DEBUG --limit 5
```

### Log Files

- `log/scraper.log` - Main application logs
- `connection_errors.log` - Selenium connection issues
- `failed_products.txt` - Products that failed to scrape

## 📊 **Output Files**

### Generated Files

- `espscraper/data/api_scraped_links.jsonl` - Product links
- `espscraper/data/final_product_details.jsonl` - Scraped product details
- `espscraper/data/api_scraped_links.checkpoint.txt` - Progress checkpoint
- `espscraper/data/api_scraped_links.meta.json` - Metadata

### Data Format

```json
{
  "ProductID": "123456789",
  "Name": "Product Name",
  "SKU": "SKU123",
  "ShortDescription": "Product description",
  "ImageURL": "https://...",
  "PricingTable": [...],
  "Colors": ["Red", "Blue"],
  "ProductionTime": "2-3 weeks",
  "Supplier": "Supplier Name",
  "Imprint": {...},
  "ProductionInfo": {...}
}
```

## 🚀 **GitHub Actions Workflow**

The workflow automatically:

1. **Sets up environment** - Python, Chrome, dependencies
2. **Validates configuration** - Checks environment variables
3. **Runs scraper** - Collects links and scrapes details
4. **Uploads artifacts** - Saves data and logs
5. **Handles errors** - Proper error reporting and cleanup

### Workflow Triggers

- **Manual**: Run from GitHub Actions tab
- **Scheduled**: Add cron schedule in workflow file
- **Webhook**: Trigger via API calls

## 🔒 **Security**

- **Secrets**: All credentials stored in GitHub Secrets
- **No hardcoded values**: All sensitive data in environment variables
- **Secure logging**: No passwords in log files
- **Cleanup**: Temporary files removed after run

## 📈 **Performance**

### Optimizations

- **Headless mode**: Faster, less memory usage
- **Image disabling**: Reduces bandwidth and memory
- **Batch processing**: Efficient data handling
- **Checkpointing**: Resume from failures
- **Rate limiting**: Respects server limits

### Expected Performance

- **Link collection**: ~100 products/minute
- **Detail scraping**: ~30 products/minute
- **Memory usage**: ~2-4GB peak
- **Duration**: ~1 hour for 1000 products

## 🆘 **Support**

### Before Reporting Issues

1. **Check logs**: Review `log/scraper.log`
2. **Validate config**: Run `--validate-only`
3. **Test locally**: Try with small limits first
4. **Check credentials**: Verify login works manually

### Common Commands

```bash
# Test configuration
python espscraper/production_main.py --validate-only

# Test with small sample
python espscraper/production_main.py --limit 5 --collect-links

# Force fresh login
python espscraper/production_main.py --force-relogin --limit 10

# Debug mode
python espscraper/production_main.py --log-level DEBUG --limit 3
```

## 📝 **Changelog**

### Latest Updates

- ✅ **Fixed data extraction** - Updated selectors for current website
- ✅ **Simplified session management** - Removed complex retry logic
- ✅ **Production configuration** - Optimized for CI/CD
- ✅ **GitHub Actions workflow** - Automated deployment
- ✅ **Better error handling** - Graceful failure recovery
- ✅ **Memory optimization** - Reduced Chrome memory usage

---

**Ready for production!** 🎉 