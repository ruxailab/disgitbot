#!/usr/bin/env python3
"""
Standalone script to update Discord voice channel names with repository statistics.
This script is designed to run once daily from GitHub Actions workflow.
"""

import os
import sys
import discord
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
import datetime

# Add the parent directory to the path to import utilities
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.firestore import get_firestore_data

# Load environment variables
load_dotenv("config/.env")

# Get Discord bot token
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    print("ERROR: DISCORD_BOT_TOKEN not found in environment variables")
    sys.exit(1)

# Initialize Firebase if not already initialized
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate("config/credentials.json")
        firebase_admin.initialize_app(cred)
        print("Firebase initialized successfully")
    except Exception as e:
        print(f"ERROR: Failed to initialize Firebase: {e}")
        sys.exit(1)

async def update_voice_channel_stats():
    """Update voice channel names to display repository stats."""
    try:
        # Create Discord client with minimal intents
        intents = discord.Intents.default()
        client = discord.Client(intents=intents)
        
        @client.event
        async def on_ready():
            try:
                print(f"Connected as {client.user}")
                
                # Get the first guild (server) the bot is in
                guild = None
                for g in client.guilds:
                    guild = g
                    break
                    
                if not guild:
                    print("Bot is not in any guild. Cannot update voice channel stats.")
                    await client.close()
                    return
                    
                # Check basic permission
                if not client.user:
                    print("Client user not available")
                    await client.close()
                    return
                    
                bot_member = guild.get_member(client.user.id)
                if not bot_member or not bot_member.guild_permissions.manage_channels:
                    print("Bot lacks 'Manage Channels' permission")
                    await client.close()
                    return
                    
                # Fetch all data from Firestore
                repo_metrics, discord_contributions, _ = get_firestore_data()
                print(f"Retrieved repo metrics from Firestore: {repo_metrics}")
                
                # If repo_metrics is empty, just use zeros
                if not repo_metrics:
                    print("WARNING: No repo metrics found in Firestore. Using zeros.")
                    repo_metrics = {"stars_count": 0, "forks_count": 0, "total_contributors": 0}
                    
                # Get stats from repo metrics
                stars_count = repo_metrics.get('stars_count', 0)
                forks_count = repo_metrics.get('forks_count', 0) 
                total_contributors = repo_metrics.get('total_contributors', 0)  
                total_prs = repo_metrics.get('pr_count', 0)
                total_issues = repo_metrics.get('issues_count', 0)
                total_commits = repo_metrics.get('commits_count', 0)
                
                # Find the stats category
                stats_category = discord.utils.get(guild.categories, name="REPOSITORY STATS")
                if not stats_category:
                    print("REPOSITORY STATS category not found. Creating it...")
                    stats_category = await guild.create_category("REPOSITORY STATS")
                
                # Define channel names with stats
                channel_names = [
                    f"Stars: {stars_count}",
                    f"Forks: {forks_count}",
                    f"Issues: {total_issues}",
                    f"PRs: {total_prs}",
                    f"Contributors: {total_contributors}",
                    f"Commits: {total_commits}"
                ]
                
                # Find existing stats channels
                stats_keywords = ["Stars:", "Forks:", "Issues:", "PRs:", "Contributors:", "Commits:"]
                existing_stats_channels = {}
                
                # Map existing channels by their keyword prefix (only in the stats category)
                for channel in stats_category.voice_channels:
                    for keyword in stats_keywords:
                        if channel.name.startswith(keyword):
                            existing_stats_channels[keyword] = channel
                            break
                
                print(f"Found {len(existing_stats_channels)} existing stats channels")
                
                # Update existing channels or create new ones
                for target_name in channel_names:
                    # Extract keyword from target name
                    keyword = target_name.split(":")[0] + ":"
                    
                    try:
                        if keyword in existing_stats_channels:
                            # Update existing channel name if different
                            channel = existing_stats_channels[keyword]
                            if channel.name != target_name:
                                print(f"Updating channel: {channel.name} → {target_name}")
                                await channel.edit(name=target_name)
                                print(f"Updated: {target_name}")
                            else:
                                print(f"Channel already up to date: {target_name}")
                        else:
                            # Create new channel only if it doesn't exist
                            print(f"Creating new channel: {target_name}")
                            await guild.create_voice_channel(name=target_name, category=stats_category)
                            print(f"Created: {target_name}")
                            
                    except discord.Forbidden as e:
                        print(f"Permission denied for '{target_name}': {e}")
                        print(f"   This channel was probably created by a higher-role user")
                        print(f"   Skipping update to avoid creating duplicates...")
                    except Exception as e:
                        print(f"Error with '{target_name}': {e}")
                        
                print(f"Stats update completed at {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
                
            except Exception as e:
                print(f"Error in channel update process: {e}")
                import traceback
                traceback.print_exc()
            finally:
                # Close the client
                await client.close()
        
        # Run the Discord client
        if TOKEN:
            await client.start(TOKEN)
        else:
            print("ERROR: No Discord token available")
            return
            
    except Exception as e:
        print(f"Error updating voice channel stats: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main function to run the channel update."""
    print("="*50)
    print("Discord Channel Stats Updater")
    print("="*50)
    
    await update_voice_channel_stats()
    
    print("Channel update process completed")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 