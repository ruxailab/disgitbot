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

def get_time_based_metrics(username, contribution_type, headers, time_ranges):
    """
    Generic function to fetch time-based metrics for any contribution type across all organization repos.
    
    Args:
        username: GitHub username
        contribution_type: 'pr', 'issue', or 'commit'
        headers: API request headers
        time_ranges: Dictionary with date ranges
    
    Returns:
        Dictionary with daily, weekly, monthly, and all-time counts
    """
    # Set up query parameters based on contribution type
    if contribution_type == 'pr':
        query_type = 'type:pr+is:merged'
        time_field = 'merged'
    elif contribution_type == 'issue':
        query_type = 'type:issue'
        time_field = 'created'
    elif contribution_type == 'commit':
        # Get list of organization repositories
        org_repos = fetch_org_repositories()
        
        # All-time commits across all repos
        all_time = 0
        for repo in org_repos:
            commits_url = f"{GITHUB_API_URL}/search/commits?q=repo:{repo['owner']}/{repo['name']}+author:{username}"
            print(f"DEBUG - Commit URL for {repo['name']}: {commits_url}")
            commits_response = make_github_request(commits_url, headers, 'search')
            
            if commits_response and commits_response.status_code == 200:
                all_time += commits_response.json().get("total_count", 0)
        
        # GitHub API limitations make time-based commit queries more complex
        # For simplicity, we'll use the all-time count for each time range
        return {
            'daily': 0,
            'weekly': 0,
            'monthly': 0,
            'all_time': all_time
        }
    
    # Get list of organization repositories
    org_repos = fetch_org_repositories()
    
    # Initialize counters
    all_time = 0
    daily = 0
    weekly = 0
    monthly = 0
    
    # Query each repository and sum the results
    for repo in org_repos:
        # Get all-time count
        all_time_url = f"{GITHUB_API_URL}/search/issues?q=repo:{repo['owner']}/{repo['name']}+{query_type}+author:{username}"
        print(f"DEBUG - All-time {contribution_type} URL for {repo['name']}: {all_time_url}")
        all_time_response = make_github_request(all_time_url, headers, 'search')
        
        if all_time_response and all_time_response.status_code == 200:
            all_time += all_time_response.json().get("total_count", 0)
        
        # Get daily count - Use 24 hours ago instead of today's date
        daily_url = f"{GITHUB_API_URL}/search/issues?q=repo:{repo['owner']}/{repo['name']}+{query_type}+author:{username}+{time_field}:>={time_ranges['yesterday']}"
        print(f"DEBUG - Daily {contribution_type} URL for {repo['name']}: {daily_url}")
        daily_response = make_github_request(daily_url, headers, 'search')
        
        if daily_response and daily_response.status_code == 200:
            daily += daily_response.json().get("total_count", 0)
        
        # Get weekly count
        weekly_url = f"{GITHUB_API_URL}/search/issues?q=repo:{repo['owner']}/{repo['name']}+{query_type}+author:{username}+{time_field}:>={time_ranges['week_ago']}"
        print(f"DEBUG - Weekly {contribution_type} URL for {repo['name']}: {weekly_url}")
        weekly_response = make_github_request(weekly_url, headers, 'search')
        
        if weekly_response and weekly_response.status_code == 200:
            weekly += weekly_response.json().get("total_count", 0)
        
        # Get monthly count
        monthly_url = f"{GITHUB_API_URL}/search/issues?q=repo:{repo['owner']}/{repo['name']}+{query_type}+author:{username}+{time_field}:>={time_ranges['month_ago']}"
        print(f"DEBUG - Monthly {contribution_type} URL for {repo['name']}: {monthly_url}")
        monthly_response = make_github_request(monthly_url, headers, 'search')
        
        if monthly_response and monthly_response.status_code == 200:
            monthly += monthly_response.json().get("total_count", 0)
    
    return {
        'daily': daily,
        'weekly': weekly,
        'monthly': monthly,
        'all_time': all_time
    }

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

def get_contributions(username):
    """
    Fetch comprehensive contribution data for a user.
    This includes all-time counts as well as time-based metrics for PRs, issues, and commits.
    """
    headers = get_github_headers()
    
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
    
    print(f"DEBUG - Time ranges: {time_ranges}")
    
    # Get metrics for each contribution type
    pr_metrics = get_time_based_metrics(username, 'pr', headers, time_ranges)
    issue_metrics = get_time_based_metrics(username, 'issue', headers, time_ranges)
    commit_metrics = get_time_based_metrics(username, 'commit', headers, time_ranges)
    
    # Calculate streaks for each contribution type
    pr_streaks = calculate_streaks(username, 'pr', headers, month_ago_date)
    issue_streaks = calculate_streaks(username, 'issue', headers, month_ago_date)
    commit_streaks = calculate_streaks(username, 'commit', headers, month_ago_date)
    
    # Calculate average per day for current month
    days_this_month = min(now.day, 30)  # Use actual days passed this month, max 30
    pr_avg_per_day = round(pr_metrics['monthly'] / max(days_this_month, 1), 1)
    issue_avg_per_day = round(issue_metrics['monthly'] / max(days_this_month, 1), 1)
    commit_avg_per_day = round(commit_metrics['monthly'] / max(days_this_month, 1), 1)
    
    # Build the complete contribution data structure
    return {
        "pr_count": pr_metrics['all_time'],
        "issues_count": issue_metrics['all_time'],
        "commits_count": commit_metrics['all_time'],
        "stats": {
            "tracking_since": "March 24, 2025",  # Example date - adjust as needed
            "current_month": current_month,
            "prs": {
                "daily": pr_metrics['daily'],
                "weekly": pr_metrics['weekly'],
                "monthly": pr_metrics['monthly'],
                "all_time": pr_metrics['all_time'],
                "current_streak": pr_streaks['current_streak'],
                "longest_streak": pr_streaks['longest_streak'],
                "avg_per_day": pr_avg_per_day
            },
            "issues": {
                "daily": issue_metrics['daily'],
                "weekly": issue_metrics['weekly'],
                "monthly": issue_metrics['monthly'],
                "all_time": issue_metrics['all_time'],
                "current_streak": issue_streaks['current_streak'],
                "longest_streak": issue_streaks['longest_streak'],
                "avg_per_day": issue_avg_per_day
            },
            "commits": {
                "daily": commit_metrics['daily'],
                "weekly": commit_metrics['weekly'],
                "monthly": commit_metrics['monthly'],
                "all_time": commit_metrics['all_time'],
                "current_streak": commit_streaks['current_streak'],
                "longest_streak": commit_streaks['longest_streak'],
                "avg_per_day": commit_avg_per_day
            }
        }
    }

def fetch_all_contributors():
    """Fetch all contributors across all organization repositories."""
    headers = get_github_headers()
    all_contributors = set()
    
    # Get all repos in the organization
    org_repos = fetch_org_repositories()
    
    # Fetch contributors for each repo
    for repo in org_repos:
        contributors_url = f"{GITHUB_API_URL}/repos/{repo['owner']}/{repo['name']}/contributors"
        response = make_github_request(contributors_url, headers, 'core')
        
        if response and response.status_code == 200:
            repo_contributors = [contributor['login'] for contributor in response.json()]
            all_contributors.update(repo_contributors)
    
    return list(all_contributors)

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

def save_progress(all_contributions, contributors_processed, all_contributors):
    """Save the current progress to a temporary file."""
    progress_data = {
        'all_contributions': all_contributions,
        'contributors_processed': contributors_processed,
        'all_contributors': all_contributors,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    with open("contributions_progress.json", "w") as f:
        json.dump(progress_data, f, indent=2)
    
    print(f"Progress saved: {len(contributors_processed)}/{len(all_contributors)} contributors processed.")

def load_progress():
    """Load progress from a temporary file if it exists."""
    try:
        if os.path.exists("contributions_progress.json"):
            with open("contributions_progress.json", "r") as f:
                progress_data = json.load(f)
                
            print(f"Found saved progress from {progress_data.get('timestamp')}")
            print(f"Resuming from {len(progress_data.get('contributors_processed', []))}/{len(progress_data.get('all_contributors', []))} contributors.")
            
            return (
                progress_data.get('all_contributions', {}),
                progress_data.get('contributors_processed', []),
                progress_data.get('all_contributors', [])
            )
    except Exception as e:
        print(f"Error loading progress: {str(e)}")
    
    return {}, [], []

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
    
    # Try to load previous progress
    all_contributions, contributors_processed, all_contributors = load_progress()
    
    # If no saved progress or contributors list is empty, fetch all contributors
    if not all_contributors:
        all_contributors = fetch_all_contributors()
        
    if not all_contributors:
        print("ERROR: No contributors found. Check GitHub API access and repository settings.")
        exit(1)
    
    print(f"Found {len(all_contributors)} contributors.")
    print("Fetching contribution data...")
    
    try:
        # Process only contributors that haven't been processed yet
        remaining_contributors = [c for c in all_contributors if c not in contributors_processed]
        
        for username in remaining_contributors:
            try:
                print(f"\nProcessing user: {username}")
                contributions = get_contributions(username)
                all_contributions[username] = contributions
                contributors_processed.append(username)
                
                print(f"User: {username}")
                print(f"PRs: {contributions['pr_count']} (Daily: {contributions['stats']['prs']['daily']}, Weekly: {contributions['stats']['prs']['weekly']}, Monthly: {contributions['stats']['prs']['monthly']})")
                print(f"PR Streak: Current {contributions['stats']['prs']['current_streak']}, Longest: {contributions['stats']['prs']['longest_streak']}")
                print(f"Issues: {contributions['issues_count']} (Daily: {contributions['stats']['issues']['daily']}, Weekly: {contributions['stats']['issues']['weekly']}, Monthly: {contributions['stats']['issues']['monthly']})")
                print(f"Issue Streak: Current {contributions['stats']['issues']['current_streak']}, Longest: {contributions['stats']['issues']['longest_streak']}")
                print(f"Commits: {contributions['commits_count']} (Daily: {contributions['stats']['commits']['daily']}, Weekly: {contributions['stats']['commits']['weekly']}, Monthly: {contributions['stats']['commits']['monthly']})")
                
                # Save progress after each contributor
                save_progress(all_contributions, contributors_processed, all_contributors)
                
                # Check if we're close to rate limits after each contributor
                if not wait_for_rate_limit('search'):
                    print("Rate limits reached. Saving progress and exiting.")
                    break
                    
            except Exception as e:
                print(f"ERROR processing user {username}: {str(e)}")
                import traceback
                traceback.print_exc()
    except KeyboardInterrupt:
        print("\nOperation interrupted by user. Saving progress...")
    finally:
        # Check API rate limits after processing
        check_rate_limit()
        
        # Calculate and add rankings for the processed contributors
        all_contributions = calculate_rankings(all_contributions)
        
        # Save to a JSON file for the Discord bot to use
        with open("contributions.json", "w") as f:
            json.dump(all_contributions, f, indent=2)
        
        print("Contribution data saved to contributions.json")
        
        # If we have processed all contributors, remove the progress file
        if len(contributors_processed) == len(all_contributors):
            if os.path.exists("contributions_progress.json"):
                os.remove("contributions_progress.json")
                print("All contributors processed. Progress file removed.")
        else:
            remaining = len(all_contributors) - len(contributors_processed)
            print(f"Partial completion: {len(contributors_processed)}/{len(all_contributors)} contributors processed. {remaining} remaining.")
            print("Run the script again later to continue processing.")
