# DisGitBot - Discord GitHub Integration System

A Discord bot that automatically assigns roles based on GitHub contributions, with additional AI-powered issue labeling and PR review components.

## Project Structure

### Discord Bot Core
- **init_discord_bot.py** - Main Discord bot with slash commands (/link, /getstats, /halloffame, /setup_voice_stats)
- **auth.py** - GitHub OAuth authentication using Flask and ngrok
- **update_discord_roles.py** - Updates Discord roles based on GitHub activity
- **fetch_contributors.py** - GitHub API integration to collect contribution data
- **firestore.py** - Firestore database operations for user data storage
- **role_utils.py** - Role determination logic based on contribution thresholds
- **deploy.sh** - Google Cloud Run deployment script
- **takedown.sh** - Cloud Run service removal script
- **Dockerfile** - Container configuration
- **entrypoint.sh** - Container startup script with health checks
- **discord_bot_requirements.txt** - Python dependencies

### AI Components
- **issue_label/** - RAG-based AI system for automatic issue labeling using repository-specific context
- **pr_review/** - RAG-based AI system for code reviews using historical review data

### Configuration
- **.env** - Environment variables (Discord tokens, GitHub credentials, ngrok domain)
- **credentials.json** - Google Cloud service account credentials

## Demo Videos

**Firestore, Workflow, Data Fetching, Auto Role Update**  
[![Firestore Demo](https://img.youtube.com/vi/AGuPckbdqdY/0.jpg)](https://youtu.be/AGuPckbdqdY)

**GitHub Link Integration & OAuth**  
[![GitHub OAuth Demo](https://img.youtube.com/vi/3uSMN4r4Af0/0.jpg)](https://youtu.be/3uSMN4r4Af0)

## Discord Bot Setup

### Required Permissions Setup

1. Go to Discord Developer Portal: https://discord.com/developers/applications
2. Select your bot application
3. Navigate to OAuth2 → OAuth2 URL Generator

**Configure these exact settings based on the OAuth2 interface:**

**SCOPES:**
- bot
- applications.commands

**BOT PERMISSIONS:**
- Manage Roles
- Manage Channels  
- Send Messages
- Read Message History
- Use Slash Commands

**Important:** Each time you want to edit the bot's permissions, you must:
1. Kick the bot from your Discord server
2. Return to the OAuth2 URL Generator tab
3. Generate a new invite link with updated permissions
4. Re-invite the bot using the new URL

### Environment Configuration

Create `.env` file:
```
DISCORD_BOT_TOKEN=your_discord_bot_token
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
NGROK_DOMAIN=your_ngrok_domain
SECRET_KEY=random_secret_key
GH_TOKEN=github_token_with_repo_scope
```

### Repository Secrets (for GitHub Actions)
- `DISCORD_BOT_TOKEN`
- `GH_TOKEN` 
- `GOOGLE_CREDENTIALS_JSON`

## How It Works

### Authentication Flow
1. User runs `/link` command
2. Bot starts Flask server with ngrok tunnel
3. User authenticates via GitHub OAuth
4. GitHub username linked to Discord ID in Firestore

### Automated Role Updates
- Daily GitHub workflow at midnight
- Fetches contribution data (PRs, issues, commits) 
- Updates user roles based on contribution thresholds
- All data stored in Firestore

### Available Commands
- `/link [username]` - Link Discord account to GitHub
- `/unlink` - Unlink GitHub account
- `/getstats` - Display your GitHub statistics and roles
- `/halloffame` - Show top contributors
- `/setup_voice_stats` - Create stat display channels

## Local Development

Requirements: Python 3.13

```bash
pip install -r discord_bot_requirements.txt
python init_discord_bot.py
```

## Cloud Deployment

### Google Cloud Run
```bash
# Configure Google Cloud CLI
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Deploy
bash deploy.sh

# Remove deployment
bash takedown.sh
```

### AI Components Setup

**Issue Label System:**
```bash
cd issue_label
pip install -r requirements.txt
python scripts/build_index.py --repo owner/repo
python main.py --repo owner/repo --issue 123
```

**PR Review System:**
```bash
cd pr_review  
pip install -r requirements.txt
python scripts/build_index.py
python main.py --repo owner/repo --pr 123
```

## Data Storage

Firestore structure:
- Collection: `discord`
- Document ID: Discord user ID  
- Fields: `github_id`, `pr_count`, `issues_count`, `commits_count`, `role`

## Technical Notes

- Authentication always uses ngrok tunneling
- Cloud Run environment variables are ignored to prevent URL conflicts  
- Bot requires Python 3.13 for full compatibility
- AI components use RAG for repository-specific context 