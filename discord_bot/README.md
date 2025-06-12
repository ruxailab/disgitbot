# DisGitBot - Discord GitHub Integration System

## Project Structure

```
discord_bot/
├── init_discord_bot.py          # Main Discord bot with slash commands
├── auth.py                      # GitHub OAuth authentication using Flask and ngrok
├── update_discord_roles.py      # Updates Discord roles based on GitHub activity
├── fetch_contributors.py        # GitHub API integration to collect contribution data
├── firestore.py                 # Firestore database operations
├── role_utils.py               # Role determination logic based on contribution thresholds
├── deploy.sh                   # Google Cloud Run deployment script
├── takedown.sh                 # Cloud Run service removal script
├── Dockerfile                  # Container configuration
├── entrypoint.sh              # Container startup script with health checks
├── discord_bot_requirements.txt # Python dependencies
├── .env                       # Environment variables
└── credentials.json           # Google Cloud service account credentials

issue_label/                    # RAG-based AI system for automatic issue labeling
pr_review/                     # RAG-based AI system for code reviews
```

## Setup

### 1. Discord Bot Creation
1. Make discord bot at https://discord.com/developers/applications
2. Ensure these permissions are given  
   - bot
   - applications.commands
   - Manage Roles
   - Manage Channels
   - Send Messages
   - Read Message History
   - Use Slash Commands
3. Get the discord bot token, put it in `.env` and repo secret as `DISCORD_BOT_TOKEN`

### 2. Firestore Setup
1. Make firestore database
2. Get private key (service account JSON)
3. Put the JSON file in repo as `credentials.json`
4. Put the base64 encoded version in repo secret as `GOOGLE_CREDENTIALS_JSON`

### 3. GitHub Token
1. Make github token with repo permissions
2. Put in `.env` and repo secret as `GH_TOKEN`

### 4. GitHub OAuth App
1. Make github OAuth app
2. Set homepage URL = `https://ruxauth.ngrok.io`
3. Set callback URL = `https://ruxauth.ngrok.io/login/github/authorized`
4. Put client id and client secret in `.env`

### 5. Run Commands
```bash
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r discord_bot/discord_bot_requirements.txt
cd discord_bot
chmod +x deploy.sh
./deploy.sh
```

## File Explanations

**init_discord_bot.py** - Main Discord bot with slash commands (/link, /getstats, /halloffame, /setup_voice_stats)

**auth.py** - GitHub OAuth authentication using Flask and ngrok

**update_discord_roles.py** - Updates Discord roles based on GitHub activity

**fetch_contributors.py** - GitHub API integration to collect contribution data

**firestore.py** - Firestore database operations for user data storage

**role_utils.py** - Role determination logic based on contribution thresholds

**deploy.sh** - Google Cloud Run deployment script

**takedown.sh** - Cloud Run service removal script

**Dockerfile** - Container configuration

**entrypoint.sh** - Container startup script with health checks

**discord_bot_requirements.txt** - Python dependencies

**.env** - Environment variables (Discord tokens, GitHub credentials, ngrok domain)

**credentials.json** - Google Cloud service account credentials

**issue_label/** - RAG-based AI system for automatic issue labeling using repository-specific context

**pr_review/** - RAG-based AI system for code reviews using historical review data

## Demos

**Firestore, Workflow, Data Fetching, Auto Role Update**  
[![Firestore Demo](https://img.youtube.com/vi/AGuPckbdqdY/0.jpg)](https://youtu.be/AGuPckbdqdY)

**GitHub Link Integration & OAuth**  
[![GitHub OAuth Demo](https://img.youtube.com/vi/3uSMN4r4Af0/0.jpg)](https://youtu.be/3uSMN4r4Af0) 