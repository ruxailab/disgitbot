"""
Core Module

Service management and configuration for the Discord bot.
"""

from ..services.guild_service import GuildService
from ..services.github_service import GitHubService
from ..services.role_service import RoleService
from ..services.notification_service import NotificationService

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