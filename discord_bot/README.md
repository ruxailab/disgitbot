# Discord Bot Setup Guide

## 1. Project Structure

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

## 2. Complete Setup Guide

### Overview: What You Need to Configure

First, let's understand what we need to set up. Note the file `discord_bot/config/.env.example` - this shows all the environment variables we need to fill in. 

**Step 1:** Copy `.env.example` to `.env` in the same directory:
```bash
cp discord_bot/config/.env.example discord_bot/config/.env
```

**Your `.env` file needs these values:**
- `DISCORD_BOT_TOKEN=` (Discord bot authentication)
- `GITHUB_TOKEN=` (GitHub API access)
- `GITHUB_CLIENT_ID=` (GitHub OAuth app ID)
- `GITHUB_CLIENT_SECRET=` (GitHub OAuth app secret)
- `REPO_OWNER=` (Your GitHub organization name)
- `NGROK_DOMAIN=` (Temporary tunneling domain)
- `NGROK_AUTHTOKEN=` (Ngrok authentication token)

**Additional files you need:**
- `discord_bot/config/credentials.json` (Firebase/Google Cloud credentials)

**GitHub repository secrets you need to configure:**
Go to your GitHub repository → Settings → Secrets and variables → Actions → Click "New repository secret" for each:
- `DISCORD_BOT_TOKEN`
- `GH_TOKEN` 
- `GOOGLE_CREDENTIALS_JSON`

---

## 3. Step-by-Step Configuration

### Step 1: Get DISCORD_BOT_TOKEN (.env) + DISCORD_BOT_TOKEN (GitHub Secret)

**What this configures:** 
- `.env` file: `DISCORD_BOT_TOKEN=your_token_here`
- GitHub Secret: `DISCORD_BOT_TOKEN`

**What this does:** Creates a Discord application and bot that can interact with your Discord server.

1. **Go to Discord Developer Portal:** https://discord.com/developers/applications
2. **Create New Application:** Click "New Application" → Enter any name you want
3. **Configure OAuth2 Scopes:**
   - Go to "OAuth2" tab
   - Under "Scopes", check these boxes:
     - ✅ `bot`
     - ✅ `applications.commands`
4. **Set Bot Permissions:**
   - Under "Bot Permissions", check these boxes:
     - ✅ `Manage Roles`
     - ✅ `View Channels` 
     - ✅ `Manage Channels`
     - ✅ `Send Messages`
     - ✅ `Embed Links`
     - ✅ `Read Message History`
     - ✅ `Use Slash Commands`
     - ✅ `Use Embedded Activities`
     - ✅ `Connect` (for voice channels)
5. **Invite Bot to Your Server:**
   - Copy the generated URL from the OAuth2 page
   - Paste it in your browser and invite the bot to your Discord server
6. **Enable Required Intents:**
   - Go to "Bot" tab
   - Enable these 3 intents:
     - ✅ `PRESENCE INTENT`
     - ✅ `SERVER MEMBERS INTENT` 
     - ✅ `MESSAGE CONTENT INTENT`
7. **Get Your Bot Token:**
   - Click "Reset Token" → Copy the token
   - **Add to `.env`:** `DISCORD_BOT_TOKEN=your_token_here`
   - **Add to GitHub Secrets:** Create secret named `DISCORD_BOT_TOKEN`

### Step 2: Get credentials.json (config file) + GOOGLE_CREDENTIALS_JSON (GitHub Secret)

**What this configures:** 
- Config file: `discord_bot/config/credentials.json`
- GitHub Secret: `GOOGLE_CREDENTIALS_JSON`

**What this does:** Creates a database to store Discord-GitHub user links and contribution data.

1. **Create Firebase Project:**
   - Go to https://console.firebase.google.com
   - Click "Get started" → "Create a project"
   - Enter any project name
   - Accept or decline Google Analytics (doesn't matter for this project)
   - Click "Create project"

2. **Create Firestore Database:**
   - In your Firebase project, click "Firestore Database" in the left sidebar
   - Click "Create database"
   - Choose "Start in production mode" → Click "Next"
   - Select any region → Click "Done"

3. **Add Test Data (Important!):**
   - Click "Start collection"
   - Collection ID: `discord`
   - Document ID: `123456789` (any numbers)
   - Add field: `github_id` with value: `testuser`
   - Click "Save"

4. **Download Service Account Key:**
   - Click the gear icon (Project Settings) in the top left
   - Go to "Service accounts" tab
   - Under "Admin SDK configuration snippet", select "Python"
   - Click "Generate new private key"
   - Download the JSON file

5. **Set Up credentials.json:**
   - **Rename** the downloaded file to `credentials.json`
   - **Move** it to `discord_bot/config/credentials.json`

6. **Create GitHub Secret:**
   - Open the `credentials.json` file in a text editor
   - Copy the entire JSON content
   - Go to https://www.base64encode.org/
   - Paste the JSON content and encode it to base64
   - Copy the base64 string
   - **Add to GitHub Secrets:** Create secret named `GOOGLE_CREDENTIALS_JSON` with the base64 string

### Step 3: Get GITHUB_TOKEN (.env) + GH_TOKEN (GitHub Secret)

**What this configures:** 
- `.env` file: `GITHUB_TOKEN=your_token_here`
- GitHub Secret: `GH_TOKEN`

**What this does:** Allows the bot to access GitHub API to fetch repository and contribution data.

1. **Go to GitHub Token Settings:** https://github.com/settings/tokens
2. **Create New Token:**
   - Click "Generate new token" → "Generate new token (classic)"
3. **Set Permissions:**
   - Check only: ✅ `repo` (this gives full repository access)
4. **Generate and Save:**
   - Click "Generate token" → Copy the token
   - **Add to `.env`:** `GITHUB_TOKEN=your_token_here`
   - **Add to GitHub Secrets:** Create secret named `GH_TOKEN`

### Step 4: Get GITHUB_CLIENT_ID (.env) + GITHUB_CLIENT_SECRET (.env)

**What this configures:** 
- `.env` file: `GITHUB_CLIENT_ID=your_client_id`
- `.env` file: `GITHUB_CLIENT_SECRET=your_secret`

**What this does:** Allows users to link their Discord accounts with their GitHub accounts securely.

1. **Go to GitHub Developer Settings:** https://github.com/settings/developers
2. **Create OAuth App:**
   - Click "New OAuth App"
3. **Fill in Application Details:**
   - **Application name:** `Your Bot Name` (anything you want)
   - **Homepage URL:** `https://your-ngrok-domain.ngrok.io` (you'll get this in Step 6)
   - **Authorization callback URL:** `https://your-ngrok-domain.ngrok.io/login/github/authorized`
4. **Get Credentials:**
   - Click "Register application"
   - Copy the "Client ID" → **Add to `.env`:** `GITHUB_CLIENT_ID=your_client_id`
   - Click "Generate a new client secret" → Copy it → **Add to `.env`:** `GITHUB_CLIENT_SECRET=your_secret`

### Step 5: Get REPO_OWNER (.env)

**What this configures:** 
- `.env` file: `REPO_OWNER=your_org_name`

**What this does:** Tells the bot which GitHub organization's repositories to monitor for contributions.

1. **Find Your Organization Name:**
   - Go to your organization's repositories page (example: `https://github.com/orgs/ruxailab/repositories`)
   - The organization name is the part after `/orgs/` (example: `ruxailab`)
2. **Set in Configuration:**
   - **Add to `.env`:** `REPO_OWNER=your_org_name` (example: `REPO_OWNER=ruxailab`)
   - **Important:** Use ONLY the organization name, NOT the full URL

### Step 6: Get NGROK_DOMAIN (.env) + NGROK_AUTHTOKEN (.env)

**What this configures:** 
- `.env` file: `NGROK_DOMAIN=your_subdomain`
- `.env` file: `NGROK_AUTHTOKEN=your_auth_token`

**What this does:** Creates a tunnel so GitHub can send OAuth callbacks to your local bot during development.

**Option 1 (Recommended):** Get pre-configured values:
- Contact `onlineee__.` on Discord for the `NGROK_DOMAIN` and `NGROK_AUTHTOKEN` values
- **Add to `.env`:** Set both values as provided

**Option 2:** Use your own Ngrok setup:
- Sign up at https://ngrok.com
- Get your authtoken from the dashboard
- Choose a subdomain (if you have a paid plan)
- **Add to `.env`:** `NGROK_DOMAIN=your_subdomain` (just the subdomain, not the full URL)
- **Add to `.env`:** `NGROK_AUTHTOKEN=your_auth_token`

---

## 4. Running the Bot Locally

### Install and Run

```bash
# 1. Make sure no virtual environment is active
deactivate

# 2. Create new virtual environment with Python 3.13
python3.13 -m venv discord_bot_env

# 3. Activate the virtual environment
source discord_bot_env/bin/activate

# 4. Upgrade pip to latest version
python -m pip install --upgrade pip

# 5. Install all required dependencies
pip install -r discord_bot/config/discord_bot_requirements.txt

# 6. Navigate to bot directory and run
cd discord_bot
python main.py
```

### Test the Bot

1. **Link Your Discord Account:**
   - In your Discord server, type `/link`
   - Click the URL the bot provides
   - Authorize with GitHub
   - You should see a success message

2. **Test Role Updates:**
   ```bash
   # Set your repository as default for GitHub CLI
   gh repo set-default
   
   # Trigger the workflow to fetch data and assign roles
   gh workflow run update-discord-roles.yml
   ```

---

## 5. Optional: Deploy to Google Cloud

If you want to deploy the bot to the cloud instead of running it locally:

```bash
# Make the deployment script executable
chmod +x discord_bot/deployment/deploy.sh

# Run the deployment script
./discord_bot/deployment/deploy.sh
```

The deployment script will guide you through:
- Selecting a Google Cloud project
- Configuring environment variables
- Setting up credentials
- Deploying to Cloud Run

---

## 6. Troubleshooting

**Common Issues:**

1. **Bot doesn't respond to commands:**
   - Check that all intents are enabled in Discord Developer Portal
   - Verify the bot has proper permissions in your Discord server

2. **Authentication errors:**
   - Double-check all tokens in your `.env` file
   - Make sure `credentials.json` is in the correct location

3. **GitHub linking fails:**
   - Verify your GitHub OAuth app settings
   - Check that the callback URL matches your Ngrok domain

4. **Role assignment doesn't work:**
   - Ensure the bot has "Manage Roles" permission
   - Check that the bot's role is higher than the roles it's trying to assign

**Need help?** Contact `onlineee__.` on Discord for support.