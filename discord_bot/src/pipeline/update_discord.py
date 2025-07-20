#!/usr/bin/env python3
"""
Stage 3: Discord Update Pipeline
Update Discord roles and channels using data from Firestore
"""

import os
import sys
import subprocess

# Add the parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'utils'))

def main():
    """Main Discord update pipeline"""
    print("========== Stage 3: Discord Update Pipeline ==========")
    
    # Check for required environment variables
    discord_token = os.getenv('DISCORD_BOT_TOKEN')
    google_creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    if not discord_token:
        print("ERROR: DISCORD_BOT_TOKEN environment variable is not set")
        sys.exit(1)
    
    if not google_creds:
        print("ERROR: GOOGLE_APPLICATION_CREDENTIALS environment variable is not set")
        sys.exit(1)
    
    try:
        # Get the path to the utils directory
        utils_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'utils')
        
        # Update Discord roles
        print("Updating Discord roles...")
        roles_script = os.path.join(utils_dir, 'update_discord_roles.py')
        
        result = subprocess.run([
            sys.executable, roles_script
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error updating Discord roles: {result.stderr}")
            print(f"Stdout: {result.stdout}")
        else:
            print("Discord roles updated successfully")
            if result.stdout:
                print(f"Output: {result.stdout}")
        
        # Update Discord channel stats
        print("Updating Discord channel stats...")
        channels_script = os.path.join(utils_dir, 'update_discord_channels.py')
        
        # Change to discord_bot directory for the channels script
        original_cwd = os.getcwd()
        discord_bot_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.chdir(discord_bot_dir)
        
        try:
            result = subprocess.run([
                sys.executable, channels_script
            ], capture_output=True, text=True, cwd=discord_bot_dir)
            
            if result.returncode != 0:
                print(f"Error updating Discord channels: {result.stderr}")
                print(f"Stdout: {result.stdout}")
            else:
                print("Discord channels updated successfully")
                if result.stdout:
                    print(f"Output: {result.stdout}")
        finally:
            # Restore original working directory
            os.chdir(original_cwd)
        
        print("Stage 3: Discord Update - COMPLETED")
        
    except Exception as e:
        print(f"Error in Discord update pipeline: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 