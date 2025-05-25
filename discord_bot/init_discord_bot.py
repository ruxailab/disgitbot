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
from firestore import load_data_from_firestore
from role_utils import determine_role, get_next_role
from auth import get_github_username, wait_for_username, start_flask

# Load env vars
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

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
    await bot.tree.sync()
    print(f"{bot.user} is online!")

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
@app_commands.describe(type="Type of stats to display: pr, issue, or commit (default: pr)")
async def getstats(interaction: discord.Interaction, type: str = "pr"): 
    contributions, user_mappings = load_data_from_firestore()
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

        # Pass the required data to determine_role
        pr_role, issue_role, commit_role = determine_role(
            user_data["pr_count"],
            user_data["issues_count"],
            user_data["commits_count"]
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
                description=f"Stats tracked across all RUXAILAB repositories. Updated daily at {stats.get('tracking_since', 'March 24, 2025')}, 00:00:00 PDT",
                color=discord.Color.blue()
            )
            
            # Create stats table with customized format
            display_prefix = f"{title_prefix}s{' ' * (12 - len(title_prefix + 's'))}"
            stats_table = f"```\n{display_prefix}   Volume   Ranking\n"
            stats_table += f"24h:           {type_stats['daily']}        #{user_data.get('rankings', {}).get(f'{stats_type}_daily', 0)}\n"
            stats_table += f"7 days:        {type_stats['weekly']}        #{user_data.get('rankings', {}).get(f'{stats_type}_weekly', 0)}\n"
            stats_table += f"30 days:       {type_stats['monthly']}       #{user_data.get('rankings', {}).get(f'{stats_type}_monthly', 0)}\n"
            stats_table += f"Lifetime:      {type_stats['all_time']}       #{user_data.get('rankings', {}).get(stats_type, 0)}\n\n"
            
            # Add averages and streaks with customized wording
            stats_table += f"Daily Average ({stats.get('current_month', 'March')}): {type_stats.get('avg_per_day', 0)} {title_prefix}s\n\n"
            stats_table += f"Active {title_prefix} Streak: {type_stats.get('current_streak', 0)} {title_prefix}s\n"
            stats_table += f"Best {title_prefix} Streak: {type_stats.get('longest_streak', 0)} {title_prefix}s\n```"
            
            # Add level information based on role
            embed.add_field(name="Statistics", value=stats_table, inline=False)
            embed.add_field(name="Current level:", value=f"@{role}", inline=True)
            
            # Determine next level using role_utils instead of hardcoded logic
            next_level = get_next_role(role, stats_type)
            
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
            
            await interaction.response.send_message(embed=embed)
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

            await interaction.response.send_message(embed=embed)

    except Exception as e:
        await interaction.response.send_message(
            f"An error occurred: {str(e)}",
            ephemeral=True
        )

bot.run(TOKEN)