"""
Notification Commands Module

Handles Discord commands for managing GitHub to Discord notifications.
"""

import asyncio
import discord
from discord import app_commands
from typing import Literal
import re
from src.services.notification_service import WebhookManager
from shared.firestore import get_mt_client

class NotificationCommands:
    """Handles notification management Discord commands."""
    
    def __init__(self, bot):
        self.bot = bot
    
    def register_commands(self):
        """Register all notification commands with the bot."""
        # CI/CD monitoring commands disabled - webhook handler inactive
        # To re-enable: uncomment below and re-enable /github/webhook handler in auth.py
        # self.bot.tree.add_command(self._add_repo_command())
        # self.bot.tree.add_command(self._remove_repo_command())
        # self.bot.tree.add_command(self._list_repos_command())
        # PR automation commands disabled - keeping code for future re-enablement
        # self.bot.tree.add_command(self._webhook_status_command())
        pass
    
    # /set_webhook command removed - PR automation feature disabled
    # To re-enable, restore the _set_webhook_command method and register it above
    
    def _add_repo_command(self):
        """Create the add_repo command."""
        @app_commands.command(name="add_repo", description="Add repository to CI/CD monitoring")
        @app_commands.describe(repository="Repository in owner/repo format")
        async def add_repo(interaction: discord.Interaction, repository: str):
            await interaction.response.defer()
            
            try:
                # Validate repository format
                if not self._is_valid_repo_format(repository):
                    await interaction.followup.send(
                        "Invalid repository format. Please use 'owner/repo' format (e.g., 'ruxailab/disgitbot')."
                    )
                    return
                
                # Validate repo belongs to the configured GitHub org
                repo_owner = repository.split('/')[0]
                mt_client = get_mt_client()
                github_org = await asyncio.to_thread(
                    mt_client.get_org_from_server,
                    str(interaction.guild_id)
                )
                if not github_org:
                    await interaction.followup.send(
                        "This server hasn't been set up yet. Run `/setup` first to connect a GitHub organization."
                    )
                    return
                if repo_owner.lower() != github_org.lower():
                    await interaction.followup.send(
                        f"You can only monitor repositories within your configured organization **{github_org}**.\n"
                        f"The repository `{repository}` belongs to `{repo_owner}`, not `{github_org}`.\n\n"
                        f"Use the format: `{github_org}/repo-name`"
                    )
                    return
                
                # Add repository to monitoring list
                success = await asyncio.to_thread(
                    WebhookManager.add_monitored_repository,
                    repository, 
                    discord_server_id=str(interaction.guild_id)
                )
                
                if success:
                    await interaction.followup.send(
                        f"Successfully added `{repository}` to CI/CD monitoring.\n"
                        f"GitHub Actions in this repository will now send status notifications to Discord."
                    )
                else:
                    await interaction.followup.send(
                        "Failed to add repository to monitoring list. Please try again."
                    )
                    
            except Exception as e:
                await interaction.followup.send(f"Error adding repository: {str(e)}")
                print(f"Error in add_repo: {e}")
                import traceback
                traceback.print_exc()
        
        return add_repo
    
    def _remove_repo_command(self):
        """Create the remove_repo command."""
        @app_commands.command(name="remove_repo", description="Remove repository from CI/CD monitoring")
        @app_commands.describe(repository="Repository in owner/repo format")
        async def remove_repo(interaction: discord.Interaction, repository: str):
            await interaction.response.defer()
            
            try:
                # Validate repository format
                if not self._is_valid_repo_format(repository):
                    await interaction.followup.send(
                        "Invalid repository format. Please use 'owner/repo' format (e.g., 'ruxailab/disgitbot')."
                    )
                    return
                
                # Validate repo belongs to the configured GitHub org
                repo_owner = repository.split('/')[0]
                mt_client = get_mt_client()
                github_org = await asyncio.to_thread(
                    mt_client.get_org_from_server,
                    str(interaction.guild_id)
                )
                if not github_org:
                    await interaction.followup.send(
                        "This server hasn't been set up yet. Run `/setup` first to connect a GitHub organization."
                    )
                    return
                if repo_owner.lower() != github_org.lower():
                    await interaction.followup.send(
                        f"You can only manage repositories within your configured organization **{github_org}**.\n"
                        f"The repository `{repository}` belongs to `{repo_owner}`, not `{github_org}`."
                    )
                    return
                
                # Remove repository from monitoring list
                success = await asyncio.to_thread(
                    WebhookManager.remove_monitored_repository,
                    repository,
                    discord_server_id=str(interaction.guild_id)
                )
                
                if success:
                    await interaction.followup.send(
                        f"Successfully removed `{repository}` from CI/CD monitoring.\n"
                        f"This repository will no longer send notifications to Discord."
                    )
                else:
                    await interaction.followup.send(
                        "Failed to remove repository from monitoring list. Please try again."
                    )
                    
            except Exception as e:
                await interaction.followup.send(f"Error removing repository: {str(e)}")
                print(f"Error in remove_repo: {e}")
                import traceback
                traceback.print_exc()
        
        return remove_repo
    
    def _list_repos_command(self):
        """Create the list_repos command."""
        @app_commands.command(name="list_repos", description="List repositories being monitored for CI/CD")
        async def list_repos(interaction: discord.Interaction):
            await interaction.response.defer()
            
            try:
                repositories = await asyncio.to_thread(
                    WebhookManager.get_monitored_repositories,
                    discord_server_id=str(interaction.guild_id)
                )
                
                embed = discord.Embed(
                    title="CI/CD Monitoring Status",
                    color=discord.Color.blue()
                )
                
                if repositories:
                    repo_list = '\n'.join([f"• [{repo}](https://github.com/{repo})" for repo in repositories])
                    embed.add_field(
                        name=f"Monitored Repositories ({len(repositories)})",
                        value=repo_list,
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="Monitored Repositories",
                        value="No repositories currently being monitored.",
                        inline=False
                    )
                
                embed.add_field(
                    name="How to Add Repositories",
                    value="Use `/add_repo owner/repo` to add a repository to monitoring.",
                    inline=False
                )
                
                await interaction.followup.send(embed=embed)
                
            except Exception as e:
                await interaction.followup.send(f"Error retrieving repository list: {str(e)}")
                print(f"Error in list_repos: {e}")
                import traceback
                traceback.print_exc()
        
        return list_repos
    
    def _webhook_status_command(self):
        """Create the webhook_status command."""
        @app_commands.command(name="webhook_status", description="Check webhook configuration status")
        async def webhook_status(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            
            try:
                from shared.firestore import get_document
                
                webhook_config = await asyncio.to_thread(
                    get_document,
                    'pr_config', 
                    'webhooks', 
                    discord_server_id=str(interaction.guild_id)
                )
                
                embed = discord.Embed(
                    title="Webhook Configuration Status",
                    color=discord.Color.blue()
                )
                
                # New logic: Look in the webhooks list for this specific server
                webhooks_list = webhook_config.get('webhooks', []) if webhook_config else []
                
                # Find PR automation webhook for THIS server
                pr_webhook_entry = next((w for w in webhooks_list if w.get('type') == 'pr_automation' and w.get('server_id') == str(interaction.guild_id)), None)
                pr_webhook = None
                if pr_webhook_entry:
                    pr_webhook = pr_webhook_entry.get('url')
                elif webhook_config:
                    pr_webhook = webhook_config.get('pr_automation_webhook_url')
                
                pr_status = "Configured" if pr_webhook else "Not configured"
                embed.add_field(
                    name="PR Automation Notifications",
                    value=pr_status,
                    inline=True
                )
                
                # Find CI/CD webhook for THIS server
                cicd_webhook_entry = next((w for w in webhooks_list if w.get('type') == 'cicd' and w.get('server_id') == str(interaction.guild_id)), None)
                cicd_webhook = None
                if cicd_webhook_entry:
                    cicd_webhook = cicd_webhook_entry.get('url')
                elif webhook_config:
                    cicd_webhook = webhook_config.get('cicd_webhook_url')
                
                cicd_status = "Configured" if cicd_webhook else "Not configured"
                embed.add_field(
                    name="CI/CD Notifications",
                    value=cicd_status,
                    inline=True
                )
                
                # Last updated - show most recent webhook update for THIS server
                webhook_updates = []
                if pr_webhook_entry and pr_webhook_entry.get('last_updated'):
                    webhook_updates.append(pr_webhook_entry['last_updated'])
                if cicd_webhook_entry and cicd_webhook_entry.get('last_updated'):
                    webhook_updates.append(cicd_webhook_entry['last_updated'])
                
                if webhook_updates:
                    latest_update = max(webhook_updates)
                    embed.add_field(
                        name="Last Updated",
                        value=latest_update,
                        inline=False
                    )
                
                if not pr_webhook or not cicd_webhook:
                    embed.add_field(
                        name="Setup Instructions",
                        value="Use `/set_webhook` to configure missing webhook URLs.",
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
            except Exception as e:
                await interaction.followup.send(f"Error checking webhook status: {str(e)}", ephemeral=True)
                print(f"Error in webhook_status: {e}")
                import traceback
                traceback.print_exc()
        
        return webhook_status
    
    def _is_valid_webhook_url(self, url: str) -> bool:
        """Validate Discord webhook URL format."""
        discord_webhook_pattern = r'^https://discord(?:app)?\.com/api/webhooks/\d+/[\w-]+$'
        return bool(re.match(discord_webhook_pattern, url))
    
    def _is_valid_repo_format(self, repo: str) -> bool:
        """Validate repository format (owner/repo)."""
        repo_pattern = r'^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$'
        return bool(re.match(repo_pattern, repo))
