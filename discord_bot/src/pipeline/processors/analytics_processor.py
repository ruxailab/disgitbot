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
    
    contributors = list(all_contributions.keys())
    
    # Sort by PR count for hall of fame
    top_prs = sorted(
        contributors,
        key=lambda x: all_contributions[x].get('pr_count', 0),
        reverse=True
    )[:10]
    
    # Sort by issues
    top_issues = sorted(
        contributors,
        key=lambda x: all_contributions[x].get('issues_count', 0),
        reverse=True
    )[:10]
    
    # Sort by commits
    top_commits = sorted(
        contributors,
        key=lambda x: all_contributions[x].get('commits_count', 0),
        reverse=True
    )[:10]
    
    return {
        'last_updated': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
        'pr': {
            'all_time': [
                {
                    'username': username,
                    'count': all_contributions[username].get('pr_count', 0)
                }
                for username in top_prs
            ]
        },
        'issues': {
            'all_time': [
                {
                    'username': username,
                    'count': all_contributions[username].get('issues_count', 0)
                }
                for username in top_issues
            ]
        },
        'commits': {
            'all_time': [
                {
                    'username': username,
                    'count': all_contributions[username].get('commits_count', 0)
                }
                for username in top_commits
            ]
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
    
    return {
        'summary': {
            'total_contributors': total_contributors,
            'active_contributors': active_contributors,
            'total_prs': total_prs,
            'total_issues': total_issues,
            'total_commits': total_commits
        },
        'top_contributors': {
            'by_prs': sorted(
                all_contributions.items(),
                key=lambda x: x[1].get('pr_count', 0),
                reverse=True
            )[:5],
            'by_issues': sorted(
                all_contributions.items(),
                key=lambda x: x[1].get('issues_count', 0),
                reverse=True
            )[:5],
            'by_commits': sorted(
                all_contributions.items(),
                key=lambda x: x[1].get('commits_count', 0),
                reverse=True
            )[:5]
        },
        'activity_trends': {
            'today_total': sum(c.get('today_activity', 0) for c in all_contributions.values()),
            'week_total': sum(c.get('week_activity', 0) for c in all_contributions.values()),
            'month_total': sum(c.get('month_activity', 0) for c in all_contributions.values())
        },
        'last_updated': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
    } 