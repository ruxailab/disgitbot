"""
Core Services

Discord bot functionality.
"""

import discord
from discord.ext import commands
from typing import Dict, Any, Optional, List
import time
from .config import get_discord_token
from shared.firestore import get_document, set_document, update_document, query_collection

class DiscordBotService:
    """Discord bot implementation for role and channel management."""
    
    def __init__(self, role_service = None):
        self._token = get_discord_token()
        self._role_service = role_service
    
    async def update_roles_and_channels(self, user_mappings: Dict[str, str], contributions: Dict[str, Any], metrics: Dict[str, Any]) -> bool:
        """Update Discord roles and channels in a single connection session."""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        client = discord.Client(intents=intents)
        
        success = False
        
        @client.event
        async def on_ready():
            nonlocal success
            try:
                print(f"Connected as {client.user}")
                print(f"Discord client connected to {len(client.guilds)} guilds")
                
                if not client.guilds:
                    print("WARNING: Bot is not connected to any Discord servers")
                    return
                
                for guild in client.guilds:
                    print(f"Processing guild: {guild.name} (ID: {guild.id})")
                    
                    # Update roles
                    updated_count = await self._update_roles_for_guild(guild, user_mappings, contributions)
                    print(f"Updated {updated_count} members in {guild.name}")
                    
                    # Update channels
                    await self._update_channels_for_guild(guild, metrics)
                    print(f"Updated channels in {guild.name}")
                
                success = True
                print("Discord updates completed successfully")
                
            except Exception as e:
                print(f"Error in update process: {e}")
                import traceback
                traceback.print_exc()
                success = False
            finally:
                await client.close()
        
        try:
            await client.start(self._token)
            return success
        except Exception as e:
            print(f"Error connecting to Discord: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def _update_roles_for_guild(self, guild: discord.Guild, user_mappings: Dict[str, str], contributions: Dict[str, Any]) -> int:
        """Update roles for a single guild using role service."""
        if not self._role_service:
            print("Role service not available - skipping role updates")
            return 0
        
        hall_of_fame_data = self._role_service.get_hall_of_fame_data()
        medal_assignments = self._role_service.get_medal_assignments(hall_of_fame_data or {})
        
        obsolete_roles = self._role_service.get_obsolete_role_names()
        current_roles = set(self._role_service.get_all_role_names())
        existing_roles = {role.name: role for role in guild.roles}
        
        # Remove obsolete roles from server
        for role_name in obsolete_roles:
            if role_name in existing_roles:
                try:
                    await existing_roles[role_name].delete()
                    print(f"Deleted obsolete role: {role_name}")
                except Exception as e:
                    print(f"Error deleting role {role_name}: {e}")
        
        # Create missing current roles
        roles = {}
        for role_name in current_roles:
            if role_name in existing_roles:
                roles[role_name] = existing_roles[role_name]
            else:
                try:
                    role_color = self._role_service.get_role_color(role_name)
                    roles[role_name] = await guild.create_role(
                        name=role_name, 
                        color=discord.Color.from_rgb(*role_color) if role_color else discord.Color.default()
                    )
                    print(f"Created role: {role_name}")
                except Exception as e:
                    print(f"Error creating role {role_name}: {e}")
        
        # Update users
        updated_count = 0
        for member in guild.members:
            github_username = user_mappings.get(str(member.id))
            if not github_username or github_username not in contributions:
                continue
            
            user_data = contributions[github_username]
            pr_count = user_data.get("pr_count", 0)
            issues_count = user_data.get("issues_count", 0)
            commits_count = user_data.get("commits_count", 0)
            
            # Get correct roles for user
            pr_role, issue_role, commit_role = self._role_service.determine_roles(pr_count, issues_count, commits_count)
            correct_roles = {pr_role, issue_role, commit_role}
            if github_username in medal_assignments:
                correct_roles.add(medal_assignments[github_username])
            correct_roles.discard(None)
            
            # Remove obsolete roles and roles user outgrew
            user_bot_roles = [role for role in member.roles if role.name in (obsolete_roles | current_roles)]
            roles_to_remove = [role for role in user_bot_roles if role.name not in correct_roles]
            
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove)
                print(f"Removed {[r.name for r in roles_to_remove]} from {member.name}")
            
            # Add missing roles
            for role_name in correct_roles:
                if role_name in roles and roles[role_name] not in member.roles:
                    await member.add_roles(roles[role_name])
                    print(f"Added {role_name} to {member.name}")
            
            if roles_to_remove or any(role_name in roles and roles[role_name] not in member.roles for role_name in correct_roles):
                updated_count += 1
        
        return updated_count
    
    async def _update_channels_for_guild(self, guild: discord.Guild, metrics: Dict[str, Any]) -> None:
        """Update channel names with repository metrics for a single guild."""
        try:
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
                
                try:
                    if keyword in existing_stats_channels:
                        channel = existing_stats_channels[keyword]
                        if channel.name != target_name:
                            await channel.edit(name=target_name)
                            print(f"Updated channel: {target_name}")
                    else:
                        await guild.create_voice_channel(name=target_name, category=stats_category)
                        print(f"Created channel: {target_name}")
                except discord.Forbidden:
                    print(f"Permission denied for channel: {target_name}")
                except Exception as e:
                    print(f"Error with channel {target_name}: {e}")
            
            print(f"Channels updated successfully in {guild.name}")
            
        except Exception as e:
            print(f"Error updating channels for guild {guild.name}: {e}")
            import traceback
            traceback.print_exc() 