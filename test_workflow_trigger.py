#!/usr/bin/env python3
"""
Trigger the GitHub workflow for testing
"""
import requests
import json
import os

def trigger_workflow():
    """Trigger the wordpress-import workflow"""
    print("🚀 Triggering GitHub Workflow")
    print("=" * 40)
    
    # GitHub API configuration
    repo = "your-username/espscraper-project-vscode"  # Replace with your actual repo
    workflow_id = "wordpress-import.yml"
    
    # Get GitHub token from environment or input
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        token = input("Enter your GitHub token: ").strip()
    
    if not token:
        print("❌ No GitHub token provided")
        return
    
    # Workflow inputs
    inputs = {
        "environment": "staging",
        "mode": "sync",
        "product_limit": "5",
        "use_enhanced_files": "true"
    }
    
    # API endpoint
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_id}/dispatches"
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    
    data = {
        "ref": "main",
        "inputs": inputs
    }
    
    print(f"Repository: {repo}")
    print(f"Workflow: {workflow_id}")
    print(f"Inputs: {inputs}")
    
    try:
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 204:
            print("✅ Workflow triggered successfully!")
            print("🔗 Check the workflow run at:")
            print(f"   https://github.com/{repo}/actions")
        else:
            print(f"❌ Failed to trigger workflow: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    trigger_workflow()
