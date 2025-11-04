import discord
from discord import app_commands

from src.core.interfaces import IRepoAnalyticsService 

from src.utils.analytics.chart_generator import (
    create_top_contributors_chart, 
    create_activity_comparison_chart, 
    create_activity_trend_chart, 
    create_time_series_chart,
    create_repo_growth_chart
)
from shared.firestore import get_document

class AnalyticsCommands:
    
    def __init__(self, bot: discord.Client, analytics_service: IRepoAnalyticsService):
        self.bot = bot
        self.analytics_service = analytics_service
    
    def register_commands(self):
        self.bot.tree.add_command(self._show_top_contributors_command())
        self.bot.tree.add_command(self._show_activity_comparison_command())
        self.bot.tree.add_command(self._show_activity_trends_command())
        self.bot.tree.add_command(self._show_time_series_command())
        self.bot.tree.add_command(self._repo_growth_command())

    def _show_top_contributors_command(self):
        @app_commands.command(name="show-top-contributors", description="Show top contributors chart")
        async def show_top_contributors(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            
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
                await interaction.followup.send("Top contributors by PR count:", file=file, ephemeral=True)
                
            except Exception as e:
                print(f"Error in show-top-contributors command: {e}")
                await interaction.followup.send("Error generating contributors chart.", ephemeral=True)
        
        return show_top_contributors
    
    def _show_activity_comparison_command(self):
        @app_commands.command(name="show-activity-comparison", description="Show activity comparison chart")
        async def show_activity_comparison(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            
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
                await interaction.followup.send("Activity comparison chart:", file=file, ephemeral=True)
                
            except Exception as e:
                print(f"Error in show-activity-comparison command: {e}")
                await interaction.followup.send("Error generating activity comparison chart.", ephemeral=True)
        
        return show_activity_comparison
    
    def _show_activity_trends_command(self):
        @app_commands.command(name="show-activity-trends", description="Show recent activity trends")
        async def show_activity_trends(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            
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
                await interaction.followup.send("Recent activity trends:", file=file, ephemeral=True)
                
            except Exception as e:
                print(f"Error in show-activity-trends command: {e}")
                await interaction.followup.send("Error generating activity trends chart.", ephemeral=True)
        
        return show_activity_trends
    
    def _show_time_series_command(self):
        @app_commands.command(name="show-time-series", description="Show time series chart with customizable metrics and date range")
        @app_commands.describe(
            metrics="Comma-separated metrics to display (prs,issues,commits,total)",
            days="Number of days to show (7-90, default: 30)"
        )
        async def show_time_series(interaction: discord.Interaction, metrics: str = "prs,issues,commits", days: int = 30):
            await interaction.response.defer(ephemeral=True)
            
            try:
                if days < 7 or days > 90:
                    await interaction.followup.send("Days must be between 7 and 90.", ephemeral=True)
                    return
                
                valid_metrics = ['prs', 'issues', 'commits', 'total']
                selected_metrics = [m.strip().lower() for m in metrics.split(',')]
                selected_metrics = [m for m in selected_metrics if m in valid_metrics]
                
                if not selected_metrics:
                    await interaction.followup.send("Invalid metrics. Use: prs, issues, commits, total", ephemeral=True)
                    return
                
                analytics_data = get_document('repo_stats', 'analytics')
                
                if not analytics_data:
                    await interaction.followup.send("No analytics data available for analysis.", ephemeral=True)
                    return
                
                chart_buffer = create_time_series_chart(
                    analytics_data, 
                    metrics=selected_metrics, 
                    days=days,
                    title=f"Activity Time Series - {', '.join(m.title() for m in selected_metrics)}"
                )
                
                if not chart_buffer:
                    await interaction.followup.send("No data available to generate chart.", ephemeral=True)
                    return
                
                file = discord.File(chart_buffer, filename="time_series.png")
                await interaction.followup.send(f"Time series chart for last {days} days:", file=file, ephemeral=True)
                
            except Exception as e:
                print(f"Error in show-time-series command: {e}")
                await interaction.followup.send("Error generating time series chart.", ephemeral=True)
        
        return show_time_series

    def _repo_growth_command(self):
        
        @app_commands.command(
            name="repo_growth",
            description="Shows a chart of the repository's cumulative growth."
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def cmd(interaction: discord.Interaction):
            try:
                await interaction.response.defer(thinking=True, ephemeral=True)
                
                stats = await self.analytics_service.get_code_frequency_stats()
                
                if not stats:
                    await interaction.followup.send(
                        "Sorry, I couldn't fetch the repository stats. This can happen if GitHub "
                        "is caching the data. Please try again in a few minutes.",
                        ephemeral=True
                    )
                    return
                
                chart_buffer = create_repo_growth_chart(stats)
                
                if chart_buffer is None:
                     await interaction.followup.send("An error occurred while generating the chart.", ephemeral=True)
                     return

                file = discord.File(fp=chart_buffer, filename="repo_growth.png")
                
                embed = discord.Embed(
                    title="Repository Growth",
                    description="Here is the cumulative net line-of-code growth over time.",
                    color=discord.Color.blue()
                )
                embed.set_image(url="attachment://repo_growth.png")
                embed.set_footer(text="Data sourced from GitHub API")
                
                await interaction.followup.send(embed=embed, file=file, ephemeral=True)

            except Exception as e:
                print(f"Error in /repo_growth command: {e}")
                if not interaction.response.is_done():
                    await interaction.response.send_message("An unexpected error occurred.", ephemeral=True)
                else:
                    await interaction.followup.send("An unexpected error occurred.", ephemeral=True)

        return cmd