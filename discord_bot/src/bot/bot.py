"""
Discord Bot Module

Clean, modular Discord bot initialization and setup.
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands
from dotenv import load_dotenv

from .commands import UserCommands, AdminCommands, AnalyticsCommands, NotificationCommands, ConfigCommands

class DiscordBot:
    """Main Discord bot class with modular command registration."""
    
    def __init__(self):
        self.bot = None
        self._setup_environment()
        self._create_bot()
        self._register_commands()
        
        # Store global reference for cross-thread communication
        from . import shared
        shared.bot_instance = self
    
    def _setup_environment(self):
        """Setup environment variables and logging."""
        print("="*50)
        print("Discord Bot Starting...")
        print(f"Python version: {sys.version}")
        print("="*50)
        
        load_dotenv("config/.env")
        print("Environment variables loaded")
        
        self.token = os.getenv("DISCORD_BOT_TOKEN")
        if not self.token:
            raise ValueError("DISCORD_BOT_TOKEN environment variable is required")
    

    
    def _create_bot(self):
        """Create Discord bot instance."""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True  # Required for on_guild_join event
        self.bot = commands.Bot(command_prefix="!", intents=intents)
        
        @self.bot.event
        async def on_ready():
            try:
                synced = await self.bot.tree.sync()
                print(f"{self.bot.user} is online! Synced {len(synced)} command(s).")

            except Exception as e:
                print(f"Error in on_ready: {e}")
                import traceback
                traceback.print_exc()

        @self.bot.event
        async def on_guild_join(guild):
            """Called when bot joins a new server - provide setup guidance."""
            try:
                # Check if server is already configured (offload to thread to avoid blocking)
                from shared.firestore import get_mt_client
                mt_client = get_mt_client()
                server_config = await asyncio.to_thread(mt_client.get_server_config, str(guild.id)) or {}

                if not server_config.get('setup_completed'):
                    # Check if we sent a reminder very recently (24h cooldown)
                    last_reminder = server_config.get('setup_reminder_sent_at')
                    if last_reminder:
                        try:
                            last_dt = datetime.fromisoformat(last_reminder)
                            if last_dt.tzinfo is None:
                                last_dt = last_dt.replace(tzinfo=timezone.utc)
                            if datetime.now(timezone.utc) - last_dt < timedelta(hours=24):
                                print(f"Skipping setup guidance for {guild.name}: already sent within 24h")
                                return
                        except ValueError:
                            pass

                    # Server not configured - send setup message to system channel
                    system_channel = guild.system_channel
                    if not system_channel:
                        # Fallback: find first available text channel
                        system_channel = next((ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages), None)

                    if system_channel:
                        base_url = os.getenv("OAUTH_BASE_URL")
                        from urllib.parse import urlencode
                        setup_url = f"{base_url}/setup?{urlencode({'guild_id': guild.id, 'guild_name': guild.name})}"

                        setup_message = f"""**DisgitBot Added Successfully!**

This server needs to be configured to track GitHub contributions.

**Quick Setup (30 seconds):**
1. Visit: {setup_url}
2. Install the GitHub App and select repositories
3. Use `/link` in Discord to connect GitHub accounts
4. Customize roles with `/configure roles`

**Or use this command:** `/setup`

After setup, try these commands:
• `/getstats` - View contribution statistics
• `/halloffame` - Top contributors leaderboard
• `/link` - Connect your GitHub account

*This message will only appear once during setup.*"""

                        await system_channel.send(setup_message)
                        
                        # Mark reminder as sent
                        await asyncio.to_thread(mt_client.set_server_config, str(guild.id), {
                            **server_config,
                            'setup_reminder_sent_at': datetime.now(timezone.utc).isoformat()
                        })
                        print(f"Sent setup guidance to server: {guild.name} (ID: {guild.id})")

            except Exception as e:
                print(f"Error sending setup guidance for guild {guild.id}: {e}")
                import traceback
                traceback.print_exc()


    def _register_commands(self):
        """Register all command modules."""
        user_commands = UserCommands(self.bot)
        admin_commands = AdminCommands(self.bot)
        analytics_commands = AnalyticsCommands(self.bot)
        notification_commands = NotificationCommands(self.bot)
        config_commands = ConfigCommands(self.bot)
        
        user_commands.register_commands()
        admin_commands.register_commands()
        analytics_commands.register_commands()
        notification_commands.register_commands()
        config_commands.register_commands()
        
        print("All command modules registered")
    
    def run(self):
        """Start the Discord bot."""
        print("Starting Discord bot...")
        if self.bot and self.token:
            self.bot.run(self.token)

def create_bot():
    """Factory function to create Discord bot instance."""
    return DiscordBot() 
