"""
Configuration Management

Centralized configuration management using Factory pattern.
Handles all environment variables, paths, and application settings.
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv

@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    credentials_path: Optional[str] = None
    project_id: Optional[str] = None

@dataclass
class GitHubConfig:
    """GitHub API configuration settings."""
    token: Optional[str] = None
    repo_owner: str = "ruxailab"
    api_url: str = "https://api.github.com"

@dataclass
class DiscordConfig:
    """Discord bot configuration settings."""
    bot_token: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None

@dataclass
class ServerConfig:
    """Server configuration settings."""
    oauth_base_url: Optional[str] = None
    port: int = 8080

class ConfigurationManager:
    """
    Centralized configuration manager using Factory pattern.
    Provides type-safe access to all configuration settings.
    """
    
    def __init__(self, env_file: Optional[str] = None):
        self._database_config: Optional[DatabaseConfig] = None
        self._github_config: Optional[GitHubConfig] = None
        self._discord_config: Optional[DiscordConfig] = None
        self._server_config: Optional[ServerConfig] = None
        
        self._load_environment(env_file)
    
    def _load_environment(self, env_file: Optional[str] = None) -> None:
        """Load environment variables from file and system."""
        if env_file:
            load_dotenv(env_file)
        else:
            # Try common locations for .env file
            env_paths = [
                'discord_bot/config/.env',
                'config/.env',
                '.env'
            ]
            
            for path in env_paths:
                if os.path.exists(path):
                    load_dotenv(path)
                    break
    
    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration using lazy initialization."""
        if self._database_config is None:
            self._database_config = self._create_database_config()
        return self._database_config
    
    def get_github_config(self) -> GitHubConfig:
        """Get GitHub configuration using lazy initialization."""
        if self._github_config is None:
            self._github_config = self._create_github_config()
        return self._github_config
    
    def get_discord_config(self) -> DiscordConfig:
        """Get Discord configuration using lazy initialization."""
        if self._discord_config is None:
            self._discord_config = self._create_discord_config()
        return self._discord_config
    
    def get_server_config(self) -> ServerConfig:
        """Get server configuration using lazy initialization."""
        if self._server_config is None:
            self._server_config = self._create_server_config()
        return self._server_config
    
    def _create_database_config(self) -> DatabaseConfig:
        """Factory method for database configuration."""
        return DatabaseConfig(
            credentials_path=os.getenv('GOOGLE_APPLICATION_CREDENTIALS'),
            project_id=os.getenv('GOOGLE_PROJECT_ID')
        )
    
    def _create_github_config(self) -> GitHubConfig:
        """Factory method for GitHub configuration."""
        return GitHubConfig(
            token=os.getenv('GITHUB_TOKEN'),
            repo_owner=os.getenv('REPO_OWNER', 'ruxailab'),
            api_url=os.getenv('GITHUB_API_URL', 'https://api.github.com')
        )
    
    def _create_discord_config(self) -> DiscordConfig:
        """Factory method for Discord configuration."""
        return DiscordConfig(
            bot_token=os.getenv('DISCORD_BOT_TOKEN'),
            client_id=os.getenv('GITHUB_CLIENT_ID'),
            client_secret=os.getenv('GITHUB_CLIENT_SECRET')
        )
    
    def _create_server_config(self) -> ServerConfig:
        """Factory method for server configuration."""
        return ServerConfig(
            oauth_base_url=os.getenv('OAUTH_BASE_URL'),
            port=int(os.getenv('PORT', '8080'))
        )
    
    def validate_required_settings(self) -> Dict[str, bool]:
        """Validate that all required configuration settings are present."""
        validations = {}
        
        # Validate GitHub settings
        github_config = self.get_github_config()
        validations['github_token'] = bool(github_config.token)
        validations['repo_owner'] = bool(github_config.repo_owner)
        
        # Validate Discord settings
        discord_config = self.get_discord_config()
        validations['discord_token'] = bool(discord_config.bot_token)
        
        # Validate Database settings
        database_config = self.get_database_config()
        validations['firebase_credentials'] = bool(database_config.credentials_path)
        
        return validations
    
    def get_firebase_credentials_path(self) -> str:
        """Get Firebase credentials path with fallback logic."""
        db_config = self.get_database_config()
        
        # First try environment variable (preferred for production)
        if db_config.credentials_path and os.path.exists(db_config.credentials_path):
            return os.path.abspath(db_config.credentials_path)
        
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
        
        # If we reach here, show what we tried
        attempted_paths = [db_config.credentials_path] + fallback_paths if db_config.credentials_path else fallback_paths
        attempted_paths = [os.path.abspath(p) for p in attempted_paths if p]
        
        raise FileNotFoundError(
            f"Firebase credentials not found. Tried:\n" + 
            "\n".join(f"  - {path}" for path in attempted_paths)
        )

# Global configuration manager instance (Singleton pattern)
_config_manager: Optional[ConfigurationManager] = None

def get_config() -> ConfigurationManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager()
    return _config_manager

def create_config_manager(env_file: Optional[str] = None) -> ConfigurationManager:
    """Factory function to create a new configuration manager."""
    return ConfigurationManager(env_file) 