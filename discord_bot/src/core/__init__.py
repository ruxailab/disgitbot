"""
Core Module

Service management and configuration for the Discord bot.
"""


from .services import FirestoreService, DiscordBotService
from .github_service import GitHubService
from .role_service import RoleService
from .config import ConfigurationManager, get_config, create_config_manager

__all__ = [
    'FirestoreService',
    'DiscordBotService', 
    'GitHubService',
    'RoleService',
    'ConfigurationManager',
    'get_config',
    'create_config_manager'
] 