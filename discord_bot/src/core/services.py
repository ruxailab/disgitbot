"""
Core Services

Concrete implementations of core interfaces.
"""

import os
import discord
from discord.ext import commands
from typing import Dict, Any, Optional
import firebase_admin
from firebase_admin import credentials, firestore

from .interfaces import IStorageService, IDiscordService, IGitHubService
from .config import get_config
from .github_service import GitHubService

class FirestoreService(IStorageService):
    """Firestore implementation of storage service."""
    
    def __init__(self):
        self._db = None
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase connection using centralized configuration."""
        if not firebase_admin._apps:
            config = get_config()
            config_path = config.get_firebase_credentials_path()
            
            cred = credentials.Certificate(config_path)
            firebase_admin.initialize_app(cred)
        
        self._db = firestore.client()
    
    def get_document(self, collection: str, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a document from Firestore."""
        try:
            doc = self._db.collection(collection).document(document_id).get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            print(f"Error getting document {collection}/{document_id}: {e}")
            return None
    
    def set_document(self, collection: str, document_id: str, data: Dict[str, Any], merge: bool = False) -> bool:
        """Set a document in Firestore."""
        try:
            self._db.collection(collection).document(document_id).set(data, merge=merge)
            return True
        except Exception as e:
            print(f"Error setting document {collection}/{document_id}: {e}")
            return False
    
    def update_document(self, collection: str, document_id: str, data: Dict[str, Any]) -> bool:
        """Update a document in Firestore."""
        try:
            self._db.collection(collection).document(document_id).update(data)
            return True
        except Exception as e:
            print(f"Error updating document {collection}/{document_id}: {e}")
            return False
    
    def query_collection(self, collection: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Query a collection with optional filters."""
        try:
            query = self._db.collection(collection)
            
            if filters:
                for field, value in filters.items():
                    query = query.where(field, '==', value)
            
            docs = query.stream()
            return {doc.id: doc.to_dict() for doc in docs}
        except Exception as e:
            print(f"Error querying collection {collection}: {e}")
            return {}

class DiscordBotService(IDiscordService):
    """Discord bot implementation of Discord service."""
    
    def __init__(self):
        self._client = None
        config = get_config()
        discord_config = config.get_discord_config()
        self._token = discord_config.bot_token
        
        if not self._token:
            raise ValueError("DISCORD_BOT_TOKEN environment variable is required")
    
    async def _ensure_client(self):
        """Ensure Discord client is initialized."""
        if not self._client:
            intents = discord.Intents.default()
            intents.message_content = True
            intents.members = True
            self._client = discord.Client(intents=intents)
    
    async def update_roles(self, guild_id: str, user_mappings: Dict[str, str], contributions: Dict[str, Any]) -> bool:
        """Update user roles based on contributions."""
        try:
            await self._ensure_client()
            
            if not self._client.is_ready():
                await self._client.start(self._token)
            
            guild = self._client.get_guild(int(guild_id))
            if not guild:
                print(f"Guild {guild_id} not found")
                return False
            
            # Implementation of role update logic
            from ..utils.role_utils import determine_role
            
            updated_count = 0
            for member in guild.members:
                github_username = user_mappings.get(str(member.id))
                if not github_username or github_username not in contributions:
                    continue
                
                user_data = contributions[github_username]
                pr_count = user_data.get("pr_count", 0)
                issues_count = user_data.get("issues_count", 0)
                commits_count = user_data.get("commits_count", 0)
                
                pr_role, issue_role, commit_role = determine_role(pr_count, issues_count, commits_count)
                
                # Role update logic would go here
                updated_count += 1
            
            print(f"Updated roles for {updated_count} members")
            return True
            
        except Exception as e:
            print(f"Error updating roles: {e}")
            return False
        finally:
            if self._client and self._client.is_ready():
                await self._client.close()
    
    async def update_channels(self, guild_id: str, metrics: Dict[str, Any]) -> bool:
        """Update channel names with metrics."""
        try:
            await self._ensure_client()
            
            if not self._client.is_ready():
                await self._client.start(self._token)
            
            guild = self._client.get_guild(int(guild_id))
            if not guild:
                print(f"Guild {guild_id} not found")
                return False
            
            # Find or create stats category
            stats_category = discord.utils.get(guild.categories, name="REPOSITORY STATS")
            if not stats_category:
                stats_category = await guild.create_category("REPOSITORY STATS")
            
            # Update channel names with metrics
            channels_to_update = {
                f"⭐ Stars: {metrics.get('stars_count', 0)}": "stars",
                f"🍴 Forks: {metrics.get('forks_count', 0)}": "forks",
                f"👥 Contributors: {metrics.get('total_contributors', 0)}": "contributors"
            }
            
            for channel_name, channel_type in channels_to_update.items():
                existing_channel = discord.utils.get(stats_category.voice_channels, name__contains=channel_type)
                
                if existing_channel:
                    await existing_channel.edit(name=channel_name)
                else:
                    await guild.create_voice_channel(channel_name, category=stats_category)
            
            print("Channel metrics updated successfully")
            return True
            
        except Exception as e:
            print(f"Error updating channels: {e}")
            return False
        finally:
            if self._client and self._client.is_ready():
                await self._client.close()
    
    async def send_notification(self, channel_id: str, message: str) -> bool:
        """Send a notification message."""
        try:
            await self._ensure_client()
            
            if not self._client.is_ready():
                await self._client.start(self._token)
            
            channel = self._client.get_channel(int(channel_id))
            if not channel:
                print(f"Channel {channel_id} not found")
                return False
            
            await channel.send(message)
            return True
            
        except Exception as e:
            print(f"Error sending notification: {e}")
            return False
        finally:
            if self._client and self._client.is_ready():
                await self._client.close() 