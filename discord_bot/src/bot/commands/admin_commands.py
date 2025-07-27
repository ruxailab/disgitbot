"""
Admin Commands Module

Handles administrative Discord commands like permissions and setup.
"""

import discord
from discord import app_commands
from ...core.database import get_document, set_document

class AdminCommands:
    """Handles administrative Discord commands."""
    
    def __init__(self, bot):
        self.bot = bot
    
    def register_commands(self):
        """Register all admin commands with the bot."""
        self.bot.tree.add_command(self._check_permissions_command())
        self.bot.tree.add_command(self._setup_voice_stats_command())
        self.bot.tree.add_command(self._add_reviewer_command())
        self.bot.tree.add_command(self._remove_reviewer_command())
        self.bot.tree.add_command(self._list_reviewers_command())
    
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
    
    def _setup_voice_stats_command(self):
        """Create the setup_voice_stats command."""
        @app_commands.command(name="setup_voice_stats", description="Sets up voice channels for repository stats display")
        async def setup_voice_stats(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            
            try:
                guild = interaction.guild
                assert guild is not None, "Command should only work in guilds"
                
                existing_category = discord.utils.get(guild.categories, name="REPOSITORY STATS")
                
                if existing_category:
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
                reviewer_data = get_document('pr_config', 'reviewers')
                if not reviewer_data:
                    reviewer_data = {'reviewers': [], 'count': 0, 'selection_criteria': 'manual_additions'}
                
                current_reviewers = reviewer_data.get('reviewers', [])
                
                # Check if reviewer already exists
                if username in current_reviewers:
                    await interaction.followup.send(f"GitHub user `{username}` is already in the reviewer pool.")
                    return
                
                # Add the reviewer
                current_reviewers.append(username)
                reviewer_data['reviewers'] = current_reviewers
                reviewer_data['count'] = len(current_reviewers)
                reviewer_data['last_updated'] = __import__('time').strftime('%Y-%m-%d %H:%M:%S UTC', __import__('time').gmtime())
                
                # Save to Firestore
                success = set_document('pr_config', 'reviewers', reviewer_data)
                
                if success:
                    await interaction.followup.send(f"Successfully added `{username}` to the PR reviewer pool.\nTotal reviewers: {len(current_reviewers)}")
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
                reviewer_data = get_document('pr_config', 'reviewers')
                if not reviewer_data or not reviewer_data.get('reviewers'):
                    await interaction.followup.send("No reviewers found in the database.")
                    return
                
                current_reviewers = reviewer_data.get('reviewers', [])
                
                # Check if reviewer exists
                if username not in current_reviewers:
                    await interaction.followup.send(f"GitHub user `{username}` is not in the reviewer pool.")
                    return
                
                # Remove the reviewer
                current_reviewers.remove(username)
                reviewer_data['reviewers'] = current_reviewers
                reviewer_data['count'] = len(current_reviewers)
                reviewer_data['last_updated'] = __import__('time').strftime('%Y-%m-%d %H:%M:%S UTC', __import__('time').gmtime())
                
                # Save to Firestore
                success = set_document('pr_config', 'reviewers', reviewer_data)
                
                if success:
                    await interaction.followup.send(f"Successfully removed `{username}` from the PR reviewer pool.\nTotal reviewers: {len(current_reviewers)}")
                else:
                    await interaction.followup.send("Failed to remove reviewer from the database.")
                    
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
                reviewer_data = get_document('pr_config', 'reviewers')
                contributor_data = get_document('repo_stats', 'contributor_summary')
                
                embed = discord.Embed(
                    title="PR Reviewer Pool Status",
                    color=discord.Color.blue()
                )
                
                # Show current reviewers
                if reviewer_data and reviewer_data.get('reviewers'):
                    reviewers = reviewer_data['reviewers']
                    reviewers_text = '\n'.join([f"• {reviewer}" for reviewer in reviewers])
                    embed.add_field(
                        name=f"Current Reviewers ({len(reviewers)})",
                        value=reviewers_text,
                        inline=False
                    )
                    
                    embed.add_field(
                        name="Pool Info",
                        value=f"Last Updated: {reviewer_data.get('last_updated', 'Unknown')}\nSelection: {reviewer_data.get('selection_criteria', 'Unknown')}",
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