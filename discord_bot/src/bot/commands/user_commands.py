"""
User Commands Module

Handles user-related Discord commands like linking, stats, and hall of fame.
"""

import discord
from discord import app_commands
import asyncio
import threading
from ...utils.firestore import get_firestore_data, get_hall_of_fame_data, db
from ...utils.role_utils import determine_role, get_next_role
from ..auth import get_github_username_for_user, wait_for_username

class UserCommands:
    """Handles user-related Discord commands."""
    
    def __init__(self, bot):
        self.bot = bot
        self.verification_lock = threading.Lock()
    
    def register_commands(self):
        """Register all user commands with the bot."""
        self.bot.tree.add_command(self._link_command())
        self.bot.tree.add_command(self._unlink_command())
        self.bot.tree.add_command(self._getstats_command())
        self.bot.tree.add_command(self._halloffame_command())
    
    def _link_command(self):
        """Create the link command."""
        @app_commands.command(name="link", description="Link your Discord to GitHub")
        async def link(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)

            if not self.verification_lock.acquire(blocking=False):
                await interaction.followup.send("The verification process is currently busy. Please try again later.", ephemeral=True)
                return

            try:
                discord_user_id = str(interaction.user.id)
                
                oauth_url = get_github_username_for_user(discord_user_id)
                await interaction.followup.send(f"Please complete GitHub authentication: {oauth_url}", ephemeral=True)

                github_username = await asyncio.get_event_loop().run_in_executor(
                    None, wait_for_username, discord_user_id
                )

                if github_username:
                    doc_ref = db.collection('discord').document(discord_user_id)
                    doc_ref.set({
                        'github_id': github_username,
                        'pr_count': 0,
                        'issues_count': 0,
                        'commits_count': 0,
                        'role': 'member'
                    })
                    await interaction.followup.send(f"Successfully linked to GitHub user: `{github_username}`", ephemeral=True)
                else:
                    await interaction.followup.send("Authentication timed out or failed. Please try again.", ephemeral=True)

            except Exception as e:
                print("Error in /link:", e)
                await interaction.followup.send("Failed to link GitHub account.", ephemeral=True)
            finally:
                self.verification_lock.release()
        
        return link
    
    def _unlink_command(self):
        """Create the unlink command."""
        @app_commands.command(name="unlink", description="Unlinks your Discord account from your GitHub username")
        async def unlink(interaction: discord.Interaction):
            try:
                await interaction.response.defer(ephemeral=True)

                doc_ref = db.collection('discord').document(str(interaction.user.id))

                if doc_ref.get().exists:
                    doc_ref.delete()
                    await interaction.followup.send(
                        "Successfully unlinked your Discord account from your GitHub username.",
                        ephemeral=True
                    )
                    print(f"Unlinked Discord user {interaction.user.name}")
                else:
                    await interaction.followup.send(
                        "Your Discord account is not linked to any GitHub username.",
                        ephemeral=True
                    )

            except Exception as e:
                print(f"Error unlinking user: {e}")
                await interaction.followup.send("An error occurred while unlinking your account.", ephemeral=True)
        
        return unlink
    
    def _getstats_command(self):
        """Create the getstats command."""
        @app_commands.command(name="getstats", description="Displays your GitHub stats and current role")
        @app_commands.describe(type="Type of stats to display")
        @app_commands.choices(type=[
            app_commands.Choice(name="Pull Requests", value="pr"),
            app_commands.Choice(name="Issues", value="issue"),
            app_commands.Choice(name="Commits", value="commit")
        ])
        async def getstats(interaction: discord.Interaction, type: str = "pr"):
            await interaction.response.defer()
            
            _, contributions, user_mappings = get_firestore_data()
            
            try:
                stats_type = type.lower().strip()
                if stats_type not in ["pr", "issue", "commit"]:
                    stats_type = "pr"
                
                user_id = str(interaction.user.id)
                github_username = user_mappings.get(user_id)
                
                if not github_username:
                    await interaction.followup.send(
                        "Your Discord account is not linked to a GitHub username. Use `/link your_github_username` to link it.",
                        ephemeral=True
                    )
                    return
                    
                user_data = contributions.get(github_username)
                    
                if not user_data:
                    await interaction.followup.send(
                        f"No contribution data found for GitHub user '{github_username}'.",
                        ephemeral=True
                    )
                    return

                # Get stats and create embed
                embed = self._create_stats_embed(user_data, github_username, stats_type)
                await interaction.followup.send(embed=embed)
                
            except Exception as e:
                print(f"Error in getstats command: {e}")
                await interaction.followup.send("Error retrieving your stats.", ephemeral=True)
        
        return getstats
    
    def _halloffame_command(self):
        """Create the halloffame command."""
        @app_commands.command(name="halloffame", description="Shows top 3 contributors")
        @app_commands.describe(type="Contribution type", period="Time period")
        @app_commands.choices(type=[
            app_commands.Choice(name="Pull Requests", value="pr"),
            app_commands.Choice(name="Issues", value="issue"),
            app_commands.Choice(name="Commits", value="commit")
        ])
        @app_commands.choices(period=[
            app_commands.Choice(name="All Time", value="all_time"),
            app_commands.Choice(name="Monthly", value="monthly"),
            app_commands.Choice(name="Weekly", value="weekly"),
            app_commands.Choice(name="Daily", value="daily")
        ])
        async def halloffame(interaction: discord.Interaction, type: str = "pr", period: str = "all_time"):
            await interaction.response.defer()
            
            hall_of_fame_data = get_hall_of_fame_data()
            
            if not hall_of_fame_data:
                await interaction.followup.send("Hall of fame data not available yet.", ephemeral=True)
                return
            
            top_3 = hall_of_fame_data.get(type, {}).get(period, [])
            
            if not top_3:
                await interaction.followup.send(f"No data for {type} {period}.", ephemeral=True)
                return
            
            embed = self._create_halloffame_embed(top_3, type, period, hall_of_fame_data.get('last_updated'))
            await interaction.followup.send(embed=embed)
        
        return halloffame
    
    def _create_stats_embed(self, user_data, github_username, stats_type):
        """Create stats embed for user."""
        pr_all_time = user_data.get("stats", {}).get("prs", {}).get("all_time", 0)
        issues_all_time = user_data.get("stats", {}).get("issues", {}).get("all_time", 0)
        commits_all_time = user_data.get("stats", {}).get("commits", {}).get("all_time", 0)
        
        pr_role, issue_role, commit_role = determine_role(pr_all_time, issues_all_time, commits_all_time)
        
        type_names = {"pr": "Pull Requests", "issue": "Issues", "commit": "Commits"}
        
        embed = discord.Embed(
            title=f"{type_names[stats_type]} Stats for {github_username}",
            color=discord.Color.blue()
        )
        
        if stats_type == "pr":
            current_role = pr_role
            all_time_count = pr_all_time
            stats = user_data.get("stats", {}).get("prs", {})
        elif stats_type == "issue":
            current_role = issue_role
            all_time_count = issues_all_time
            stats = user_data.get("stats", {}).get("issues", {})
        else:  # commit
            current_role = commit_role
            all_time_count = commits_all_time
            stats = user_data.get("stats", {}).get("commits", {})
        
        embed.add_field(name="Current Role", value=current_role or "None", inline=True)
        embed.add_field(name="All Time", value=str(all_time_count), inline=True)
        embed.add_field(name="This Month", value=str(stats.get("monthly", 0)), inline=True)
        embed.add_field(name="This Week", value=str(stats.get("weekly", 0)), inline=True)
        embed.add_field(name="Today", value=str(stats.get("daily", 0)), inline=True)
        embed.add_field(name="Next Role", value=get_next_role(current_role, stats_type), inline=False)
        
        return embed
    
    def _create_halloffame_embed(self, top_3, type, period, last_updated):
        """Create hall of fame embed."""
        type_names = {"pr": "Pull Requests", "issue": "Issues", "commit": "Commits"}
        period_names = {"all_time": "All Time", "monthly": "Monthly", "weekly": "Weekly", "daily": "Daily"}
        
        embed = discord.Embed(
            title=f"{type_names[type]} Hall of Fame ({period_names[period]})",
            color=discord.Color.gold()
        )
        
        trophies = ["🥇", "🥈", "🥉"]
        for i, contributor in enumerate(top_3[:3]):
            username = contributor.get('username', 'Unknown')
            value = contributor.get('value', 0)
            embed.add_field(
                name=f"{trophies[i]} {username}",
                value=f"{value} {type_names[type].lower()}",
                inline=False
            )
        
        embed.set_footer(text=f"Last updated: {last_updated or 'Unknown'}")
        return embed 