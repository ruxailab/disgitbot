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

def process_repository_labels(raw_data):
    """Process repository labels from raw data for storage."""
    print("Processing repository labels...")
    
    repositories = raw_data.get('repositories', {})
    processed_labels = {}
    
    for repo_name, repo_data in repositories.items():
        labels = repo_data.get('labels', [])
        if labels:
            repo_full_name = f"{repo_data.get('owner', 'unknown')}/{repo_name}"
            
            # Process labels into storage format
            processed_labels[repo_full_name] = {
                'repository': repo_full_name,
                'labels': [
                    {
                        'name': label.get('name', ''),
                        'color': label.get('color', ''),
                        'description': label.get('description', ''),
                        'url': label.get('url', ''),
                        'id': label.get('id', 0)
                    }
                    for label in labels
                ],
                'count': len(labels),
                'last_updated': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
            }
            print(f"Processed {len(labels)} labels for {repo_full_name}")
    
    print(f"Processed labels for {len(processed_labels)} repositories")
    return processed_labels 