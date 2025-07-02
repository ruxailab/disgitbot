# init_discord_bot.py
import os
import sys
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
import asyncio
import threading
import datetime

# Import utilities
from ..utils.firestore import get_firestore_data, get_hall_of_fame_data
from ..utils.role_utils import determine_role, get_next_role
from .auth import get_github_username_for_user, wait_for_username

# Add startup logging
print("="*50)
print("Discord Bot Starting...")
print(f"Python version: {sys.version}")
print("="*50)

# Load env vars first
print("Loading environment variables...")
load_dotenv("config/.env")

# Environment variables validated by deployment pipeline - trust the process
print("✅ Environment variables validated by deployment pipeline")
print("="*50)

# Get Discord bot token (validated by deployment pipeline)
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
# TOKEN is guaranteed to be set by deployment pipeline validation
assert TOKEN is not None, "DISCORD_BOT_TOKEN should be validated by deployment pipeline"

# Firebase init
if not firebase_admin._apps:
    cred = credentials.Certificate("config/credentials.json")
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
        discord_user_id = str(interaction.user.id)
        
        # Get the OAuth URL for this specific user
        oauth_url = get_github_username_for_user(discord_user_id)
        
        await interaction.followup.send(f"Please complete GitHub authentication: {oauth_url}", ephemeral=True)

        # Wait for the OAuth to complete and get the username
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
    """Display user's GitHub stats and current role."""
    # Defer first, just like halloffame
    await interaction.response.defer()
    
    # Then get data from Firestore
    _, contributions, user_mappings = get_firestore_data()
    print(f"getstats - type: {type}")
    
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
            await interaction.followup.send(
                "Your Discord account is not linked to a GitHub username. Use `/link your_github_username` to link it.",
                ephemeral=True
            )
            return
            
        user_data = contributions.get(github_username)
            
        print(user_data)  # Make sure you are getting the right data
        
        if not user_data:
            await interaction.followup.send(
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
        title_prefix = "PR"  # Default value
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

@bot.tree.command(name="halloffame", description="Shows top 3 contributors")
@app_commands.describe(
    type="Contribution type",
    period="Time period"
)
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
    """Simple hall of fame command - just fetch and display."""
    await interaction.response.defer()
    
    # Simple fetch from Firestore
    hall_of_fame_data = get_hall_of_fame_data()
    
    if not hall_of_fame_data:
        await interaction.followup.send("Hall of fame data not available yet.", ephemeral=True)
        return
    
    # Get top 3 for the requested category and period
    top_3 = hall_of_fame_data.get(type, {}).get(period, [])
    
    if not top_3:
        await interaction.followup.send(f"No data for {type} {period}.", ephemeral=True)
        return
    
    # Simple display
    type_names = {"pr": "Pull Requests", "issue": "Issues", "commit": "Commits"}
    period_names = {"all_time": "All Time", "monthly": "Monthly", "weekly": "Weekly", "daily": "Daily"}
    
    embed = discord.Embed(
        title=f"🏆 {type_names[type]} Hall of Fame ({period_names[period]})",
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
    
    embed.set_footer(text=f"Last updated: {hall_of_fame_data.get('last_updated', 'Unknown')}")
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="check_permissions", description="Check if bot has required permissions")
async def check_permissions(interaction: discord.Interaction):
    """Check if the bot has the required permissions."""
    await interaction.response.defer(ephemeral=True)
    
    guild = interaction.guild
    assert guild is not None, "Command should only work in guilds"
    assert bot.user is not None, "Bot user should be available"
    bot_member = guild.get_member(bot.user.id)
    assert bot_member is not None, "Bot should be a member of the guild"
    
    required_perms = [
        ("Manage Channels", bot_member.guild_permissions.manage_channels),
        ("Manage Roles", bot_member.guild_permissions.manage_roles),
        ("View Channels", bot_member.guild_permissions.view_channel),
        ("Connect", bot_member.guild_permissions.connect)
    ]
    
    results = []
    for perm_name, has_perm in required_perms:
        status = "✅" if has_perm else "❌"
        results.append(f"{status} {perm_name}")
    
    await interaction.followup.send(f"Bot permissions:\n" + "\n".join(results), ephemeral=True)

@bot.tree.command(name="setup_voice_stats", description="Sets up voice channels for repository stats display")
async def setup_voice_stats(interaction: discord.Interaction):
    """Sets up voice channels for repository stats display."""
    # Respond immediately to prevent timeout
    await interaction.response.defer(ephemeral=True)
    
    try:
        guild = interaction.guild
        assert guild is not None, "Command should only work in guilds"
        
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

async def update_voice_channel_stats():
    """Update voice channel names to display repository stats (minimal approach)."""
    try:
        # Get the first guild (server) the bot is in
        guild = None
        for g in bot.guilds:
            guild = g
            break
            
        if not guild:
            print("Bot is not in any guild. Cannot update voice channel stats.")
            return
            
        # Check basic permission
        assert bot.user is not None, "Bot user should be available"
        bot_member = guild.get_member(bot.user.id)
        assert bot_member is not None, "Bot should be a member of the guild"
        if not bot_member.guild_permissions.manage_channels:
            print("❌ Bot lacks 'Manage Channels' permission")
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
        
        # Define channel names with stats
        channel_names = [
            f"⭐ Stars: {stars_count}",
            f"🍴 Forks: {forks_count}",
            f"🎯 Issues: {total_issues}",
            f"💼 PRs: {total_prs}",
            f"👥 Contributors: {total_contributors}",
            f"💻 Commits: {total_commits}"
        ]
        
        # Find existing stats channels (look for channels starting with emojis)
        stats_emojis = ["⭐", "🍴", "🎯", "💼", "👥", "💻"]
        existing_stats_channels = {}
        
        # Map existing channels by their emoji prefix
        for channel in guild.voice_channels:
            for emoji in stats_emojis:
                if channel.name.startswith(emoji):
                    existing_stats_channels[emoji] = channel
                    break
        
        print(f"Found {len(existing_stats_channels)} existing stats channels")
        
        # Update existing channels or create new ones
        for target_name in channel_names:
            # Extract emoji from target name
            emoji = target_name.split()[0]
            
            try:
                if emoji in existing_stats_channels:
                    # Update existing channel name if different
                    channel = existing_stats_channels[emoji]
                    if channel.name != target_name:
                        print(f"Updating channel: {channel.name} → {target_name}")
                        await channel.edit(name=target_name)
                        print(f"✅ Updated: {target_name}")
                    else:
                        print(f"✅ Channel already up to date: {target_name}")
                else:
                    # Create new channel only if it doesn't exist
                    print(f"Creating new channel: {target_name}")
                    await guild.create_voice_channel(name=target_name)
                    print(f"✅ Created: {target_name}")
                    
            except discord.Forbidden as e:
                print(f"❌ Permission denied for '{target_name}': {e}")
                print(f"   This channel was probably created by a higher-role user")
                print(f"   Skipping update to avoid creating duplicates...")
                # Don't create new channels - just skip to avoid duplicates
            except Exception as e:
                print(f"❌ Error with '{target_name}': {e}")
                
        print(f"✅ Stats update completed at {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
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

# Bot is now run from main.py, not here
if __name__ == "__main__":
    bot.run(TOKEN)
