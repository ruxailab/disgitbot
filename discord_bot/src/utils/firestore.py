import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

# Handle both relative and absolute imports
try:
    from .role_utils import determine_role
except ImportError:
    from role_utils import determine_role

# ---------- Firebase Initialization ----------
try:
    if not firebase_admin._apps:
        print("Initializing Firebase...") 
        
        # Calculate path to config directory relative to this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, "../../config/credentials.json")
        config_path = os.path.abspath(config_path)  # Normalize the path
        
        if os.path.exists(config_path):
            print(f"Using credentials.json from {config_path}")
            cred = credentials.Certificate(config_path)
        else:
            print("ERROR: No valid credentials found.")
            print(f"Place credentials.json at: {config_path}")
            exit(1)
            
        # Initialize Firebase
        firebase_admin.initialize_app(cred)
        print("Firebase initialized successfully")
                
    db = firestore.client()
    print("Firestore client initialized successfully!")
except Exception as e:
    print(f"Firebase init error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# ---------- Generic Firestore Utilities ----------
def set_document(collection_name, document_id, data, merge=False):
    """Generic function to set a document in Firestore."""
    try:
        doc_ref = db.collection(collection_name).document(document_id)
        doc_ref.set(data, merge=merge)
        return True
    except Exception as e:
        print(f"Error setting document {collection_name}/{document_id}: {e}")
        return False

def get_document(collection_name, document_id):
    """Generic function to get a document from Firestore."""
    try:
        doc_ref = db.collection(collection_name).document(document_id)
        doc = doc_ref.get()
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        print(f"Error getting document {collection_name}/{document_id}: {e}")
        return None

def update_document(collection_name, document_id, data):
    """Generic function to update a document in Firestore."""
    try:
        doc_ref = db.collection(collection_name).document(document_id)
        doc_ref.update(data)
        return True
    except Exception as e:
        print(f"Error updating document {collection_name}/{document_id}: {e}")
        return False

def query_collection(collection_name, field_name, operator, value):
    """Generic function to query a collection in Firestore."""
    try:
        docs = db.collection(collection_name).where(field_name, operator, value).stream()
        return [doc for doc in docs if doc.exists]
    except Exception as e:
        print(f"Error querying collection {collection_name}: {e}")
        return []

def get_collection(collection_name):
    """Generic function to get all documents from a collection."""
    try:
        docs = db.collection(collection_name).stream()
        return [doc for doc in docs if doc.exists]
    except Exception as e:
        print(f"Error getting collection {collection_name}: {e}")
        return []

def get_firestore_data():
    """
    A simplified function to get all necessary data from Firestore.
    
    Returns:
        tuple: (repo_metrics, contributions)
            - repo_metrics: Dictionary with repository stats (stars, forks, etc.)
            - contributions: Dictionary mapping GitHub usernames to their contribution data
    """
    repo_metrics = {}
    contributions = {}
    user_mappings = {}
    
    try:
        # 1. Get repository metrics
        metrics_doc = db.collection('repo_stats').document('metrics').get()
        if metrics_doc.exists:
            repo_metrics = metrics_doc.to_dict()
            print(f"Retrieved repo metrics from Firestore: {repo_metrics}")
        else:
            print("No repository metrics found in Firestore")
        
        # 2. Get user contributions
        docs = db.collection('discord').stream()
        for doc in docs:
            if not doc.exists:
                continue

            data = doc.to_dict()
            github_id = data.get('github_id')
            if not github_id:
                continue

            discord_id = doc.id
            
            # Create base contribution data
            user_data = {
                'pr_count': data.get('pr_count', 0),
                'issues_count': data.get('issues_count', 0),
                'commits_count': data.get('commits_count', 0)
            }
            
            # Add enhanced stats if available
            if 'stats' in data:
                user_data['stats'] = data['stats']
            
            # Add rankings if available
            if 'rankings' in data:
                user_data['rankings'] = data['rankings']
            
            contributions[github_id] = user_data
            user_mappings[discord_id] = github_id
    except Exception as e:
        print(f"Firestore read error: {e}")
        import traceback
        traceback.print_exc()

    return repo_metrics, contributions, user_mappings

def get_hall_of_fame_data():
    """
    Get hall of fame data from Firestore.
    
    Returns:
        Dictionary with hall of fame data or None if not found
    """
    try:
        # Get hall of fame document
        hof_doc = db.collection('repo_stats').document('hall_of_fame').get()
        if hof_doc.exists:
            hall_of_fame = hof_doc.to_dict()
            print(f"Retrieved hall of fame data from Firestore")
            return hall_of_fame
        else:
            print("No hall of fame data found in Firestore")
            return None
    except Exception as e:
        print(f"Error retrieving hall of fame data from Firestore: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_contributor_analytics_data():
    """
    Get contributor analytics data from Firestore for visualization.
    
    Returns:
        Dictionary with contributor activity data
    """
    try:
        contributors_data = {}
        
        # Get all contributor data from discord collection
        docs = db.collection('discord').stream()
        for doc in docs:
            if not doc.exists:
                continue
                
            data = doc.to_dict()
            github_id = data.get('github_id')
            if not github_id:
                continue
                
            # Extract analytics-relevant data
            contributor_stats = {
                'github_username': github_id,
                'pr_count': data.get('pr_count', 0),
                'issues_count': data.get('issues_count', 0),
                'commits_count': data.get('commits_count', 0)
            }
            
            # Add enhanced stats if available
            if 'stats' in data:
                stats = data['stats']
                contributor_stats.update({
                    'daily_prs': stats.get('prs', {}).get('daily', 0),
                    'weekly_prs': stats.get('prs', {}).get('weekly', 0),
                    'monthly_prs': stats.get('prs', {}).get('monthly', 0),
                    'daily_issues': stats.get('issues', {}).get('daily', 0),
                    'weekly_issues': stats.get('issues', {}).get('weekly', 0),
                    'monthly_issues': stats.get('issues', {}).get('monthly', 0),
                    'daily_commits': stats.get('commits', {}).get('daily', 0),
                    'weekly_commits': stats.get('commits', {}).get('weekly', 0),
                    'monthly_commits': stats.get('commits', {}).get('monthly', 0),
                    'last_updated': stats.get('last_updated', '')
                })
            
            # Add rankings if available
            if 'rankings' in data:
                rankings = data['rankings']
                contributor_stats.update({
                    'pr_rank': rankings.get('pr', 0),
                    'issue_rank': rankings.get('issue', 0),
                    'commit_rank': rankings.get('commit', 0)
                })
            
            contributors_data[github_id] = contributor_stats
        
        return contributors_data
        
    except Exception as e:
        print(f"Error retrieving contributor analytics data from Firestore: {e}")
        import traceback
        traceback.print_exc()
        return {}

def store_repository_labels(repo_name, labels_data):
    """
    Store repository labels in Firestore for AI PR labeling.
    
    Args:
        repo_name: Repository name (e.g., 'ruxailab/disgitbot')
        labels_data: List of label dictionaries with name, description, color
    """
    try:
        doc_ref = db.collection('repo_labels').document(repo_name.replace('/', '_'))
        
        labels_formatted = []
        for label in labels_data:
            labels_formatted.append({
                'name': label.get('name', ''),
                'description': label.get('description', ''),
                'color': label.get('color', '')
            })
        
        from datetime import datetime
        doc_ref.set({
            'repository': repo_name,
            'labels': labels_formatted,
            'last_updated': datetime.now().isoformat()
        })
        
        print(f"Stored {len(labels_formatted)} labels for repository {repo_name}")
        return True
        
    except Exception as e:
        print(f"Error storing repository labels in Firestore: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_repository_labels(repo_name):
    """
    Get repository labels from Firestore for AI PR labeling.
    
    Args:
        repo_name: Repository name (e.g., 'ruxailab/disgitbot')
        
    Returns:
        List of label names for AI classification
    """
    try:
        doc_ref = db.collection('repo_labels').document(repo_name.replace('/', '_'))
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            if data:
                labels = data.get('labels', [])
                label_names = [label.get('name', '') for label in labels if label.get('name')]
                print(f"Retrieved {len(label_names)} labels for repository {repo_name}")
                return label_names
        else:
            print(f"No labels found for repository {repo_name}")
            return []
            
    except Exception as e:
        print(f"Error retrieving repository labels from Firestore: {e}")
        import traceback
        traceback.print_exc()
        return []

def get_all_ruxailab_labels():
    """
    Get aggregated labels from all RUXAILAB repositories for comprehensive AI training.
    
    Returns:
        List of unique label names across all repositories
    """
    try:
        docs = db.collection('repo_labels').stream()
        all_labels = set()
        
        for doc in docs:
            if not doc.exists:
                continue
                
            data = doc.to_dict()
            labels = data.get('labels', [])
            for label in labels:
                label_name = label.get('name', '')
                if label_name:
                    all_labels.add(label_name)
        
        label_list = sorted(list(all_labels))
        print(f"Retrieved {len(label_list)} unique labels across all repositories")
        return label_list
        
    except Exception as e:
        print(f"Error retrieving all repository labels from Firestore: {e}")
        import traceback
        traceback.print_exc()
        return []

def store_analytics_data(analytics_data):
    """Store analytics data in Firestore."""
    from datetime import datetime
    analytics_data['last_updated'] = datetime.now().isoformat()
    return set_document('analytics', 'contributor_stats', analytics_data)

def get_analytics_data():
    """Get analytics data from Firestore."""
    return get_document('analytics', 'contributor_stats') or {}
