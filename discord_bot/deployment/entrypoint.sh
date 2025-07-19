#!/bin/bash
set -e

echo "=== Starting Discord Bot with Flask OAuth ==="
echo "Discord Bot + Flask OAuth Integration"

# Check for environment variables
echo "Checking for environment variables..."
for ENV_VAR in DISCORD_BOT_TOKEN GITHUB_TOKEN GITHUB_CLIENT_ID GITHUB_CLIENT_SECRET REPO_OWNER OAUTH_BASE_URL; do
  if [ -n "${!ENV_VAR}" ]; then
    # Print first 5 characters followed by ...
    VALUE="${!ENV_VAR}"
    echo "Found $ENV_VAR: ${VALUE:0:5}..."
  else
    echo "$ENV_VAR not found!"
  fi
done

# Check for credentials
echo "Checking for Firebase credentials..."
if [ -f "/secret/firebase-credentials" ]; then
  echo "Found credentials at /secret/firebase-credentials (production mode)"
  # Copy to expected location
  cp /secret/firebase-credentials config/credentials.json
elif [ -f "config/credentials.json" ]; then
  echo "Found credentials.json in config directory"
else
  echo "No Firebase credentials found! Application will fail to start."
  echo "In production: Mount secret to /secret/firebase-credentials"
  echo "In development: Place credentials.json in config/ directory"
fi

# List current directory for debugging
echo "Directory contents:"
ls -la

# Create a simple status file to record running processes
touch discord_bot_status.log
echo "Startup timestamp: $(date)" > discord_bot_status.log

echo "===== STARTING DISCORD BOT WITH FLASK OAUTH ====="
echo "Starting Discord bot with Flask OAuth integration..."
echo "Command: python -u main.py"
echo "Command executed at: $(date)" >> discord_bot_status.log

# Run the new main.py which includes both Discord bot and Flask OAuth
python -u main.py 2>&1 | tee -a discord_bot.log

# Report on exit
echo "Discord bot exited with code $?" | tee -a discord_bot_status.log

# Keep the container running for logs inspection
echo "Bot exited, keeping container alive for logs inspection"
tail -f discord_bot.log 