# DisGitBot - Discord GitHub Integration System

## Quick Start Checklist

Before setting up, make sure you have:
- [ ] Discord bot token (from Discord Developer Portal)
- [ ] GitHub personal access token (with repo permissions)
- [ ] GitHub OAuth app (with ngrok callback URL)
- [ ] Google Cloud Firestore database and service account
- [ ] Ngrok account and authtoken (free tier works)
- [ ] Python 3.13+ installed

## Project Structure

```
discord_bot/
├── main.py                     # Main entry point for the Discord bot
├── src/
│   ├── __init__.py
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── init_discord_bot.py # Main Discord bot with slash commands
│   │   └── auth.py             # GitHub OAuth authentication using Flask and ngrok
│   └── utils/
│       ├── __init__.py
│       ├── firestore.py        # Firestore database operations
│       ├── role_utils.py       # Role determination logic based on contribution thresholds
│       ├── fetch_contributors.py # GitHub API integration to collect contribution data
│       └── update_discord_roles.py # Updates Discord roles based on GitHub activity
├── config/
│   ├── .env                    # Environment variables
│   ├── credentials.json        # Google Cloud service account credentials
│   └── discord_bot_requirements.txt # Python dependencies
├── deployment/
│   ├── deploy.sh               # Google Cloud Run deployment script
│   ├── takedown.sh             # Cloud Run service removal script
│   ├── Dockerfile              # Container configuration
│   └── entrypoint.sh           # Container startup script with health checks
└── README.md 
```

## Setup

### 1. Discord Bot Creation
1. Create a Discord bot at https://discord.com/developers/applications
2. Enable the following bot permissions:
   - **Bot** (Send messages, embed links, etc.)
   - **applications.commands** (Use slash commands)
   - **Manage Roles** (Assign roles based on contributions)
   - **Manage Channels** (Create/update voice channels for stats)
   - **Send Messages** (Bot responses)
   - **Read Message History** (Command processing)
   - **Use Slash Commands** (Primary interface)
3. Copy the bot token for environment variables

### 2. Firestore Database Setup
1. Create a Google Cloud project and enable Firestore
2. Create a service account with Firestore permissions
3. Download the service account JSON key file
4. Place the file as `config/credentials.json`
5. For deployment, encode the JSON as base64 for secrets

### 3. GitHub Personal Access Token
1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Create a token with the following permissions:
   - **repo** (Full repository access)
   - **read:org** (Read organization data)
   - **read:user** (Read user profile data)
3. Copy the token for environment variables

### 4. GitHub OAuth App Setup
1. Go to GitHub Settings → Developer settings → OAuth Apps
2. Create a new OAuth App with these settings:
   - **Application name**: Your bot name
   - **Homepage URL**: `https://ruxauth.ngrok.io`
   - **Authorization callback URL**: `https://ruxauth.ngrok.io/login/github/authorized`
3. Copy the Client ID and Client Secret for environment variables

### 5. Ngrok Authentication Setup
1. Sign up for a free ngrok account at https://dashboard.ngrok.com/signup
2. Go to https://dashboard.ngrok.com/get-started/your-authtoken
3. Copy your authtoken for environment variables
4. Choose a custom subdomain (e.g., "ruxauth") for consistent URLs

### 6. Environment Variables Configuration
Create a `config/.env` file with all required variables:

```bash
# Discord Configuration
DISCORD_BOT_TOKEN=your_discord_bot_token_here

# GitHub Configuration  
GITHUB_TOKEN=your_github_personal_access_token
GITHUB_CLIENT_ID=your_github_oauth_client_id
GITHUB_CLIENT_SECRET=your_github_oauth_client_secret

# Repository Configuration
REPO_OWNER=your_github_username_or_org
REPO_NAME=your_repository_name

# Ngrok Configuration (for GitHub OAuth)
NGROK_DOMAIN=your_chosen_subdomain
NGROK_AUTHTOKEN=your_ngrok_authtoken
```

### 7. Repository Secrets (for GitHub Actions/Cloud Deployment)
If using GitHub Actions or Cloud Run deployment, add these repository secrets:
- `DISCORD_BOT_TOKEN`
- `GITHUB_TOKEN` (as `GH_TOKEN`)
- `GOOGLE_CREDENTIALS_JSON` (base64 encoded credentials.json)
- `GITHUB_CLIENT_ID`
- `GITHUB_CLIENT_SECRET`
- `REPO_OWNER`
- `REPO_NAME`
- `NGROK_DOMAIN`
- `NGROK_AUTHTOKEN`

### 8. Installation and Running

**Local Development:**
```bash
# Create virtual environment
python3.13 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
python -m pip install --upgrade pip
pip install -r discord_bot/config/discord_bot_requirements.txt

# Verify environment variables
cd discord_bot
python -c "from dotenv import load_dotenv; import os; load_dotenv('config/.env'); print('Environment variables loaded successfully')"

# Run the bot
python src/bot/init_discord_bot.py
```

**Cloud Deployment:**
```bash
cd discord_bot
chmod +x deployment/deploy.sh
./deployment/deploy.sh
```

**⚠️ Important:** Make sure all environment variables are properly set in your `config/.env` file before running. The bot will check for missing variables on startup and display their status.

### 9. Troubleshooting

**Common Issues:**

1. **Ngrok Authentication Error (ERR_NGROK_4018)**
   - Make sure you have a valid `NGROK_AUTHTOKEN` in your `.env` file
   - Verify your ngrok account is active at https://dashboard.ngrok.com/

2. **Discord Bot Permission Issues**
   - Ensure the bot role is high enough in your server's role hierarchy
   - Check that all required permissions are enabled in Discord Developer Portal

3. **GitHub OAuth Not Working**
   - Verify your GitHub OAuth app callback URL matches your ngrok domain
   - Check that `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` are correct

4. **Firestore Connection Issues**
   - Ensure `credentials.json` exists in the `config/` directory
   - Verify the service account has proper Firestore permissions

5. **Environment Variables Not Loading**
   - Check that your `.env` file is in the `config/` directory
   - Ensure there are no extra spaces or quotes around values
   - Use the startup logs to verify which variables are loaded

**Debug Commands:**
```bash
# Check environment variables
python -c "from dotenv import load_dotenv; import os; load_dotenv('config/.env'); print([k for k in os.environ.keys() if k.startswith(('DISCORD_', 'GITHUB_', 'NGROK_', 'REPO_'))])"

# Test bot permissions
# Use the /check_permissions command in Discord
```

## File Explanations

### Core Bot Files
**main.py** - Main entry point for running the Discord bot

**src/bot/init_discord_bot.py** - Main Discord bot with slash commands (/link, /getstats, /halloffame, /setup_voice_stats)

**src/bot/auth.py** - GitHub OAuth authentication using Flask and ngrok

### Utility Files
**src/utils/firestore.py** - Firestore database operations for user data storage

**src/utils/role_utils.py** - Role determination logic based on contribution thresholds

**src/utils/fetch_contributors.py** - GitHub API integration to collect contribution data

**src/utils/update_discord_roles.py** - Updates Discord roles based on GitHub activity

### Configuration Files
**config/.env** - Environment variables (Discord tokens, GitHub credentials, ngrok domain)

**config/credentials.json** - Google Cloud service account credentials

**config/discord_bot_requirements.txt** - Python dependencies

### Deployment Files
**deployment/deploy.sh** - Google Cloud Run deployment script

**deployment/takedown.sh** - Cloud Run service removal script

**deployment/Dockerfile** - Container configuration

**deployment/entrypoint.sh** - Container startup script with health checks

### AI Components
**../issue_label/** - RAG-based AI system for automatic issue labeling using repository-specific context

**../pr_review/** - RAG-based AI system for code reviews using historical review data

## Demos

**Firestore, Workflow, Data Fetching, Auto Role Update**  
[![Firestore Demo](https://img.youtube.com/vi/AGuPckbdqdY/0.jpg)](https://youtu.be/AGuPckbdqdY)

**GitHub Link Integration & OAuth**  
[![GitHub OAuth Demo](https://img.youtube.com/vi/3uSMN4r4Af0/0.jpg)](https://youtu.be/3uSMN4r4Af0) 