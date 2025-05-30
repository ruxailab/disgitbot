#!/bin/bash
set -e

echo "=== Starting Discord Bot Deployment ==="
echo "Checking environment and files..."

# Check for environment variables
echo "Checking for environment variables..."
for ENV_VAR in DISCORD_BOT_TOKEN GITHUB_TOKEN GITHUB_CLIENT_ID GITHUB_CLIENT_SECRET REPO_OWNER REPO_NAME NGROK_DOMAIN; do
  if [ -n "${!ENV_VAR}" ]; then
    # Print first 5 characters followed by ...
    VALUE="${!ENV_VAR}"
    echo "✅ Found $ENV_VAR: ${VALUE:0:5}..."
  else
    echo "❌ $ENV_VAR not found!"
  fi
done

# Check for credentials
if [ -n "$CREDENTIALS_JSON" ] && [ -f "$CREDENTIALS_JSON" ]; then
  echo "✅ credentials.json found at $CREDENTIALS_JSON"
elif [ -f "credentials.json" ]; then
  echo "✅ credentials.json found in current directory"
else
  echo "❌ credentials.json not found!"
  # Search for it
  echo "Searching for credentials.json..."
  find / -name credentials.json -type f 2>/dev/null || echo "Not found"
fi

# List current directory for debugging
echo "📂 Directory contents:"
ls -la

# Create a simple status file to record running processes
touch discord_bot_status.log
echo "Startup timestamp: $(date)" > discord_bot_status.log

# Create health check server
PORT=${PORT:-8080}
echo "Creating health check server on port $PORT..."

cat > health_server.py << 'EOF'
import http.server
import socketserver
import os

PORT = int(os.environ.get('PORT', 8080))

class HealthHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'Discord bot is running')
        
    def log_message(self, format, *args):
        return

print(f"Health check server started at port {PORT}")
httpd = socketserver.TCPServer(("", PORT), HealthHandler)
httpd.serve_forever()
EOF

# Start the health check server in the background and save its PID
python health_server.py &
HEALTH_PID=$!

# Make sure the health server is running before continuing
echo "Waiting for health check server to start..."
sleep 5

# Check if the health server process is still running
if kill -0 $HEALTH_PID 2>/dev/null; then
  echo "✅ Health check server running on port $PORT"
else
  echo "❌ Health check server failed to start!"
  exit 1
fi

# Run the Discord bot with output to log file
echo "===== STARTING DISCORD BOT NOW! =====" >> discord_bot_status.log
echo "Starting Discord bot with command: python -u init_discord_bot.py"
echo "Starting Discord bot..."
echo "Command executed at: $(date)" >> discord_bot_status.log

# Run the Discord bot with all output captured to the log file
python -u init_discord_bot.py 2>&1 | tee -a discord_bot.log

# Report on exit
echo "Discord bot exited with code $?" | tee -a discord_bot_status.log

# Keep the container running for health check
echo "Bot exited, keeping container alive for logs inspection"
tail -f discord_bot.log 