"""
Core Module

Dependency injection container, service management, and configuration.
"""

from .container import ServiceContainer
from .interfaces import IDataProcessor, IDiscordService, IStorageService, IGitHubService, IRoleService
from .services import FirestoreService, DiscordBotService
from .github_service import GitHubService
from .role_service import RoleService
from .config import ConfigurationManager, get_config, create_config_manager

__all__ = [
    'ServiceContainer',
    'IDataProcessor', 
    'IDiscordService',
    'IStorageService',
    'IGitHubService',
    'IRoleService',
    'FirestoreService',
    'DiscordBotService', 
    'GitHubService',
    'RoleService',
    'ConfigurationManager',
    'get_config',
    'create_config_manager'
] 