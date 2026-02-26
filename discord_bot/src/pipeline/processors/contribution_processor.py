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
    
    # Ensure the account owner (organization or personal account) is always
    # present in contributions, even if they have zero activity.  This
    # prevents the user_mappings lookup from failing for personal accounts
    # that only have forked repos with no direct contributions yet.
    account_owner = raw_data.get('organization', '')
    if account_owner:
        _initialize_user_if_needed(account_owner, all_contributions)
        print(f"Pre-initialized account owner: {account_owner}")
    
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
    
    # Also include the repo owner so they always appear in the contributions
    repo_owner = repo_data.get('owner')
    if repo_owner:
        all_usernames.add(repo_owner)
    
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
        if pr and pr.get('user') and pr['user'].get('login'):
            all_usernames.add(pr['user']['login'])
    
    for issue in issues:
        if issue and issue.get('user') and issue['user'].get('login'):
            all_usernames.add(issue['user']['login'])
    
    for commit in commits:
        if commit and commit.get('author') and commit['author'].get('login'):
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
            'profile': {},
            'pr_dates': [],
            'issue_dates': [],
            'commit_dates': [],
            'stats': {
                'current_month': current_month,
                'last_updated': now.strftime('%Y-%m-%d %H:%M:%S UTC'),
                'pr': {
                    'daily': 0,
                    'weekly': 0,
                    'monthly': 0,
                    'all_time': 0,
                    'current_streak': 0,
                    'longest_streak': 0,
                    'avg_per_day': 0
                },
                'issue': {
                    'daily': 0,
                    'weekly': 0,
                    'monthly': 0,
                    'all_time': 0,
                    'current_streak': 0,
                    'longest_streak': 0,
                    'avg_per_day': 0
                },
                'commit': {
                    'daily': 0,
                    'weekly': 0,
                    'monthly': 0,
                    'all_time': 0,
                    'current_streak': 0,
                    'longest_streak': 0,
                    'avg_per_day': 0
                }
            },
            'rankings': {}
        }

def _process_user_contributions(username, pull_requests, issues, commits, all_contributions):
    """Process all contributions for a single user."""
    user_data = all_contributions[username]
    
    # Process PRs
    for pr in pull_requests:
        if pr and pr.get('user') and pr['user'].get('login') == username:
            user_data['pr_count'] += 1
            user_data['stats']['pr']['all_time'] += 1
            created_at = pr.get('created_at', '')
            _update_activity_counts(created_at, user_data)
            _update_time_based_stats(created_at, user_data['stats']['pr'])
            
            # Store date for streak calculation
            if created_at:
                date_str = created_at.split('T')[0]
                user_data['pr_dates'].append(date_str)
            
            if pr.get('repository') and pr['repository'].get('name'):
                repo_name = pr['repository']['name']
                user_data['repositories'].add(repo_name)
    
    # Process issues
    for issue in issues:
        if issue and issue.get('user') and issue['user'].get('login') == username:
            if not issue.get('pull_request'):  # Exclude PRs counted as issues
                user_data['issues_count'] += 1
                user_data['stats']['issue']['all_time'] += 1
                created_at = issue.get('created_at', '')
                _update_activity_counts(created_at, user_data)
                _update_time_based_stats(created_at, user_data['stats']['issue'])
                
                # Store date for streak calculation
                if created_at:
                    date_str = created_at.split('T')[0]
                    user_data['issue_dates'].append(date_str)
    
    # Process commits
    for commit in commits:
        if commit and commit.get('author') and commit['author'].get('login') == username:
            user_data['commits_count'] += 1
            user_data['stats']['commit']['all_time'] += 1
            # Safe nested access for commit date
            commit_obj = commit.get('commit')
            if commit_obj and commit_obj.get('author'):
                commit_date = commit_obj['author'].get('date', '')
                _update_activity_counts(commit_date, user_data)
                _update_time_based_stats(commit_date, user_data['stats']['commit'])
                
                # Store date for streak calculation
                if commit_date:
                    date_str = commit_date.split('T')[0]
                    user_data['commit_dates'].append(date_str)

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

def _update_time_based_stats(date_str, stats_dict):
    """Update time-based stats (daily, weekly, monthly) based on date."""
    if not date_str:
        return
    
    try:
        activity_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).strftime('%Y-%m-%d')
        
        if activity_date == today_date:
            stats_dict['daily'] += 1
        
        if activity_date >= week_ago_date:
            stats_dict['weekly'] += 1
            
        if activity_date >= month_ago_date:
            stats_dict['monthly'] += 1
            
    except (ValueError, AttributeError):
        pass

def calculate_rankings(contributions):
    """Calculate rankings for all contributors."""
    print("Calculating rankings for all contributors...")
    
    if not contributions:
        return contributions
    
    # Define ranking categories
    ranking_categories = {
        'pr': lambda x: x[1]['stats']['pr']['all_time'],
        'issue': lambda x: x[1]['stats']['issue']['all_time'],
        'commit': lambda x: x[1]['stats']['commit']['all_time'],
        'pr_daily': lambda x: x[1]['stats']['pr']['daily'],
        'pr_weekly': lambda x: x[1]['stats']['pr']['weekly'],
        'pr_monthly': lambda x: x[1]['stats']['pr']['monthly'],
        'issue_daily': lambda x: x[1]['stats']['issue']['daily'],
        'issue_weekly': lambda x: x[1]['stats']['issue']['weekly'],
        'issue_monthly': lambda x: x[1]['stats']['issue']['monthly'],
        'commit_daily': lambda x: x[1]['stats']['commit']['daily'],
        'commit_weekly': lambda x: x[1]['stats']['commit']['weekly'],
        'commit_monthly': lambda x: x[1]['stats']['commit']['monthly'],
    }
    
    # Calculate rankings for each category
    for rank_name, sort_key in ranking_categories.items():
        sorted_contributors = sorted(contributions.items(), key=sort_key, reverse=True)
        for rank, (username, data) in enumerate(sorted_contributors, 1):
            if 'rankings' not in data:
                data['rankings'] = {}
            data['rankings'][rank_name] = rank
    
    return contributions

def calculate_streaks_and_averages(contributions):
    """Calculate streaks and averages for contributors."""
    print("Calculating streaks and averages...")
    
    for username, data in contributions.items():
        # Calculate streaks for each contribution type
        for contrib_type, date_key in [('pr', 'pr_dates'), ('issue', 'issue_dates'), ('commit', 'commit_dates')]:
            dates = data.get(date_key, [])
            if dates:
                current_streak, longest_streak = _calculate_streak_from_dates(dates)
                data['stats'][contrib_type]['current_streak'] = current_streak
                data['stats'][contrib_type]['longest_streak'] = longest_streak
            
            # Calculate average per day for current month
            monthly_count = data['stats'][contrib_type]['monthly']
            days_this_month = min(now.day, 30)
            data['stats'][contrib_type]['avg_per_day'] = round(monthly_count / max(days_this_month, 1), 1)
        
        # Convert repositories set to list for JSON serialization
        if isinstance(data.get('repositories'), set):
            data['repositories'] = list(data['repositories'])
        
        # Legacy fields for backward compatibility
        if data['today_activity'] > 0 and data['yesterday_activity'] > 0:
            data['streak'] = 2
        elif data['today_activity'] > 0 or data['yesterday_activity'] > 0:
            data['streak'] = 1
        else:
            data['streak'] = 0
            
        data['longest_streak'] = max(data['streak'], 1) if data['total_activity'] > 0 else 0
        data['average_daily'] = round(data['total_activity'] / 30.0, 2) if data['total_activity'] > 0 else 0
        
        # Keep date arrays for analytics processing
        # Note: Date arrays will be cleaned up after analytics processing
    
    return contributions

def _calculate_streak_from_dates(dates):
    """Calculate current and longest streak from a list of dates."""
    if not dates:
        return 0, 0
    
    # Remove duplicates and sort dates (most recent first)
    unique_dates = sorted(list(set(dates)), reverse=True)
    
    # Calculate current streak
    current_streak = 0
    if unique_dates:
        last_date = datetime.strptime(unique_dates[0], '%Y-%m-%d')
        current_streak = 1
        
        for i in range(1, len(unique_dates)):
            date_obj = datetime.strptime(unique_dates[i], '%Y-%m-%d')
            if (last_date - date_obj).days <= 1:  # Consecutive days
                current_streak += 1
                last_date = date_obj
            else:
                break
    
    # Calculate longest streak
    longest_streak = 0
    if unique_dates:
        # Sort oldest first for proper streak calculation
        unique_dates.sort()
        
        current_group = 1
        longest_streak = 1
        
        for i in range(1, len(unique_dates)):
            prev_date = datetime.strptime(unique_dates[i-1], '%Y-%m-%d')
            curr_date = datetime.strptime(unique_dates[i], '%Y-%m-%d')
            
            if (curr_date - prev_date).days <= 1:  # Consecutive days
                current_group += 1
                longest_streak = max(longest_streak, current_group)
            else:
                current_group = 1
    
    return current_streak, longest_streak 