"""
Chart Generation Utilities

Modular chart generators for analytics visualization.
"""

import matplotlib.pyplot as plt
import numpy as np
import io

class ChartGenerator:
    """Base class for chart generation."""
    
    def __init__(self):
        self.figure_size = (12, 8)
        self.default_color = 'steelblue'
        self.alpha = 0.8
    
    def _create_buffer(self, fig):
        """Create image buffer from matplotlib figure."""
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', bbox_inches='tight', dpi=150)
        buffer.seek(0)
        plt.close(fig)
        return buffer

class TopContributorsChart(ChartGenerator):
    """Generates top contributors charts."""
    
    def create(self, analytics_data, metric='prs', title="Top Contributors"):
        """Create a bar chart showing top contributors by specified metric."""
        if not analytics_data:
            return None
        
        data_key = f'top_contributors_{metric}'
        if data_key not in analytics_data:
            return None
            
        contributors = analytics_data[data_key]
        if not contributors:
            return None
        
        usernames, values = self._extract_data(contributors, metric)
        if not any(values):
            return None
        
        fig, ax = plt.subplots(figsize=self.figure_size)
        bars = ax.bar(range(len(usernames)), values, color=self.default_color, alpha=self.alpha)
        
        self._configure_chart(ax, usernames, bars, values, metric, title)
        
        return self._create_buffer(fig)
    
    def _extract_data(self, contributors, metric):
        """Extract usernames and values from contributors data."""
        usernames = [contrib['username'] for contrib in contributors[:10]]
        
        if metric == 'prs':
            values = [contrib['pr_count'] for contrib in contributors[:10]]
        elif metric == 'issues':
            values = [contrib['issues_count'] for contrib in contributors[:10]]
        elif metric == 'commits':
            values = [contrib['commits_count'] for contrib in contributors[:10]]
        else:
            values = []
        
        return usernames, values
    
    def _configure_chart(self, ax, usernames, bars, values, metric, title):
        """Configure chart appearance."""
        ax.set_xlabel('Contributors')
        ax.set_ylabel(metric.title())
        ax.set_title(title)
        ax.set_xticks(range(len(usernames)))
        ax.set_xticklabels(usernames, rotation=45, ha='right')
        
        # Add value labels on bars
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    str(value), ha='center', va='bottom')
        
        plt.tight_layout()

class ActivityComparisonChart(ChartGenerator):
    """Generates activity comparison charts."""
    
    def create(self, analytics_data, title="Activity Comparison"):
        """Create a grouped bar chart comparing different types of contributions."""
        if not analytics_data or 'activity_comparison' not in analytics_data:
            return None
        
        activity_data = analytics_data['activity_comparison']
        if not activity_data:
            return None
        
        usernames, pr_counts, issue_counts, commit_counts = self._extract_activity_data(activity_data)
        
        if not any(pr_counts + issue_counts + commit_counts):
            return None
        
        fig, ax = plt.subplots(figsize=self.figure_size)
        
        x = np.arange(len(usernames))
        width = 0.25
        
        bars1 = ax.bar(x - width, pr_counts, width, label='PRs', color='skyblue', alpha=self.alpha)
        bars2 = ax.bar(x, issue_counts, width, label='Issues', color='lightcoral', alpha=self.alpha)
        bars3 = ax.bar(x + width, commit_counts, width, label='Commits', color='lightgreen', alpha=self.alpha)
        
        self._configure_comparison_chart(ax, usernames, title, x)
        
        return self._create_buffer(fig)
    
    def _extract_activity_data(self, activity_data):
        """Extract activity data for comparison chart."""
        usernames = [user['username'] for user in activity_data]
        pr_counts = [user['pr_count'] for user in activity_data]
        issue_counts = [user['issues_count'] for user in activity_data]
        commit_counts = [user['commits_count'] for user in activity_data]
        
        return usernames, pr_counts, issue_counts, commit_counts
    
    def _configure_comparison_chart(self, ax, usernames, title, x):
        """Configure comparison chart appearance."""
        ax.set_xlabel('Contributors')
        ax.set_ylabel('Contributions')
        ax.set_title(title)
        ax.set_xticks(x)
        ax.set_xticklabels(usernames, rotation=45, ha='right')
        ax.legend()
        plt.tight_layout()

class ActivityTrendChart(ChartGenerator):
    """Generates activity trend charts."""
    
    def create(self, analytics_data, title="Activity Trends"):
        """Create a line chart showing activity trends over time periods."""
        if not analytics_data or 'activity_trends' not in analytics_data:
            return None
        
        trends = analytics_data['activity_trends']
        if not trends:
            return None
        
        periods, pr_data, issue_data, commit_data = self._extract_trend_data(trends)
        
        if not any(pr_data + issue_data + commit_data):
            return None
        
        fig, ax = plt.subplots(figsize=self.figure_size)
        
        ax.plot(periods, pr_data, marker='o', label='PRs', linewidth=2, markersize=8)
        ax.plot(periods, issue_data, marker='s', label='Issues', linewidth=2, markersize=8)
        ax.plot(periods, commit_data, marker='^', label='Commits', linewidth=2, markersize=8)
        
        self._configure_trend_chart(ax, title)
        
        return self._create_buffer(fig)
    
    def _extract_trend_data(self, trends):
        """Extract trend data for line chart."""
        periods = ['Daily', 'Weekly', 'Monthly']
        pr_data = [trends['daily']['prs'], trends['weekly']['prs'], trends['monthly']['prs']]
        issue_data = [trends['daily']['issues'], trends['weekly']['issues'], trends['monthly']['issues']]
        commit_data = [trends['daily']['commits'], trends['weekly']['commits'], trends['monthly']['commits']]
        
        return periods, pr_data, issue_data, commit_data
    
    def _configure_trend_chart(self, ax, title):
        """Configure trend chart appearance."""
        ax.set_xlabel('Time Period')
        ax.set_ylabel('Total Contributions')
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()

# Factory functions for backward compatibility
def create_top_contributors_chart(analytics_data, metric='prs', title="Top Contributors"):
    """Create top contributors chart."""
    generator = TopContributorsChart()
    return generator.create(analytics_data, metric, title)

def create_activity_comparison_chart(analytics_data, title="Activity Comparison"):
    """Create activity comparison chart."""
    generator = ActivityComparisonChart()
    return generator.create(analytics_data, title)

def create_activity_trend_chart(analytics_data, title="Activity Trends"):
    """Create activity trend chart."""
    generator = ActivityTrendChart()
    return generator.create(analytics_data, title) 