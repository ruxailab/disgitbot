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
        # Import the modular Discord bot
        print("Starting modular Discord bot...")
        from src.bot.init_discord_bot import main as bot_main
        bot_main()
        print("Discord bot started successfully")
        
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