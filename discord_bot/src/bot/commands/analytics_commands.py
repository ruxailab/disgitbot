"""
Analytics Commands Module

Handles analytics and visualization-related Discord commands.
"""

import asyncio
import discord
from discord import app_commands
from ...utils.analytics import create_top_contributors_chart, create_activity_comparison_chart, create_activity_trend_chart, create_time_series_chart
from shared.firestore import get_document

class AnalyticsCommands:
    """Handles analytics and visualization Discord commands."""
    
    def __init__(self, bot):
        self.bot = bot
    
    def register_commands(self):
        """Register all analytics commands with the bot."""
        self.bot.tree.add_command(self._show_top_contributors_command())
        self.bot.tree.add_command(self._show_activity_comparison_command())
        self.bot.tree.add_command(self._show_activity_trends_command())
        self.bot.tree.add_command(self._show_time_series_command())
    
    def _show_top_contributors_command(self):
        """Create the show-top-contributors command."""
        @app_commands.guild_only()
        @app_commands.command(name="show-top-contributors", description="Show top contributors chart")
        async def show_top_contributors(interaction: discord.Interaction):
            await interaction.response.defer()
            
            try:
                discord_server_id = str(interaction.guild.id)
                analytics_data = await asyncio.to_thread(get_document, 'repo_stats', 'analytics', discord_server_id)
                
                if not analytics_data:
                    await interaction.followup.send("No analytics data available for analysis.", ephemeral=True)
                    return
                
                chart_buffer = await asyncio.to_thread(create_top_contributors_chart, analytics_data, 'prs', "Top Contributors by PRs")
                
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
        @app_commands.guild_only()
        @app_commands.command(name="show-activity-comparison", description="Show activity comparison chart")
        async def show_activity_comparison(interaction: discord.Interaction):
            await interaction.response.defer()
            
            try:
                discord_server_id = str(interaction.guild.id)
                analytics_data = await asyncio.to_thread(get_document, 'repo_stats', 'analytics', discord_server_id)
                
                if not analytics_data:
                    await interaction.followup.send("No analytics data available for analysis.", ephemeral=True)
                    return
                
                chart_buffer = await asyncio.to_thread(create_activity_comparison_chart, analytics_data, "Activity Comparison")
                
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
        @app_commands.guild_only()
        @app_commands.command(name="show-activity-trends", description="Show recent activity trends")
        async def show_activity_trends(interaction: discord.Interaction):
            await interaction.response.defer()
            
            try:
                discord_server_id = str(interaction.guild.id)
                analytics_data = await asyncio.to_thread(get_document, 'repo_stats', 'analytics', discord_server_id)
                
                if not analytics_data:
                    await interaction.followup.send("No analytics data available for analysis.", ephemeral=True)
                    return
                
                chart_buffer = await asyncio.to_thread(create_activity_trend_chart, analytics_data, "Recent Activity Trends")
                
                if not chart_buffer:
                    await interaction.followup.send("No data available to generate chart.", ephemeral=True)
                    return
                
                file = discord.File(chart_buffer, filename="activity_trends.png")
                await interaction.followup.send("Recent activity trends:", file=file)
                
            except Exception as e:
                print(f"Error in show-activity-trends command: {e}")
                await interaction.followup.send("Error generating activity trends chart.", ephemeral=True)
        
        return show_activity_trends
    
    def _show_time_series_command(self):
        """Create the show-time-series command."""
        @app_commands.guild_only()
        @app_commands.command(name="show-time-series", description="Show time series chart with customizable metrics and date range")
        @app_commands.describe(
            metrics="Comma-separated metrics to display (prs,issues,commits,total)",
            days="Number of days to show (7-90, default: 30)"
        )
        async def show_time_series(interaction: discord.Interaction, metrics: str = "prs,issues,commits", days: int = 30):
            await interaction.response.defer()
            
            try:
                # Validate inputs
                if days < 7 or days > 90:
                    await interaction.followup.send("Days must be between 7 and 90.", ephemeral=True)
                    return
                
                valid_metrics = ['prs', 'issues', 'commits', 'total']
                selected_metrics = [m.strip().lower() for m in metrics.split(',')]
                selected_metrics = [m for m in selected_metrics if m in valid_metrics]
                
                if not selected_metrics:
                    await interaction.followup.send("Invalid metrics. Use: prs, issues, commits, total", ephemeral=True)
                    return
                
                discord_server_id = str(interaction.guild.id)
                analytics_data = await asyncio.to_thread(get_document, 'repo_stats', 'analytics', discord_server_id)
                
                if not analytics_data:
                    await interaction.followup.send("No analytics data available for analysis.", ephemeral=True)
                    return
                
                chart_buffer = await asyncio.to_thread(
                    create_time_series_chart,
                    analytics_data, 
                    metrics=selected_metrics, 
                    days=days,
                    title=f"Activity Time Series - {', '.join(m.title() for m in selected_metrics)}"
                )
                
                if not chart_buffer:
                    await interaction.followup.send("No data available to generate chart.", ephemeral=True)
                    return
                
                file = discord.File(chart_buffer, filename="time_series.png")
                await interaction.followup.send(f"Time series chart for last {days} days:", file=file)
                
            except Exception as e:
                print(f"Error in show-time-series command: {e}")
                await interaction.followup.send("Error generating time series chart.", ephemeral=True)
        
        return show_time_series 