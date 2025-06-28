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
    """Run the Discord bot asynchronously using existing bot setup"""
    print("🤖 Starting Discord bot...")
    
    try:
        # Import the existing Discord bot with all commands
        print("📦 Importing existing Discord bot setup...")
        import src.bot.init_discord_bot as discord_bot_module
        
        # The init_discord_bot module will handle all the Discord bot setup
        # including commands like /getstats, /halloffame, /link, etc.
        print("✅ Discord bot setup imported successfully")
        
        # Get the bot instance and run it
        print("🤖 Starting Discord bot connection...")
        discord_bot_module.bot.run(discord_bot_module.TOKEN)
        
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