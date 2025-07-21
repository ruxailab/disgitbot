"""
Contribution Processing Functions

Simple functions for processing raw GitHub data into structured contribution data.
"""

from datetime import datetime, timedelta

# Global date constants
now = datetime.now()
today_date = now.strftime('%Y-%m-%d')
yesterday_date = (now - timedelta(days=1)).strftime('%Y-%m-%d')
week_ago_date = (now - timedelta(days=7)).strftime('%Y-%m-%d')
month_ago_date = (now - timedelta(days=30)).strftime('%Y-%m-%d')
current_month = now.strftime("%B")

def process_raw_data(raw_data):
    """Process raw GitHub data into structured contribution data."""
    print("Processing raw data into contribution structures...")
    
    all_contributions = {}
    repositories = raw_data.get('repositories', {})
    
    for repo_name, repo_data in repositories.items():
        print(f"Processing repository: {repo_name}")
        _process_repository(repo_data, all_contributions)
    
    print(f"Processed {len(all_contributions)} contributors")
    return all_contributions

def _process_repository(repo_data, all_contributions):
    """Process a single repository's data."""
    contributors = repo_data.get('contributors', [])
    pull_requests = repo_data.get('pull_requests', {}).get('items', [])
    issues = repo_data.get('issues', {}).get('items', [])
    commits = repo_data.get('commits_search', {}).get('items', [])
    
    all_usernames = _extract_usernames(contributors, pull_requests, issues, commits)
    
    for username in all_usernames:
        if not username:
            continue
        
        _initialize_user_if_needed(username, all_contributions)
        _process_user_contributions(username, pull_requests, issues, commits, all_contributions)

def _extract_usernames(contributors, pull_requests, issues, commits):
    """Extract all unique usernames from various data sources."""
    all_usernames = set()
    
    for contributor in contributors:
        if contributor and contributor.get('login'):
            all_usernames.add(contributor['login'])
    
    for pr in pull_requests:
        if pr and pr.get('user', {}).get('login'):
            all_usernames.add(pr['user']['login'])
    
    for issue in issues:
        if issue and issue.get('user', {}).get('login'):
            all_usernames.add(issue['user']['login'])
    
    for commit in commits:
        if commit and commit.get('author', {}).get('login'):
            all_usernames.add(commit['author']['login'])
    
    return all_usernames

def _initialize_user_if_needed(username, all_contributions):
    """Initialize user data structure if not exists."""
    if username not in all_contributions:
        all_contributions[username] = {
            'pr_count': 0,
            'issues_count': 0, 
            'commits_count': 0,
            'today_activity': 0,
            'yesterday_activity': 0,
            'week_activity': 0,
            'month_activity': 0,
            'total_activity': 0,
            'monthly_data': {},
            'streak': 0,
            'longest_streak': 0,
            'average_daily': 0.0,
            'repositories': set(),
            'profile': {}
        }

def _process_user_contributions(username, pull_requests, issues, commits, all_contributions):
    """Process all contributions for a single user."""
    user_data = all_contributions[username]
    
    # Process PRs
    for pr in pull_requests:
        if pr and pr.get('user', {}).get('login') == username:
            user_data['pr_count'] += 1
            _update_activity_counts(pr.get('created_at', ''), user_data)
            
            if 'repository' in pr:
                repo_name = pr['repository'].get('name', 'unknown')
                user_data['repositories'].add(repo_name)
    
    # Process issues
    for issue in issues:
        if issue and issue.get('user', {}).get('login') == username:
            if not issue.get('pull_request'):  # Exclude PRs counted as issues
                user_data['issues_count'] += 1
                _update_activity_counts(issue.get('created_at', ''), user_data)
    
    # Process commits
    for commit in commits:
        if commit and commit.get('author', {}).get('login') == username:
            user_data['commits_count'] += 1
            commit_date = commit.get('commit', {}).get('author', {}).get('date', '')
            _update_activity_counts(commit_date, user_data)

def _update_activity_counts(date_str, user_data):
    """Update activity counters based on date."""
    if not date_str:
        return
        
    try:
        activity_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).strftime('%Y-%m-%d')
        
        user_data['total_activity'] += 1
        
        if activity_date == today_date:
            user_data['today_activity'] += 1
        elif activity_date == yesterday_date:
            user_data['yesterday_activity'] += 1
            
        if activity_date >= week_ago_date:
            user_data['week_activity'] += 1
            
        if activity_date >= month_ago_date:
            user_data['month_activity'] += 1
            
        # Monthly tracking
        activity_datetime = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        month_key = activity_datetime.strftime('%Y-%m')
        
        if month_key not in user_data['monthly_data']:
            user_data['monthly_data'][month_key] = 0
        user_data['monthly_data'][month_key] += 1
        
    except (ValueError, AttributeError):
        pass

def calculate_rankings(contributions):
    """Calculate rankings for all contributors."""
    print("Calculating rankings for all contributors...")
    
    # Sort contributors by total activity
    sorted_contributors = sorted(
        contributions.items(),
        key=lambda x: x[1]['total_activity'],
        reverse=True
    )
    
    for rank, (username, data) in enumerate(sorted_contributors, 1):
        data['overall_rank'] = rank
    
    # PR rankings
    sorted_by_prs = sorted(contributions.items(), key=lambda x: x[1]['pr_count'], reverse=True)
    for rank, (username, data) in enumerate(sorted_by_prs, 1):
        data['pr_rank'] = rank
    
    # Issues rankings
    sorted_by_issues = sorted(contributions.items(), key=lambda x: x[1]['issues_count'], reverse=True)
    for rank, (username, data) in enumerate(sorted_by_issues, 1):
        data['issues_rank'] = rank
    
    # Commits rankings
    sorted_by_commits = sorted(contributions.items(), key=lambda x: x[1]['commits_count'], reverse=True)
    for rank, (username, data) in enumerate(sorted_by_commits, 1):
        data['commits_rank'] = rank
    
    return contributions

def calculate_streaks_and_averages(contributions):
    """Calculate streaks and averages for contributors."""
    print("Calculating streaks and averages...")
    
    for username, data in contributions.items():
        # Calculate average daily activity
        if data['total_activity'] > 0:
            # Simple approximation - total activity / 30 days
            data['average_daily'] = round(data['total_activity'] / 30.0, 2)
        
        # Convert repositories set to list for JSON serialization
        data['repositories'] = list(data['repositories'])
        
        # Simple streak calculation based on recent activity
        if data['today_activity'] > 0 and data['yesterday_activity'] > 0:
            data['streak'] = 2
        elif data['today_activity'] > 0 or data['yesterday_activity'] > 0:
            data['streak'] = 1
        else:
            data['streak'] = 0
            
        data['longest_streak'] = max(data['streak'], 1) if data['total_activity'] > 0 else 0
    
    return contributions 