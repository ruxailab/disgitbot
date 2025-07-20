"""
Admin Commands Module

Handles administrative Discord commands like permissions and setup.
"""

import discord
from discord import app_commands

class AdminCommands:
    """Handles administrative Discord commands."""
    
    def __init__(self, bot):
        self.bot = bot
    
    def register_commands(self):
        """Register all admin commands with the bot."""
        self.bot.tree.add_command(self._check_permissions_command())
        self.bot.tree.add_command(self._setup_voice_stats_command())
    
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