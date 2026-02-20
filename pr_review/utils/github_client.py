#!/usr/bin/env python3
"""
GitHub API client for PR automation
"""

import os
import requests
import logging
from typing import List, Dict, Any, Optional
from github import Github

try:
    from pr_review.config import GITHUB_TOKEN
except ImportError:
    from config import GITHUB_TOKEN

class GitHubClient:
    """GitHub API client for PR review system"""
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize the GitHub client.
        
        Args:
            token: GitHub API token (defaults to GITHUB_TOKEN config)
        """
        self.token = token or GITHUB_TOKEN
        if not self.token:
            raise ValueError("GitHub token is required")
        
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.logger = logging.getLogger(__name__)
    
    def _make_request(self, endpoint: str, method: str = "GET", params: Dict = None, data: Dict = None) -> Dict:
        """
        Make a request to the GitHub API.
        
        Args:
            endpoint: API endpoint (relative to base URL)
            method: HTTP method
            params: Query parameters
            data: Request body
            
        Returns:
            Response data
        """
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=data
            )
            
            response.raise_for_status()
            
            if response.status_code == 204:  # No content
                return {}
                
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"GitHub API error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                self.logger.error(f"Response: {e.response.text}")
            raise
    
    def get_pull_requests(self, repo: str, state: str = "all", count: int = 100) -> List[Dict[str, Any]]:
        """
        Get pull requests from a repository.
        
        Args:
            repo: Repository name in format "owner/repo"
            state: PR state ('open', 'closed', 'all')
            count: Maximum number of PRs to fetch
            
        Returns:
            List of pull requests
        """
        all_prs = []
        page = 1
        per_page = min(100, count)  # GitHub API max per page is 100
        
        while len(all_prs) < count:
            endpoint = f"repos/{repo}/pulls"
            params = {
                "state": state,
                "sort": "updated",
                "direction": "desc",
                "per_page": per_page,
                "page": page
            }
            
            prs = self._make_request(endpoint, params=params)
            
            if not prs:
                break
                
            all_prs.extend(prs)
            
            if len(prs) < per_page:
                break
                
            page += 1
        
        return all_prs[:count]
    
    def get_pull_request_details(self, repo: str, pr_number: int) -> Dict[str, Any]:
        """
        Get details for a specific pull request.
        
        Args:
            repo: Repository name in format "owner/repo"
            pr_number: Pull request number
            
        Returns:
            Pull request details
        """
        endpoint = f"repos/{repo}/pulls/{pr_number}"
        return self._make_request(endpoint)
    
    def get_pull_request_reviews(self, repo: str, pr_number: int) -> List[Dict[str, Any]]:
        """
        Get reviews for a pull request.
        
        Args:
            repo: Repository name in format "owner/repo"
            pr_number: Pull request number
            
        Returns:
            List of reviews
        """
        endpoint = f"repos/{repo}/pulls/{pr_number}/reviews"
        reviews = self._make_request(endpoint)
        
        # Get detailed review comments for each review
        for review in reviews:
            if review.get("id"):
                review["comments"] = self.get_pull_request_review_comments(repo, pr_number, review["id"])
        
        return reviews
    
    def get_pull_request_review_comments(self, repo: str, pr_number: int, review_id: int) -> List[Dict[str, Any]]:
        """
        Get comments for a specific review.
        
        Args:
            repo: Repository name in format "owner/repo"
            pr_number: Pull request number
            review_id: Review ID
            
        Returns:
            List of review comments
        """
        endpoint = f"repos/{repo}/pulls/{pr_number}/reviews/{review_id}/comments"
        try:
            return self._make_request(endpoint)
        except requests.exceptions.RequestException:
            # Some reviews don't have comments endpoint
            return []
    
    def get_pull_request_diff(self, repo: str, pr_number: int) -> str:
        """
        Get the diff for a pull request.
        
        Args:
            repo: Repository name in format "owner/repo"
            pr_number: Pull request number
            
        Returns:
            Pull request diff as text
        """
        url = f"{self.base_url}/repos/{repo}/pulls/{pr_number}"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3.diff"  # Request diff format
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching PR diff: {str(e)}")
            return ""
    
    def create_pull_request_review(self, repo: str, pr_number: int, review_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a review on a pull request.
        
        Args:
            repo: Repository name in format "owner/repo"
            pr_number: Pull request number
            review_data: Review data including body, event, and comments
            
        Returns:
            Created review data
        """
        endpoint = f"repos/{repo}/pulls/{pr_number}/reviews"
        return self._make_request(endpoint, method="POST", data=review_data)
    
    def create_pull_request_comment(self, repo: str, pr_number: int, comment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a comment on a pull request.
        
        Args:
            repo: Repository name in format "owner/repo"
            pr_number: Pull request number
            comment_data: Comment data
            
        Returns:
            Created comment data
        """
        endpoint = f"repos/{repo}/pulls/{pr_number}/comments"
        return self._make_request(endpoint, method="POST", data=comment_data)
    
    # New methods for PR automation
    
    def get_repository_labels(self, repo: str) -> List[Dict[str, Any]]:
        """
        Get repository labels from stored Discord bot pipeline data.
        
        Args:
            repo: Repository in format 'owner/repo'
            
        Returns:
            List of label dictionaries with name, color, description
        """
        try:
            from shared.firestore import get_document
            
            doc_id = repo.replace('/', '_')
            label_data = get_document('repository_labels', doc_id)
            
            if not label_data or 'labels' not in label_data:
                raise ValueError(f"No label configuration found for repository {repo}")
                
            labels = label_data['labels']
            self.logger.info(f"Retrieved {len(labels)} labels for {repo} from stored data")
            return labels
                
        except Exception as e:
            self.logger.error(f"Error getting stored labels for {repo}: {e}")
            raise
    

    
    def add_labels_to_pull_request(self, repo: str, pr_number: int, labels: List[str]) -> Dict[str, Any]:
        """
        Add labels to a pull request.
        
        Args:
            repo: Repository name in format "owner/repo"
            pr_number: Pull request number
            labels: List of label names to add
            
        Returns:
            Updated issue data
        """
        endpoint = f"repos/{repo}/issues/{pr_number}/labels"
        data = {"labels": labels}
        return self._make_request(endpoint, method="POST", data=data)
    
    def remove_labels_from_pull_request(self, repo: str, pr_number: int, labels: List[str]) -> Dict[str, Any]:
        """
        Remove labels from a pull request.
        
        Args:
            repo: Repository name in format "owner/repo"
            pr_number: Pull request number
            labels: List of label names to remove
            
        Returns:
            Response data
        """
        for label in labels:
            endpoint = f"repos/{repo}/issues/{pr_number}/labels/{label}"
            try:
                self._make_request(endpoint, method="DELETE")
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Failed to remove label {label}: {e}")
        return {}
    
    def request_reviewers(self, repo: str, pr_number: int, reviewers: List[str], team_reviewers: List[str] = None) -> Dict[str, Any]:
        """
        Request reviewers for a pull request.
        
        Args:
            repo: Repository name in format "owner/repo"
            pr_number: Pull request number
            reviewers: List of GitHub usernames to request as reviewers
            team_reviewers: List of team names to request as reviewers
            
        Returns:
            Updated pull request data
        """
        endpoint = f"repos/{repo}/pulls/{pr_number}/requested_reviewers"
        data = {"reviewers": reviewers}
        if team_reviewers:
            data["team_reviewers"] = team_reviewers
        
        return self._make_request(endpoint, method="POST", data=data)
    
    def remove_review_request(self, repo: str, pr_number: int, reviewers: List[str], team_reviewers: List[str] = None) -> Dict[str, Any]:
        """
        Remove review request from a pull request.
        
        Args:
            repo: Repository name in format "owner/repo"
            pr_number: Pull request number
            reviewers: List of GitHub usernames to remove from reviewers
            team_reviewers: List of team names to remove from reviewers
            
        Returns:
            Updated pull request data
        """
        endpoint = f"repos/{repo}/pulls/{pr_number}/requested_reviewers"
        data = {"reviewers": reviewers}
        if team_reviewers:
            data["team_reviewers"] = team_reviewers
        
        return self._make_request(endpoint, method="DELETE", data=data)
    
    def create_issue_comment(self, repo: str, issue_number: int, body: str) -> Dict[str, Any]:
        """
        Create a comment on an issue or pull request.
        
        Args:
            repo: Repository name in format "owner/repo"
            issue_number: Issue or PR number
            body: Comment body
            
        Returns:
            Created comment data
        """
        endpoint = f"repos/{repo}/issues/{issue_number}/comments"
        data = {"body": body}
        return self._make_request(endpoint, method="POST", data=data)
    
    def get_repository_contributors(self, repo: str) -> List[Dict[str, Any]]:
        """
        Get contributors for a repository.
        
        Args:
            repo: Repository name in format "owner/repo"
            
        Returns:
            List of contributors
        """
        endpoint = f"repos/{repo}/contributors"
        return self._make_request(endpoint)
    
    def get_repository_collaborators(self, repo: str) -> List[Dict[str, Any]]:
        """
        Get collaborators for a repository.
        
        Args:
            repo: Repository name in format "owner/repo"
            
        Returns:
            List of collaborators
        """
        endpoint = f"repos/{repo}/collaborators"
        return self._make_request(endpoint)
    
    def get_user_pull_requests(self, username: str, state: str = "open") -> List[Dict[str, Any]]:
        """
        Get pull requests for a specific user across all repositories.
        
        Args:
            username: GitHub username
            state: PR state ('open', 'closed', 'all')
            
        Returns:
            List of pull requests
        """
        endpoint = "search/issues"
        params = {
            "q": f"type:pr author:{username} state:{state}",
            "sort": "updated",
            "order": "desc"
        }
        
        response = self._make_request(endpoint, params=params)
        return response.get("items", [])
    
    def get_pull_request_files(self, repo: str, pr_number: int) -> List[Dict[str, Any]]:
        """
        Get files changed in a pull request.
        
        Args:
            repo: Repository name in format "owner/repo"
            pr_number: Pull request number
            
        Returns:
            List of changed files
        """
        endpoint = f"repos/{repo}/pulls/{pr_number}/files"
        return self._make_request(endpoint) 