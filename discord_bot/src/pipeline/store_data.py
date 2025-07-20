#!/usr/bin/env python3
"""
Stage 3: Data Storage Pipeline
Store processed data in Firestore collections
"""

import os
import sys
import json

# Add the parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'utils'))

def update_user_in_firestore(discord_id, user_data, db, determine_role):
    """Update a Discord user's contribution data in Firestore."""
    from src.utils.firestore import get_document, set_document, update_document
    
    doc = get_document('discord', discord_id)
    
    # Extract the basic contribution counts
    pr_count = user_data.get('pr_count', 0)
    issues_count = user_data.get('issues_count', 0)
    commits_count = user_data.get('commits_count', 0)
    
    # Determine the role using the determine_role function
    pr_role, issue_role, commit_role = determine_role(pr_count, issues_count, commits_count)
    
    # Format the roles as a comma-separated string
    role = ', '.join(filter(None, [pr_role, issue_role, commit_role]))
    
    # Create the update data
    update_data = {
        'pr_count': pr_count,
        'issues_count': issues_count,
        'commits_count': commits_count,
        'role': role
    }
    
    # Add enhanced stats if available
    if 'stats' in user_data:
        update_data['stats'] = user_data['stats']
    
    # Add rankings if available
    if 'rankings' in user_data:
        update_data['rankings'] = user_data['rankings']
    
    if doc:
        return update_document('discord', discord_id, update_data)
    else:
        # Set default values for missing fields
        return set_document('discord', discord_id, {**update_data, 'github_id': None})

def update_repo_metrics_in_firestore(repo_metrics):
    """Update repository metrics in Firestore."""
    from src.utils.firestore import set_document
    
    # Convert numeric values to integers to ensure proper storage
    if 'stars_count' in repo_metrics:
        repo_metrics['stars_count'] = int(repo_metrics['stars_count'])
    if 'forks_count' in repo_metrics:
        repo_metrics['forks_count'] = int(repo_metrics['forks_count'])
    
    print(f"Updating repository metrics: Stars: {repo_metrics.get('stars_count', 0)}, Forks: {repo_metrics.get('forks_count', 0)}")
    return set_document('repo_stats', 'metrics', repo_metrics, merge=True)

def main():
    """Main data storage pipeline"""
    print("========== Stage 3: Data Storage Pipeline ==========")
    
    # Check for required input files
    required_files = ['contributions.json', 'repo_metrics.json', 'hall_of_fame.json', 'analytics_data.json']
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"ERROR: Required input file {file_path} not found")
            print("Please run Stage 2 (process_data.py) first")
            sys.exit(1)
        else:
            file_size = os.path.getsize(file_path)
            print(f"Found {file_path} ({file_size} bytes)")
    
    try:
        # Import Firestore functions and role utils
        from src.utils.firestore import store_analytics_data, set_document, query_collection
        from src.utils.role_utils import determine_role
        
        # Get database reference
        from src.utils.firestore import db
        
        print("Loading processed data files...")
        
        # Load all processed data
        with open('contributions.json', 'r') as f:
            contributions = json.load(f)
        
        with open('repo_metrics.json', 'r') as f:
            repo_metrics = json.load(f)
        
        with open('hall_of_fame.json', 'r') as f:
            hall_of_fame_data = json.load(f)
        
        with open('analytics_data.json', 'r') as f:
            analytics_data = json.load(f)
        
        print(f"Loaded data: {len(contributions)} contributors, {len(hall_of_fame_data)} hall of fame categories")
        
        # Store contributions data for Discord users
        print("Storing contributions data...")
        discord_users_updated = 0
        
        for github_id, user_data in contributions.items():
            try:
                # Check if this GitHub user is registered in Discord
                docs = query_collection('discord', 'github_id', '==', github_id)
                user_found = False
                
                for doc in docs:
                    discord_id = doc.id
                    update_user_in_firestore(discord_id, user_data, db, determine_role)
                    discord_users_updated += 1
                    user_found = True
                    break
                
                if not user_found:
                    print(f"  GitHub user {github_id} not registered in Discord - skipping")
                    
            except Exception as e:
                print(f"Error updating Firestore for GitHub user {github_id}: {e}")
        
        print(f"Updated {discord_users_updated} Discord users in Firestore")
        
        # Store repository metrics
        print("Storing repository metrics...")
        success = update_repo_metrics_in_firestore(repo_metrics)
        if success:
            print("Repository metrics stored in Firestore")
        else:
            print("Failed to store repository metrics")
        
        # Store hall of fame data
        print("Storing hall of fame data...")
        success = set_document('repo_stats', 'hall_of_fame', hall_of_fame_data, merge=True)
        if success:
            print("Hall of fame data stored in Firestore")
        else:
            print("Failed to store hall of fame data")
        
        # Store analytics data
        print("Storing analytics data...")
        analytics_success = store_analytics_data(analytics_data)
        if analytics_success:
            print("Analytics data stored in Firestore")
        else:
            print("Failed to store analytics data")
        
        print("Stage 3: Data Storage - COMPLETED")
        
    except Exception as e:
        print(f"Error in data storage pipeline: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 