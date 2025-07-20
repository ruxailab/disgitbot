"""
Metrics Processing Module

Handles creation of repository metrics from raw data.
"""

import time

class MetricsProcessor:
    """Processes raw data into repository metrics."""
    
    def create_repo_metrics(self, raw_data, all_contributions):
        """Create repository metrics from raw data."""
        print("Creating repository metrics...")
        
        repositories = raw_data.get('repositories', {})
        
        metrics = {
            'stars_count': self._calculate_total_stars(repositories),
            'forks_count': self._calculate_total_forks(repositories),
            'issues_count': self._calculate_total_issues(repositories),
            'pr_count': self._calculate_total_prs(repositories),
            'commits_count': self._calculate_total_commits(all_contributions),
            'total_contributors': len(all_contributions),
            'last_updated': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
        }
        
        return metrics
    
    def _calculate_total_stars(self, repositories):
        """Calculate total stars across all repositories."""
        total_stars = 0
        for repo_name, repo_data in repositories.items():
            repo_info = repo_data.get('repo_info', {})
            total_stars += repo_info.get('stargazers_count', 0)
        return total_stars
    
    def _calculate_total_forks(self, repositories):
        """Calculate total forks across all repositories."""
        total_forks = 0
        for repo_name, repo_data in repositories.items():
            repo_info = repo_data.get('repo_info', {})
            total_forks += repo_info.get('forks_count', 0)
        return total_forks
    
    def _calculate_total_issues(self, repositories):
        """Calculate total issues across all repositories."""
        total_issues = 0
        for repo_name, repo_data in repositories.items():
            issues = repo_data.get('issues', {})
            total_issues += issues.get('total_count', 0)
        return total_issues
    
    def _calculate_total_prs(self, repositories):
        """Calculate total pull requests across all repositories."""
        total_prs = 0
        for repo_name, repo_data in repositories.items():
            pull_requests = repo_data.get('pull_requests', {})
            total_prs += pull_requests.get('total_count', 0)
        return total_prs
    
    def _calculate_total_commits(self, all_contributions):
        """Calculate total commits from all contributors."""
        return sum(user_data.get("commits_count", 0) for user_data in all_contributions.values()) 