"""
Metrics Processing Functions

Simple functions for creating repository metrics from raw data.
"""

import time

def create_repo_metrics(raw_data, all_contributions):
    """Create repository metrics from raw data."""
    print("Creating repository metrics...")
    
    repositories = raw_data.get('repositories', {})
    
    # Calculate totals
    stars_count = sum(
        repo_data.get('repo_info', {}).get('stargazers_count', 0)
        for repo_data in repositories.values()
    )
    
    forks_count = sum(
        repo_data.get('repo_info', {}).get('forks_count', 0)
        for repo_data in repositories.values()
    )
    
    issues_count = sum(
        repo_data.get('issues', {}).get('total_count', 0)
        for repo_data in repositories.values()
    )
    
    pr_count = sum(
        repo_data.get('pull_requests', {}).get('total_count', 0)
        for repo_data in repositories.values()
    )
    
    commits_count = sum(
        contrib.get('commits_count', 0)
        for contrib in all_contributions.values()
    )
    
    return {
        'stars_count': stars_count,
        'forks_count': forks_count,
        'issues_count': issues_count,
        'pr_count': pr_count,
        'commits_count': commits_count,
        'total_contributors': len(all_contributions),
        'last_updated': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
    } 