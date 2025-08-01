import os
from typing import Dict, Any, Optional, List
import firebase_admin
from firebase_admin import credentials, firestore

_db = None

def _get_credentials_path() -> str:
    """Get the path to Firebase credentials file.
    
    This shared package gets copied around different environments:
    - GitHub workflows: runs from repo root with discord_bot/ subdirectory
    - Docker container: copied to /app/shared/ with credentials at /app/config/
    - PR review: runs from pr_review/ subdirectory
    
    We try multiple paths to handle all these scenarios.
    """
    current_dir = os.getcwd()
    
    # List of possible credential paths to try (in order of preference)
    possible_paths = [
        # Docker container path (when shared is copied to /app/shared/)
        '/app/config/credentials.json',
        
        # GitHub workflow path (from discord_bot/ directory)
        os.path.join(current_dir, 'config', 'credentials.json'),
        
        # GitHub workflow path (from repo root)
        os.path.join(current_dir, 'discord_bot', 'config', 'credentials.json'),
        
        # PR review path (from pr_review/ directory)
        os.path.join(os.path.dirname(current_dir), 'discord_bot', 'config', 'credentials.json'),
        
        # Fallback: relative to this file's location
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'discord_bot', 'config', 'credentials.json'),
    ]
    
    for cred_path in possible_paths:
        if os.path.exists(cred_path):
            print(f"Found Firebase credentials at: {cred_path}")
            return cred_path
    
    # If none found, show all attempted paths for debugging
    attempted_paths = '\n'.join(f"  - {path}" for path in possible_paths)
    raise FileNotFoundError(
        f"Firebase credentials file not found. Tried these paths:\n{attempted_paths}\n"
        f"Current working directory: {current_dir}"
    )

def _get_firestore_client():
    """Get Firestore client, initializing if needed."""
    global _db
    if _db is None:
        if not firebase_admin._apps:
            cred_path = _get_credentials_path()
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        _db = firestore.client()
    return _db

def get_document(collection: str, document_id: str) -> Optional[Dict[str, Any]]:
    """Get a document from Firestore."""
    try:
        db = _get_firestore_client()
        doc = db.collection(collection).document(document_id).get()
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        print(f"Error getting document {collection}/{document_id}: {e}")
        return None

def set_document(collection: str, document_id: str, data: Dict[str, Any], merge: bool = False) -> bool:
    """Set a document in Firestore."""
    try:
        db = _get_firestore_client()
        db.collection(collection).document(document_id).set(data, merge=merge)
        return True
    except Exception as e:
        print(f"Error setting document {collection}/{document_id}: {e}")
        return False

def update_document(collection: str, document_id: str, data: Dict[str, Any]) -> bool:
    """Update a document in Firestore."""
    try:
        db = _get_firestore_client()
        db.collection(collection).document(document_id).update(data)
        return True
    except Exception as e:
        print(f"Error updating document {collection}/{document_id}: {e}")
        return False

def delete_document(collection: str, document_id: str) -> bool:
    """Delete a document from Firestore."""
    try:
        db = _get_firestore_client()
        db.collection(collection).document(document_id).delete()
        return True
    except Exception as e:
        print(f"Error deleting document {collection}/{document_id}: {e}")
        return False

def query_collection(collection: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Query a collection with optional filters."""
    try:
        db = _get_firestore_client()
        query = db.collection(collection)
        
        if filters:
            for field, value in filters.items():
                query = query.where(field, '==', value)
        
        docs = query.stream()
        return {doc.id: doc.to_dict() for doc in docs}
    except Exception as e:
        print(f"Error querying collection {collection}: {e}")
        return {} 