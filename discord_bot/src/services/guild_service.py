"""
Discord Guild Manager

Manages Discord server roles and channels based on GitHub data.
"""

import discord
from typing import Dict, Any
import os
from shared.firestore import get_mt_client

class GuildService:
    """Manages Discord guild roles and channels based on GitHub activity."""
    
    def __init__(self, role_service = None):
        self._token = os.getenv('DISCORD_BOT_TOKEN')
        if not self._token:
            raise ValueError("DISCORD_BOT_TOKEN environment variable is required")
        self._role_service = role_service
    
    async def update_roles_and_channels(self, discord_server_id: str, user_mappings: Dict[str, str], contributions: Dict[str, Any], metrics: Dict[str, Any]) -> bool:
        """Update Discord roles and channels for a single server.
        
        Delegates to update_multiple_servers() with a single-item list so that
        the bot only connects to Discord once per pipeline run instead of opening
        a new client session for every server (which causes unclosed-connector
        warnings and wastes the connection handshake).
        """
        results = await self.update_multiple_servers([
            {
                'discord_server_id': discord_server_id,
                'user_mappings': user_mappings,
                'contributions': contributions,
                'metrics': metrics,
            }
        ])
        return results.get(discord_server_id, False)

    async def update_multiple_servers(
        self,
        server_jobs: list,
    ) -> Dict[str, bool]:
        """Update roles and channels for multiple Discord servers in a SINGLE
        bot connection, avoiding repeated connect/disconnect overhead and
        preventing unclosed-connector warnings from leftover aiohttp sessions.

        Args:
            server_jobs: list of dicts with keys:
                discord_server_id, user_mappings, contributions, metrics
        Returns:
            dict mapping discord_server_id -> success bool
        """
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        client = discord.Client(intents=intents)

        from shared.firestore import get_mt_client
        mt_client = get_mt_client()

        # Build a quick lookup: server_id -> job
        jobs_by_server = {job['discord_server_id']: job for job in server_jobs}
        results: Dict[str, bool] = {job['discord_server_id']: False for job in server_jobs}

        @client.event
        async def on_ready():
            try:
                print(f"Connected as {client.user}")
                print(f"Discord client connected to {len(client.guilds)} guilds")

                if not client.guilds:
                    print("WARNING: Bot is not connected to any Discord servers")
                    return

                for guild in client.guilds:
                    server_id = str(guild.id)
                    if server_id not in jobs_by_server:
                        print(f"Skipping guild {guild.name} - not the target server")
                        continue

                    job = jobs_by_server[server_id]
                    server_config = mt_client.get_server_config(server_id)
                    github_org = server_config.get('github_org') if server_config else None
                    role_rules = (server_config.get('role_rules') if server_config else {}) or {}

                    print(f"Processing guild: {guild.name} (ID: {guild.id})")
                    try:
                        updated_count = await self._update_roles_for_guild(
                            guild,
                            job['user_mappings'],
                            job['contributions'],
                            github_org,
                            role_rules,
                        )
                        print(f"Updated {updated_count} members in {guild.name}")

                        await self._update_channels_for_guild(guild, job['metrics'])
                        print(f"Updated channels in {guild.name}")

                        results[server_id] = True
                        print(f"Discord updates completed successfully for {guild.name}")
                    except Exception as e:
                        print(f"Error updating guild {guild.name}: {e}")
                        import traceback
                        traceback.print_exc()

            except Exception as e:
                print(f"Error in update process: {e}")
                import traceback
                traceback.print_exc()
            finally:
                await client.close()

        try:
            await client.start(self._token)
        except Exception as e:
            print(f"Error connecting to Discord: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if not client.is_closed():
                await client.close()

        return results
    
    async def _update_roles_for_guild(
        self,
        guild: discord.Guild,
        user_mappings: Dict[str, str],
        contributions: Dict[str, Any],
        github_org: str,
        role_rules: Dict[str, Any]
    ) -> int:
        """Update roles for a single guild using role service."""
        if not self._role_service:
            print("Role service not available - skipping role updates")
            return 0
  
        # Get organization-specific hall of fame data
        from shared.firestore import get_mt_client
        mt_client = get_mt_client()
        hall_of_fame_data = mt_client.get_org_document(github_org, 'repo_stats', 'hall_of_fame') if github_org else None
        medal_assignments = self._role_service.get_medal_assignments(hall_of_fame_data or {})
        
        obsolete_roles = self._role_service.get_obsolete_role_names()
        current_roles = set(self._role_service.get_all_role_names())
        existing_roles = {role.name: role for role in guild.roles}
        existing_roles_by_id = {role.id: role for role in guild.roles}

        custom_role_ids = set()
        custom_role_names = set()
        for rules in role_rules.values():
            if not isinstance(rules, list):
                continue
            for rule in rules:
                role_id = str(rule.get('role_id', '')).strip()
                role_name = str(rule.get('role_name', '')).strip()
                if role_id.isdigit():
                    custom_role_ids.add(int(role_id))
                if role_name:
                    custom_role_names.add(role_name)

        managed_role_names = current_roles | custom_role_names
        
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
        
        def resolve_custom_role(rule: Dict[str, Any]):
            if not rule:
                return None
            role_id = str(rule.get('role_id', '')).strip()
            if role_id.isdigit():
                role_obj = existing_roles_by_id.get(int(role_id))
                if role_obj:
                    return role_obj
            role_name = str(rule.get('role_name', '')).strip()
            if role_name:
                return existing_roles.get(role_name)
            return None

        # Ensure all members are cached before iterating
        if not guild.chunked:
            await guild.chunk()
        
        # Update users
        updated_count = 0
        print(f"Guild has {len(guild.members)} members, user_mappings has {len(user_mappings)} entries")
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
            custom_roles = self._role_service.determine_custom_roles(pr_count, issues_count, commits_count, role_rules)

            pr_role_obj = resolve_custom_role(custom_roles.get('pr')) or existing_roles.get(pr_role)
            issue_role_obj = resolve_custom_role(custom_roles.get('issue')) or existing_roles.get(issue_role)
            commit_role_obj = resolve_custom_role(custom_roles.get('commit')) or existing_roles.get(commit_role)

            correct_role_objs = []
            for role_obj in (pr_role_obj, issue_role_obj, commit_role_obj):
                if role_obj and role_obj not in correct_role_objs:
                    correct_role_objs.append(role_obj)

            if github_username in medal_assignments:
                medal_role_name = medal_assignments[github_username]
                medal_role_obj = existing_roles.get(medal_role_name)
                if medal_role_obj and medal_role_obj not in correct_role_objs:
                    correct_role_objs.append(medal_role_obj)

            correct_role_ids = {role.id for role in correct_role_objs}

            # Remove obsolete roles and roles user outgrew
            user_bot_roles = [
                role for role in member.roles
                if role.name in (obsolete_roles | managed_role_names) or role.id in custom_role_ids
            ]
            roles_to_remove = [role for role in user_bot_roles if role.id not in correct_role_ids]
            
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove)
                print(f"Removed {[r.name for r in roles_to_remove]} from {member.name}")
            
            # Add missing roles
            for role_obj in correct_role_objs:
                if role_obj not in member.roles:
                    await member.add_roles(role_obj)
                    print(f"Added {role_obj.name} to {member.name}")
            
            if roles_to_remove or any(role_obj not in member.roles for role_obj in correct_role_objs):
                updated_count += 1
        
        return updated_count
    
    async def _update_channels_for_guild(self, guild: discord.Guild, metrics: Dict[str, Any]) -> None:
        """Update channel names with repository metrics for a single guild."""
        try:
            print(f"Updating channels in guild: {guild.name}")
            
            # Find or create stats category
            # Use a list scan instead of discord.utils.get so we can detect and
            # clean up duplicate categories (can appear if setup and the pipeline
            # both try to create the category at the same time).
            all_stats_categories = [c for c in guild.categories if c.name == "REPOSITORY STATS"]
            if not all_stats_categories:
                stats_category = await guild.create_category("REPOSITORY STATS")
            else:
                stats_category = all_stats_categories[0]
                # Delete any extras, including all their channels
                for dup in all_stats_categories[1:]:
                    for ch in dup.channels:
                        try:
                            await ch.delete()
                        except Exception:
                            pass
                    try:
                        await dup.delete()
                        print(f"Deleted duplicate REPOSITORY STATS category in {guild.name}")
                    except Exception as e:
                        print(f"Could not delete duplicate category in {guild.name}: {e}")
            
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
