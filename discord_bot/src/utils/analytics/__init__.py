"""
Analytics Module

Modular analytics utilities for data visualization.
"""

from .chart_generators import (
    create_top_contributors_chart,
    create_activity_comparison_chart,
    create_activity_trend_chart,
    create_time_series_chart,
    TopContributorsChart,
    ActivityComparisonChart,
    ActivityTrendChart,
    TimeSeriesChart
)

__all__ = [
    'create_top_contributors_chart',
    'create_activity_comparison_chart', 
    'create_activity_trend_chart',
    'create_time_series_chart',
    'TopContributorsChart',
    'ActivityComparisonChart',
    'ActivityTrendChart',
    'TimeSeriesChart'
] 