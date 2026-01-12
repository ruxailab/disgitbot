import os
from typing import Dict, Any, Optional
import firebase_admin
from firebase_admin import credentials, firestore

_db = None

class FirestoreMultiTenant:
    """Multi-tenant Firestore client that organizes data by Discord server and GitHub organization."""
    
    def __init__(self):
        self.db = _get_firestore_client()
    
    def get_server_config(self, discord_server_id: str) -> Optional[Dict[str, Any]]:
        """Get Discord server configuration including GitHub org mapping."""
        try:
            doc = self.db.collection('discord_servers').document(discord_server_id).get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            print(f"Error getting server config for {discord_server_id}: {e}")
            return None

    def set_server_config(self, discord_server_id: str, config: Dict[str, Any]) -> bool:
        """Set Discord server configuration."""
        try:
            self.db.collection('discord_servers').document(discord_server_id).set(config)
            return True
        except Exception as e:
            print(f"Error setting server config for {discord_server_id}: {e}")
            return False

    def get_user_mapping(self, discord_user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's Discord-GitHub mapping across all servers."""
        try:
            doc = self.db.collection('discord_users').document(discord_user_id).get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            print(f"Error getting user mapping for {discord_user_id}: {e}")
            return None
  
    def set_user_mapping(self, discord_user_id: str, mapping: Dict[str, Any]) -> bool:
        """Set user's Discord-GitHub mapping."""
        try:
            self.db.collection('discord_users').document(discord_user_id).set(mapping)
            return True
        except Exception as e:
            print(f"Error setting user mapping for {discord_user_id}: {e}")
            return False
    
    def get_org_document(self, github_org: str, collection: str, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a document from an organization's collection."""
        try:
            doc = self.db.collection('organizations').document(github_org).collection(collection).document(document_id).get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            print(f"Error getting org document {github_org}/{collection}/{document_id}: {e}")
            return None
    
    def set_org_document(self, github_org: str, collection: str, document_id: str, data: Dict[str, Any], merge: bool = False) -> bool:
        """Set a document in an organization's collection."""
        try:
            self.db.collection('organizations').document(github_org).collection(collection).document(document_id).set(data, merge=merge)
            return True
        except Exception as e:
            print(f"Error setting org document {github_org}/{collection}/{document_id}: {e}")
            return False
    
    def update_org_document(self, github_org: str, collection: str, document_id: str, data: Dict[str, Any]) -> bool:
        """Update a document in an organization's collection."""
        try:
            self.db.collection('organizations').document(github_org).collection(collection).document(document_id).update(data)
            return True
        except Exception as e:
            print(f"Error updating org document {github_org}/{collection}/{document_id}: {e}")
            return False
    
    def query_org_collection(self, github_org: str, collection: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Query an organization's collection with optional filters."""
        try:
            query = self.db.collection('organizations').document(github_org).collection(collection)
            
            if filters:
                for field, value in filters.items():
                    query = query.where(field, '==', value)
            
            docs = query.stream()
            return {doc.id: doc.to_dict() for doc in docs}
        except Exception as e:
            print(f"Error querying org collection {github_org}/{collection}: {e}")
            return {}

    def get_org_from_server(self, discord_server_id: str) -> Optional[str]:
        """Get GitHub organization name from Discord server ID."""
        server_config = self.get_server_config(discord_server_id)
        return server_config.get('github_org') if server_config else None

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

# Global multi-tenant instance
_mt_client = None

def get_mt_client() -> FirestoreMultiTenant:
    """Get global multi-tenant Firestore client."""
    global _mt_client
    if _mt_client is None:
        _mt_client = FirestoreMultiTenant()
    return _mt_client

ORG_SCOPED_COLLECTIONS = {
    'repo_stats',
    'pr_config',
    'repository_labels',
    'contributions',
}
GLOBAL_COLLECTIONS = {
    'global_config',
}

def get_document(collection: str, document_id: str, discord_server_id: str = None, github_org: str = None) -> Optional[Dict[str, Any]]:
    """Get a document from Firestore with explicit collection routing."""
    mt_client = get_mt_client()

    if collection in ORG_SCOPED_COLLECTIONS:
        if not github_org:
            if not discord_server_id:
                raise ValueError(f"discord_server_id or github_org required for org-scoped collection: {collection}")
            github_org = mt_client.get_org_from_server(discord_server_id)
            if not github_org:
                raise ValueError(f"No GitHub org found for Discord server: {discord_server_id}")
        return mt_client.get_org_document(github_org, collection, document_id)

    if collection == 'discord_users':
        if discord_server_id:
            raise ValueError("discord_users is global; do not pass discord_server_id")
        return mt_client.get_user_mapping(document_id)

    if collection in GLOBAL_COLLECTIONS:
        db = _get_firestore_client()
        doc = db.collection(collection).document(document_id).get()
        return doc.to_dict() if doc.exists else None

    raise ValueError(f"Unsupported collection: {collection}")

def set_document(collection: str, document_id: str, data: Dict[str, Any], merge: bool = False, discord_server_id: str = None, github_org: str = None) -> bool:
    """Set a document in Firestore with explicit collection routing."""
    mt_client = get_mt_client()

    if collection in ORG_SCOPED_COLLECTIONS:
        if not github_org:
            if not discord_server_id:
                raise ValueError(f"discord_server_id or github_org required for org-scoped collection: {collection}")
            github_org = mt_client.get_org_from_server(discord_server_id)
            if not github_org:
                raise ValueError(f"No GitHub org found for Discord server: {discord_server_id}")
        return mt_client.set_org_document(github_org, collection, document_id, data, merge)

    if collection == 'discord_users':
        if discord_server_id:
            raise ValueError("discord_users is global; do not pass discord_server_id")
        return mt_client.set_user_mapping(document_id, data)

    if collection in GLOBAL_COLLECTIONS:
        db = _get_firestore_client()
        db.collection(collection).document(document_id).set(data, merge=merge)
        return True

    raise ValueError(f"Unsupported collection: {collection}")

def update_document(collection: str, document_id: str, data: Dict[str, Any], discord_server_id: str = None) -> bool:
    """Update a document in Firestore with explicit collection routing."""
    mt_client = get_mt_client()

    if collection in ORG_SCOPED_COLLECTIONS:
        if not discord_server_id:
            raise ValueError(f"discord_server_id required for org-scoped collection: {collection}")
        github_org = mt_client.get_org_from_server(discord_server_id)
        if not github_org:
            raise ValueError(f"No GitHub org found for Discord server: {discord_server_id}")
        return mt_client.update_org_document(github_org, collection, document_id, data)

    if collection == 'discord_users':
        if discord_server_id:
            raise ValueError("discord_users is global; do not pass discord_server_id")
        return mt_client.set_user_mapping(document_id, data)

    if collection in GLOBAL_COLLECTIONS:
        db = _get_firestore_client()
        db.collection(collection).document(document_id).update(data)
        return True

    raise ValueError(f"Unsupported collection: {collection}")

def delete_document(collection: str, document_id: str, discord_server_id: str = None) -> bool:
    """Delete a document in Firestore with explicit collection routing."""
    mt_client = get_mt_client()

    if collection in ORG_SCOPED_COLLECTIONS:
        if not discord_server_id:
            raise ValueError(f"discord_server_id required for org-scoped collection: {collection}")
        github_org = mt_client.get_org_from_server(discord_server_id)
        if not github_org:
            raise ValueError(f"No GitHub org found for Discord server: {discord_server_id}")
        mt_client.db.collection('organizations').document(github_org).collection(collection).document(document_id).delete()
        return True

    if collection == 'discord_users':
        if discord_server_id:
            raise ValueError("discord_users is global; do not pass discord_server_id")
        _get_firestore_client().collection('discord_users').document(document_id).delete()
        return True

    if collection in GLOBAL_COLLECTIONS:
        _get_firestore_client().collection(collection).document(document_id).delete()
        return True

    raise ValueError(f"Unsupported collection: {collection}")

def query_collection(collection: str, filters: Optional[Dict[str, Any]] = None, discord_server_id: str = None) -> Dict[str, Any]:
    """Query a collection with explicit collection routing."""
    mt_client = get_mt_client()

    if collection in ORG_SCOPED_COLLECTIONS:
        if not discord_server_id:
            raise ValueError(f"discord_server_id required for org-scoped collection: {collection}")
        github_org = mt_client.get_org_from_server(discord_server_id)
        if not github_org:
            raise ValueError(f"No GitHub org found for Discord server: {discord_server_id}")
        return mt_client.query_org_collection(github_org, collection, filters)

    if collection == 'discord_users':
        if discord_server_id:
            raise ValueError("discord_users is global; do not pass discord_server_id")
        db = _get_firestore_client()
        query = db.collection('discord_users')
    elif collection in GLOBAL_COLLECTIONS:
        db = _get_firestore_client()
        query = db.collection(collection)
    else:
        raise ValueError(f"Unsupported collection: {collection}")

    if filters:
        for field, value in filters.items():
            query = query.where(field, '==', value)

    docs = query.stream()
    return {doc.id: doc.to_dict() for doc in docs}
