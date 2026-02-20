"""
GitHub Service

Handles all GitHub API interactions following Single Responsibility Principle.
"""

import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import os

class GitHubService:
    """GitHub API service for data collection."""
    
    def __init__(self, repo_owner: str = None, token: Optional[str] = None, installation_id: Optional[int] = None):
        self.api_url = "https://api.github.com"
        self.token = token or os.getenv('GITHUB_TOKEN')
        self.repo_owner = repo_owner or os.getenv('REPO_OWNER', 'ruxailab')
        self.installation_id = installation_id
        
        self._request_count = 0
    
    def _get_headers(self) -> Dict[str, str]:
        """Get GitHub API headers with authentication."""
        if not self.token:
            raise ValueError("GitHub token is required for API access")
        return {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def _check_rate_limit(self) -> Optional[Dict[str, Any]]:
        """Check GitHub API rate limit status with detailed logging."""
        response = requests.get(f"{self.api_url}/rate_limit", headers=self._get_headers())
        
        if response.status_code != 200:
            print(f"DEBUG - Rate limit check failed: {response.status_code} - {response.text}")
            return None
        
        data = response.json()
        resources = data.get('resources', {})
        core_limit = resources.get('core', {})
        search_limit = resources.get('search', {})
        
        core_remaining = core_limit.get('remaining', 0)
        core_total = core_limit.get('limit', 0)
        core_reset = core_limit.get('reset', 0)
        
        search_remaining = search_limit.get('remaining', 0)
        search_total = search_limit.get('limit', 0)
        search_reset = search_limit.get('reset', 0)
        
        core_reset_time = datetime.fromtimestamp(core_reset).strftime('%H:%M:%S')
        search_reset_time = datetime.fromtimestamp(search_reset).strftime('%H:%M:%S')
        
        print(f"GitHub API Rate Limits:")
        print(f"Core: {core_remaining}/{core_total} - Reset at: {core_reset_time}")
        print(f"Search: {search_remaining}/{search_total} - Reset at: {search_reset_time}")
        
        return {
            'core': core_limit,
            'search': search_limit
        }
    
    def _wait_for_rate_limit(self, rate_type: str = 'search', min_remaining: int = 5) -> bool:
        """Wait for rate limit reset if necessary."""
        limits = self._check_rate_limit()
        if not limits:
            print("DEBUG - Unable to check rate limits, proceeding with caution")
            time.sleep(2)
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
                print("WARNING: Long wait time required for rate limits")
                return False
            
            time.sleep(wait_seconds)
            print("Continuing after rate limit reset.")
            return True
        
        return True
    
    def _make_request(self, url: str, rate_type: str = 'search', retries: int = 3) -> Optional[requests.Response]:
        """Make GitHub API request with comprehensive error handling and rate limiting."""
        self._request_count += 1
        
        print(f"DEBUG - API Request #{self._request_count}: {url}")
        
        for attempt in range(retries):
            if not self._wait_for_rate_limit(rate_type):
                print(f"DEBUG - Rate limits exhausted for {rate_type} API")
                return None
            
            try:
                response = requests.get(url, headers=self._get_headers())
                
                print(f"DEBUG - Response: {response.status_code} - Content-Length: {len(response.content)} bytes")
                
                if response.status_code == 200:
                    time.sleep(0.5)  # Rate limiting courtesy delay
                    return response
                
                if response.status_code == 403 and "rate limit exceeded" in response.text.lower():
                    print(f"DEBUG - Rate limit exceeded, waiting for reset")
                    if not self._wait_for_rate_limit(rate_type):
                        return None
                    continue
                
                print(f"DEBUG - API Error: {response.status_code} - {response.text[:200]}")
                
                if attempt == retries - 1:
                    return response
                    
                wait_time = 2 ** attempt
                print(f"DEBUG - Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                
            except Exception as e:
                print(f"DEBUG - Request exception: {str(e)}")
                if attempt == retries - 1:
                    return None
                
                wait_time = 2 ** attempt
                print(f"DEBUG - Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        
        return None
    
    def _paginate_search_results(self, base_url: str, rate_type: str = 'search') -> Dict[str, Any]:
        """Paginate through all search results to get complete data."""
        all_items = []
        total_count = 0
        page = 1
        per_page = 100
        
        print(f"DEBUG - Starting pagination for: {base_url}")
        
        while True:
            paginated_url = f"{base_url}&per_page={per_page}&page={page}"
            response = self._make_request(paginated_url, rate_type)
            
            if not response or response.status_code != 200:
                print(f"DEBUG - Pagination failed at page {page}")
                break
            
            data = response.json()
            items = data.get('items', [])
            
            if not items:
                print(f"DEBUG - No more items at page {page}")
                break
            
            all_items.extend(items)
            
            # For search API, we can get total_count from first response
            if page == 1:
                total_count = data.get('total_count', len(items))
                print(f"DEBUG - Total items expected: {total_count}")
            
            print(f"DEBUG - Page {page}: Got {len(items)} items (Total so far: {len(all_items)})")
            
            # GitHub search API has max 1000 results per query
            if len(items) < per_page or len(all_items) >= 1000:
                print(f"DEBUG - Pagination complete: {len(all_items)} items collected")
                break
            
            page += 1
        
        return {
            'items': all_items,
            'total_count': max(total_count, len(all_items))
        }
    
    def _paginate_list_results(self, base_url: str, rate_type: str = 'core') -> List[Dict[str, Any]]:
        """Paginate through all list results (non-search API)."""
        all_items = []
        page = 1
        per_page = 100
        
        print(f"DEBUG - Starting list pagination for: {base_url}")
        
        while True:
            joiner = "&" if "?" in base_url else "?"
            paginated_url = f"{base_url}{joiner}per_page={per_page}&page={page}"
            response = self._make_request(paginated_url, rate_type)
            
            if not response or response.status_code != 200:
                print(f"DEBUG - List pagination failed at page {page}")
                break
            
            items = response.json()
            
            if not items:
                print(f"DEBUG - No more items at page {page}")
                break
            
            all_items.extend(items)
            print(f"DEBUG - Page {page}: Got {len(items)} items (Total so far: {len(all_items)})")
            
            if len(items) < per_page:
                print(f"DEBUG - List pagination complete: {len(all_items)} items collected")
                break
            
            page += 1
        
        return all_items
    
    def fetch_repository_data(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetch basic repository information."""
        repo_url = f"{self.api_url}/repos/{owner}/{repo}"
        response = self._make_request(repo_url, 'core')
        
        if response and response.status_code == 200:
            return response.json()
        
        return {}
    
    def fetch_contributors(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Fetch ALL contributors for a repository."""
        contributors_url = f"{self.api_url}/repos/{owner}/{repo}/contributors"
        return self._paginate_list_results(contributors_url, 'core')
    
    def fetch_repository_labels(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Fetch all labels for a repository."""
        labels_url = f"{self.api_url}/repos/{owner}/{repo}/labels"
        return self._paginate_list_results(labels_url, 'core')

    def fetch_installation_repositories(self) -> List[Dict[str, str]]:
        """Fetch repositories available to the current installation token."""
        if not self.installation_id:
            return []

        try:
            repos_url = f"{self.api_url}/installation/repositories"
            all_repos: List[Dict[str, str]] = []
            page = 1
            per_page = 100

            while True:
                url = f"{repos_url}?per_page={per_page}&page={page}"
                response = self._make_request(url, 'core')

                if not response or response.status_code != 200:
                    print(f"Failed to fetch installation repositories at page {page}")
                    break

                data = response.json() or {}
                repos_data = data.get('repositories', []) or []
                if not repos_data:
                    break

                for repo in repos_data:
                    owner = (repo.get('owner') or {}).get('login')
                    name = repo.get('name')
                    if owner and name:
                        all_repos.append({'name': name, 'owner': owner})

                total = data.get('total_count', len(all_repos))
                if len(repos_data) < per_page or len(all_repos) >= total:
                    break

                page += 1

            print(f"Found {len(all_repos)} repositories for installation")
            return all_repos
        except Exception as e:
            print(f"Error fetching installation repositories: {e}")
            return []

    def fetch_organization_repositories(self) -> List[Dict[str, str]]:
        """Fetch all repositories for the organization."""
        try:
            org_url = f"{self.api_url}/orgs/{self.repo_owner}/repos"
            response = self._make_request(org_url, 'core')
            
            if response and response.status_code == 200:
                repos_data = response.json()
                repos = [{'name': repo['name'], 'owner': repo['owner']['login']} for repo in repos_data]
                print(f"Found {len(repos)} repositories in {self.repo_owner}")
                return repos
            
            print(f"Failed to fetch repositories for {self.repo_owner}")
            return []
            
        except Exception as e:
            print(f"Error fetching repositories: {e}")
            return []

    def fetch_accessible_repositories(self) -> List[Dict[str, str]]:
        """Fetch repositories accessible by this token (installation or org token)."""
        if self.installation_id:
            repos = self.fetch_installation_repositories()
            if repos:
                return repos
        return self.fetch_organization_repositories()
    
    def search_pull_requests(self, owner: str, repo: str) -> Dict[str, Any]:
        """Search for ALL pull requests in a repository with complete pagination."""
        pr_url = f"{self.api_url}/search/issues?q=repo:{owner}/{repo}+type:pr+is:merged"
        print(f"DEBUG - Collecting ALL PRs for {owner}/{repo}")
        
        results = self._paginate_search_results(pr_url, 'search')
        print(f"DEBUG - Collected {len(results['items'])} PRs for {owner}/{repo}")
        
        return results
    
    def search_issues(self, owner: str, repo: str) -> Dict[str, Any]:
        """Search for ALL issues in a repository with complete pagination."""
        issue_url = f"{self.api_url}/search/issues?q=repo:{owner}/{repo}+type:issue"
        print(f"DEBUG - Collecting ALL issues for {owner}/{repo}")
        
        results = self._paginate_search_results(issue_url, 'search')
        print(f"DEBUG - Collected {len(results['items'])} issues for {owner}/{repo}")
        
        return results
    
    def search_commits(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get ALL commits for a repository using complete pagination."""
        commits_url = f"{self.api_url}/repos/{owner}/{repo}/commits"
        print(f"DEBUG - Collecting ALL commits for {owner}/{repo}")
        
        commits_list = self._paginate_list_results(commits_url, 'core')
        
        print(f"DEBUG - Collected {len(commits_list)} commits for {owner}/{repo}")
        
        return {
            'items': commits_list,
            'total_count': len(commits_list)
        }
    
    def collect_complete_repository_data(self, owner: str, repo: str) -> Dict[str, Any]:
        """Collect ALL data for a single repository."""
        print(f"DEBUG - Starting complete data collection for {owner}/{repo}")
        
        repo_data = {
            'name': repo,
            'owner': owner,
            'repo_info': self.fetch_repository_data(owner, repo),
            'contributors': self.fetch_contributors(owner, repo),
            'pull_requests': self.search_pull_requests(owner, repo),
            'issues': self.search_issues(owner, repo),
            'commits_search': self.search_commits(owner, repo),
            'labels': self.fetch_repository_labels(owner, repo)
        }
        
        # Log summary of collected data
        print(f"DEBUG - Data collection summary for {owner}/{repo}:")
        print(f"  - Contributors: {len(repo_data['contributors'])}")
        print(f"  - Pull Requests: {repo_data['pull_requests']['total_count']}")
        print(f"  - Issues: {repo_data['issues']['total_count']}")
        print(f"  - Commits: {repo_data['commits_search']['total_count']}")
        print(f"  - Labels: {len(repo_data['labels'])}")
        
        return repo_data

    def collect_organization_data(self) -> Dict[str, Any]:
        """Collect complete data for all repositories accessible by this token."""
        print("========== Collecting Organization Data ==========")
        
        # Validate GitHub token
        if not self.token:
            raise ValueError("GitHub token is required for API access")
        
        masked_token = self.token[:4] + "..." + self.token[-4:] if len(self.token) > 8 else "***"
        print(f"Using GitHub token: {masked_token}")
        
        # Initial rate limit check
        rate_limits = self._check_rate_limit()
        if not rate_limits:
            print("WARNING: Unable to check initial rate limits")
        
        # Fetch all repositories
        repos = self.fetch_accessible_repositories()
        
        # Collect data for each repository
        all_data = {
            'repositories': {},
            'organization': self.repo_owner,
            'collection_timestamp': datetime.now().isoformat(),
            'total_repos': len(repos),
            'total_api_requests': 0
        }
        
        print(f"DEBUG - Processing {len(repos)} repositories")
        
        for i, repo in enumerate(repos):
            print(f"\n========== Processing repository {i+1}/{len(repos)}: {repo['owner']}/{repo['name']} ==========")
            
            repo_data = self.collect_complete_repository_data(repo['owner'], repo['name'])
            all_data['repositories'][repo['name']] = repo_data
            
            print(f"DEBUG - Completed data collection for {repo['name']}")
        
        all_data['total_api_requests'] = self._request_count
        print(f"DEBUG - Total API requests made: {self._request_count}")
        
        return all_data 
