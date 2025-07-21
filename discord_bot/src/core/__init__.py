"""
Core Module

Dependency injection container, service management, and configuration.
"""

from .container import ServiceContainer
from .interfaces import IDataProcessor, IDiscordService, IStorageService, IGitHubService
from .services import FirestoreService, DiscordBotService
from .github_service import GitHubService
from .config import ConfigurationManager, get_config, create_config_manager

__all__ = [
    'ServiceContainer',
    'IDataProcessor', 
    'IDiscordService',
    'IStorageService',
    'IGitHubService',
    'FirestoreService',
    'DiscordBotService', 
    'GitHubService',
    'ConfigurationManager',
    'get_config',
    'create_config_manager'
] 