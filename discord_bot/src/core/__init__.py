"""
Core Module

Service management and configuration for the Discord bot.
"""

from src.services.guild_service import GuildService
from src.services.github_service import GitHubService
from src.services.role_service import RoleService
from src.services.notification_service import NotificationService

from shared.firestore import (
    get_document, set_document, update_document, query_collection
)

__all__ = [
    'get_document', 'set_document', 'update_document', 'query_collection',
    'GuildService',
    'GitHubService', 
    'RoleService',
    'NotificationService'
] 