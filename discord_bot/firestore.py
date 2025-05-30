import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from role_utils import determine_role

# ---------- Firebase Initialization ----------
try:
    if not firebase_admin._apps:
        # Try different approaches to find credentials
        credentials_path = "credentials.json"  # Default path
        
        # 1. Check if CREDENTIALS_JSON environment variable is set
        if 'CREDENTIALS_JSON' in os.environ:
            # The secret is mounted by Cloud Run
            print("Using credentials from CREDENTIALS_JSON environment variable")
            credentials_path = os.environ['CREDENTIALS_JSON']
        # 2. Check if credentials.json exists in current directory
        elif os.path.exists("credentials.json"):
            print("Using credentials.json from current directory")
        # 3. Check if credentials.json exists in parent directory
        elif os.path.exists("../credentials.json"):
            print("Using credentials.json from parent directory")
            credentials_path = "../credentials.json"
        else:
            print("WARNING: Could not find credentials.json, will attempt to use default path")
            
        print(f"Initializing Firebase with credentials from: {credentials_path}")
        cred = credentials.Certificate(credentials_path)
        firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    print(f"Firebase init error: {e}")
    exit(1)

# ---------- Firestore Helper Functions ----------
def update_user_in_firestore(discord_id, user_data):
    """
    Update a user's contribution data in Firestore.
    
    Args:
        discord_id: The Discord user ID
        user_data: Dictionary containing the user's contribution data
    """
    doc_ref = db.collection('discord').document(discord_id)
    doc = doc_ref.get()
    
    # Extract the basic contribution counts
    pr_count = user_data.get('pr_count', 0)
    issues_count = user_data.get('issues_count', 0)
    commits_count = user_data.get('commits_count', 0)
    
    # Determine the role using the determine_role function
    pr_role, issue_role, commit_role = determine_role(pr_count, issues_count, commits_count)
    
    # Format the roles as a comma-separated string
    role = ', '.join(filter(None, [pr_role, issue_role, commit_role]))  # Filter out None values and join

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

    if doc.exists:
        doc_ref.update(update_data)
    else:
        # Set default values for missing fields
        doc_ref.set({
            **update_data,
            'github_id': None
        })

def update_repo_metrics_in_firestore(repo_metrics):
    """
    Update repository metrics (stars, forks) in Firestore.
    
    Args:
        repo_metrics: Dictionary containing repository metrics like stars_count and forks_count
    """
    try:
        # Ensure we have a metrics document
        print(f"DEBUG: In update_repo_metrics_in_firestore with metrics: {repo_metrics}")
        doc_ref = db.collection('repo_stats').document('metrics')
        
        # Add debug log to show what's in the document before update
        doc_before = doc_ref.get()
        if doc_before.exists:
            print(f"DEBUG: Existing metrics document: {doc_before.to_dict()}")
        else:
            print("DEBUG: No existing metrics document found")
        
        # Convert numeric values to integers to ensure proper storage
        if 'stars_count' in repo_metrics:
            repo_metrics['stars_count'] = int(repo_metrics['stars_count'])
        if 'forks_count' in repo_metrics:
            repo_metrics['forks_count'] = int(repo_metrics['forks_count'])
            
        print(f"DEBUG: Setting metrics with values: {repo_metrics}")
        doc_ref.set(repo_metrics, merge=True)
        
        # Verify the update
        doc_after = doc_ref.get()
        if doc_after.exists:
            print(f"DEBUG: Metrics after update: {doc_after.to_dict()}")
        
        print(f"Repository metrics updated in Firestore: Stars: {repo_metrics.get('stars_count', 0)}, Forks: {repo_metrics.get('forks_count', 0)}")
        return True
    except Exception as e:
        print(f"Error updating repository metrics in Firestore: {e}")
        import traceback
        traceback.print_exc()
        return False

def load_repo_metrics_from_firestore():
    """
    Load repository metrics from Firestore.
    
    Returns:
        Dictionary containing repository metrics
    """
    try:
        doc_ref = db.collection('repo_stats').document('metrics')
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        else:
            print("No repository metrics found in Firestore")
            return {
                'stars_count': 0,
                'forks_count': 0
            }
    except Exception as e:
        print(f"Error loading repository metrics from Firestore: {e}")
        return {
            'stars_count': 0,
            'forks_count': 0
        }

def load_data_from_firestore():
    contributions = {}
    user_mappings = {}

    try:
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

    return contributions, user_mappings

# ---------- Load JSON Contributions ----------
if not os.path.exists('contributions.json'):
    with open('contributions.json', 'w') as f:
        json.dump({}, f)

with open('contributions.json', 'r') as f:
    try:
        contributions = json.load(f)
    except json.JSONDecodeError:
        print("Invalid JSON format in contributions.json.")
        contributions = {}

# ---------- Load Repository Metrics ----------
if os.path.exists('repo_metrics.json'):
    with open('repo_metrics.json', 'r') as f:
        try:
            repo_metrics = json.load(f)
            # Update repository metrics in Firestore
            doc_ref = db.collection('repo_stats').document('metrics')
            doc_ref.set(repo_metrics, merge=True)
            print(f"Repository metrics updated in Firestore: Stars: {repo_metrics.get('stars_count', 0)}, Forks: {repo_metrics.get('forks_count', 0)}")
        except json.JSONDecodeError:
            print("Invalid JSON format in repo_metrics.json.")
else:
    print("repo_metrics.json not found. Skipping repository metrics update.")

# ---------- Sync to Firestore ----------
for github_id, user_data in contributions.items():
    try:
        docs = db.collection('discord').where('github_id', '==', github_id).stream()
        for doc in docs:
            if not doc.exists:
                continue
            discord_id = doc.id
            
            # Pass the entire user_data object
            update_user_in_firestore(discord_id, user_data)
    except Exception as e:
        print(f"Error updating Firestore for GitHub user {github_id}: {e}")

print("Firestore update completed.")
