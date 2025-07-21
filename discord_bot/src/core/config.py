"""
Configuration Management

Simple configuration functions for environment variables and paths.
"""

import os
from dotenv import load_dotenv

def load_env():
    """Load environment variables from .env file."""
    env_paths = [
        'discord_bot/config/.env',
        'config/.env', 
        '.env'
    ]
    
    for path in env_paths:
        if os.path.exists(path):
            load_dotenv(path)
            return
    
    print("WARNING: No .env file found")

# Load env on import
load_env()

def get_firebase_credentials_path() -> str:
    """Get the path to Firebase credentials with fallback logic."""
    # First try environment variable
    env_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if env_path and os.path.exists(env_path):
        return env_path
    
    # Fallback to common locations
    fallback_paths = [
        'discord_bot/config/credentials.json',
        'config/credentials.json',
        os.path.join(os.getcwd(), 'discord_bot', 'config', 'credentials.json'),
        os.path.join(os.getcwd(), 'config', 'credentials.json')
    ]
    
    for path in fallback_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            return abs_path
    
    raise FileNotFoundError(
        f"Firebase credentials not found. Tried:\n" + 
        "\n".join(f"  - {os.path.abspath(path)}" for path in fallback_paths)
    )

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