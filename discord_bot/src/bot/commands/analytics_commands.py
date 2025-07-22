"""
Analytics Commands Module

Handles analytics and visualization-related Discord commands.
"""

import discord
from discord import app_commands
from ...core.services import get_document
from ...utils.analytics import create_top_contributors_chart, create_activity_comparison_chart, create_activity_trend_chart

class AnalyticsCommands:
    """Handles analytics and visualization Discord commands."""
    
    def __init__(self, bot):
        self.bot = bot
    
    def register_commands(self):
        """Register all analytics commands with the bot."""
        self.bot.tree.add_command(self._show_top_contributors_command())
        self.bot.tree.add_command(self._show_activity_comparison_command())
        self.bot.tree.add_command(self._show_activity_trends_command())
    
    def _show_top_contributors_command(self):
        """Create the show-top-contributors command."""
        @app_commands.command(name="show-top-contributors", description="Show top contributors chart")
        async def show_top_contributors(interaction: discord.Interaction):
            await interaction.response.defer()
            
            try:
                analytics_data = get_document('repo_stats', 'analytics')
                
                if not analytics_data:
                    await interaction.followup.send("No analytics data available for analysis.", ephemeral=True)
                    return
                
                chart_buffer = create_top_contributors_chart(analytics_data, 'prs', "Top Contributors by PRs")
                
                if not chart_buffer:
                    await interaction.followup.send("No data available to generate chart.", ephemeral=True)
                    return
                
                file = discord.File(chart_buffer, filename="top_contributors.png")
                await interaction.followup.send("Top contributors by PR count:", file=file)
                
            except Exception as e:
                print(f"Error in show-top-contributors command: {e}")
                await interaction.followup.send("Error generating contributors chart.", ephemeral=True)
        
        return show_top_contributors
    
    def _show_activity_comparison_command(self):
        """Create the show-activity-comparison command."""
        @app_commands.command(name="show-activity-comparison", description="Show activity comparison chart")
        async def show_activity_comparison(interaction: discord.Interaction):
            await interaction.response.defer()
            
            try:
                analytics_data = get_document('repo_stats', 'analytics')
                
                if not analytics_data:
                    await interaction.followup.send("No analytics data available for analysis.", ephemeral=True)
                    return
                
                chart_buffer = create_activity_comparison_chart(analytics_data, "Activity Comparison")
                
                if not chart_buffer:
                    await interaction.followup.send("No data available to generate chart.", ephemeral=True)
                    return
                
                file = discord.File(chart_buffer, filename="activity_comparison.png")
                await interaction.followup.send("Activity comparison chart:", file=file)
                
            except Exception as e:
                print(f"Error in show-activity-comparison command: {e}")
                await interaction.followup.send("Error generating activity comparison chart.", ephemeral=True)
        
        return show_activity_comparison
    
    def _show_activity_trends_command(self):
        """Create the show-activity-trends command."""
        @app_commands.command(name="show-activity-trends", description="Show recent activity trends")
        async def show_activity_trends(interaction: discord.Interaction):
            await interaction.response.defer()
            
            try:
                analytics_data = get_document('repo_stats', 'analytics')
                
                if not analytics_data:
                    await interaction.followup.send("No analytics data available for analysis.", ephemeral=True)
                    return
                
                chart_buffer = create_activity_trend_chart(analytics_data, "Recent Activity Trends")
                
                if not chart_buffer:
                    await interaction.followup.send("No data available to generate chart.", ephemeral=True)
                    return
                
                file = discord.File(chart_buffer, filename="activity_trends.png")
                await interaction.followup.send("Recent activity trends:", file=file)
                
            except Exception as e:
                print(f"Error in show-activity-trends command: {e}")
                await interaction.followup.send("Error generating activity trends chart.", ephemeral=True)
        
        return show_activity_trends 