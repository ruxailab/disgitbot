"""
Admin Commands Module

Handles administrative Discord commands like permissions and setup.
"""

import asyncio
import discord
from discord import app_commands
from shared.firestore import get_document, set_document

class AdminCommands:
    """Handles administrative Discord commands."""
    
    def __init__(self, bot):
        self.bot = bot
    
    def register_commands(self):
        """Register all admin commands with the bot."""
        self.bot.tree.add_command(self._check_permissions_command())
        self.bot.tree.add_command(self._setup_command())
        self.bot.tree.add_command(self._sync_command())
        self.bot.tree.add_command(self._setup_voice_stats_command())
        # PR automation commands disabled - keeping code for future re-enablement
        # self.bot.tree.add_command(self._add_reviewer_command())
        # self.bot.tree.add_command(self._remove_reviewer_command())
        # self.bot.tree.add_command(self._list_reviewers_command())
    
    def _check_permissions_command(self):
        """Create the check_permissions command."""
        @app_commands.command(name="check_permissions", description="Check if bot has required permissions")
        async def check_permissions(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)

            guild = interaction.guild
            assert guild is not None, "Command should only work in guilds"
            assert self.bot.user is not None, "Bot user should be available"
            bot_member = guild.get_member(self.bot.user.id)
            assert bot_member is not None, "Bot should be a member of the guild"
            
            required_perms = [
                ("Manage Channels", bot_member.guild_permissions.manage_channels),
                ("Manage Roles", bot_member.guild_permissions.manage_roles),
                ("View Channels", bot_member.guild_permissions.view_channel),
                ("Connect", bot_member.guild_permissions.connect)
            ]
            
            results = []
            for perm_name, has_perm in required_perms:
                status = "PASS" if has_perm else "FAIL"
                results.append(f"{status} {perm_name}")
            
            await interaction.followup.send(f"Bot permissions:\n" + "\n".join(results), ephemeral=True)
        
        return check_permissions

    def _setup_command(self):
        """Create the setup command for server configuration."""
        @app_commands.command(name="setup", description="Get setup link to connect GitHub organization")
        async def setup(interaction: discord.Interaction):
            """Provides setup link for server administrators."""
            await interaction.response.defer(ephemeral=True)

            try:
                # Check if user has administrator permissions
                if not interaction.user.guild_permissions.administrator:
                    await interaction.followup.send("Only server administrators can use this command.", ephemeral=True)
                    return

                guild = interaction.guild
                assert guild is not None, "Command should only work in guilds"

                # Check existing configuration
                from shared.firestore import get_mt_client
                mt_client = get_mt_client()
                server_config = await asyncio.to_thread(mt_client.get_server_config, str(guild.id)) or {}
                if server_config.get('setup_completed'):
                    github_org = server_config.get('github_org', 'unknown')
                    await interaction.followup.send(
                        f"This server is already configured.\n\n"
                        f"GitHub org/account: `{github_org}`\n"
                        f"Users can run `/link` to connect their accounts.\n"
                        f"Admins can adjust roles with `/configure roles`.",
                        ephemeral=True
                    )
                    return

                # Get the base URL from environment
                import os
                from urllib.parse import urlencode
                base_url = os.getenv("OAUTH_BASE_URL")
                if not base_url:
                    await interaction.followup.send("Bot configuration error - please contact support.", ephemeral=True)
                    return

                setup_url = f"{base_url}/setup?{urlencode({'guild_id': guild.id, 'guild_name': guild.name})}"

                setup_message = f"""**DisgitBot Setup Required**

Your server needs to connect a GitHub organization.

**Steps:**
1. Visit: {setup_url}
2. Install the GitHub App and select repositories
3. Users can then link accounts with `/link`
4. Configure roles with `/configure roles`

**Current Status:** Not configured
**After Setup:** Ready to track contributions

This setup is required only once per server."""

                await interaction.followup.send(setup_message, ephemeral=True)

            except Exception as e:
                await interaction.followup.send(f"Error generating setup link: {str(e)}", ephemeral=True)
                print(f"Error in setup command: {e}")
                import traceback
                traceback.print_exc()

        return setup

    def _sync_command(self):
        """Create the sync command for manually triggering data sync."""
        @app_commands.command(name="sync", description="Manually trigger a GitHub data sync for this server")
        async def sync(interaction: discord.Interaction):
            """Triggers the data pipeline to refresh GitHub stats."""
            await interaction.response.defer(ephemeral=True)

            try:
                # Check if user has administrator permissions
                if not interaction.user.guild_permissions.administrator:
                    await interaction.followup.send(
                        "Only server administrators can trigger a sync.",
                        ephemeral=True
                    )
                    return

                guild = interaction.guild
                assert guild is not None, "Command should only work in guilds"
                guild_id = str(guild.id)

                # Check if server is set up
                from shared.firestore import get_mt_client
                mt_client = get_mt_client()
                server_config = await asyncio.to_thread(mt_client.get_server_config, guild_id) or {}

                if not server_config.get('setup_completed'):
                    await interaction.followup.send(
                        "This server hasn't been set up yet. Run `/setup` first to connect a GitHub organization.",
                        ephemeral=True
                    )
                    return

                github_org = server_config.get('github_org')
                if not github_org:
                    await interaction.followup.send(
                        "No GitHub organization found for this server. Run `/setup` to configure.",
                        ephemeral=True
                    )
                    return

                installation_id = server_config.get('github_installation_id')

                # Trigger sync (with cooldown enforcement)
                from src.bot.auth import trigger_sync
                result = await asyncio.to_thread(
                    trigger_sync, guild_id, github_org,
                    installation_id=installation_id, respect_cooldown=True
                )

                if result["cooldown_remaining"] is not None:
                    remaining = result["cooldown_remaining"]
                    hours = remaining // 3600
                    minutes = (remaining % 3600) // 60

                    if hours > 0:
                        time_str = f"{hours}h {minutes}m"
                    else:
                        time_str = f"{minutes}m"

                    embed = discord.Embed(
                        title="⏳ Sync on Cooldown",
                        description=(
                            f"A sync was already dispatched recently.\n\n"
                            f"Next manual sync available in **{time_str}**.\n\n"
                            f"The daily automatic sync also runs at **midnight UTC**.\n\n"
                            f"_Note: if the pipeline run itself failed, wait for the cooldown or contact the bot maintainer._"
                        ),
                        color=0xfee75c  # yellow
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return

                if result["triggered"]:
                    embed = discord.Embed(
                        title="✅ Sync Triggered",
                        description=(
                            f"Data pipeline is now running for **{github_org}**.\n\n"
                            f"Stats will be updated in approximately **5–10 minutes**.\n\n"
                            f"_Use `/getstats` after a few minutes to see fresh data._"
                        ),
                        color=0x43b581  # green
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    error_msg = result.get("error", "Unknown error")
                    embed = discord.Embed(
                        title="❌ Sync Failed",
                        description=error_msg,
                        color=0xed4245  # red
                    )
                    embed.set_footer(text="If this persists, contact the bot maintainer or check GitHub App settings.")
                    await interaction.followup.send(embed=embed, ephemeral=True)

            except Exception as e:
                await interaction.followup.send(
                    f"Error triggering sync: {str(e)}",
                    ephemeral=True
                )
                print(f"Error in sync command: {e}")
                import traceback
                traceback.print_exc()

        return sync

    def _setup_voice_stats_command(self):
        """Create the setup_voice_stats command."""
        @app_commands.command(name="setup_voice_stats", description="Sets up voice channels for repository stats display")
        async def setup_voice_stats(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            
            try:
                guild = interaction.guild
                assert guild is not None, "Command should only work in guilds"
                
                all_stats_categories = [c for c in guild.categories if c.name == "REPOSITORY STATS"]
                if len(all_stats_categories) > 1:
                    # Clean up duplicates — keep the first, delete the rest
                    for dup in all_stats_categories[1:]:
                        for ch in dup.channels:
                            try:
                                await ch.delete()
                            except Exception:
                                pass
                        try:
                            await dup.delete()
                        except Exception:
                            pass
                    await interaction.followup.send(
                        "⚠️ Found duplicate stats categories — cleaned up. "
                        "One 'REPOSITORY STATS' category remains. "
                        "Stats are updated daily via automated workflow."
                    )
                elif all_stats_categories:
                    await interaction.followup.send("Repository stats display already exists! Stats are updated daily via automated workflow.")
                else:
                    await guild.create_category("REPOSITORY STATS")
                    await interaction.followup.send("Repository stats display created! Stats will be updated daily via automated workflow.")
                
            except Exception as e:
                await interaction.followup.send(f"Error setting up voice stats: {str(e)}")
                print(f"Error in setup_voice_stats: {e}")
                import traceback
                traceback.print_exc()
        
        return setup_voice_stats
    
    def _add_reviewer_command(self):
        """Create the add_reviewer command."""
        @app_commands.command(name="add_reviewer", description="Add a GitHub username to the PR reviewer pool")
        @app_commands.describe(username="GitHub username to add as reviewer")
        async def add_reviewer(interaction: discord.Interaction, username: str):
            await interaction.response.defer()
            
            try:
                # Get current reviewer configuration
                discord_server_id = str(interaction.guild.id)
                reviewer_data = await asyncio.to_thread(get_document, 'pr_config', 'reviewers', discord_server_id)
                if not reviewer_data:
                    reviewer_data = {'reviewers': [], 'manual_reviewers': [], 'top_contributor_reviewers': [], 'count': 0}
                
                manual_reviewers = reviewer_data.get('manual_reviewers', [])
                all_reviewers = reviewer_data.get('reviewers', [])
                
                # Check if reviewer already exists
                if username in all_reviewers:
                    await interaction.followup.send(f"GitHub user `{username}` is already in the reviewer pool.")
                    return
                
                # Add to manual reviewers pool
                manual_reviewers.append(username)
                all_reviewers.append(username)
                
                reviewer_data['manual_reviewers'] = manual_reviewers
                reviewer_data['reviewers'] = all_reviewers
                reviewer_data['count'] = len(all_reviewers)
                reviewer_data['last_updated'] = __import__('time').strftime('%Y-%m-%d %H:%M:%S UTC', __import__('time').gmtime())
                
                # Save to Firestore
                success = await asyncio.to_thread(set_document, 'pr_config', 'reviewers', reviewer_data, discord_server_id=discord_server_id)
                
                if success:
                    await interaction.followup.send(f"Successfully added `{username}` to the manual reviewer pool.\nTotal reviewers: {len(all_reviewers)}")
                else:
                    await interaction.followup.send("Failed to add reviewer to the database.")
                    
            except Exception as e:
                await interaction.followup.send(f"Error adding reviewer: {str(e)}")
                print(f"Error in add_reviewer: {e}")
                import traceback
                traceback.print_exc()
        
        return add_reviewer
    
    def _remove_reviewer_command(self):
        """Create the remove_reviewer command."""
        @app_commands.command(name="remove_reviewer", description="Remove a GitHub username from the PR reviewer pool")
        @app_commands.describe(username="GitHub username to remove from reviewers")
        async def remove_reviewer(interaction: discord.Interaction, username: str):
            await interaction.response.defer()
            
            try:
                # Get current reviewer configuration
                discord_server_id = str(interaction.guild.id)
                reviewer_data = await asyncio.to_thread(get_document, 'pr_config', 'reviewers', discord_server_id)
                if not reviewer_data or not reviewer_data.get('reviewers'):
                    await interaction.followup.send("No reviewers found in the database.")
                    return
                
                manual_reviewers = reviewer_data.get('manual_reviewers', [])
                top_contributor_reviewers = reviewer_data.get('top_contributor_reviewers', [])
                
                # Check if reviewer exists and determine which pool
                if username not in reviewer_data.get('reviewers', []):
                    await interaction.followup.send(f"GitHub user `{username}` is not in the reviewer pool.")
                    return
                
                # Only allow removal from manual pool (top contributors are auto-managed)
                if username in manual_reviewers:
                    manual_reviewers.remove(username)
                    all_reviewers = list(set(top_contributor_reviewers + manual_reviewers))
                    
                    reviewer_data['manual_reviewers'] = manual_reviewers
                    reviewer_data['reviewers'] = all_reviewers
                    reviewer_data['count'] = len(all_reviewers)
                    reviewer_data['last_updated'] = __import__('time').strftime('%Y-%m-%d %H:%M:%S UTC', __import__('time').gmtime())
                    
                    # Save to Firestore
                    success = await asyncio.to_thread(set_document, 'pr_config', 'reviewers', reviewer_data, discord_server_id=discord_server_id)
                    
                    if success:
                        await interaction.followup.send(f"Successfully removed `{username}` from the manual reviewer pool.\nTotal reviewers: {len(all_reviewers)}")
                    else:
                        await interaction.followup.send("Failed to remove reviewer from the database.")
                        
                elif username in top_contributor_reviewers:
                    await interaction.followup.send(f"`{username}` is a top contributor reviewer and cannot be manually removed. They will be updated automatically by the system.")
                else:
                    await interaction.followup.send(f"Unable to determine reviewer pool for `{username}`.")
                    
            except Exception as e:
                await interaction.followup.send(f"Error removing reviewer: {str(e)}")
                print(f"Error in remove_reviewer: {e}")
                import traceback
                traceback.print_exc()
        
        return remove_reviewer
    
    def _list_reviewers_command(self):
        """Create the list_reviewers command."""
        @app_commands.command(name="list_reviewers", description="Show current PR reviewer pool and top contributors")
        async def list_reviewers(interaction: discord.Interaction):
            await interaction.response.defer()
            
            try:
                # Get reviewer data
                discord_server_id = str(interaction.guild.id)
                reviewer_data = await asyncio.to_thread(get_document, 'pr_config', 'reviewers', discord_server_id)
                contributor_data = await asyncio.to_thread(get_document, 'repo_stats', 'contributor_summary', discord_server_id)
                
                embed = discord.Embed(
                    title="PR Reviewer Pool Status",
                    color=discord.Color.blue()
                )
                
                # Show current reviewers by pool
                if reviewer_data and reviewer_data.get('reviewers'):
                    # Top contributor reviewers
                    top_contributors = reviewer_data.get('top_contributor_reviewers', [])
                    if top_contributors:
                        top_text = '\n'.join([f"• {reviewer}" for reviewer in top_contributors])
                        embed.add_field(
                            name=f"Top Contributor Reviewers ({len(top_contributors)})",
                            value=top_text,
                            inline=True
                        )
                    
                    # Manual reviewers
                    manual_reviewers = reviewer_data.get('manual_reviewers', [])
                    if manual_reviewers:
                        manual_text = '\n'.join([f"• {reviewer}" for reviewer in manual_reviewers])
                        embed.add_field(
                            name=f"Manual Reviewers ({len(manual_reviewers)})",
                            value=manual_text,
                            inline=True
                        )
                    
                    total_reviewers = reviewer_data['reviewers']
                    embed.add_field(
                        name="Pool Info",
                        value=f"Total Reviewers: {len(total_reviewers)}\nLast Updated: {reviewer_data.get('last_updated', 'Unknown')}",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="Current Reviewers",
                        value="No reviewers configured",
                        inline=False
                    )
                
                # Show top contributors (potential reviewers)
                if contributor_data and contributor_data.get('top_contributors'):
                    top_contributors = contributor_data['top_contributors'][:7]
                    contrib_text = '\n'.join([
                        f"• {c['username']} ({c['pr_count']} PRs)"
                        for c in top_contributors
                    ])
                    embed.add_field(
                        name="Top Contributors (Auto-Selected Pool)",
                        value=contrib_text,
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed)
                
            except Exception as e:
                await interaction.followup.send(f"Error retrieving reviewer information: {str(e)}")
                print(f"Error in list_reviewers: {e}")
                import traceback
                traceback.print_exc()
        
        return list_reviewers 
