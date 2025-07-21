"""
Data Processing Modules

Modular processors for transforming raw GitHub data into structured analytics.
"""

from pipeline.processors.contribution_processor import ContributionProcessor
from pipeline.processors.analytics_processor import AnalyticsProcessor
from pipeline.processors.metrics_processor import MetricsProcessor

__all__ = ['ContributionProcessor', 'AnalyticsProcessor', 'MetricsProcessor'] 