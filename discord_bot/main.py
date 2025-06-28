#!/usr/bin/env python3
"""
Main entry point for the Discord bot with integrated OAuth service.
This script runs both the Discord bot and Flask OAuth on the same port.
"""

import os
import threading
import asyncio
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/.env")

def run_discord_bot_async():
    """Run the Discord bot asynchronously"""
    print("🤖 Starting Discord bot...")
    
    try:
        # Import Discord bot components
        import discord
        from discord.ext import commands
        from discord import app_commands
        import firebase_admin
        from firebase_admin import credentials, firestore
        import datetime
        import sys
        
        print("✅ Discord imports successful")
        
        # Import utilities
        try:
            from src.utils.firestore import get_firestore_data, get_hall_of_fame_data
            from src.utils.role_utils import determine_role, get_next_role
            from src.bot.auth import get_github_username_for_user, wait_for_username
            print("✅ Utility imports successful")
        except ImportError as e:
            print(f"⚠️  ImportError for utils, trying fallback: {e}")
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
            from utils.firestore import get_firestore_data, get_hall_of_fame_data
            from utils.role_utils import determine_role, get_next_role
            from bot.auth import get_github_username_for_user, wait_for_username
            print("✅ Fallback utility imports successful")

        TOKEN = os.getenv("DISCORD_BOT_TOKEN")
        if not TOKEN:
            print("❌ ERROR: DISCORD_BOT_TOKEN not found!")
            return

        # Firebase init
        print("🔥 Initializing Firebase...")
        if not firebase_admin._apps:
            cred = credentials.Certificate("config/credentials.json")
            firebase_admin.initialize_app(cred)
        print("✅ Firebase initialized")

        db = firestore.client()

        intents = discord.Intents.default()
        intents.message_content = True
        bot = commands.Bot(command_prefix="!", intents=intents)

        verification_lock = threading.Lock()

        @bot.event
        async def on_ready():
            try:
                synced = await bot.tree.sync()
                print(f"🤖 {bot.user} is online! Synced {len(synced)} command(s).")
            except Exception as e:
                print(f"Failed to sync commands: {e}")

        @bot.tree.command(name="link", description="Link your Discord to GitHub")
        async def link(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)

            if not verification_lock.acquire(blocking=False):
                await interaction.followup.send("The verification process is currently busy. Please try again later.", ephemeral=True)
                return

            try:
                discord_user_id = str(interaction.user.id)
                oauth_url = get_github_username_for_user(discord_user_id)
                
                await interaction.followup.send(f"Please complete GitHub authentication: {oauth_url}", ephemeral=True)

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
                verification_lock.release()

        # Add other Discord commands here if needed (keeping it minimal for now)
        print("🤖 Starting Discord bot connection...")
        # Run the bot
        return bot.run(TOKEN)
        
    except Exception as e:
        print(f"❌ Error in Discord bot setup: {e}")
        import traceback
        traceback.print_exc()
        raise

def main():
    """Main orchestrator function"""
    print("="*60)
    print("🚀 Starting Discord Bot with Integrated OAuth Service")
    print("="*60)
    
    try:
        # Check required environment variables
        required_vars = [
            "DISCORD_BOT_TOKEN", 
            "GITHUB_TOKEN", 
            "GITHUB_CLIENT_ID", 
            "GITHUB_CLIENT_SECRET"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            print("Please check your .env file configuration.")
            return
        
        print("✅ All required environment variables found")
        
        # Set OAuth base URL if not provided
        if not os.getenv("OAUTH_BASE_URL"):
            # Try to detect if we're on Cloud Run
            if os.getenv("PORT"):  # Cloud Run sets PORT
                service_url = os.getenv("SERVICE_URL")
                if service_url:
                    os.environ["OAUTH_BASE_URL"] = service_url
                    print(f"📍 Detected Cloud Run service URL: {service_url}")
                else:
                    print("⚠️  Running on Cloud Run but SERVICE_URL not detected")
                    print("   OAuth callbacks will use default URL")
            else:
                print("🏠 Running locally - OAuth will use default URL")
        
        # Import and create the OAuth Flask app
        print("📦 Importing Flask OAuth components...")
        try:
            from src.bot.auth import create_oauth_app
            print("✅ Flask OAuth import successful")
        except Exception as e:
            print(f"❌ Failed to import Flask OAuth: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        # Create the Flask OAuth app
        print("🌶️  Creating Flask OAuth app...")
        try:
            oauth_app = create_oauth_app()
            print("✅ Flask OAuth app created successfully")
        except Exception as e:
            print(f"❌ Failed to create Flask OAuth app: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        # Start Discord bot in a separate thread
        print("🧵 Setting up Discord bot thread...")
        def start_discord_bot():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                print("🤖 Starting Discord bot in thread...")
                run_discord_bot_async()
            except Exception as e:
                print(f"❌ Discord bot error: {e}")
                import traceback
                traceback.print_exc()
        
        discord_thread = threading.Thread(target=start_discord_bot, daemon=True)
        discord_thread.start()
        print("✅ Discord bot thread started")
        
        print("⏳ Waiting for Discord bot to initialize...")
        time.sleep(3)  # Give Discord bot time to start
        
        # Get port from environment (Cloud Run uses PORT=8080)
        port = int(os.environ.get("PORT", 8080))
        
        print(f"🌐 Starting Flask OAuth service on port {port}...")
        print(f"   Listening on 0.0.0.0:{port}")
        
        # Run Flask web server in main thread
        oauth_app.run(
            host="0.0.0.0",
            port=port,
            debug=True,  # Enable debug for more logging
            use_reloader=False,
            threaded=True
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down services...")
    except Exception as e:
        print(f"❌ Error in main(): {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main() 