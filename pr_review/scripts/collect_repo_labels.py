#!/usr/bin/env python3
"""
Script to collect all labels from RUXAILAB repositories
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Set

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.github_client import GitHubClient
from config import GITHUB_TOKEN, REPO_OWNER

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RepositoryLabelsCollector:
    """Collects labels from all RUXAILAB repositories"""
    
    def __init__(self):
        """Initialize the collector"""
        self.github_client = GitHubClient()
        self.organization = REPO_OWNER
    
    def get_organization_repositories(self) -> List[str]:
        """
        Get all repositories from the RUXAILAB organization
        
        Returns:
            List of repository names in format "owner/repo"
        """
        try:
            endpoint = f"orgs/{self.organization}/repos"
            repos_data = self.github_client._make_request(endpoint, params={"per_page": 100})
            
            repo_names = []
            for repo in repos_data:
                if not repo.get('archived', False):  # Skip archived repos
                    repo_names.append(repo['full_name'])
            
            logger.info(f"Found {len(repo_names)} active repositories in {self.organization}")
            return repo_names
            
        except Exception as e:
            logger.error(f"Failed to fetch organization repositories: {e}")
            # Fallback to known RUXAILAB repos
            return [
                "ruxailab/eye-tracking-analysis",
                "ruxailab/sentiment-analysis-tool", 
                "ruxailab/heuristic-evaluation-framework",
                "ruxailab/accessibility-testing-suite",
                "ruxailab/figma-integration-plugin",
                "ruxailab/vr-ar-research-tools",
                "ruxailab/research-data-pipeline"
            ]
    
    def collect_all_labels(self, repositories: List[str] = None) -> Dict[str, any]:
        """
        Collect labels from all specified repositories
        
        Args:
            repositories: List of repo names, or None to use all RUXAILAB repos
            
        Returns:
            Dictionary containing all collected labels data
        """
        if repositories is None:
            repositories = self.get_organization_repositories()
        
        all_labels = {}
        unique_labels = set()
        label_frequencies = {}
        
        logger.info(f"Collecting labels from {len(repositories)} repositories...")
        
        for repo in repositories:
            try:
                logger.info(f"Fetching labels from {repo}...")
                repo_labels = self.github_client.get_repository_labels(repo)
                
                # Store repo-specific labels
                all_labels[repo] = []
                
                for label in repo_labels:
                    label_name = label.get('name', '')
                    label_desc = label.get('description', '')
                    label_color = label.get('color', '')
                    
                    # Add to repo labels
                    all_labels[repo].append({
                        'name': label_name,
                        'description': label_desc,
                        'color': label_color
                    })
                    
                    # Track unique labels
                    unique_labels.add(label_name)
                    
                    # Count frequency
                    if label_name in label_frequencies:
                        label_frequencies[label_name] += 1
                    else:
                        label_frequencies[label_name] = 1
                
                logger.info(f"  → Found {len(repo_labels)} labels in {repo}")
                
            except Exception as e:
                logger.error(f"Failed to fetch labels from {repo}: {e}")
                all_labels[repo] = []
        
        # Create summary
        summary = {
            'total_repositories': len(repositories),
            'total_unique_labels': len(unique_labels),
            'most_common_labels': sorted(
                label_frequencies.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:20],  # Top 20 most common labels
            'collection_timestamp': self._get_timestamp()
        }
        
        return {
            'summary': summary,
            'repository_labels': all_labels,
            'unique_labels': sorted(list(unique_labels)),
            'label_frequencies': label_frequencies
        }
    
    def save_labels_data(self, labels_data: Dict, output_file: str = "data/collected_repo_labels.json"):
        """
        Save collected labels data to file
        
        Args:
            labels_data: Labels data to save
            output_file: Output file path
        """
        try:
            # Ensure directory exists
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            
            # Save to JSON file
            with open(output_file, 'w') as f:
                json.dump(labels_data, f, indent=2)
            
            logger.info(f"Labels data saved to {output_file}")
            
            # Also create a simplified version for AI labeler
            simplified_labels = {
                'last_updated': labels_data['summary']['collection_timestamp'],
                'available_labels': labels_data['unique_labels'],
                'common_labels': [label[0] for label in labels_data['summary']['most_common_labels'][:15]]
            }
            
            simplified_file = output_file.replace('.json', '_simplified.json')
            with open(simplified_file, 'w') as f:
                json.dump(simplified_labels, f, indent=2)
            
            logger.info(f"Simplified labels saved to {simplified_file}")
            
        except Exception as e:
            logger.error(f"Failed to save labels data: {e}")
    
    def generate_labels_report(self, labels_data: Dict) -> str:
        """
        Generate a human-readable report of collected labels
        
        Args:
            labels_data: Collected labels data
            
        Returns:
            Formatted report string
        """
        summary = labels_data['summary']
        
        report = f"""
# RUXAILAB Repository Labels Collection Report

## Summary
- **Total Repositories Analyzed:** {summary['total_repositories']}
- **Total Unique Labels Found:** {summary['total_unique_labels']}
- **Collection Date:** {summary['collection_timestamp']}

## Most Common Labels Across All Repositories

"""
        
        for i, (label, count) in enumerate(summary['most_common_labels'], 1):
            percentage = (count / summary['total_repositories']) * 100
            report += f"{i:2d}. **{label}** - Used in {count} repositories ({percentage:.1f}%)\n"
        
        report += f"""

## All Unique Labels Found

{', '.join(labels_data['unique_labels'])}

## Repository-Specific Labels

"""
        
        for repo, labels in labels_data['repository_labels'].items():
            if labels:  # Only show repos with labels
                report += f"### {repo}\n"
                report += f"Labels: {', '.join([l['name'] for l in labels])}\n\n"
        
        report += """
---
*Report generated by RUXAILAB PR Automation System*
"""
        
        return report
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()

def main():
    """Main entry point"""
    collector = RepositoryLabelsCollector()
    
    # Collect labels from all RUXAILAB repositories
    print("Collecting labels from RUXAILAB repositories...")
    labels_data = collector.collect_all_labels()
    
    # Save the data
    print("Saving labels data...")
    collector.save_labels_data(labels_data)
    
    # Generate and save report
    print("Generating report...")
    report = collector.generate_labels_report(labels_data)
    
    with open("data/labels_collection_report.md", 'w') as f:
        f.write(report)
    
    # Print summary
    print("\n" + "="*60)
    print("LABELS COLLECTION COMPLETE")
    print("="*60)
    print(f"Repositories analyzed: {labels_data['summary']['total_repositories']}")
    print(f"Unique labels found: {labels_data['summary']['total_unique_labels']}")
    print(f"Data saved to: data/collected_repo_labels.json")
    print(f"Report saved to: data/labels_collection_report.md")
    
    print("\nTop 10 Most Common Labels:")
    for i, (label, count) in enumerate(labels_data['summary']['most_common_labels'][:10], 1):
        print(f"  {i:2d}. {label} ({count} repos)")

if __name__ == "__main__":
    main() 