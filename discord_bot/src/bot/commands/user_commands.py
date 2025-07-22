"""
User Commands Module

Handles user-related Discord commands like linking, stats, and hall of fame.
"""

import discord
from discord import app_commands
import asyncio
import threading
from ...core.services import get_document, set_document, query_collection
from ...core.role_service import RoleService
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
                    set_document('discord', discord_user_id, {
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

                user_data = get_document('discord', str(interaction.user.id))

                if user_data:
                    # Delete document by setting it to empty (Firestore will remove it)
                    set_document('discord', str(interaction.user.id), {})
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
            
            try:
                stats_type = type.lower().strip()
                if stats_type not in ["pr", "issue", "commit"]:
                    stats_type = "pr"
                
                user_id = str(interaction.user.id)
                
                # Get user's Discord data to find their GitHub username
                discord_user_data = get_document('discord', user_id)
                if not discord_user_data or not discord_user_data.get('github_id'):
                    await interaction.followup.send(
                        "Your Discord account is not linked to a GitHub username. Use `/link` to link it.",
                        ephemeral=True
                    )
                    return
                
                github_username = discord_user_data['github_id']
                
                # Use the Discord user data which should contain the full contribution stats
                # The pipeline updates Discord documents with full contribution data
                user_data = discord_user_data
                    
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
                import traceback
                traceback.print_exc()
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
            
            hall_of_fame_data = get_document('repo_stats', 'hall_of_fame')
            
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
        import datetime
        
        role_service = RoleService()
        
        # Get stats from the detailed structure if available
        pr_all_time = user_data.get("stats", {}).get("prs", {}).get("all_time", user_data.get("pr_count", 0))
        issues_all_time = user_data.get("stats", {}).get("issues", {}).get("all_time", user_data.get("issues_count", 0))
        commits_all_time = user_data.get("stats", {}).get("commits", {}).get("all_time", user_data.get("commits_count", 0))
        
        pr_role, issue_role, commit_role = role_service.determine_roles(pr_all_time, issues_all_time, commits_all_time)
        
        # Set up type-specific variables
        title_prefix = "PR"
        if stats_type == "pr":
            count_field = "pr_count"
            stats_field = "prs"
            role = pr_role
            title_prefix = "PR"
        elif stats_type == "issue":
            count_field = "issues_count"
            stats_field = "issues"
            role = issue_role if issue_role else "None"
            title_prefix = "Issue"
        elif stats_type == "commit":
            count_field = "commits_count"
            stats_field = "commits"
            role = commit_role if commit_role else "None"
            title_prefix = "Commit"
 
        # Get enhanced stats
        stats = user_data["stats"]
        type_stats = stats[stats_field]
        
        # Create enhanced embed
        embed = discord.Embed(
            title=f"GitHub Contribution Metrics for {github_username}",
            description=f"Stats tracked across all RUXAILAB repositories. Updated hourly. Last update: {stats.get('last_updated', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'))}",
            color=discord.Color.blue()
        )
        
        # Create stats table with customized format
        display_prefix = f"{title_prefix}s{' ' * (12 - len(title_prefix + 's'))}"
        stats_table = f"```\n{display_prefix}   Count   Ranking\n"
        stats_table += f"24h:           {type_stats.get('daily', 0):<8}#{user_data.get('rankings', {}).get(f'{stats_type}_daily', 0)}\n"
        stats_table += f"7 days:        {type_stats.get('weekly', 0):<8}#{user_data.get('rankings', {}).get(f'{stats_type}_weekly', 0)}\n"
        stats_table += f"30 days:       {type_stats.get('monthly', 0):<8}#{user_data.get('rankings', {}).get(f'{stats_type}_monthly', 0)}\n"
        stats_table += f"Lifetime:      {type_stats.get('all_time', 0):<8}#{user_data.get('rankings', {}).get(stats_type, 0)}\n\n"
        
        # Add averages and streaks with customized wording
        stats_table += f"Daily Average ({stats.get('current_month', 'June')}): {type_stats.get('avg_per_day', 0)} {title_prefix}s\n\n"
        stats_table += f"Active {title_prefix} Streak: {type_stats.get('current_streak', 0)} {title_prefix}s\n"
        stats_table += f"Best {title_prefix} Streak: {type_stats.get('longest_streak', 0)} {title_prefix}s\n```"
        
        # Add level information based on role
        embed.add_field(name="Statistics", value=stats_table, inline=False)
        embed.add_field(name="Current level:", value=f"{role}", inline=True)
        
        # Determine next level
        next_level = role_service.get_next_role(role, stats_type)
        
        # Remove @ if present in next_level
        if next_level.startswith('@'):
            next_level = next_level[1:]
            
        embed.add_field(name="Next level:", value=next_level, inline=True)
        
        # Add info about other stat types
        other_types = []
        if stats_type != "pr":
            other_types.append(f"`/getstats type:pr` - View PR stats")
        if stats_type != "issue":
            other_types.append(f"`/getstats type:issue` - View Issue stats")
        if stats_type != "commit":
            other_types.append(f"`/getstats type:commit` - View Commit stats")
            
        embed.add_field(
            name="Other Statistics:", 
            value="\n".join(other_types),
            inline=False
        )
        
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
            count = contributor.get('count', 0)  # Changed from 'value' to 'count' to match new structure
            embed.add_field(
                name=f"{trophies[i]} {username}",
                value=f"{count} {type_names[type].lower()}",
                inline=False
            )
        
        embed.set_footer(text=f"Last updated: {last_updated or 'Unknown'}")
        return embed 