#!/bin/bash

# GitHub Secrets Setup Script for ESP Scraper
# Replace the placeholder values with your actual credentials

echo "Setting up GitHub secrets for ESP Scraper..."

# Authentication secrets
gh secret set ESP_USERNAME --body "your_esp_username"
gh secret set ESP_PASSWORD --body "your_esp_password"

# URL secrets
gh secret set PRODUCTS_URL --body "https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductResults"
gh secret set SEARCH_API_URL --body "https://espweb.asicentral.com/WebServices/ProductSearch.asmx/Search"
gh secret set GOTO_PAGE_API_URL --body "https://espweb.asicentral.com/WebServices/ProductSearch.asmx/GotoPage"

# API Configuration secrets
gh secret set PRODUCT_API_URL --body "https://api.asicentral.com/v1/products/{product_id}.json"
gh secret set PRODUCT_URL_TEMPLATE --body "https://espweb.asicentral.com/Default.aspx?appCode=WESP&appVersion=4.1.0&page=ProductDetails&referrerPage=ProductResults&referrerModule=PRDRES&refModSufx=Generic&PCUrl=1&productID={product_id}&autoLaunchVS=0&tab=list"

echo "✅ All GitHub secrets have been set!"
echo "⚠️  Remember to replace 'your_esp_username' and 'your_esp_password' with your actual credentials"


gh secret set WP_API_SECRET --body "QwErTy1234567890zxcvbnmASDFGHJKLqwertyuiop"

# WordPress Basic Auth credentials (for LocalWP)
gh secret set WP_BASIC_AUTH_USER --body "nonfiction"
gh secret set WP_BASIC_AUTH_PASS --body "cautious"