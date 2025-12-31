"""
Notification Commands Module

Handles Discord commands for managing GitHub to Discord notifications.
"""

import discord
from discord import app_commands
from typing import Literal
import re
from src.services.notification_service import WebhookManager

class NotificationCommands:
    """Handles notification management Discord commands."""
    
    def __init__(self, bot):
        self.bot = bot
    
    def register_commands(self):
        """Register all notification commands with the bot."""
        self.bot.tree.add_command(self._set_webhook_command())
        self.bot.tree.add_command(self._add_repo_command())
        self.bot.tree.add_command(self._remove_repo_command())
        self.bot.tree.add_command(self._list_repos_command())
        self.bot.tree.add_command(self._webhook_status_command())
    
    def _set_webhook_command(self):
        """Create the set_webhook command."""
        @app_commands.command(name="set_webhook", description="Set Discord webhook URL for notifications")
        @app_commands.describe(
            notification_type="Type of notifications",
            webhook_url="Discord webhook URL"
        )
        async def set_webhook(
            interaction: discord.Interaction, 
            notification_type: Literal["pr_automation", "cicd"],
            webhook_url: str
        ):
            await interaction.response.defer(ephemeral=True)
            
            try:
                # Validate webhook URL format
                if not self._is_valid_webhook_url(webhook_url):
                    await interaction.followup.send(
                        "Invalid webhook URL format. Please provide a valid Discord webhook URL.",
                        ephemeral=True
                    )
                    return
                
                # Set the webhook URL
                success = WebhookManager.set_webhook_url(notification_type, webhook_url)
                
                if success:
                    await interaction.followup.send(
                        f"Successfully configured {notification_type} webhook URL.",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        "Failed to save webhook configuration. Please try again.",
                        ephemeral=True
                    )
                    
            except Exception as e:
                await interaction.followup.send(f"Error setting webhook: {str(e)}", ephemeral=True)
                print(f"Error in set_webhook: {e}")
                import traceback
                traceback.print_exc()
        
        return set_webhook
    
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
                
                # Add repository to monitoring list
                success = WebhookManager.add_monitored_repository(repository)
                
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
                
                # Remove repository from monitoring list
                success = WebhookManager.remove_monitored_repository(repository)
                
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
                repositories = WebhookManager.get_monitored_repositories()
                
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
                
                webhook_config = get_document('global_config', 'ci_cd_webhooks')
                
                embed = discord.Embed(
                    title="Webhook Configuration Status",
                    color=discord.Color.blue()
                )
                
                # Check PR automation webhook
                pr_webhook = webhook_config.get('pr_automation_webhook_url') if webhook_config else None
                pr_status = "Configured" if pr_webhook else "Not configured"
                embed.add_field(
                    name="PR Automation Notifications",
                    value=pr_status,
                    inline=True
                )
                
                # Check CI/CD webhook
                cicd_webhook = webhook_config.get('cicd_webhook_url') if webhook_config else None
                cicd_status = "Configured" if cicd_webhook else "Not configured"
                embed.add_field(
                    name="CI/CD Notifications",
                    value=cicd_status,
                    inline=True
                )
                
                # Last updated
                if webhook_config and webhook_config.get('last_updated'):
                    embed.add_field(
                        name="Last Updated",
                        value=webhook_config['last_updated'],
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
