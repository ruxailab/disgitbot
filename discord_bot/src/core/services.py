"""
Core Services

Concrete implementations for Discord bot functionality.
"""

import os
import discord
from discord.ext import commands
from typing import Dict, Any, Optional
import firebase_admin
from firebase_admin import credentials, firestore

from .interfaces import IRoleService
from .config import get_config

class FirestoreService:
    """Firestore implementation for data storage."""
    
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

class DiscordBotService:
    """Discord bot implementation for role and channel management."""
    
    def __init__(self, role_service: Optional[IRoleService] = None):
        self._client = None
        config = get_config()
        discord_config = config.get_discord_config()
        self._token = discord_config.bot_token
        self._role_service = role_service
        
        if not self._token:
            raise ValueError("DISCORD_BOT_TOKEN environment variable is required")
    
    async def _ensure_client(self):
        """Ensure Discord client is initialized."""
        if not self._client:
            intents = discord.Intents.default()
            intents.message_content = True
            intents.members = True
            self._client = discord.Client(intents=intents)
    
    async def update_roles(self, user_mappings: Dict[str, str], contributions: Dict[str, Any]) -> bool:
        """Update user roles based on contributions."""
        try:
            await self._ensure_client()
            
            if not self._client.is_ready():
                await self._client.start(self._token)
            
            total_updated = 0
            for guild in self._client.guilds:
                print(f"Updating roles in guild: {guild.name}")
                updated_count = await self._update_roles_for_guild(guild, user_mappings, contributions)
                total_updated += updated_count
                print(f"Updated {updated_count} members in {guild.name}")
            
            print(f"Updated roles for {total_updated} total members")
            return True
            
        except Exception as e:
            print(f"Error updating roles: {e}")
            return False
        finally:
            if self._client and self._client.is_ready():
                await self._client.close()
    
    async def _update_roles_for_guild(self, guild: discord.Guild, user_mappings: Dict[str, str], contributions: Dict[str, Any]) -> int:
        """Update roles for a single guild using role service."""
        if not self._role_service:
            print("Role service not available - skipping role updates")
            return 0
        
        hall_of_fame_data = self._role_service.get_hall_of_fame_data()
        medal_assignments = self._role_service.get_medal_assignments(hall_of_fame_data or {})
        print(f"Medal assignments: {medal_assignments}")
        
        roles = {}
        existing_roles = {role.name: role for role in guild.roles}
        
        all_role_names = self._role_service.get_all_role_names()
        
        # Ensure the required roles exist or create them
        for role_name in all_role_names:
            if role_name in existing_roles:
                print(f"Role {role_name} already exists, skipping creation.")
                roles[role_name] = existing_roles[role_name]
            else:
                try:
                    print(f"Creating role: {role_name}")
                    role_color = self._role_service.get_role_color(role_name)
                    if role_color:
                        roles[role_name] = await guild.create_role(
                            name=role_name, 
                            color=discord.Color.from_rgb(*role_color)
                        )
                    else:
                        roles[role_name] = await guild.create_role(name=role_name)
                except discord.Forbidden:
                    print(f"Insufficient permissions to create role: {role_name}")
                    continue
                except Exception as e:
                    print(f"Error creating role {role_name}: {e}")
                    continue
        
        # Update roles for each member
        updated_count = 0
        for member in guild.members:
            github_username = user_mappings.get(str(member.id))
            if not github_username:
                continue
            user_data = contributions.get(github_username)
            if not user_data:
                continue
            
            # Remove all roles from the member except @everyone
            roles_to_remove = [role for role in member.roles if role.name != "@everyone"]
            try:
                if roles_to_remove:
                    await member.remove_roles(*roles_to_remove)
                    print(f"Removed all roles from {member.name}")
            except Exception as e:
                print(f"Error removing roles from {member.name}: {e}")
            
            # Get contribution counts
            pr_count = user_data.get("pr_count", 0)
            issues_count = user_data.get("issues_count", 0)
            commits_count = user_data.get("commits_count", 0)
            
            # Use role service to determine roles
            pr_role, issue_role, commit_role = self._role_service.determine_roles(
                pr_count, issues_count, commits_count
            )
            print(pr_role, issue_role, commit_role)
            new_role_names = [pr_role, issue_role, commit_role]
            
            # Add medal role if user is in top 3 all-time PRs
            if github_username in medal_assignments:
                medal_role = medal_assignments[github_username]
                new_role_names.append(medal_role)
                print(f"Adding medal role {medal_role} to {member.name}")
            
            # Add roles to the member
            for role_name in new_role_names:
                if role_name and role_name in roles:
                    try:
                        await member.add_roles(roles[role_name])
                        print(f"Added role {role_name} to {member.name}")
                    except Exception as e:
                        print(f"Error adding role {role_name} to {member.name}: {e}")
            
            updated_count += 1
        
        return updated_count
    
    async def update_channels(self, metrics: Dict[str, Any]) -> bool:
        """Update channel names with repository metrics."""
        try:
            await self._ensure_client()
            
            if not self._client.is_ready():
                await self._client.start(self._token)
            
            for guild in self._client.guilds:
                print(f"Updating channels in guild: {guild.name}")
                
                # Find or create stats category
                stats_category = discord.utils.get(guild.categories, name="REPOSITORY STATS")
                if not stats_category:
                    stats_category = await guild.create_category("REPOSITORY STATS")
                
                # Channel names for all repository metrics
                channels_to_update = [
                    f"Stars: {metrics.get('stars_count', 0)}",
                    f"Forks: {metrics.get('forks_count', 0)}",
                    f"Contributors: {metrics.get('total_contributors', 0)}",
                    f"PRs: {metrics.get('pr_count', 0)}",
                    f"Issues: {metrics.get('issues_count', 0)}",
                    f"Commits: {metrics.get('commits_count', 0)}"
                ]
                
                # Keywords for matching existing channels
                stats_keywords = ["Stars:", "Forks:", "Contributors:", "PRs:", "Issues:", "Commits:"]
                existing_stats_channels = {}
                
                for channel in stats_category.voice_channels:
                    for keyword in stats_keywords:
                        if channel.name.startswith(keyword):
                            existing_stats_channels[keyword] = channel
                            break
                
                # Update or create channels
                for target_name in channels_to_update:
                    keyword = target_name.split(":")[0] + ":"
                    
                    if keyword in existing_stats_channels:
                        channel = existing_stats_channels[keyword]
                        if channel.name != target_name:
                            await channel.edit(name=target_name)
                    else:
                        await guild.create_voice_channel(name=target_name, category=stats_category)
                
                print(f"Channels updated in {guild.name}")
            
            return True
            
        except Exception as e:
            print(f"Error updating channels: {e}")
            return False
        finally:
            if self._client and self._client.is_ready():
                await self._client.close()
    
    async def send_notification(self, channel_id: str, message: str) -> bool:
        """Send a notification message to a specific channel."""
        try:
            await self._ensure_client()
            
            if not self._client.is_ready():
                await self._client.start(self._token)
            
            channel = self._client.get_channel(int(channel_id))
            if channel:
                await channel.send(message)
                print(f"Sent notification to channel {channel_id}")
                return True
            else:
                print(f"Channel {channel_id} not found")
                return False
                
        except Exception as e:
            print(f"Error sending notification: {e}")
            return False
        finally:
            if self._client and self._client.is_ready():
                await self._client.close() 