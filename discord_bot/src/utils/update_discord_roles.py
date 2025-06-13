# Importing libraries and modules
import os # Allows interaction with the operating system
import discord # Provides methods to interact with the Discord API
from discord.ext import commands # Extends discord.py and allows creation and handling of commands
from discord import app_commands # Allows parameters to be used for slash-commands
from dotenv import load_dotenv # Allows the use of environment variables (this is what we'll use to manage our
                               # tokens and keys)
 
import json  
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from firestore import get_firestore_data, get_hall_of_fame_data
from role_utils import determine_role, PR_THRESHOLDS, ISSUE_THRESHOLDS, COMMIT_THRESHOLDS, MEDAL_ROLES, get_medal_assignments
# Environment variables for tokens and other sensitive data
load_dotenv("config/.env") # Loads and reads the .env file 
TOKEN = os.getenv("DISCORD_BOT_TOKEN") # Reads and stores the Discord Token from the .env file

# Setup of intents. Intents are permissions the bot has on the server
intents = discord.Intents.default() # Intents can be set through this object
intents.message_content = True  # This intent allows you to read and handle messages from users
intents.members = True
# Bot setup
bot = commands.Bot(command_prefix="!", intents=intents) # Creates a bot and uses the intents created earlier


@bot.event
async def on_message(msg):
    if msg.author.id != bot.user.id:
        await msg.channel.send(f"Interesting message, {msg.author.mention}")

@bot.tree.command(name="greet", description="Sends a greeting to the user")
async def greet(interaction: discord.Interaction):
    username = interaction.user.mention
    await interaction.response.send_message(f"Hello there, {username}")

async def update_roles_for_guild(guild: discord.Guild):
    _, contributions, user_mappings = get_firestore_data()
    hall_of_fame_data = get_hall_of_fame_data()
    print(contributions, user_mappings)

    roles = {}

    # Retrieve existing roles in the guild
    existing_roles = {role.name: role for role in guild.roles}
    
    # Get medal assignments for top 3 all-time PR contributors
    medal_assignments = get_medal_assignments(hall_of_fame_data)
    print(f"Medal assignments: {medal_assignments}")

    # All roles to create (regular + medal roles)
    all_role_names = list(PR_THRESHOLDS.keys() | ISSUE_THRESHOLDS.keys() | COMMIT_THRESHOLDS.keys()) + MEDAL_ROLES

    # Ensure the required roles exist or recreate them as needed
    for role_name in all_role_names:
        # Check if the role already exists in the guild
        if role_name in existing_roles:
            print(f"Role {role_name} already exists, skipping creation.")
            roles[role_name] = existing_roles[role_name]
        else:
            try:
                print(f"Creating role: {role_name}")
                # Set special colors for medal roles
                if role_name == "🥇 PR Champion":
                    roles[role_name] = await guild.create_role(name=role_name, color=discord.Color.gold())
                elif role_name == "🥈 PR Runner-up":
                    roles[role_name] = await guild.create_role(name=role_name, color=discord.Color.from_rgb(192, 192, 192))  # Silver
                elif role_name == "🥉 PR Bronze":
                    roles[role_name] = await guild.create_role(name=role_name, color=discord.Color.from_rgb(205, 127, 50))  # Bronze
                else:
                    roles[role_name] = await guild.create_role(name=role_name)
            except discord.Forbidden:
                print(f"Insufficient permissions to create role: {role_name}")
                continue
            except Exception as e:
                print(f"Error creating role {role_name}: {e}")
                continue

    # Update roles for each member
    updated_count = 0
    for member in guild.members:
        github_username = user_mappings.get(str(member.id))
        if not github_username:
            continue
        user_data = contributions.get(github_username)
        if not user_data:
            continue

        # Remove all roles from the member except @everyone
        roles_to_remove = [role for role in member.roles if role.name != "@everyone"]
        try:
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove)
                print(f"Removed all roles from {member.name}")
        except Exception as e:
            print(f"Error removing roles from {member.name}: {e}")

        pr_count = user_data["pr_count"]
        issues_count = user_data["issues_count"]
        commits_count = user_data["commits_count"]

        pr_role, issue_role, commit_role = determine_role(pr_count, issues_count, commits_count)
        print(pr_role, issue_role, commit_role)
        new_role_names = [pr_role, issue_role, commit_role]

        # Add medal role if user is in top 3 all-time PRs
        if github_username in medal_assignments:
            medal_role = medal_assignments[github_username]
            new_role_names.append(medal_role)
            print(f"Adding medal role {medal_role} to {member.name}")

        # Add new roles
        for role_name in new_role_names:
            if role_name:
                try:
                    await member.add_roles(roles[role_name])
                    print(f"Added role {role_name} to {member.name}")
                except Exception as e:
                    print(f"Error adding role {role_name} to {member.name}: {e}")

        updated_count += 1

    print(f"Role update completed for {updated_count} members in guild {guild.name}")

@bot.event
async def on_ready():
    print(f"{bot.user} is online!")
    # Use a flag to ensure this update runs only once per startup
    if not hasattr(bot, 'roles_updated'):
        bot.roles_updated = True
        # Iterate through all guilds (or target specific guilds if needed)
        for guild in bot.guilds:
            await update_roles_for_guild(guild)
    await bot.close()

bot.run(TOKEN)    
