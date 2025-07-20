#!/usr/bin/env python3
"""
Stage 1: Raw Data Collection Pipeline
Fetch raw GitHub data and save to local JSON files
"""

import os
import requests
import json
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import sys

# Add the parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv("config/.env")

GITHUB_API_URL = "https://api.github.com"
ORG_NAME = os.getenv("ORG_NAME", "ruxailab")

def get_github_headers():
    """Create properly formatted headers for GitHub API requests."""
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        print("WARNING: GITHUB_TOKEN not set. API requests will be rate limited.")
        return {"Accept": "application/vnd.github.v3+json"}
    
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

def check_rate_limit():
    """Check GitHub API rate limit status."""
    headers = get_github_headers()
    response = requests.get(f"{GITHUB_API_URL}/rate_limit", headers=headers)
    
    if response.status_code != 200:
        print(f"ERROR checking rate limit: {response.status_code} - {response.text}")
        return
    
    data = response.json()
    core_limit = data.get('resources', {}).get('core', {})
    search_limit = data.get('resources', {}).get('search', {})
    
    print("\nGitHub API Rate Limits:")
    print(f"Core: {core_limit.get('remaining', 'N/A')}/{core_limit.get('limit', 'N/A')} - Reset at: {datetime.fromtimestamp(core_limit.get('reset', 0)).strftime('%H:%M:%S')}")
    print(f"Search: {search_limit.get('remaining', 'N/A')}/{search_limit.get('limit', 'N/A')} - Reset at: {datetime.fromtimestamp(search_limit.get('reset', 0)).strftime('%H:%M:%S')}")
    
    return {
        'core': core_limit,
        'search': search_limit
    }

def wait_for_rate_limit(rate_type='search', min_remaining=5):
    """Check rate limits and wait if necessary."""
    limits = check_rate_limit()
    if not limits:
        print("WARNING: Unable to check rate limits")
        time.sleep(5)
        return True
    
    limit_data = limits.get(rate_type, {})
    remaining = limit_data.get('remaining', 0)
    reset_time = limit_data.get('reset', 0)
    
    if remaining <= min_remaining:
        current_time = datetime.now().timestamp()
        wait_seconds = max(1, reset_time - current_time + 2)
        
        reset_datetime = datetime.fromtimestamp(reset_time)
        print(f"\nRate limit for {rate_type} API almost exhausted ({remaining} remaining).")
        print(f"Waiting until reset at {reset_datetime.strftime('%H:%M:%S')} ({int(wait_seconds)} seconds)...")
        
        if wait_seconds > 60:
            return False
        
        time.sleep(wait_seconds)
        print("Continuing after rate limit reset.")
        return True
    
    return True

def make_github_request(url, headers, request_type='search', retries=3, retry_delay=2):
    """Make a GitHub API request with retry logic and rate limit handling."""
    for attempt in range(retries):
        if not wait_for_rate_limit(request_type):
            print(f"Rate limits exhausted for {request_type} API. Consider running the script later.")
            return None
            
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                time.sleep(0.5)
                return response
            
            if response.status_code == 403 and "rate limit exceeded" in response.text.lower():
                print(f"Rate limit exceeded: {response.text}")
                if not wait_for_rate_limit(request_type):
                    return None
                continue
                
            print(f"ERROR - API response: {response.status_code} - {response.text}")
            
            if attempt == retries - 1:
                return response
                
            wait_time = retry_delay * (2 ** attempt)
            print(f"Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
            
        except Exception as e:
            print(f"Request error: {str(e)}")
            if attempt == retries - 1:
                return None
            
            wait_time = retry_delay * (2 ** attempt)
            print(f"Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
    
    return None

def fetch_org_repositories():
    """Fetch all repositories in the organization."""
    headers = get_github_headers()
    repos = []
    page = 1
    per_page = 100
    
    while True:
        repos_url = f"{GITHUB_API_URL}/orgs/{ORG_NAME}/repos?per_page={per_page}&page={page}"
        response = make_github_request(repos_url, headers, 'core')
        
        if not response or response.status_code != 200:
            print(f"Failed to fetch repositories for page {page}.")
            break
            
        repo_page = response.json()
        if not repo_page:
            break
            
        for repo in repo_page:
            repos.append({
                "name": repo["name"],
                "owner": repo["owner"]["login"]
            })
        
        page += 1
        
        if len(repo_page) < per_page:
            break
    
    print(f"Found {len(repos)} repositories in the {ORG_NAME} organization.")
    return repos

def collect_raw_repo_data(repo_owner, repo_name, headers):
    """Collect all raw data for a single repository."""
    print(f"Collecting raw data for {repo_owner}/{repo_name}")
    
    repo_data = {
        'name': repo_name,
        'owner': repo_owner,
        'contributors': [],
        'pull_requests': [],
        'issues': [],
        'commits_search': [],
        'repo_info': {}
    }
    
    # Get repository info
    repo_url = f"{GITHUB_API_URL}/repos/{repo_owner}/{repo_name}"
    response = make_github_request(repo_url, headers, 'core')
    if response and response.status_code == 200:
        repo_data['repo_info'] = response.json()
    
    # Get contributors
    contributors_url = f"{GITHUB_API_URL}/repos/{repo_owner}/{repo_name}/contributors"
    response = make_github_request(contributors_url, headers, 'core')
    if response and response.status_code == 200:
        repo_data['contributors'] = response.json()
    
    # Get pull requests
    pr_url = f"{GITHUB_API_URL}/search/issues?q=repo:{repo_owner}/{repo_name}+type:pr+is:merged"
    response = make_github_request(pr_url, headers, 'search')
    if response and response.status_code == 200:
        repo_data['pull_requests'] = response.json()
    
    # Get issues
    issue_url = f"{GITHUB_API_URL}/search/issues?q=repo:{repo_owner}/{repo_name}+type:issue"
    response = make_github_request(issue_url, headers, 'search')
    if response and response.status_code == 200:
        repo_data['issues'] = response.json()
    
    # Get commits (search API)
    commits_url = f"{GITHUB_API_URL}/search/commits?q=repo:{repo_owner}/{repo_name}"
    response = make_github_request(commits_url, headers, 'search')
    if response and response.status_code == 200:
        repo_data['commits_search'] = response.json()
    
    return repo_data

def main():
    """Main raw data collection pipeline"""
    print("========== Stage 1: Raw Data Collection Pipeline ==========")
    
    # Check GitHub token
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("ERROR: GITHUB_TOKEN environment variable is not set or empty")
        print("Please set the GITHUB_TOKEN environment variable with a valid GitHub token")
        exit(1)
    
    masked_token = github_token[:4] + "..." + github_token[-4:] if len(github_token) > 8 else "***"
    print(f"Using GitHub token: {masked_token}")
    
    # Check API rate limits
    rate_limits = check_rate_limit()
    if not rate_limits or rate_limits.get('search', {}).get('remaining', 0) < 5:
        print("WARNING: Low search API rate limits. Some requests may fail.")
    
    # Get all repositories
    headers = get_github_headers()
    org_repos = fetch_org_repositories()
    
    # Collect raw data for each repository
    all_raw_data = {
        'repositories': {},
        'organization': ORG_NAME,
        'collection_timestamp': datetime.now().isoformat(),
        'total_repos': len(org_repos)
    }
    
    try:
        for i, repo in enumerate(org_repos):
            print(f"\n========== Processing repository {i+1}/{len(org_repos)}: {repo['owner']}/{repo['name']} ==========")
            
            repo_data = collect_raw_repo_data(repo['owner'], repo['name'], headers)
            all_raw_data['repositories'][repo['name']] = repo_data
            
            # Save progress after each repo
            with open("raw_github_data.json", "w") as f:
                json.dump(all_raw_data, f, indent=2)
            
            print(f"Raw data collected for {repo['name']}")
            
    except KeyboardInterrupt:
        print("\nOperation interrupted by user. Saving progress...")
    finally:
        # Final save
        with open("raw_github_data.json", "w") as f:
            json.dump(all_raw_data, f, indent=2)
        
        print(f"\nRaw data collection completed for {len(all_raw_data['repositories'])} repositories")
        print("Raw data saved to raw_github_data.json")
        print("Stage 1: Raw Data Collection - COMPLETED")

if __name__ == "__main__":
    main() 