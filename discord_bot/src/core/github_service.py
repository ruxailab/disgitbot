"""
GitHub Service

Handles all GitHub API interactions following Single Responsibility Principle.
"""

import requests
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

from .config import get_config
from .interfaces import IGitHubService

class GitHubService(IGitHubService):
    """Service for GitHub API operations with rate limiting and error handling."""
    
    def __init__(self):
        self._config = get_config()
        self._github_config = self._config.get_github_config()
    
    def _get_headers(self) -> Dict[str, str]:
        """Create properly formatted headers for GitHub API requests."""
        if not self._github_config.token:
            return {"Accept": "application/vnd.github.v3+json"}
        
        return {
            "Authorization": f"token {self._github_config.token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def _check_rate_limit(self) -> Optional[Dict[str, Any]]:
        """Check GitHub API rate limit status."""
        headers = self._get_headers()
        response = requests.get(f"{self._github_config.api_url}/rate_limit", headers=headers)
        
        if response.status_code != 200:
            print(f"ERROR checking rate limit: {response.status_code} - {response.text}")
            return None
        
        data = response.json()
        core_limit = data.get('resources', {}).get('core', {})
        search_limit = data.get('resources', {}).get('search', {})
        
        print(f"GitHub API Rate Limits:")
        print(f"Core: {core_limit.get('remaining', 'N/A')}/{core_limit.get('limit', 'N/A')} - Reset at: {datetime.fromtimestamp(core_limit.get('reset', 0)).strftime('%H:%M:%S')}")
        print(f"Search: {search_limit.get('remaining', 'N/A')}/{search_limit.get('limit', 'N/A')} - Reset at: {datetime.fromtimestamp(search_limit.get('reset', 0)).strftime('%H:%M:%S')}")
        
        return {
            'core': core_limit,
            'search': search_limit
        }
    
    def _wait_for_rate_limit(self, rate_type: str = 'search', min_remaining: int = 5) -> bool:
        """Check rate limits and wait if necessary."""
        limits = self._check_rate_limit()
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
    
    def _make_request(self, url: str, request_type: str = 'search', retries: int = 3, retry_delay: int = 2) -> Optional[requests.Response]:
        """Make a GitHub API request with retry logic and rate limit handling."""
        headers = self._get_headers()
        
        for attempt in range(retries):
            if not self._wait_for_rate_limit(request_type):
                print(f"Rate limits exhausted for {request_type} API. Consider running the script later.")
                return None
                
            try:
                response = requests.get(url, headers=headers)
                
                if response.status_code == 200:
                    time.sleep(0.5)
                    return response
                
                if response.status_code == 403 and "rate limit exceeded" in response.text.lower():
                    print(f"Rate limit exceeded: {response.text}")
                    if not self._wait_for_rate_limit(request_type):
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
    
    def fetch_repository_data(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetch repository data from GitHub API."""
        repo_url = f"{self._github_config.api_url}/repos/{owner}/{repo}"
        response = self._make_request(repo_url, 'core')
        
        if response and response.status_code == 200:
            return response.json()
        
        return {}
    
    def fetch_contributors(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Fetch contributors for a repository."""
        contributors_url = f"{self._github_config.api_url}/repos/{owner}/{repo}/contributors"
        response = self._make_request(contributors_url, 'core')
        
        if response and response.status_code == 200:
            return response.json()
        
        return []
    
    def fetch_organization_repositories(self) -> List[Dict[str, Any]]:
        """Fetch all repositories in the organization."""
        repos = []
        page = 1
        per_page = 100
        
        while True:
            repos_url = f"{self._github_config.api_url}/orgs/{self._github_config.repo_owner}/repos?per_page={per_page}&page={page}"
            response = self._make_request(repos_url, 'core')
            
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
        
        print(f"Found {len(repos)} repositories in the {self._github_config.repo_owner} organization.")
        return repos
    
    def search_pull_requests(self, owner: str, repo: str) -> Dict[str, Any]:
        """Search for pull requests in a repository."""
        pr_url = f"{self._github_config.api_url}/search/issues?q=repo:{owner}/{repo}+type:pr+is:merged"
        response = self._make_request(pr_url, 'search')
        
        if response and response.status_code == 200:
            return response.json()
        
        return {'items': []}
    
    def search_issues(self, owner: str, repo: str) -> Dict[str, Any]:
        """Search for issues in a repository."""
        issue_url = f"{self._github_config.api_url}/search/issues?q=repo:{owner}/{repo}+type:issue"
        response = self._make_request(issue_url, 'search')
        
        if response and response.status_code == 200:
            return response.json()
        
        return {'items': []}
    
    def search_commits(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get commits for a repository using the commits API."""
        commits_url = f"{self._github_config.api_url}/repos/{owner}/{repo}/commits?per_page=100"
        response = self._make_request(commits_url, 'core')
        
        if response and response.status_code == 200:
            commits = response.json()
            return {
                'items': commits,
                'total_count': len(commits)
            }
        
        return {'items': [], 'total_count': 0}
    
    def collect_complete_repository_data(self, owner: str, repo: str) -> Dict[str, Any]:
        """Collect all data for a single repository."""
        print(f"Collecting complete data for {owner}/{repo}")
        
        return {
            'name': repo,
            'owner': owner,
            'repo_info': self.fetch_repository_data(owner, repo),
            'contributors': self.fetch_contributors(owner, repo),
            'pull_requests': self.search_pull_requests(owner, repo),
            'issues': self.search_issues(owner, repo),
            'commits_search': self.search_commits(owner, repo)
        }
    
    def collect_organization_data(self) -> Dict[str, Any]:
        """Collect complete data for all repositories in the organization."""
        print("========== Collecting Organization Data ==========")
        
        # Validate GitHub token
        if not self._github_config.token:
            raise ValueError("GitHub token is required for API access")
        
        masked_token = self._github_config.token[:4] + "..." + self._github_config.token[-4:] if len(self._github_config.token) > 8 else "***"
        print(f"Using GitHub token: {masked_token}")
        
        # Check rate limits
        rate_limits = self._check_rate_limit()
        if not rate_limits or rate_limits.get('search', {}).get('remaining', 0) < 5:
            print("WARNING: Low search API rate limits. Some requests may fail.")
        
        # Fetch all repositories
        repos = self.fetch_organization_repositories()
        
        # Collect data for each repository
        all_data = {
            'repositories': {},
            'organization': self._github_config.repo_owner,
            'collection_timestamp': datetime.now().isoformat(),
            'total_repos': len(repos)
        }
        
        for i, repo in enumerate(repos):
            print(f"\n========== Processing repository {i+1}/{len(repos)}: {repo['owner']}/{repo['name']} ==========")
            
            repo_data = self.collect_complete_repository_data(repo['owner'], repo['name'])
            all_data['repositories'][repo['name']] = repo_data
            
            print(f"Data collected for {repo['name']}")
        
        return all_data 