#!/usr/bin/env python3
"""
Collect repository labels from all RUXAILAB repositories and store in Firestore
"""

import os
import sys
import requests
import time
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Firestore functions from Discord bot
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'discord_bot', 'src', 'utils'))
from firestore import store_repository_labels

from config import GITHUB_TOKEN, REPO_OWNER

class LabelCollector:
    """Collect labels from RUXAILAB repositories"""
    
    def __init__(self):
        self.github_token = GITHUB_TOKEN
        self.repo_owner = REPO_OWNER
        self.headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
    
    def get_org_repositories(self):
        """Get all repositories for the organization"""
        try:
            url = f'https://api.github.com/orgs/{self.repo_owner}/repos'
            params = {'per_page': 100, 'type': 'all'}
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            repos = response.json()
            repo_names = [repo['full_name'] for repo in repos]
            print(f"Found {len(repo_names)} repositories in {self.repo_owner}")
            return repo_names
            
        except Exception as e:
            print(f"Error fetching repositories: {e}")
            return []
    
    def get_repository_labels(self, repo_name):
        """Get labels for a specific repository"""
        try:
            url = f'https://api.github.com/repos/{repo_name}/labels'
            params = {'per_page': 100}
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            labels = response.json()
            print(f"Retrieved {len(labels)} labels from {repo_name}")
            return labels
            
        except Exception as e:
            print(f"Error fetching labels from {repo_name}: {e}")
            return []
    
    def collect_and_store_all_labels(self):
        """Collect labels from all repositories and store in Firestore"""
        try:
            repositories = self.get_org_repositories()
            
            for repo_name in repositories:
                print(f"Processing {repo_name}...")
                
                # Get labels for this repository
                labels = self.get_repository_labels(repo_name)
                
                if labels:
                    # Store in Firestore
                    success = store_repository_labels(repo_name, labels)
                    if success:
                        print(f"Successfully stored labels for {repo_name}")
                    else:
                        print(f"Failed to store labels for {repo_name}")
                else:
                    print(f"No labels found for {repo_name}")
                
                # Rate limiting - GitHub API allows 5000 requests per hour
                time.sleep(1)
            
            print(f"Label collection completed for {len(repositories)} repositories")
            
        except Exception as e:
            print(f"Error in label collection process: {e}")
            import traceback
            traceback.print_exc()

def main():
    """Main function"""
    print("Starting repository label collection...")
    
    collector = LabelCollector()
    collector.collect_and_store_all_labels()
    
    print("Label collection process finished")

if __name__ == "__main__":
    main() 