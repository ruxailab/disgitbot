"""
Analytics Processing Functions

Simple functions for creating analytics data and hall of fame from contribution data.
"""

import time

def create_hall_of_fame_data(all_contributions):
    """Create hall of fame data from all contributors."""
    print("Creating hall of fame data...")
    
    if not all_contributions:
        return {}
    
    time_periods = ['all_time', 'monthly', 'weekly', 'daily']
    leaderboard_size = 10
    contributors = list(all_contributions.keys())
    
    def create_leaderboard_for_period(contrib_type, period):
        """Create a leaderboard for a specific contribution type and time period."""
        sorted_contributors = sorted(
            contributors,
            key=lambda x: all_contributions[x]['stats'][contrib_type][period],
            reverse=True
        )[:leaderboard_size]
        
        return [
            {
                'username': username,
                'count': all_contributions[username]['stats'][contrib_type][period]
            }
            for username in sorted_contributors
        ]
    
    return {
        'last_updated': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
        **{
            contrib_type: {
                period: create_leaderboard_for_period(contrib_type, period)
                for period in time_periods
            }
            for contrib_type in ['pr', 'issue', 'commit']
        }
    }

def create_analytics_data(all_contributions):
    """Create analytics data for visualization."""
    print("Creating analytics data for visualization...")
    
    if not all_contributions:
        return {}
    
    # Basic statistics
    total_contributors = len(all_contributions)
    total_prs = sum(contrib.get('pr_count', 0) for contrib in all_contributions.values())
    total_issues = sum(contrib.get('issues_count', 0) for contrib in all_contributions.values())
    total_commits = sum(contrib.get('commits_count', 0) for contrib in all_contributions.values())
    
    # Active contributors (those with recent activity)
    active_contributors = len([
        c for c in all_contributions.values()
        if c.get('week_activity', 0) > 0
    ])
    
    # Convert tuples to dictionaries for Firestore compatibility
    top_prs = sorted(
        all_contributions.items(),
        key=lambda x: x[1].get('pr_count', 0),
        reverse=True
    )[:5]
    
    top_issues = sorted(
        all_contributions.items(),
        key=lambda x: x[1].get('issues_count', 0),
        reverse=True
    )[:5]
    
    top_commits = sorted(
        all_contributions.items(),
        key=lambda x: x[1].get('commits_count', 0),
        reverse=True
    )[:5]
    
    return {
        'summary': {
            'total_contributors': total_contributors,
            'active_contributors': active_contributors,
            'total_prs': total_prs,
            'total_issues': total_issues,
            'total_commits': total_commits
        },
        'top_contributors_prs': [
            {
                'username': username,
                'pr_count': data.get('pr_count', 0),
                'total_activity': data.get('total_activity', 0)
            }
            for username, data in top_prs
        ],
        'top_contributors_issues': [
            {
                'username': username,
                'issues_count': data.get('issues_count', 0),
                'total_activity': data.get('total_activity', 0)
            }
            for username, data in top_issues
        ],
        'top_contributors_commits': [
            {
                'username': username,
                'commits_count': data.get('commits_count', 0),
                'total_activity': data.get('total_activity', 0)
            }
            for username, data in top_commits
        ],
        'activity_trends': {
            'daily': {
                'prs': sum(c.get('stats', {}).get('pr', {}).get('daily', 0) for c in all_contributions.values()),
                'issues': sum(c.get('stats', {}).get('issue', {}).get('daily', 0) for c in all_contributions.values()),
                'commits': sum(c.get('stats', {}).get('commit', {}).get('daily', 0) for c in all_contributions.values())
            },
            'weekly': {
                'prs': sum(c.get('stats', {}).get('pr', {}).get('weekly', 0) for c in all_contributions.values()),
                'issues': sum(c.get('stats', {}).get('issue', {}).get('weekly', 0) for c in all_contributions.values()),
                'commits': sum(c.get('stats', {}).get('commit', {}).get('weekly', 0) for c in all_contributions.values())
            },
            'monthly': {
                'prs': sum(c.get('stats', {}).get('pr', {}).get('monthly', 0) for c in all_contributions.values()),
                'issues': sum(c.get('stats', {}).get('issue', {}).get('monthly', 0) for c in all_contributions.values()),
                'commits': sum(c.get('stats', {}).get('commit', {}).get('monthly', 0) for c in all_contributions.values())
            }
        },
        'activity_comparison': [
            {
                'username': username,
                'pr_count': data.get('pr_count', 0),
                'issues_count': data.get('issues_count', 0),
                'commits_count': data.get('commits_count', 0)
            }
            for username, data in sorted(
                all_contributions.items(),
                key=lambda x: x[1].get('total_activity', 0),
                reverse=True
            )[:10]
        ],
        'last_updated': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
    } 