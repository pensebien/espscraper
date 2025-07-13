# GitHub Actions Workflow Guide

## Overview

The ESP Scraper uses GitHub Actions with `workflow_dispatch` to allow manual triggering with custom parameters. This guide explains how the input system works and how to use it effectively.

## Workflow Dispatch Inputs

### Available Input Parameters

The `api-scraper.yml` workflow accepts the following inputs:

```yaml
on:
  workflow_dispatch:
    inputs:
      batch_size:
        description: 'Batch size for processing'
        required: false
        default: '50'
      product_limit:
        description: 'Product limit'
        required: false
        default: '4000'
      mode:
        description: 'Scraping mode (scrape, new, missing)'
        required: false
        default: 'scrape'
      force_link_collection:
        description: 'Force link collection'
        required: false
        default: 'false'
      max_link_age:
        description: 'Maximum link age in hours'
        required: false
        default: '48'
```

### Input Parameter Details

#### 1. `batch_size`
- **Type**: Integer
- **Default**: 50
- **Range**: 10-200 recommended
- **Description**: Number of products to process in each batch
- **Usage**: Controls memory usage and processing speed

#### 2. `product_limit`
- **Type**: Integer
- **Default**: 4000
- **Range**: 1-10000+
- **Description**: Maximum number of products to scrape
- **Usage**: Limits total processing scope

#### 3. `mode`
- **Type**: String (enum)
- **Default**: 'scrape'
- **Options**: 'scrape', 'new', 'missing'
- **Description**: Processing mode for products
- **Usage**: Controls which products to process

#### 4. `force_link_collection`
- **Type**: Boolean
- **Default**: 'false'
- **Options**: 'true', 'false'
- **Description**: Force fresh link collection
- **Usage**: Override existing link files

#### 5. `max_link_age`
- **Type**: Integer
- **Default**: 48
- **Range**: 1-168 (hours)
- **Description**: Maximum age of link files before refresh
- **Usage**: Controls when to refresh links

## How to Trigger the Workflow

### Method 1: GitHub Web Interface

1. **Navigate to Actions**:
   - Go to your GitHub repository
   - Click on "Actions" tab
   - Select "API Scraper (Batch Processing)" workflow

2. **Manual Trigger**:
   - Click "Run workflow" button
   - Select branch (usually `main`)
   - Fill in desired parameters
   - Click "Run workflow"

### Method 2: GitHub CLI

```bash
# Install GitHub CLI
gh auth login

# Trigger workflow with custom parameters
gh workflow run api-scraper.yml \
  --field batch_size=50 \
  --field product_limit=4000 \
  --field mode=scrape \
  --field force_link_collection=false \
  --field max_link_age=48
```

### Method 3: REST API

```bash
# Trigger via REST API
curl -X POST \
  -H "Authorization: token YOUR_GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/OWNER/REPO/actions/workflows/api-scraper.yml/dispatches \
  -d '{
    "ref": "main",
    "inputs": {
      "batch_size": "50",
      "product_limit": "4000",
      "mode": "scrape",
      "force_link_collection": "false",
      "max_link_age": "48"
    }
  }'
```

## Input Processing in Workflow

### How Inputs Are Used

The workflow processes inputs in the "Run API scraper" step:

```yaml
- name: 🚀 Run API scraper with batch processing
  run: |
    # Set batch size from input or default
    BATCH_SIZE=${BATCH_SIZE:-${{ github.event.inputs.batch_size || '50' }}
    PRODUCT_LIMIT=${PRODUCT_LIMIT:-${{ github.event.inputs.product_limit || '4000' }}
    MODE=${MODE:-${{ github.event.inputs.mode || 'scrape' }}
    FORCE_LINK_COLLECTION=${FORCE_LINK_COLLECTION:-${{ github.event.inputs.force_link_collection || 'false' }}
    MAX_LINK_AGE=${MAX_LINK_AGE:-${{ github.event.inputs.max_link_age || '48' }}

    # Run the scraper
    python3 -m espscraper.production_main \
      --batch-size $BATCH_SIZE \
      --product-limit $PRODUCT_LIMIT \
      --mode $MODE \
      --force-link-collection $FORCE_LINK_COLLECTION \
      --max-link-age $MAX_LINK_AGE
```

### Input Validation

The workflow includes input validation:

```bash
echo "Configuration:"
echo "  Batch Size: $BATCH_SIZE"
echo "  Product Limit: $PRODUCT_LIMIT"
echo "  Mode: $MODE"
echo "  Force Link Collection: $FORCE_LINK_COLLECTION"
echo "  Max Link Age: $MAX_LINK_AGE hours"
```

## Common Use Cases

### 1. Initial Full Scrape (4000 products)

```yaml
batch_size: 50
product_limit: 4000
mode: scrape
force_link_collection: true
max_link_age: 48
```

### 2. Incremental Update (1000 products)

```yaml
batch_size: 25
product_limit: 1000
mode: new
force_link_collection: false
max_link_age: 24
```

### 3. Resume Failed Run

```yaml
batch_size: 50
product_limit: 4000
mode: missing
force_link_collection: false
max_link_age: 48
```

### 4. Test Run (100 products)

```yaml
batch_size: 10
product_limit: 100
mode: scrape
force_link_collection: true
max_link_age: 1
```

## Environment Variables

### Required Secrets

The workflow requires these secrets to be configured in GitHub:

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

### Setting Up Secrets

1. **Go to Repository Settings**:
   - Navigate to your GitHub repository
   - Click "Settings" tab
   - Click "Secrets and variables" → "Actions"

2. **Add Required Secrets**:
   - `ESP_USERNAME`: Your ESP login username
   - `ESP_PASSWORD`: Your ESP login password
   - `PRODUCTS_URL`: ESP products page URL
   - `SEARCH_API_URL`: ESP search API endpoint
   - `GOTO_PAGE_API_URL`: ESP pagination API endpoint
   - `PRODUCT_API_URL`: ESP product detail API endpoint
   - `PRODUCT_URL_TEMPLATE`: ESP product URL template

## Workflow Execution Flow

### 1. Input Processing
```yaml
# Inputs are processed and validated
BATCH_SIZE=${BATCH_SIZE:-${{ github.event.inputs.batch_size || '50' }}
```

### 2. Environment Setup
```yaml
# Python, Chrome, and dependencies are installed
- name: 🐍 Set up Python
- name: 🔧 Install system dependencies
```

### 3. Data Fetching
```yaml
# Existing files are fetched from artifacts branch
- name: 📥 Fetch latest files from artifacts branch
```

### 4. Scraper Execution
```yaml
# Main scraper runs with provided parameters
- name: 🚀 Run API scraper with batch processing
```

### 5. Validation and Statistics
```yaml
# Results are validated and statistics generated
- name: 📊 Generate batch statistics
- name: 🔧 Validate batch files
```

### 6. Artifact Storage
```yaml
# Files are saved to artifacts branch
- name: 📝 Copy files to artifacts branch
- name: 🚀 Commit and push to artifacts branch
```

## Monitoring and Debugging

### Viewing Workflow Runs

1. **GitHub Actions Tab**:
   - Go to "Actions" tab in repository
   - Click on "API Scraper (Batch Processing)"
   - View run history and logs

2. **Real-time Logs**:
   - Click on any workflow run
   - View step-by-step execution logs
   - Monitor progress in real-time

### Common Issues

#### Input Validation Errors
```bash
# Check if inputs are being passed correctly
echo "Input values:"
echo "  Batch Size: ${{ github.event.inputs.batch_size }}"
echo "  Product Limit: ${{ github.event.inputs.product_limit }}"
```

#### Missing Secrets
```bash
# Verify secrets are configured
if [ -z "$ESP_USERNAME" ]; then
  echo "❌ ESP_USERNAME secret not configured"
  exit 1
fi
```

#### Artifacts Branch Issues
```bash
# Check if artifacts branch exists
if git ls-remote --heads origin artifacts | grep -q artifacts; then
  echo "✅ Artifacts branch exists"
else
  echo "⚠️ Artifacts branch does not exist"
fi
```

## Best Practices

### 1. Input Validation
- Always provide reasonable defaults
- Validate input ranges where possible
- Log input values for debugging

### 2. Error Handling
- Use proper exit codes
- Provide meaningful error messages
- Include fallback values

### 3. Security
- Never log sensitive information
- Use secrets for credentials
- Validate input sanitization

### 4. Performance
- Use appropriate batch sizes
- Monitor resource usage
- Set reasonable timeouts

## Example Workflow Calls

### Via GitHub CLI
```bash
# Full scrape with 4000 products
gh workflow run api-scraper.yml \
  --field batch_size=50 \
  --field product_limit=4000 \
  --field mode=scrape \
  --field force_link_collection=true

# Test run with 100 products
gh workflow run api-scraper.yml \
  --field batch_size=10 \
  --field product_limit=100 \
  --field mode=scrape \
  --field force_link_collection=true
```

### Via Web Interface
1. Go to Actions → API Scraper
2. Click "Run workflow"
3. Fill in parameters:
   - Batch size: 50
   - Product limit: 4000
   - Mode: scrape
   - Force link collection: true
   - Max link age: 48
4. Click "Run workflow"

## Summary

The GitHub Actions workflow provides:

✅ **Flexible Input System**: Customizable parameters for different scenarios
✅ **Manual Triggering**: Run when needed with custom settings
✅ **Input Validation**: Proper defaults and error handling
✅ **Security**: Secrets management for credentials
✅ **Monitoring**: Real-time logs and progress tracking
✅ **Artifact Management**: Automatic file storage and sharing

The workflow can be triggered manually with custom parameters to handle different scraping scenarios efficiently! 🚀
