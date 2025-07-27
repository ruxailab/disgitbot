"""
Core Module

Service management and configuration for the Discord bot.
"""

from .services import DiscordBotService
from .github_service import GitHubService
from .role_service import RoleService
from . import config
from shared.firestore import (
    get_document, set_document, update_document, query_collection
)

__all__ = [
    'get_document', 'set_document', 'update_document', 'query_collection',
    'DiscordBotService',
    'GitHubService', 
    'RoleService',
    'config'
] 