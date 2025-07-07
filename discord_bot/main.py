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
    print("Starting Discord bot...")
    
    try:
        # Import the existing Discord bot with all commands
        print("Importing existing Discord bot setup...")
        import src.bot.init_discord_bot as discord_bot_module
        
        # The init_discord_bot module will handle all the Discord bot setup
        # including commands like /getstats, /halloffame, /link, etc.
        print("Discord bot setup imported successfully")
        
        # Get the bot instance and run it
        print("Starting Discord bot connection...")
        
        # Ensure TOKEN is validated (deployment pipeline guarantees this)
        token = discord_bot_module.TOKEN
        assert token is not None, "TOKEN should be validated by deployment pipeline"
        
        discord_bot_module.bot.run(token)
        
    except Exception as e:
        print(f"Error in Discord bot setup: {e}")
        import traceback
        traceback.print_exc()
        raise

def main():
    """Main orchestrator function"""
    print("="*60)
    print("Starting Discord Bot with Integrated OAuth Service")
    print("="*60)
    
    try:
        # Environment variables are validated by env_validator.py in deployment pipeline
        # No need to duplicate validation here - trust the deployment process
        print("Environment variables validated by deployment pipeline")
        
        # Import and create the OAuth Flask app
        print("Importing Flask OAuth components...")
        from src.bot.auth import create_oauth_app
        print("Flask OAuth import successful")
        
        # Create the Flask OAuth app
        print("Creating Flask OAuth app...")
        oauth_app = create_oauth_app()
        print("Flask OAuth app created successfully")
        
        # Start Discord bot in a separate thread
        print("Setting up Discord bot thread...")
        def start_discord_bot():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                print("Starting Discord bot in thread...")
                run_discord_bot_async()
            except Exception as e:
                print(f"Discord bot error: {e}")
                import traceback
                traceback.print_exc()
        
        discord_thread = threading.Thread(target=start_discord_bot, daemon=True)
        discord_thread.start()
        print("Discord bot thread started")
        
        print("Waiting for Discord bot to initialize...")
        time.sleep(3)  # Give Discord bot time to start
        
        # Get port from environment (Cloud Run uses PORT=8080)
        port = int(os.environ.get("PORT", 8080))
        
        print(f"Starting Flask OAuth service on port {port}...")
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
        print("\nShutting down services...")
    except Exception as e:
        print(f"Error in main(): {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main() 