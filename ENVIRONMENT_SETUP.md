# Environment Setup Guide

## Overview

This guide explains how to configure environment variables for the ESP Scraper, including the API URL format you specified.

## Required Environment Variables

### GitHub Secrets (for GitHub Actions)

You need to set these secrets in your GitHub repository:

1. **Go to Repository Settings**:
   - Navigate to your GitHub repository
   - Click "Settings" tab
   - Click "Secrets and variables" → "Actions"

2. **Add Required Secrets**:

```yaml
# Authentication
ESP_USERNAME: your_esp_username
ESP_PASSWORD: your_esp_password

# URLs
PRODUCTS_URL: https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductResults
SEARCH_API_URL: https://espweb.asicentral.com/WebServices/ProductSearch.asmx/Search
GOTO_PAGE_API_URL: https://espweb.asicentral.com/WebServices/ProductSearch.asmx/GotoPage

# API Configuration
PRODUCT_API_URL: https://api.asicentral.com/v1/products/{product_id}.json
PRODUCT_URL_TEMPLATE: https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductDetails&referrerPage=ProductResults&referrerModule=PRDRES&refModSufx=Generic&PCUrl=1&productID={product_id}&autoLaunchVS=0&tab=list
```

### Local Environment Variables (for local development)

Create a `.env` file in your project root:

```bash
# Authentication
ESP_USERNAME=your_esp_username
ESP_PASSWORD=your_esp_password

# URLs
PRODUCTS_URL=https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductResults
SEARCH_API_URL=https://espweb.asicentral.com/WebServices/ProductSearch.asmx/Search
GOTO_PAGE_API_URL=https://espweb.asicentral.com/WebServices/ProductSearch.asmx/GotoPage

# API Configuration
PRODUCT_API_URL=https://api.asicentral.com/v1/products/{product_id}.json
PRODUCT_URL_TEMPLATE=https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductDetails&referrerPage=ProductResults&referrerModule=PRDRES&refModSufx=Generic&PCUrl=1&productID={product_id}&autoLaunchVS=0&tab=list
```

## API URL Configuration

### Your Specific API URL

Yes, you can absolutely set your API URL like this:

```bash
PRODUCT_API_URL=https://api.asicentral.com/v1/products/{product_id}.json
```

### How It Works

The scraper will:

1. **Replace `{product_id}`** with the actual product ID
2. **Make GET requests** to the API endpoint
3. **Parse JSON responses** for product details

### Example API Calls

```python
# Product ID: 12345
# API URL becomes: https://api.asicentral.com/v1/products/12345.json

# Product ID: ABC123
# API URL becomes: https://api.asicentral.com/v1/products/ABC123.json
```

## Setting Up GitHub Secrets

### Step-by-Step Instructions

1. **Navigate to Repository Settings**:
   ```
   Your Repository → Settings → Secrets and variables → Actions
   ```

2. **Add Each Secret**:
   - Click "New repository secret"
   - Name: `ESP_USERNAME`
   - Value: `your_actual_username`
   - Click "Add secret"

3. **Repeat for All Secrets**:
   ```
   ESP_USERNAME: your_esp_username
   ESP_PASSWORD: your_esp_password
   PRODUCTS_URL: https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductResults
   SEARCH_API_URL: https://espweb.asicentral.com/WebServices/ProductSearch.asmx/Search
   GOTO_PAGE_API_URL: https://espweb.asicentral.com/WebServices/ProductSearch.asmx/GotoPage
   PRODUCT_API_URL: https://api.asicentral.com/v1/products/{product_id}.json
   PRODUCT_URL_TEMPLATE: https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductDetails&referrerPage=ProductResults&referrerModule=PRDRES&refModSufx=Generic&PCUrl=1&productID={product_id}&autoLaunchVS=0&tab=list
   ```

## Environment Variable Usage

### In GitHub Actions Workflow

The workflow uses these environment variables:

```yaml
env:
  ESP_USERNAME: ${{ secrets.ESP_USERNAME }}
  ESP_PASSWORD: ${{ secrets.ESP_PASSWORD }}
  PRODUCTS_URL: ${{ secrets.PRODUCTS_URL }}
  SEARCH_API_URL: ${{ secrets.SEARCH_API_URL }}
  GOTO_PAGE_API_URL: ${{ secrets.GOTO_PAGE_API_URL }}
  PRODUCT_API_URL: ${{ secrets.PRODUCT_API_URL }}
  PRODUCT_URL_TEMPLATE: ${{ secrets.PRODUCT_URL_TEMPLATE }}
```

### In Python Code

The scraper loads these variables:

```python
import os

# Load environment variables
self.PRODUCT_API_URL = os.getenv("PRODUCT_API_URL")
self.PRODUCT_URL_TEMPLATE = os.getenv("PRODUCT_URL_TEMPLATE")
```

## Testing Your Configuration

### 1. Test API URL Format

```bash
# Test with a sample product ID
curl "https://api.asicentral.com/v1/products/12345.json"
```

### 2. Test Local Environment

```bash
# Run with local environment
python3 -m espscraper.production_main --dry-run
```

### 3. Test GitHub Actions

```bash
# Trigger workflow with test parameters
gh workflow run api-scraper.yml \
  --field batch_size=10 \
  --field product_limit=100 \
  --field mode=scrape
```

## Troubleshooting

### Common Issues

#### 1. API URL Not Working
```bash
# Check if API endpoint is accessible
curl -I "https://api.asicentral.com/v1/products/12345.json"
```

#### 2. Authentication Issues
```bash
# Verify credentials are correct
echo "Username: $ESP_USERNAME"
echo "Password: ${ESP_PASSWORD:0:3}***"
```

#### 3. Missing Secrets
```bash
# Check if all secrets are set
if [ -z "$PRODUCT_API_URL" ]; then
  echo "❌ PRODUCT_API_URL not set"
  exit 1
fi
```

### Debug Mode

Enable debug logging to see API calls:

```bash
python3 -m espscraper.production_main \
  --log-level DEBUG \
  --batch-size 5 \
  --product-limit 10
```

## Security Best Practices

### 1. Never Commit Secrets
```bash
# Add .env to .gitignore
echo ".env" >> .gitignore
```

### 2. Use GitHub Secrets
- Never hardcode credentials in code
- Always use GitHub secrets for production
- Rotate passwords regularly

### 3. Validate URLs
```bash
# Test URLs before using
curl -I "$PRODUCT_API_URL" | head -1
```

## Example Configuration

### Complete Setup

```bash
# GitHub Secrets (set in repository settings)
ESP_USERNAME=your_username
ESP_PASSWORD=your_password
PRODUCTS_URL=https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductResults
SEARCH_API_URL=https://espweb.asicentral.com/WebServices/ProductSearch.asmx/Search
GOTO_PAGE_API_URL=https://espweb.asicentral.com/WebServices/ProductSearch.asmx/GotoPage
PRODUCT_API_URL=https://api.asicentral.com/v1/products/{product_id}.json
PRODUCT_URL_TEMPLATE=https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductDetails&referrerPage=ProductResults&referrerModule=PRDRES&refModSufx=Generic&PCUrl=1&productID={product_id}&autoLaunchVS=0&tab=list
```

### Test Configuration

```bash
# Test with minimal parameters
python3 -m espscraper.production_main \
  --dry-run \
  --batch-size 5 \
  --product-limit 10
```

## Summary

✅ **Your API URL format is perfect**: `https://api.asicentral.com/v1/products/{product_id}.json`  
✅ **Set as GitHub secret**: `PRODUCT_API_URL`  
✅ **Works with template replacement**: `{product_id}` gets replaced  
✅ **Supports both local and GitHub Actions**: Environment variables work everywhere  

The system will automatically replace `{product_id}` with actual product IDs when making API calls! 🚀 