"""
Core Module

Dependency injection container and service management.
"""

from .container import ServiceContainer
from .interfaces import IDataProcessor, IDiscordService, IStorageService
from .services import FirestoreService, DiscordBotService

__all__ = [
    'ServiceContainer',
    'IDataProcessor', 
    'IDiscordService',
    'IStorageService',
    'FirestoreService',
    'DiscordBotService'
] 