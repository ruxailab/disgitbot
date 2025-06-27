# Discord Bot Setup

## 1. Structure

```
discord_bot/
├── main.py                     # Entry point
├── src/
│   ├── bot/
│   │   ├── init_discord_bot.py # Main bot code with slash commands
│   │   └── auth.py             # GitHub OAuth handling
│   └── utils/                  # Database and role utilities
├── config/
│   ├── .env                    # Your environment variables
│   ├── credentials.json        # Firebase service account key
│   └── discord_bot_requirements.txt
└── deployment/                 # Cloud deployment scripts
```

## 2. Step-by-Step Setup (Monkey See, Monkey Do)

### Step 1: Create Discord Bot
1. Go to https://discord.com/developers/applications
2. Click "New Application" → name it whatever
3. Go to "OAuth2" tab → check these boxes:
   - ✅ `bot`
   - ✅ `applications.commands`
4. Under "Bot Permissions" check these:
   - ✅ `Manage Roles`
   - ✅ `View Channels` 
   - ✅ `Manage Channels`
   - ✅ `Send Messages`
   - ✅ `Embed Links`
   - ✅ `Read Message History`
   - ✅ `Use Slash Commands`
   - ✅ `Use Embedded Activities `
   - ✅ `Connect` (for voice channels)
5. Copy the generated URL and invite bot to your server
6. Go to "Bot" tab → Enable these 3 intents:
   - ✅ `PRESENCE INTENT`
   - ✅ `SERVER MEMBERS INTENT` 
   - ✅ `MESSAGE CONTENT INTENT`
7. Click "Reset Token" → copy the token (save it!)

### Step 2: Create Firebase Database
1. Go to https://console.firebase.google.com
2. Create new project → Enable Firestore
3. Create database → Start in test mode → Next → Done
4. Add a dummy document so database isn't empty:
   - Collection: `discord`
   - Document ID: `123456789` (any numbers)
   - Field: `github_id`, Value: `testuser`
5. Go to Project Settings → Service Accounts → Python
6. Click "Generate new private key" → download the JSON file
7. **IMPORTANT**: Rename it to `credentials.json` and put it in `discord_bot/config/`

### Step 3: Create GitHub Token
1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Check only: ✅ `repo` (gives full repo access)
4. Generate → copy the token (save it!)

### Step 4: Create GitHub OAuth App  
1. Go to https://github.com/settings/developers
2. Click "New OAuth App"
3. Fill in:
   - **Application name**: `Your Bot Name`
   - **Homepage URL**: `https://your-ngrok-domain.ngrok.io`
   - **Authorization callback URL**: `https://your-ngrok-domain.ngrok.io/login/github/authorized`
4. Create → copy Client ID and generate Client Secret (save both!)

### Step 5: NGROK Setup (Temporary Solution)
**Note**: NGROK is temporary. DM online for the token and URLs. We need a better solution to bridge the bot's backend server's GitHub OAuth to end users.

### Step 6: Create Environment File
Create `discord_bot/config/.env` with these EXACT values:

```bash
# Discord (use your bot token from Step 1)
DISCORD_BOT_TOKEN=your_actual_bot_token_here

# GitHub (use your token from Step 3)
GITHUB_TOKEN=your_github_token_here
GITHUB_CLIENT_ID=your_oauth_client_id_from_step_4
GITHUB_CLIENT_SECRET=your_oauth_client_secret_from_step_4

# Repository Info (JUST THE NAMES, NOT FULL URLS)
REPO_OWNER=your_github_username
REPO_NAME=your_repository_name

# NGROK (DM online for these values)
NGROK_DOMAIN=your_assigned_subdomain
NGROK_AUTHTOKEN=your_assigned_token
```

**Important Clarifications**:
- `REPO_OWNER`: Just your GitHub username (e.g., `johnsmith`, NOT `https://github.com/johnsmith`)
- `REPO_NAME`: Just the repository name (e.g., `my-project`, NOT the full URL)
- `NGROK_DOMAIN`: Just the subdomain without `https://` (e.g., `mybot`, not `https://mybot.ngrok.io`)

### Step 7: Run the Bot
```bash
# 1. Make sure no virtual environment is active
deactivate

# 2. Create new virtual environment with Python 3.13
python3.13 -m venv discord_bot_env

# 3. Activate it
source discord_bot_env/bin/activate

# 4. Upgrade pip
python -m pip install --upgrade pip

# 5. Install requirements
pip install -r discord_bot/config/discord_bot_requirements.txt

# 6. Run the bot
cd discord_bot
python main.py
```

### Step 8: Link Your Account
1. In Discord, type `/link`
2. Click the URL it gives you
3. Authorize with GitHub
4. Done! Your Discord is now linked to GitHub

### Step 9: Update Roles (One-Time Setup)
```bash
# Set default repo for workflows
gh repo set-default

# Run the workflow to fetch data and assign roles
gh workflow run update-discord-roles.yml
```

**That's it!** Your bot should now work. If you get errors, check that your `.env` file has the right values and your `credentials.json` is in the right place. 