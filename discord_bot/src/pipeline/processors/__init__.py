"""
Data Processing Functions

Simple functions for transforming raw GitHub data into structured analytics.
"""

import pipeline.processors.contribution_processor as contribution_functions
import pipeline.processors.analytics_processor as analytics_functions  
import pipeline.processors.metrics_processor as metrics_functions

__all__ = ['contribution_functions', 'analytics_functions', 'metrics_functions'] 