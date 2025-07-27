"""
Configuration Management

Simple configuration functions for environment variables and paths.
"""

import os

def get_firebase_credentials_path() -> str:
    """Get the path to Firebase credentials from environment."""
    env_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not env_path:
        raise EnvironmentError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
    
    if not os.path.exists(env_path):
        raise FileNotFoundError(f"Firebase credentials file not found: {env_path}")
    
    return env_path

def get_discord_token() -> str:
    """Get Discord bot token."""
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        raise ValueError("DISCORD_BOT_TOKEN environment variable is required")
    return token

def get_github_token() -> str:
    """Get GitHub API token."""
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is required")
    return token

def get_repo_owner() -> str:
    """Get GitHub repository owner."""
    return os.getenv('REPO_OWNER', 'ruxailab')

def get_oauth_base_url() -> str:
    """Get OAuth base URL."""
    url = os.getenv('OAUTH_BASE_URL')
    if not url:
        raise ValueError("OAUTH_BASE_URL environment variable is required")
    return url

def get_github_client_id() -> str:
    """Get GitHub OAuth client ID."""
    client_id = os.getenv('GITHUB_CLIENT_ID')
    if not client_id:
        raise ValueError("GITHUB_CLIENT_ID environment variable is required")
    return client_id

def get_github_client_secret() -> str:
    """Get GitHub OAuth client secret."""
    client_secret = os.getenv('GITHUB_CLIENT_SECRET')
    if not client_secret:
        raise ValueError("GITHUB_CLIENT_SECRET environment variable is required")
    return client_secret

def get_port() -> int:
    """Get server port."""
    return int(os.getenv('PORT', '8080')) 