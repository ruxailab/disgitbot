"""
Contribution Processing Module

Handles processing of raw GitHub data into structured contribution data.
"""

from datetime import datetime, timedelta

class ContributionProcessor:
    """Processes raw GitHub data into structured contribution data."""
    
    def __init__(self):
        self.now = datetime.now()
        self.today_date = self.now.strftime('%Y-%m-%d')
        self.yesterday_date = (self.now - timedelta(days=1)).strftime('%Y-%m-%d')
        self.week_ago_date = (self.now - timedelta(days=7)).strftime('%Y-%m-%d')
        self.month_ago_date = (self.now - timedelta(days=30)).strftime('%Y-%m-%d')
        self.current_month = self.now.strftime("%B")
    
    def process_raw_data(self, raw_data):
        """Process raw GitHub data into structured contribution data."""
        print("Processing raw data into contribution structures...")
        
        all_contributions = {}
        repositories = raw_data.get('repositories', {})
        
        for repo_name, repo_data in repositories.items():
            print(f"Processing repository: {repo_name}")
            self._process_repository(repo_data, all_contributions)
        
        print(f"Processed {len(all_contributions)} contributors")
        return all_contributions
    
    def _process_repository(self, repo_data, all_contributions):
        """Process a single repository's data."""
        contributors = repo_data.get('contributors', [])
        pull_requests = repo_data.get('pull_requests', {}).get('items', [])
        issues = repo_data.get('issues', {}).get('items', [])
        commits = repo_data.get('commits_search', {}).get('items', [])
        
        all_usernames = self._extract_usernames(contributors, pull_requests, issues, commits)
        
        for username in all_usernames:
            if not username:
                continue
            
            self._initialize_user_if_needed(username, all_contributions)
            self._process_user_contributions(username, pull_requests, issues, commits, all_contributions)
    
    def _extract_usernames(self, contributors, pull_requests, issues, commits):
        """Extract unique usernames from all data sources."""
        all_usernames = set()
        
        for contributor in contributors:
            all_usernames.add(contributor.get('login'))
        
        for pr in pull_requests:
            if pr.get('user', {}).get('login'):
                all_usernames.add(pr['user']['login'])
        
        for issue in issues:
            if issue.get('user', {}).get('login') and not issue.get('pull_request'):
                all_usernames.add(issue['user']['login'])
        
        for commit in commits:
            if commit.get('author', {}).get('login'):
                all_usernames.add(commit['author']['login'])
        
        return all_usernames
    
    def _initialize_user_if_needed(self, username, all_contributions):
        """Initialize user data structure if it doesn't exist."""
        if username not in all_contributions:
            all_contributions[username] = {
                "pr_count": 0,
                "issues_count": 0,
                "commits_count": 0,
                "pr_dates": [],
                "issue_dates": [],
                "stats": {
                    "current_month": self.current_month,
                    "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
                    "prs": self._create_stat_structure(),
                    "issues": self._create_stat_structure(),
                    "commits": self._create_stat_structure()
                }
            }
    
    def _create_stat_structure(self):
        """Create standard statistics structure."""
        return {
            "daily": 0,
            "weekly": 0,
            "monthly": 0,
            "all_time": 0,
            "current_streak": 0,
            "longest_streak": 0,
            "avg_per_day": 0
        }
    
    def _process_user_contributions(self, username, pull_requests, issues, commits, all_contributions):
        """Process all contribution types for a user."""
        self._process_user_prs(username, pull_requests, all_contributions)
        self._process_user_issues(username, issues, all_contributions)
        self._process_user_commits(username, commits, all_contributions)
    
    def _process_user_prs(self, username, pull_requests, all_contributions):
        """Process pull requests for a user."""
        user_prs = [pr for pr in pull_requests if pr.get('user', {}).get('login') == username]
        all_contributions[username]["pr_count"] += len(user_prs)
        all_contributions[username]["stats"]["prs"]["all_time"] += len(user_prs)
        
        for pr in user_prs:
            merged_date = pr.get('merged_at') or pr.get('closed_at') or pr.get('created_at')
            if merged_date:
                date_str = merged_date.split('T')[0]
                all_contributions[username]["pr_dates"].append(date_str)
                self._update_time_based_stats(date_str, all_contributions[username]["stats"]["prs"])
    
    def _process_user_issues(self, username, issues, all_contributions):
        """Process issues for a user."""
        user_issues = [issue for issue in issues if issue.get('user', {}).get('login') == username and not issue.get('pull_request')]
        all_contributions[username]["issues_count"] += len(user_issues)
        all_contributions[username]["stats"]["issues"]["all_time"] += len(user_issues)
        
        for issue in user_issues:
            created_date = issue.get('created_at')
            if created_date:
                date_str = created_date.split('T')[0]
                all_contributions[username]["issue_dates"].append(date_str)
                self._update_time_based_stats(date_str, all_contributions[username]["stats"]["issues"])
    
    def _process_user_commits(self, username, commits, all_contributions):
        """Process commits for a user."""
        user_commits = [commit for commit in commits if commit.get('author', {}).get('login') == username]
        all_contributions[username]["commits_count"] += len(user_commits)
        all_contributions[username]["stats"]["commits"]["all_time"] += len(user_commits)
        
        for commit in user_commits:
            commit_date = commit.get('commit', {}).get('author', {}).get('date')
            if commit_date:
                date_str = commit_date.split('T')[0]
                self._update_time_based_stats(date_str, all_contributions[username]["stats"]["commits"])
    
    def _update_time_based_stats(self, date_str, stats):
        """Update daily, weekly, monthly stats based on date."""
        if date_str >= self.yesterday_date:
            stats["daily"] += 1
        if date_str >= self.week_ago_date:
            stats["weekly"] += 1
        if date_str >= self.month_ago_date:
            stats["monthly"] += 1
    
    def calculate_rankings(self, all_contributions):
        """Calculate rankings for each contributor across different metrics."""
        print("Calculating rankings for all contributors...")
        
        contributors = list(all_contributions.keys())
        if not contributors:
            return all_contributions
        
        ranking_types = self._create_ranking_functions(all_contributions)
        
        for username in contributors:
            all_contributions[username]["rankings"] = {}
            
            for rank_type, key_func in ranking_types.items():
                try:
                    sorted_users = sorted(contributors, key=key_func, reverse=True)
                    all_contributions[username]["rankings"][rank_type] = sorted_users.index(username) + 1
                except Exception as e:
                    print(f"Error calculating {rank_type} ranking for {username}: {e}")
                    all_contributions[username]["rankings"][rank_type] = len(contributors)
        
        return all_contributions
    
    def _create_ranking_functions(self, all_contributions):
        """Create ranking functions for different metrics."""
        ranking_types = {
            "pr": lambda user: all_contributions[user]["pr_count"],
            "issue": lambda user: all_contributions[user]["issues_count"],
            "commit": lambda user: all_contributions[user]["commits_count"]
        }
        
        for time_period in ["daily", "weekly", "monthly", "all_time"]:
            ranking_types[f"pr_{time_period}"] = lambda user, period=time_period: all_contributions[user]["stats"]["prs"][period]
            ranking_types[f"issue_{time_period}"] = lambda user, period=time_period: all_contributions[user]["stats"]["issues"][period]
            ranking_types[f"commit_{time_period}"] = lambda user, period=time_period: all_contributions[user]["stats"]["commits"][period]
        
        return ranking_types
    
    def calculate_streaks_and_averages(self, all_contributions):
        """Calculate streaks and averages for all contributors."""
        print("Calculating streaks and averages...")
        
        days_this_month = min(self.now.day, 30)
        
        for username in all_contributions:
            self._calculate_user_streaks(username, all_contributions)
            self._calculate_user_averages(username, all_contributions, days_this_month)
        
        return all_contributions
    
    def _calculate_user_streaks(self, username, all_contributions):
        """Calculate streaks for a single user."""
        pr_dates = all_contributions[username].get("pr_dates", [])
        issue_dates = all_contributions[username].get("issue_dates", [])
        
        pr_streaks = self._calculate_streaks_from_dates(pr_dates)
        issue_streaks = self._calculate_streaks_from_dates(issue_dates)
        
        all_contributions[username]["stats"]["prs"]["current_streak"] = pr_streaks["current_streak"]
        all_contributions[username]["stats"]["prs"]["longest_streak"] = pr_streaks["longest_streak"]
        all_contributions[username]["stats"]["issues"]["current_streak"] = issue_streaks["current_streak"]
        all_contributions[username]["stats"]["issues"]["longest_streak"] = issue_streaks["longest_streak"]
    
    def _calculate_user_averages(self, username, all_contributions, days_this_month):
        """Calculate averages for a single user."""
        stats = all_contributions[username]["stats"]
        
        stats["prs"]["avg_per_day"] = round(stats["prs"]["monthly"] / max(days_this_month, 1), 1)
        stats["issues"]["avg_per_day"] = round(stats["issues"]["monthly"] / max(days_this_month, 1), 1)
        stats["commits"]["avg_per_day"] = round(stats["commits"]["monthly"] / max(days_this_month, 1), 1)
    
    def _calculate_streaks_from_dates(self, dates):
        """Calculate streaks from a list of contribution dates."""
        if not dates:
            return {'current_streak': 0, 'longest_streak': 0}
        
        unique_dates = list(set(dates))
        unique_dates.sort(reverse=True)
        
        current_streak = self._calculate_current_streak(unique_dates)
        longest_streak = self._calculate_longest_streak(unique_dates)
        
        return {'current_streak': current_streak, 'longest_streak': longest_streak}
    
    def _calculate_current_streak(self, unique_dates):
        """Calculate current streak from sorted dates."""
        last_date = datetime.strptime(unique_dates[0], '%Y-%m-%d')
        current_streak = 1
        
        for i in range(1, len(unique_dates)):
            date = datetime.strptime(unique_dates[i], '%Y-%m-%d')
            if (last_date - date).days <= 1:
                current_streak += 1
            else:
                break
            last_date = date
        
        return current_streak
    
    def _calculate_longest_streak(self, unique_dates):
        """Calculate longest streak from sorted dates."""
        unique_dates.sort()
        
        streaks = []
        current_group = [unique_dates[0]]
        
        for i in range(1, len(unique_dates)):
            prev_date = datetime.strptime(current_group[-1], '%Y-%m-%d')
            curr_date = datetime.strptime(unique_dates[i], '%Y-%m-%d')
            
            if (curr_date - prev_date).days <= 1:
                current_group.append(unique_dates[i])
            else:
                streaks.append(current_group)
                current_group = [unique_dates[i]]
        
        if current_group:
            streaks.append(current_group)
        
        return max([len(streak) for streak in streaks]) if streaks else 0 