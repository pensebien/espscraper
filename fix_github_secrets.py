#!/usr/bin/env python3
"""
Fix GitHub Secrets with correct API keys
"""
import subprocess
import sys

def fix_github_secrets():
    """Fix the GitHub secrets with correct API keys"""
    print("🔧 Fixing GitHub Secrets")
    print("=" * 40)
    
    # Correct API keys from wp-config.php
    PROMOSTANDARDS_API_KEY = "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"
    GITHUB_PARAMS_SECRET = "QwErTy1234567890zxcvbnmASDFGHJKLqwertyuiop"
    
    print("Current configuration from wp-config.php:")
    print(f"PROMOSTANDARDS_API_KEY: {PROMOSTANDARDS_API_KEY}")
    print(f"GITHUB_PARAMS_SECRET: {GITHUB_PARAMS_SECRET}")
    print()
    
    print("❌ ISSUE: The workflow is using the wrong API key!")
    print("   - Workflow uses: GITHUB_PARAMS_SECRET for API calls")
    print("   - Should use: PROMOSTANDARDS_API_KEY for API calls")
    print("   - GITHUB_PARAMS_SECRET is only for GitHub handshake")
    print()
    
    print("🔧 SOLUTION: Update GitHub secrets")
    print()
    
    # Check if gh CLI is available
    try:
        result = subprocess.run(['gh', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ GitHub CLI is available")
            
            # Set the correct secrets
            print("\n📝 Setting correct GitHub secrets...")
            
            # Set WP_API_KEY to PROMOSTANDARDS_API_KEY
            print(f"Setting WP_API_KEY to: {PROMOSTANDARDS_API_KEY}")
            subprocess.run(['gh', 'secret', 'set', 'WP_API_KEY', '--body', PROMOSTANDARDS_API_KEY])
            
            # Set WP_API_SECRET to GITHUB_PARAMS_SECRET
            print(f"Setting WP_API_SECRET to: {GITHUB_PARAMS_SECRET}")
            subprocess.run(['gh', 'secret', 'set', 'WP_API_SECRET', '--body', GITHUB_PARAMS_SECRET])
            
            print("\n✅ GitHub secrets updated!")
            print("\n📋 Summary:")
            print("   WP_API_KEY = PROMOSTANDARDS_API_KEY (for API calls)")
            print("   WP_API_SECRET = GITHUB_PARAMS_SECRET (for GitHub handshake)")
            
        else:
            print("❌ GitHub CLI not working properly")
            manual_setup()
    except FileNotFoundError:
        print("❌ GitHub CLI not found")
        manual_setup()

def manual_setup():
    """Provide manual setup instructions"""
    print("\n📋 MANUAL SETUP REQUIRED:")
    print("=" * 40)
    print("1. Go to your GitHub repository")
    print("2. Click 'Settings' → 'Secrets and variables' → 'Actions'")
    print("3. Update these secrets:")
    print()
    print("   WP_API_KEY = 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")
    print("   WP_API_SECRET = QwErTy1234567890zxcvbnmASDFGHJKLqwertyuiop")
    print()
    print("4. Save the secrets")
    print("5. Re-run the workflow")

def test_api_keys():
    """Test the API keys to verify they work"""
    print("\n🧪 Testing API Keys")
    print("=" * 40)
    
    import requests
    
    # Test URLs
    localwp_url = "https://unwritten-bottle.localsite.io/wp-json/promostandards-importer/v1"
    staging_url = "https://tmgdev.dedicatedmkt.com/wp-json/promostandards-importer/v1"
    
    # API keys
    correct_api_key = "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"
    wrong_api_key = "QwErTy1234567890zxcvbnmASDFGHJKLqwertyuiop"
    
    print("Testing LocalWP with correct API key...")
    try:
        response = requests.get(
            f"{localwp_url}/existing-products",
            headers={"X-API-Key": correct_api_key},
            timeout=10
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ LocalWP works with correct API key!")
        else:
            print(f"❌ LocalWP failed: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\nTesting LocalWP with wrong API key...")
    try:
        response = requests.get(
            f"{localwp_url}/existing-products",
            headers={"X-API-Key": wrong_api_key},
            timeout=10
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 404:
            print("✅ Confirmed: Wrong API key gives 404 (as expected)")
        else:
            print(f"❌ Unexpected: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    fix_github_secrets()
    test_api_keys()
