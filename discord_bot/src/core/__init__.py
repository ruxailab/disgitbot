"""
Core Module

Service management and configuration for the Discord bot.
"""

from .database import (
    get_document, set_document, update_document, query_collection
)
from .services import DiscordBotService
from .github_service import GitHubService
from .role_service import RoleService
from . import config

__all__ = [
    'get_document', 'set_document', 'update_document', 'query_collection',
    'DiscordBotService',
    'GitHubService', 
    'RoleService',
    'config'
] 