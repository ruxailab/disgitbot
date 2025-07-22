"""
Discord Bot Module

Clean, modular Discord bot initialization and setup.
"""

import os
import sys
import discord
from discord.ext import commands
from dotenv import load_dotenv

from .commands import UserCommands, AdminCommands, AnalyticsCommands

class DiscordBot:
    """Main Discord bot class with modular command registration."""
    
    def __init__(self):
        self.bot = None
        self._setup_environment()
        self._create_bot()
        self._register_commands()
    
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
        self.bot = commands.Bot(command_prefix="!", intents=intents)
        
        @self.bot.event
        async def on_ready():
            try:
                synced = await self.bot.tree.sync()
                print(f"{self.bot.user} is online! Synced {len(synced)} command(s).")
            except Exception as e:
                print(f"Failed to sync commands: {e}")
    
    def _register_commands(self):
        """Register all command modules."""
        user_commands = UserCommands(self.bot)
        admin_commands = AdminCommands(self.bot)
        analytics_commands = AnalyticsCommands(self.bot)
        
        user_commands.register_commands()
        admin_commands.register_commands()
        analytics_commands.register_commands()
        
        print("All command modules registered")
    
    def run(self):
        """Start the Discord bot."""
        print("Starting Discord bot...")
        if self.bot and self.token:
            self.bot.run(self.token)

def create_bot():
    """Factory function to create Discord bot instance."""
    return DiscordBot() 