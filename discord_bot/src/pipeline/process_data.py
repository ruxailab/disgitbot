#!/usr/bin/env python3
"""
Stage 2: Data Processing Pipeline
Process raw GitHub data and create analytics, rankings, and metrics
"""

import os
import json
from processors import ContributionProcessor, AnalyticsProcessor, MetricsProcessor

def main():
    """Main data processing pipeline"""
    print("========== Stage 2: Data Processing Pipeline ==========")
    
    # Check for required input file
    if not os.path.exists("raw_github_data.json"):
        print("ERROR: raw_github_data.json not found")
        print("Please run Stage 1 (collect_raw_data.py) first")
        exit(1)
    
    # Load raw data
    print("Loading raw GitHub data...")
    with open("raw_github_data.json", "r") as f:
        raw_data = json.load(f)
    
    print(f"Loaded raw data for {len(raw_data.get('repositories', {}))} repositories")
    
    try:
        # Initialize processors
        contribution_processor = ContributionProcessor()
        analytics_processor = AnalyticsProcessor()
        metrics_processor = MetricsProcessor()
        
        # Process raw data into contribution structures
        all_contributions = contribution_processor.process_raw_data(raw_data)
        
        # Calculate rankings
        all_contributions = contribution_processor.calculate_rankings(all_contributions)
        
        # Calculate streaks and averages
        all_contributions = contribution_processor.calculate_streaks_and_averages(all_contributions)
        
        # Create hall of fame data
        hall_of_fame_data = analytics_processor.create_hall_of_fame_data(all_contributions)
        
        # Create analytics data
        analytics_data = analytics_processor.create_analytics_data(all_contributions)
        
        # Create repository metrics
        repo_metrics = metrics_processor.create_repo_metrics(raw_data, all_contributions)
        
        # Save processed data
        print("Saving processed data...")
        
        with open("contributions.json", "w") as f:
            json.dump(all_contributions, f, indent=2)
        
        with open("hall_of_fame.json", "w") as f:
            json.dump(hall_of_fame_data, f, indent=2)
        
        with open("analytics_data.json", "w") as f:
            json.dump(analytics_data, f, indent=2)
        
        with open("repo_metrics.json", "w") as f:
            json.dump(repo_metrics, f, indent=2)
        
        print(f"Data processing completed for {len(all_contributions)} contributors")
        print("Processed data saved to:")
        print("  - contributions.json")
        print("  - hall_of_fame.json")
        print("  - analytics_data.json")
        print("  - repo_metrics.json")
        print("Stage 2: Data Processing - COMPLETED")
        
    except Exception as e:
        print(f"Error in data processing pipeline: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == "__main__":
    main() 