import os
import requests
import json
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GITHUB_API_URL = "https://api.github.com"
ORG_NAME = os.getenv("ORG_NAME", "ruxailab")
# Keep legacy variables for backward compatibility
REPO_OWNER = os.getenv("REPO_OWNER", "ruxailab")
REPO_NAME = os.getenv("REPO_NAME", "RUXAILAB")

def get_github_headers():
    """
    Create properly formatted headers for GitHub API requests.
    Handles authentication and accepts headers.
    """
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
    """
    Check rate limits and wait if necessary until reset or until we have enough requests available.
    
    Args:
        rate_type: 'core' or 'search'
        min_remaining: minimum number of requests that should be available
    
    Returns:
        True if we can continue, False if we should abort
    """
    limits = check_rate_limit()
    if not limits:
        print("WARNING: Unable to check rate limits")
        time.sleep(5)  # Wait a bit anyway
        return True
    
    limit_data = limits.get(rate_type, {})
    remaining = limit_data.get('remaining', 0)
    reset_time = limit_data.get('reset', 0)
    
    if remaining <= min_remaining:
        current_time = datetime.now().timestamp()
        wait_seconds = max(1, reset_time - current_time + 2)  # +2 seconds buffer
        
        reset_datetime = datetime.fromtimestamp(reset_time)
        print(f"\nRate limit for {rate_type} API almost exhausted ({remaining} remaining).")
        print(f"Waiting until reset at {reset_datetime.strftime('%H:%M:%S')} ({int(wait_seconds)} seconds)...")
        
        # If wait time is too long, offer to save progress
        if wait_seconds > 60:
            return False
        
        time.sleep(wait_seconds)
        print("Continuing after rate limit reset.")
        return True
    
    return True

def make_github_request(url, headers, request_type='search', retries=3, retry_delay=2):
    """
    Make a GitHub API request with retry logic and rate limit handling.
    
    Args:
        url: The API URL to request
        headers: Request headers
        request_type: 'core' or 'search' to track rate limits
        retries: Number of retries on failure
        retry_delay: Initial delay between retries (increases exponentially)
    
    Returns:
        Response object on success, None on failure after retries
    """
    for attempt in range(retries):
        # Check if we need to wait for rate limits
        if not wait_for_rate_limit(request_type):
            print(f"Rate limits exhausted for {request_type} API. Consider running the script later.")
            return None
            
        try:
            response = requests.get(url, headers=headers)
            
            # Success
            if response.status_code == 200:
                # Small delay to avoid hitting rate limits
                time.sleep(0.5)
                return response
            
            # Rate limit hit
            if response.status_code == 403 and "rate limit exceeded" in response.text.lower():
                print(f"Rate limit exceeded: {response.text}")
                if not wait_for_rate_limit(request_type):
                    return None
                continue
                
            # Other error
            print(f"ERROR - API response: {response.status_code} - {response.text}")
            
            # If this is our last retry, return the failed response
            if attempt == retries - 1:
                return response
                
            # Otherwise wait and retry
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
        if not repo_page:  # Empty page means we've reached the end
            break
            
        for repo in repo_page:
            repos.append({
                "name": repo["name"],
                "owner": repo["owner"]["login"]
            })
        
        page += 1
        
        # If we got less than per_page results, we've reached the end
        if len(repo_page) < per_page:
            break
    
    print(f"Found {len(repos)} repositories in the {ORG_NAME} organization.")
    return repos

def calculate_streaks(username, contribution_type, headers, month_ago_date):
    """
    Calculate contribution streaks for any contribution type across all organization repos.
    
    Args:
        username: GitHub username
        contribution_type: 'pr', 'issue', or 'commit'
        headers: API request headers
        month_ago_date: Date 30 days ago
    
    Returns:
        Dictionary with current_streak and longest_streak
    """
    # Cannot calculate streaks for commits via the API in the same way
    if contribution_type == 'commit':
        return {
            'current_streak': 0,
            'longest_streak': 0
        }
    
    # Set up query parameters based on contribution type
    if contribution_type == 'pr':
        query_type = 'type:pr+is:merged'
        time_field = 'merged'
        date_field = 'merged_at'
    elif contribution_type == 'issue':
        query_type = 'type:issue'
        time_field = 'created'
        date_field = 'created_at'
    
    # Get list of organization repositories
    org_repos = fetch_org_repositories()
    
    # Collect contributions across all repos
    all_contributions = []
    
    for repo in org_repos:
        # Get contribution data for the last 30 days
        streak_url = f"{GITHUB_API_URL}/search/issues?q=repo:{repo['owner']}/{repo['name']}+{query_type}+author:{username}+{time_field}:>={month_ago_date}&sort={time_field}&order=desc&per_page=100"
        streak_response = make_github_request(streak_url, headers, 'search')
        
        if streak_response and streak_response.status_code == 200 and 'items' in streak_response.json():
            items = streak_response.json()['items']
            for item in items:
                if contribution_type == 'pr' and not item.get("pull_request"):
                    continue
                
                date_str = item.get(date_field, '').split('T')[0]  # Extract date part
                if date_str:
                    all_contributions.append(date_str)
    
    # Calculate streaks based on the combined contribution dates
    current_streak = 0
    longest_streak = 0
    
    if all_contributions:
        # Remove duplicates and sort dates (most recent first)
        unique_dates = list(set(all_contributions))
        unique_dates.sort(reverse=True)  # Most recent first
        
        # Calculate current streak
        last_date = datetime.strptime(unique_dates[0], '%Y-%m-%d')
        current_streak = 1
        
        for i in range(1, len(unique_dates)):
            date = datetime.strptime(unique_dates[i], '%Y-%m-%d')
            if (last_date - date).days <= 1:  # Consecutive days
                current_streak += 1
            else:
                break
            last_date = date
        
        # Calculate longest streak
        # Re-sort dates in ascending order for proper streak calculation
        unique_dates.sort()  # Oldest first
        
        # Group dates by consecutive days
        streaks = []
        current_group = [unique_dates[0]]
        
        for i in range(1, len(unique_dates)):
            prev_date = datetime.strptime(current_group[-1], '%Y-%m-%d')
            curr_date = datetime.strptime(unique_dates[i], '%Y-%m-%d')
            
            if (curr_date - prev_date).days <= 1:  # Consecutive days
                current_group.append(unique_dates[i])
            else:
                streaks.append(current_group)
                current_group = [unique_dates[i]]
        
        # Add the last group
        if current_group:
            streaks.append(current_group)
        
        # Find the longest streak
        longest_streak = max([len(streak) for streak in streaks]) if streaks else 0
    
    return {
        'current_streak': current_streak,
        'longest_streak': longest_streak
    }

def calculate_streaks_from_dates(dates):
    """
    Calculate streaks from a list of contribution dates.
    
    Args:
        dates: List of dates in 'YYYY-MM-DD' format
    
    Returns:
        Dictionary with current_streak and longest_streak
    """
    if not dates:
        return {
            'current_streak': 0,
            'longest_streak': 0
        }
    
    # Remove duplicates and sort dates (most recent first)
    unique_dates = list(set(dates))
    unique_dates.sort(reverse=True)  # Most recent first
    
    # Calculate current streak
    last_date = datetime.strptime(unique_dates[0], '%Y-%m-%d')
    current_streak = 1
    
    for i in range(1, len(unique_dates)):
        date = datetime.strptime(unique_dates[i], '%Y-%m-%d')
        if (last_date - date).days <= 1:  # Consecutive days
            current_streak += 1
        else:
            break
        last_date = date
    
    # Calculate longest streak
    # Re-sort dates in ascending order for proper streak calculation
    unique_dates.sort()  # Oldest first
    
    # Group dates by consecutive days
    streaks = []
    current_group = [unique_dates[0]]
    
    for i in range(1, len(unique_dates)):
        prev_date = datetime.strptime(current_group[-1], '%Y-%m-%d')
        curr_date = datetime.strptime(unique_dates[i], '%Y-%m-%d')
        
        if (curr_date - prev_date).days <= 1:  # Consecutive days
            current_group.append(unique_dates[i])
        else:
            streaks.append(current_group)
            current_group = [unique_dates[i]]
    
    # Add the last group
    if current_group:
        streaks.append(current_group)
    
    # Find the longest streak
    longest_streak = max([len(streak) for streak in streaks]) if streaks else 0
    
    return {
        'current_streak': current_streak,
        'longest_streak': longest_streak
    }

def calculate_rankings(all_contributions):
    """Calculate rankings for each contributor across different metrics."""
    contributors = list(all_contributions.keys())
    if not contributors:
        return all_contributions
        
    # Calculate rankings for all contribution types
    ranking_types = {
        "pr": lambda user: all_contributions[user]["pr_count"],
        "issue": lambda user: all_contributions[user]["issues_count"],
        "commit": lambda user: all_contributions[user]["commits_count"]
    }
    
    for time_period in ["daily", "weekly", "monthly", "all_time"]:
        ranking_types[f"pr_{time_period}"] = lambda user, period=time_period: all_contributions[user]["stats"]["prs"][period]
        ranking_types[f"issue_{time_period}"] = lambda user, period=time_period: all_contributions[user]["stats"]["issues"][period]
        ranking_types[f"commit_{time_period}"] = lambda user, period=time_period: all_contributions[user]["stats"]["commits"][period]
    
    # Calculate and add all rankings
    for username in contributors:
        all_contributions[username]["rankings"] = {}
        
        for rank_type, key_func in ranking_types.items():
            sorted_users = sorted(contributors, key=key_func, reverse=True)
            all_contributions[username]["rankings"][rank_type] = sorted_users.index(username) + 1
    
    return all_contributions

if __name__ == "__main__":
    # Check if GitHub token is available
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("ERROR: GITHUB_TOKEN environment variable is not set or empty")
        print("Please set the GITHUB_TOKEN environment variable with a valid GitHub token")
        exit(1)
    else:
        # Print first few characters of token for debug (safely)
        masked_token = github_token[:4] + "..." + github_token[-4:] if len(github_token) > 8 else "***"
        print(f"Using GitHub token: {masked_token}")
    
    # Check API rate limits before starting
    rate_limits = check_rate_limit()
    if not rate_limits or rate_limits.get('search', {}).get('remaining', 0) < 5:
        print("WARNING: Low search API rate limits. Some requests may fail.")
        
        # Ask if the user wants to wait until reset
        search_reset = rate_limits.get('search', {}).get('reset', 0)
        if search_reset:
            reset_time = datetime.fromtimestamp(search_reset)
            wait_seconds = max(1, search_reset - datetime.now().timestamp() + 2)
            print(f"You can wait until {reset_time.strftime('%H:%M:%S')} (approximately {int(wait_seconds/60)} minutes) for rate limits to reset.")
            choice = input("Do you want to wait for rate limits to reset? (y/n): ")
            if choice.lower() == 'y':
                print(f"Waiting {int(wait_seconds)} seconds until rate limit reset...")
                time.sleep(wait_seconds)
                print("Continuing after rate limit reset.")
            else:
                print("Continuing with limited rate capacity. Expect partial results.")
    
    # Get all repositories in the organization
    headers = get_github_headers()
    org_repos = fetch_org_repositories()
    
    # Initialize the contributions dictionary
    all_contributions = {}
    processed_repos = []
    
    # Try to load previous progress
    try:
        if os.path.exists("contributions_progress.json"):
            with open("contributions_progress.json", "r") as f:
                progress_data = json.load(f)
                
            print(f"Found saved progress from {progress_data.get('timestamp')}")
            all_contributions = progress_data.get('all_contributions', {})
            processed_repos = progress_data.get('processed_repos', [])
            print(f"Resuming from {len(processed_repos)}/{len(org_repos)} repositories.")
    except Exception as e:
        print(f"Error loading progress: {str(e)}")
    
    # Get current date and calculate time ranges
    now = datetime.now()
    today_date = now.strftime('%Y-%m-%d')
    yesterday_date = (now - timedelta(days=1)).strftime('%Y-%m-%d')
    week_ago_date = (now - timedelta(days=7)).strftime('%Y-%m-%d')
    month_ago_date = (now - timedelta(days=30)).strftime('%Y-%m-%d')
    current_month = now.strftime("%B")
    
    time_ranges = {
        'today': today_date,
        'yesterday': yesterday_date,
        'week_ago': week_ago_date,
        'month_ago': month_ago_date
    }
    
    try:
        # Process each repository separately
        remaining_repos = [repo for repo in org_repos if repo['name'] not in processed_repos]
        
        for repo in remaining_repos:
            repo_name = repo['name']
            repo_owner = repo['owner']
            print(f"\n========== Processing repository: {repo_owner}/{repo_name} ==========")
            
            # 1. Get all contributors for this repository, grouped by contribution type
            commit_contributors = []
            pr_authors = []
            issue_creators = []
            
            # 1.1 Commit contributors
            contributors_url = f"{GITHUB_API_URL}/repos/{repo_owner}/{repo_name}/contributors"
            response = make_github_request(contributors_url, headers, 'core')
            
            if response and response.status_code == 200:
                commit_contributors = [contributor['login'] for contributor in response.json()]
                print(f"Found {len(commit_contributors)} commit contributors in {repo_name}")
            
            # 1.2 PR authors
            pr_url = f"{GITHUB_API_URL}/search/issues?q=repo:{repo_owner}/{repo_name}+type:pr+is:merged"
            pr_response = make_github_request(pr_url, headers, 'search')
            
            if pr_response and pr_response.status_code == 200 and 'items' in pr_response.json():
                pr_authors = [item['user']['login'] for item in pr_response.json()['items'] if item.get('user')]
                print(f"Found {len(pr_authors)} PR authors in {repo_name}")
            
            # 1.3 Issue creators
            issue_url = f"{GITHUB_API_URL}/search/issues?q=repo:{repo_owner}/{repo_name}+type:issue"
            issue_response = make_github_request(issue_url, headers, 'search')
            
            if issue_response and issue_response.status_code == 200 and 'items' in issue_response.json():
                issue_creators = [item['user']['login'] for item in issue_response.json()['items'] if item.get('user')]
                print(f"Found {len(issue_creators)} issue creators in {repo_name}")
            
            # Get the complete set of unique contributors
            all_repo_contributors = set(commit_contributors + pr_authors + issue_creators)
            unique_contributors = list(all_repo_contributors)
            print(f"Processing {len(unique_contributors)} unique contributors for {repo_name}")
            
            # 2. For each contributor in this repo, get their stats
            for username in unique_contributors:
                print(f"\n  Processing user: {username} in {repo_name}")
                
                # Initialize user if not exists
                if username not in all_contributions:
                    all_contributions[username] = {
                        "pr_count": 0,
                        "issues_count": 0,
                        "commits_count": 0,
                        "pr_dates": [],
                        "issue_dates": [],
                        "stats": {
                            "tracking_since": "March 24, 2025",
                            "current_month": current_month,
                            "prs": {
                                "daily": 0,
                                "weekly": 0,
                                "monthly": 0,
                                "all_time": 0,
                                "current_streak": 0,
                                "longest_streak": 0,
                                "avg_per_day": 0
                            },
                            "issues": {
                                "daily": 0,
                                "weekly": 0,
                                "monthly": 0,
                                "all_time": 0,
                                "current_streak": 0,
                                "longest_streak": 0,
                                "avg_per_day": 0
                            },
                            "commits": {
                                "daily": 0,
                                "weekly": 0,
                                "monthly": 0,
                                "all_time": 0,
                                "current_streak": 0,
                                "longest_streak": 0,
                                "avg_per_day": 0
                            }
                        }
                    }
                    print(f"  Initialized new contributor: {username}")
                    
                # Make sure date lists exist
                if "pr_dates" not in all_contributions[username]:
                    all_contributions[username]["pr_dates"] = []
                if "issue_dates" not in all_contributions[username]:
                    all_contributions[username]["issue_dates"] = []
                
                # Only query PR stats if this user has made PRs in this repo
                if username in pr_authors:
                    # 2.1 Get PR stats for this repo
                    pr_query_type = 'type:pr+is:merged'
                    pr_time_field = 'merged'
                    
                    # All-time PRs
                    pr_url = f"{GITHUB_API_URL}/search/issues?q=repo:{repo_owner}/{repo_name}+{pr_query_type}+author:{username}"
                    print(f"  DEBUG - {username} PR URL: {pr_url}")
                    pr_response = make_github_request(pr_url, headers, 'search')
                    
                    if pr_response and pr_response.status_code == 200:
                        pr_count = pr_response.json().get("total_count", 0)
                        all_contributions[username]["pr_count"] += pr_count
                        all_contributions[username]["stats"]["prs"]["all_time"] += pr_count
                        
                        # Collect PR dates for streak calculation
                        if pr_count > 0 and 'items' in pr_response.json():
                            pr_items = pr_response.json()['items']
                            for item in pr_items:
                                if not item.get('pull_request'):
                                    continue
                                    
                                # Get the date
                                merged_date = item.get('merged_at', '')
                                if not merged_date:
                                    merged_date = item.get('closed_at', '')
                                if not merged_date:
                                    merged_date = item.get('created_at', '')
                                
                                if merged_date:
                                    date_str = merged_date.split('T')[0]  # Extract date part
                                    all_contributions[username]["pr_dates"].append(date_str)
                            
                            print(f"  Found {pr_count} PRs for {username} in {repo_name}, collected {len(pr_items)} dates")
                    
                    # Daily PRs
                    pr_daily_url = f"{GITHUB_API_URL}/search/issues?q=repo:{repo_owner}/{repo_name}+{pr_query_type}+author:{username}+{pr_time_field}:>={time_ranges['yesterday']}"
                    print(f"  DEBUG - {username} Daily PR URL: {pr_daily_url}")
                    pr_daily_response = make_github_request(pr_daily_url, headers, 'search')
                    
                    if pr_daily_response and pr_daily_response.status_code == 200:
                        pr_daily_count = pr_daily_response.json().get("total_count", 0)
                        all_contributions[username]["stats"]["prs"]["daily"] += pr_daily_count
                        if pr_daily_count > 0:
                            print(f"  Found {pr_daily_count} daily PRs for {username} in {repo_name}")
                    
                    # Weekly PRs
                    pr_weekly_url = f"{GITHUB_API_URL}/search/issues?q=repo:{repo_owner}/{repo_name}+{pr_query_type}+author:{username}+{pr_time_field}:>={time_ranges['week_ago']}"
                    print(f"  DEBUG - {username} Weekly PR URL: {pr_weekly_url}")
                    pr_weekly_response = make_github_request(pr_weekly_url, headers, 'search')
                    
                    if pr_weekly_response and pr_weekly_response.status_code == 200:
                        pr_weekly_count = pr_weekly_response.json().get("total_count", 0)
                        all_contributions[username]["stats"]["prs"]["weekly"] += pr_weekly_count
                        if pr_weekly_count > 0:
                            print(f"  Found {pr_weekly_count} weekly PRs for {username} in {repo_name}")
                    
                    # Monthly PRs
                    pr_monthly_url = f"{GITHUB_API_URL}/search/issues?q=repo:{repo_owner}/{repo_name}+{pr_query_type}+author:{username}+{pr_time_field}:>={time_ranges['month_ago']}"
                    print(f"  DEBUG - {username} Monthly PR URL: {pr_monthly_url}")
                    pr_monthly_response = make_github_request(pr_monthly_url, headers, 'search')
                    
                    if pr_monthly_response and pr_monthly_response.status_code == 200:
                        pr_monthly_count = pr_monthly_response.json().get("total_count", 0)
                        all_contributions[username]["stats"]["prs"]["monthly"] += pr_monthly_count
                        if pr_monthly_count > 0:
                            print(f"  Found {pr_monthly_count} monthly PRs for {username} in {repo_name}")
                else:
                    print(f"  Skipping PR stats for {username} (no PRs in this repo)")
                    pr_count = 0
                    pr_daily_count = 0
                    pr_weekly_count = 0
                    pr_monthly_count = 0
                
                # Only query issue stats if this user has created issues in this repo
                if username in issue_creators:
                    # 2.2 Get Issue stats for this repo
                    issue_query_type = 'type:issue'
                    issue_time_field = 'created'
                    
                    # All-time Issues
                    issue_url = f"{GITHUB_API_URL}/search/issues?q=repo:{repo_owner}/{repo_name}+{issue_query_type}+author:{username}"
                    print(f"  DEBUG - {username} Issue URL: {issue_url}")
                    issue_response = make_github_request(issue_url, headers, 'search')
                    
                    if issue_response and issue_response.status_code == 200:
                        issue_count = issue_response.json().get("total_count", 0)
                        all_contributions[username]["issues_count"] += issue_count
                        all_contributions[username]["stats"]["issues"]["all_time"] += issue_count
                        
                        # Collect issue dates for streak calculation
                        if issue_count > 0 and 'items' in issue_response.json():
                            issue_items = issue_response.json()['items']
                            for item in issue_items:
                                if item.get('pull_request'):  # Skip PRs
                                    continue
                                    
                                # Get the date
                                created_date = item.get('created_at', '')
                                
                                if created_date:
                                    date_str = created_date.split('T')[0]  # Extract date part
                                    all_contributions[username]["issue_dates"].append(date_str)
                            
                            print(f"  Found {issue_count} issues for {username} in {repo_name}, collected {len(issue_items)} dates")
                    
                    # Daily Issues
                    issue_daily_url = f"{GITHUB_API_URL}/search/issues?q=repo:{repo_owner}/{repo_name}+{issue_query_type}+author:{username}+{issue_time_field}:>={time_ranges['yesterday']}"
                    print(f"  DEBUG - {username} Daily Issue URL: {issue_daily_url}")
                    issue_daily_response = make_github_request(issue_daily_url, headers, 'search')
                    
                    if issue_daily_response and issue_daily_response.status_code == 200:
                        issue_daily_count = issue_daily_response.json().get("total_count", 0)
                        all_contributions[username]["stats"]["issues"]["daily"] += issue_daily_count
                        if issue_daily_count > 0:
                            print(f"  Found {issue_daily_count} daily issues for {username} in {repo_name}")
                    
                    # Weekly Issues
                    issue_weekly_url = f"{GITHUB_API_URL}/search/issues?q=repo:{repo_owner}/{repo_name}+{issue_query_type}+author:{username}+{issue_time_field}:>={time_ranges['week_ago']}"
                    print(f"  DEBUG - {username} Weekly Issue URL: {issue_weekly_url}")
                    issue_weekly_response = make_github_request(issue_weekly_url, headers, 'search')
                    
                    if issue_weekly_response and issue_weekly_response.status_code == 200:
                        issue_weekly_count = issue_weekly_response.json().get("total_count", 0)
                        all_contributions[username]["stats"]["issues"]["weekly"] += issue_weekly_count
                        if issue_weekly_count > 0:
                            print(f"  Found {issue_weekly_count} weekly issues for {username} in {repo_name}")
                    
                    # Monthly Issues
                    issue_monthly_url = f"{GITHUB_API_URL}/search/issues?q=repo:{repo_owner}/{repo_name}+{issue_query_type}+author:{username}+{issue_time_field}:>={time_ranges['month_ago']}"
                    print(f"  DEBUG - {username} Monthly Issue URL: {issue_monthly_url}")
                    issue_monthly_response = make_github_request(issue_monthly_url, headers, 'search')
                    
                    if issue_monthly_response and issue_monthly_response.status_code == 200:
                        issue_monthly_count = issue_monthly_response.json().get("total_count", 0)
                        all_contributions[username]["stats"]["issues"]["monthly"] += issue_monthly_count
                        if issue_monthly_count > 0:
                            print(f"  Found {issue_monthly_count} monthly issues for {username} in {repo_name}")
                else:
                    print(f"  Skipping issue stats for {username} (no issues in this repo)")
                    issue_count = 0
                    issue_daily_count = 0
                    issue_weekly_count = 0
                    issue_monthly_count = 0
                
                # Only query commit stats if this user has made commits in this repo
                if username in commit_contributors:
                    # 2.3 Get Commit stats for this repo
                    commit_url = f"{GITHUB_API_URL}/search/commits?q=repo:{repo_owner}/{repo_name}+author:{username}"
                    print(f"  DEBUG - {username} Commit URL: {commit_url}")
                    commit_response = make_github_request(commit_url, headers, 'search')
                    
                    if commit_response and commit_response.status_code == 200:
                        commit_count = commit_response.json().get("total_count", 0)
                        all_contributions[username]["commits_count"] += commit_count
                        all_contributions[username]["stats"]["commits"]["all_time"] += commit_count
                        if commit_count > 0:
                            print(f"  Found {commit_count} commits for {username} in {repo_name}")
                else:
                    print(f"  Skipping commit stats for {username} (no commits in this repo)")
                    commit_count = 0
                
                # Print summary for this user in this repo
                print(f"\n  Summary for {username} in {repo_name}:")
                stats_found = False
                
                if username in pr_authors:
                    stats_found = True
                    print(f"    PRs: {pr_count} (Daily: {pr_daily_count if 'pr_daily_count' in locals() else 0}, Weekly: {pr_weekly_count if 'pr_weekly_count' in locals() else 0}, Monthly: {pr_monthly_count if 'pr_monthly_count' in locals() else 0})")
                
                if username in issue_creators:
                    stats_found = True
                    print(f"    Issues: {issue_count if 'issue_count' in locals() else 0} (Daily: {issue_daily_count if 'issue_daily_count' in locals() else 0}, Weekly: {issue_weekly_count if 'issue_weekly_count' in locals() else 0}, Monthly: {issue_monthly_count if 'issue_monthly_count' in locals() else 0})")
                
                if username in commit_contributors:
                    stats_found = True
                    print(f"    Commits: {commit_count if 'commit_count' in locals() else 0}")
                
                if not stats_found:
                    print("    No contributions found (user may have been removed from items during processing)")
                
                # Check if we're close to rate limits after each user
                if not wait_for_rate_limit('search'):
                    print("Rate limits reached. Saving progress and exiting.")
                    break
            
            # Print summary for this repo
            print(f"\n========== Summary for {repo_owner}/{repo_name} ==========")
            print(f"Processed {len(unique_contributors)} contributors")
            
            # Mark this repo as processed
            processed_repos.append(repo_name)
            
            # Save progress after each repo
            progress_data = {
                'all_contributions': all_contributions,
                'processed_repos': processed_repos,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open("contributions_progress.json", "w") as f:
                json.dump(progress_data, f, indent=2)
            
            print(f"Progress saved: {len(processed_repos)}/{len(org_repos)} repositories processed ({len(processed_repos)/len(org_repos)*100:.1f}%)")
            print(f"Repositories remaining: {len(org_repos) - len(processed_repos)}")
            
    except KeyboardInterrupt:
        print("\nOperation interrupted by user. Saving progress...")
    finally:
        # Check API rate limits after processing
        check_rate_limit()
        
        # Calculate streaks for all users from collected dates
        print("\n========== Calculating streaks for all contributors ==========")
        
        for username in all_contributions:
            print(f"Calculating streaks for {username}...")
            
            # Calculate PR streaks from collected dates
            pr_dates = all_contributions[username].get("pr_dates", [])
            if pr_dates:
                print(f"  Using {len(pr_dates)} collected PR dates for streak calculation")
                pr_streaks = calculate_streaks_from_dates(pr_dates)
            else:
                print(f"  No PR dates collected, setting streak to 0")
                pr_streaks = {"current_streak": 0, "longest_streak": 0}
            
            all_contributions[username]["stats"]["prs"]["current_streak"] = pr_streaks["current_streak"]
            all_contributions[username]["stats"]["prs"]["longest_streak"] = pr_streaks["longest_streak"]
            
            # Calculate Issue streaks from collected dates
            issue_dates = all_contributions[username].get("issue_dates", [])
            if issue_dates:
                print(f"  Using {len(issue_dates)} collected issue dates for streak calculation")
                issue_streaks = calculate_streaks_from_dates(issue_dates)
            else:
                print(f"  No issue dates collected, setting streak to 0")
                issue_streaks = {"current_streak": 0, "longest_streak": 0}
            
            all_contributions[username]["stats"]["issues"]["current_streak"] = issue_streaks["current_streak"]
            all_contributions[username]["stats"]["issues"]["longest_streak"] = issue_streaks["longest_streak"]
            
            # Calculate average per day for current month
            days_this_month = min(now.day, 30)  # Use actual days passed this month, max 30
            all_contributions[username]["stats"]["prs"]["avg_per_day"] = round(
                all_contributions[username]["stats"]["prs"]["monthly"] / max(days_this_month, 1), 1
            )
            all_contributions[username]["stats"]["issues"]["avg_per_day"] = round(
                all_contributions[username]["stats"]["issues"]["monthly"] / max(days_this_month, 1), 1
            )
            all_contributions[username]["stats"]["commits"]["avg_per_day"] = round(
                all_contributions[username]["stats"]["commits"]["monthly"] / max(days_this_month, 1), 1
            )
            
            # Print streak and average info
            print(f"  PR Streaks: Current {pr_streaks['current_streak']}, Longest {pr_streaks['longest_streak']}")
            print(f"  Issue Streaks: Current {issue_streaks['current_streak']}, Longest {issue_streaks['longest_streak']}")
            print(f"  Averages: PRs {all_contributions[username]['stats']['prs']['avg_per_day']}/day, Issues {all_contributions[username]['stats']['issues']['avg_per_day']}/day, Commits {all_contributions[username]['stats']['commits']['avg_per_day']}/day")
        
        print("\n========== Calculating rankings for all contributors ==========")
        # Calculate and add rankings for all contributors
        all_contributions = calculate_rankings(all_contributions)
        
        # Save to a JSON file for the Discord bot to use
        with open("contributions.json", "w") as f:
            json.dump(all_contributions, f, indent=2)
        
        print("\n========== Process Complete ==========")
        print(f"Found {len(all_contributions)} total contributors across all repositories")
        print("Contribution data saved to contributions.json")
        
        # If we have processed all repos, remove the progress file
        if len(processed_repos) == len(org_repos):
            if os.path.exists("contributions_progress.json"):
                os.remove("contributions_progress.json")
                print("All repositories processed. Progress file removed.")
        else:
            remaining = len(org_repos) - len(processed_repos)
            print(f"Partial completion: {len(processed_repos)}/{len(org_repos)} repositories processed. {remaining} remaining.")
            print("Run the script again later to continue processing.")
