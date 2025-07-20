"""
Analytics Processing Module

Handles creation of analytics data and hall of fame from contribution data.
"""

import time

class AnalyticsProcessor:
    """Processes contribution data into analytics and hall of fame data."""
    
    def create_hall_of_fame_data(self, all_contributions):
        """Create hall of fame data from all contributors."""
        print("Creating hall of fame data...")
        
        if not all_contributions:
            return {}
        
        contributors = list(all_contributions.keys())
        categories = self._create_hall_of_fame_categories(all_contributions)
        
        hall_of_fame = {
            'last_updated': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
        }
        
        for category, time_periods in categories.items():
            category_data = {}
            
            for time_period, sort_func in time_periods.items():
                top_3 = self._get_top_contributors(contributors, sort_func, 3)
                category_data[time_period] = top_3
            
            hall_of_fame[category] = category_data
        
        return hall_of_fame
    
    def _create_hall_of_fame_categories(self, all_contributions):
        """Create category functions for hall of fame."""
        return {
            'pr': {
                'all_time': lambda user: all_contributions[user].get('pr_count', 0),
                'monthly': lambda user: all_contributions[user].get('stats', {}).get('prs', {}).get('monthly', 0),
                'weekly': lambda user: all_contributions[user].get('stats', {}).get('prs', {}).get('weekly', 0),
                'daily': lambda user: all_contributions[user].get('stats', {}).get('prs', {}).get('daily', 0)
            },
            'issue': {
                'all_time': lambda user: all_contributions[user].get('issues_count', 0),
                'monthly': lambda user: all_contributions[user].get('stats', {}).get('issues', {}).get('monthly', 0),
                'weekly': lambda user: all_contributions[user].get('stats', {}).get('issues', {}).get('weekly', 0),
                'daily': lambda user: all_contributions[user].get('stats', {}).get('issues', {}).get('daily', 0)
            },
            'commit': {
                'all_time': lambda user: all_contributions[user].get('commits_count', 0),
                'monthly': lambda user: all_contributions[user].get('stats', {}).get('commits', {}).get('monthly', 0),
                'weekly': lambda user: all_contributions[user].get('stats', {}).get('commits', {}).get('weekly', 0),
                'daily': lambda user: all_contributions[user].get('stats', {}).get('commits', {}).get('daily', 0)
            }
        }
    
    def _get_top_contributors(self, contributors, sort_func, count):
        """Get top N contributors for a given metric."""
        sorted_contributors = sorted(contributors, key=sort_func, reverse=True)
        top_contributors = []
        
        for i, username in enumerate(sorted_contributors[:count]):
            value = sort_func(username)
            if value > 0:
                top_contributors.append({
                    'username': username,
                    'value': value,
                    'rank': i + 1
                })
        
        return top_contributors
    
    def create_analytics_data(self, all_contributions):
        """Create analytics data for visualization from all contributors."""
        print("Creating analytics data for visualization...")
        
        if not all_contributions:
            return {}
        
        contributors = list(all_contributions.keys())
        
        return {
            'top_contributors_prs': self._get_top_contributors_by_prs(contributors, all_contributions),
            'top_contributors_issues': self._get_top_contributors_by_issues(contributors, all_contributions),
            'top_contributors_commits': self._get_top_contributors_by_commits(contributors, all_contributions),
            'activity_comparison': self._get_activity_comparison(contributors, all_contributions),
            'activity_trends': self._calculate_activity_trends(contributors, all_contributions)
        }
    
    def _get_top_contributors_by_prs(self, contributors, all_contributions):
        """Get top 10 contributors by PR count."""
        top_contributors = sorted(
            contributors,
            key=lambda user: all_contributions[user].get('pr_count', 0),
            reverse=True
        )[:10]
        
        return [
            {
                'username': user,
                'pr_count': all_contributions[user].get('pr_count', 0)
            }
            for user in top_contributors
            if all_contributions[user].get('pr_count', 0) > 0
        ]
    
    def _get_top_contributors_by_issues(self, contributors, all_contributions):
        """Get top 10 contributors by issue count."""
        top_contributors = sorted(
            contributors,
            key=lambda user: all_contributions[user].get('issues_count', 0),
            reverse=True
        )[:10]
        
        return [
            {
                'username': user,
                'issues_count': all_contributions[user].get('issues_count', 0)
            }
            for user in top_contributors
            if all_contributions[user].get('issues_count', 0) > 0
        ]
    
    def _get_top_contributors_by_commits(self, contributors, all_contributions):
        """Get top 10 contributors by commit count."""
        top_contributors = sorted(
            contributors,
            key=lambda user: all_contributions[user].get('commits_count', 0),
            reverse=True
        )[:10]
        
        return [
            {
                'username': user,
                'commits_count': all_contributions[user].get('commits_count', 0)
            }
            for user in top_contributors
            if all_contributions[user].get('commits_count', 0) > 0
        ]
    
    def _get_activity_comparison(self, contributors, all_contributions):
        """Get top 5 contributors by total activity."""
        top_5_by_total_activity = sorted(
            contributors,
            key=lambda user: (
                all_contributions[user].get('pr_count', 0) +
                all_contributions[user].get('issues_count', 0) +
                all_contributions[user].get('commits_count', 0)
            ),
            reverse=True
        )[:5]
        
        return [
            {
                'username': user,
                'pr_count': all_contributions[user].get('pr_count', 0),
                'issues_count': all_contributions[user].get('issues_count', 0),
                'commits_count': all_contributions[user].get('commits_count', 0)
            }
            for user in top_5_by_total_activity
        ]
    
    def _calculate_activity_trends(self, contributors, all_contributions):
        """Calculate aggregated activity trends."""
        trends = {
            'daily': {'prs': 0, 'issues': 0, 'commits': 0},
            'weekly': {'prs': 0, 'issues': 0, 'commits': 0},
            'monthly': {'prs': 0, 'issues': 0, 'commits': 0}
        }
        
        for user in contributors:
            stats = all_contributions[user].get('stats', {})
            
            for period in ['daily', 'weekly', 'monthly']:
                trends[period]['prs'] += stats.get('prs', {}).get(period, 0)
                trends[period]['issues'] += stats.get('issues', {}).get(period, 0)
                trends[period]['commits'] += stats.get('commits', {}).get(period, 0)
        
        return trends 