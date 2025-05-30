# init_discord_bot.py
import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
import json
import asyncio
import threading
from firestore import get_firestore_data
from role_utils import determine_role, get_next_role
from auth import get_github_username, wait_for_username, start_flask
import datetime
import sys

# Add startup logging
print("="*50)
print("Discord Bot Starting...")
print(f"Python version: {sys.version}")
print("Checking environment variables:")
for env_var in ["DISCORD_BOT_TOKEN", "GITHUB_TOKEN", "GITHUB_CLIENT_ID", 
                "GITHUB_CLIENT_SECRET", "REPO_OWNER", "REPO_NAME", 
                "NGROK_DOMAIN"]:
    value = os.getenv(env_var)
    if value:
        # Print first 5 chars and last 5 chars with ... in between for security
        masked_value = value[:5] + "..." + value[-5:] if len(value) > 15 else "[SET]"
        print(f"  ✅ {env_var}: {masked_value}")
    else:
        print(f"  ❌ {env_var}: Not set")
print("="*50)

# Load env vars
print("Loading environment variables...")
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    print("ERROR: DISCORD_BOT_TOKEN not found in environment variables!")
    sys.exit(1)

# Firebase init
if not firebase_admin._apps:
    cred = credentials.Certificate("credentials.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Create a lock for the verification process
verification_lock = threading.Lock()

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"{bot.user} is online! Synced {len(synced)} command(s).")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    
    # Start the auto-update task
    bot.loop.create_task(auto_update_voice_stats())

@bot.tree.command(name="link", description="Link your Discord to GitHub")
async def link(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    # Attempt to acquire the lock
    if not verification_lock.acquire(blocking=False):
        await interaction.followup.send("The verification process is currently busy. Please try again later.", ephemeral=True)
        return

    try:
        github_auth_url = await asyncio.get_event_loop().run_in_executor(None, get_github_username)
        await interaction.followup.send(f"Please complete GitHub auth: {github_auth_url}", ephemeral=True)

        # Wait for the Flask auth to complete and get the username
        github_username = await asyncio.get_event_loop().run_in_executor(None, wait_for_username)

        doc_ref = db.collection('discord').document(str(interaction.user.id))
        doc_ref.set({
            'github_id': github_username,
            'pr_count': 0,
            'issues_count': 0,
            'commits_count': 0,
            'role': 'member'
        })

        await interaction.followup.send(f"Successfully linked to GitHub user: `{github_username}`", ephemeral=True)

    except Exception as e:
        print("Error in /link:", e)
        await interaction.followup.send("Failed to link GitHub account.", ephemeral=True)

    finally:
        # Release the lock
        verification_lock.release()


@bot.tree.command(name="unlink", description="Unlinks your Discord account from your GitHub username")
async def unlink(interaction: discord.Interaction):
    try:
        # Defer the response immediately to prevent timeout
        await interaction.response.defer(ephemeral=True)

        # Reference the Firestore document
        doc_ref = db.collection('discord').document(str(interaction.user.id))

        # Check if the document exists
        if doc_ref.get().exists:
            # Delete the document
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


@bot.tree.command(name="getstats", description="Displays your GitHub stats and current role")
@app_commands.describe(type="Type of stats to display")
@app_commands.choices(type=[
    app_commands.Choice(name="Pull Requests", value="pr"),
    app_commands.Choice(name="Issues", value="issue"),
    app_commands.Choice(name="Commits", value="commit")
])
async def getstats(interaction: discord.Interaction, type: str = "pr"): 
    # Get data from Firestore first (before we do any interaction response)
    _, contributions, user_mappings = get_firestore_data()
    print(f"getstats - type: {type}")
    """Display user's GitHub stats and current role."""
    try:
        # Normalize the type parameter
        stats_type = type.lower().strip()
        if stats_type not in ["pr", "issue", "commit"]:
            stats_type = "pr"  # Default to PR stats
        
        user_id = str(interaction.user.id)
        github_username = user_mappings.get(user_id)
        print(user_id)
        print(github_username)
        if not github_username:
            await interaction.response.send_message(
                "Your Discord account is not linked to a GitHub username. Use `/link your_github_username` to link it.",
                ephemeral=True
            )
            return
            
        user_data = contributions.get(github_username)
            
        print(user_data)  # Make sure you are getting the right data
        
        if not user_data:
            await interaction.response.send_message(
                f"No contribution data found for GitHub user '{github_username}'.",
                ephemeral=True
            )
            return

        # Ensure 'stats' and necessary sub-fields exist before trying to access them for role determination
        pr_all_time = user_data.get("stats", {}).get("prs", {}).get("all_time", 0)
        issues_all_time = user_data.get("stats", {}).get("issues", {}).get("all_time", 0)
        commits_all_time = user_data.get("stats", {}).get("commits", {}).get("all_time", 0)

        pr_role, issue_role, commit_role = determine_role(
            pr_all_time,
            issues_all_time,
            commits_all_time
        )

        # Set up type-specific variables
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

        # Check if enhanced stats are available
        if "stats" in user_data and stats_field in user_data["stats"]:
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
            stats_table += f"24h:           {type_stats['daily']:<8}#{user_data.get('rankings', {}).get(f'{stats_type}_daily', 0)}\n"
            stats_table += f"7 days:        {type_stats['weekly']:<8}#{user_data.get('rankings', {}).get(f'{stats_type}_weekly', 0)}\n"
            stats_table += f"30 days:       {type_stats['monthly']:<8}#{user_data.get('rankings', {}).get(f'{stats_type}_monthly', 0)}\n"
            stats_table += f"Lifetime:      {type_stats['all_time']:<8}#{user_data.get('rankings', {}).get(stats_type, 0)}\n\n"
            
            # Add averages and streaks with customized wording
            stats_table += f"Daily Average ({stats.get('current_month', 'March')}): {type_stats.get('avg_per_day', 0)} {title_prefix}s\n\n"
            stats_table += f"Active {title_prefix} Streak: {type_stats.get('current_streak', 0)} {title_prefix}s\n"
            stats_table += f"Best {title_prefix} Streak: {type_stats.get('longest_streak', 0)} {title_prefix}s\n```"
            
            # Add level information based on role
            embed.add_field(name="Statistics", value=stats_table, inline=False)
            embed.add_field(name="Current level:", value=f"{role}", inline=True)
            
            # Determine next level using role_utils instead of hardcoded logic
            next_level = get_next_role(role, stats_type)
            
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
            
            await interaction.followup.send(embed=embed)
        else:
            # Use basic embed format if enhanced stats aren't available
            embed = discord.Embed(
                title=f"GitHub Stats for {github_username}",
                color=discord.Color.blue()
            )
            embed.add_field(name="Merged PRs", value=str(user_data["pr_count"]), inline=True)
            embed.add_field(name="Issues Opened", value=str(user_data["issues_count"]), inline=True)
            embed.add_field(name="Commits", value=str(user_data["commits_count"]), inline=True)
            embed.add_field(name="PR Role", value=pr_role, inline=True)
            embed.add_field(name="Issue Role", value=issue_role if issue_role else "None", inline=True)
            embed.add_field(name="Commit Role", value=commit_role if commit_role else "None", inline=True)

            await interaction.followup.send(embed=embed)

    except Exception as e:
        print(f"Error in getstats command: {e}")
        import traceback
        traceback.print_exc()
        # Try to respond with error if we haven't already responded
        try:
            await interaction.followup.send(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )
        except Exception as follow_up_error:
            print(f"Error sending followup: {follow_up_error}")

@bot.tree.command(name="setup_voice_stats", description="Sets up voice channels for repository stats display")
async def setup_voice_stats(interaction: discord.Interaction):
    """Sets up voice channels for repository stats display."""
    # Respond immediately to prevent timeout
    await interaction.response.defer(ephemeral=True)
    
    try:
        guild = interaction.guild
        
        # Check if a stats category already exists
        existing_category = discord.utils.get(guild.categories, name="📊 REPOSITORY STATS")
        
        if existing_category:
            # Category already exists, inform user
            await interaction.followup.send("Repository stats display already exists! Refreshing stats now.")
        else:
            # Create a new category for stats
            await guild.create_category("📊 REPOSITORY STATS")
            await interaction.followup.send("Repository stats display created! Refreshing stats now.")
        
        # Update the stats
        await update_voice_channel_stats()
        
    except Exception as e:
        await interaction.followup.send(f"Error setting up voice stats: {str(e)}")
        print(f"Error in setup_voice_stats: {e}")
        import traceback
        traceback.print_exc()

# Note: We use slash commands (/) as the primary interface for better Discord integration
# and user experience. Traditional text commands (!) are not used for consistency.

async def update_voice_channel_stats():
    """Update voice channel names to display repository stats on the sidebar."""
    try:
        # Get the first guild (server) the bot is in
        guild = None
        for g in bot.guilds:
            guild = g
            break
            
        if not guild:
            print("Bot is not in any guild. Cannot update voice channel stats.")
            return
            
        # Fetch all data from Firestore
        repo_metrics, discord_contributions, _ = get_firestore_data()
        print(f"Retrieved repo metrics from Firestore: {repo_metrics}")
        
        # If repo_metrics is empty, just use zeros (this should never happen in production)
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
        
        # Define channel names with stats
        channel_names = [
            f"⭐ Stars: {stars_count}",
            f"🍴 Forks: {forks_count}",
            f"🎯 Issues: {total_issues}",
            f"💼 PRs: {total_prs}",
            f"👥 Contributors: {total_contributors}",
            f"💻 Commits: {total_commits}"
        ]
        
        # Set up permissions to make channels private
        everyone_role = guild.default_role
        private_overwrites = {
            everyone_role: discord.PermissionOverwrite(
                connect=False,  # Prevent users from joining
                view_channel=True  # Still allow them to see the channel in sidebar
            )
        }
        
        # Try to find the stats category
        stats_category = discord.utils.get(guild.categories, name="📊 REPOSITORY STATS")
        
        # Create it if it doesn't exist
        if not stats_category:
            stats_category = await guild.create_category("📊 REPOSITORY STATS")
        
        # Get existing voice channels in the category
        existing_channels = [c for c in guild.voice_channels if c.category == stats_category]
        
        # Create or update channels
        for i, name in enumerate(channel_names):
            if i < len(existing_channels):
                # Update existing channel
                channel = existing_channels[i]
                if channel.name != name:
                    await channel.edit(name=name)
                
                # Make sure permissions are set correctly
                await channel.edit(overwrites=private_overwrites)
            else:
                # Create new channel with private permissions
                await guild.create_voice_channel(
                    name=name, 
                    category=stats_category,
                    overwrites=private_overwrites
                )
                
        # Delete extra channels if there are more than needed
        if len(existing_channels) > len(channel_names):
            for channel in existing_channels[len(channel_names):]:
                await channel.delete()
                
        print(f"Updated voice channel stats at {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
    except Exception as e:
        print(f"Error updating voice channel stats: {e}")

async def auto_update_voice_stats():
    """Background task to automatically update voice channel stats."""
    await bot.wait_until_ready()
    
    # Initial update
    await update_voice_channel_stats()
    
    while not bot.is_closed():
        try:
            await asyncio.sleep(3600)  # 1 hour
            await update_voice_channel_stats()
        except Exception as e:
            print(f"Error in auto update voice stats task: {e}")
            await asyncio.sleep(300)  # Wait 5 minutes on error

bot.run(TOKEN)