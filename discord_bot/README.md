# Discord Bot Setup Guide

## 1. Project Structure

```
discord_bot/
├── main.py                     # Entry point with Flask OAuth integration
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
- `OAUTH_BASE_URL=` (Your Cloud Run URL - set in Step 4)

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

### Step 4: Deploy to Cloud Run & Set OAUTH_BASE_URL

**What this configures:** 
- `.env` file: `OAUTH_BASE_URL=YOUR_CLOUD_RUN_URL` 

**What this does:** Deploys your bot to Google Cloud Run to get a stable URL for GitHub OAuth, then saves it to your config.

1. **Deploy Your Bot:**
   ```bash
   # Make the deployment script executable
   chmod +x discord_bot/deployment/deploy.sh
   
   # Run the deployment script
   ./discord_bot/deployment/deploy.sh
   ```

2. **Get Your Cloud Run URL:**
   - After deployment completes, you'll see a URL like: `https://discord-bot-abcd1234-uc.a.run.app`
   - **IMPORTANT: Copy this exact URL** - you'll use it multiple times!
   
   **Alternative way to find your URL:**
   - Go to [Google Cloud Run Console](https://console.cloud.google.com/run)
   - Click on your service name (usually `discord-bot`)
   - Copy the URL shown at the top of the page

3. **Save Your URL to .env file:**
   - **Add to `.env`:** `OAUTH_BASE_URL=YOUR_CLOUD_RUN_URL`
   - **Example:** `OAUTH_BASE_URL=https://discord-bot-abcd1234-uc.a.run.app`

4. **Keep Your URL Handy:**
   - **Save this URL somewhere** - you'll need it for GitHub OAuth setup in the next step!
   - **Redeploy after updating .env:**
     ```bash
     ./discord_bot/deployment/deploy.sh
     ```

### Step 5: Get GITHUB_CLIENT_ID (.env) + GITHUB_CLIENT_SECRET (.env)

**What this configures:** 
- `.env` file: `GITHUB_CLIENT_ID=your_client_id`
- `.env` file: `GITHUB_CLIENT_SECRET=your_secret`

**What this does:** Allows users to link their Discord accounts with their GitHub accounts securely.

1. **Go to GitHub Developer Settings:** https://github.com/settings/developers
2. **Create OAuth App:**
   - Click "New OAuth App"
3. **Fill in Application Details:**
   - **Application name:** `Your Bot Name` (anything you want)
   - **Homepage URL:** `YOUR_CLOUD_RUN_URL` (from Step 4)
   - **Authorization callback URL:** `YOUR_CLOUD_RUN_URL/login/github/authorized`
   
   **Example URLs:** If your Cloud Run URL is `https://discord-bot-abcd1234-uc.a.run.app`, then:
   - Homepage URL: `https://discord-bot-abcd1234-uc.a.run.app`
   - Callback URL: `https://discord-bot-abcd1234-uc.a.run.app/login/github/authorized`

4. **Get Credentials:**
   - Click "Register application"
   - Copy the "Client ID" → **Add to `.env`:** `GITHUB_CLIENT_ID=your_client_id`
   - Click "Generate a new client secret" → Copy it → **Add to `.env`:** `GITHUB_CLIENT_SECRET=your_secret`

### Step 6: Get REPO_OWNER (.env)

**What this configures:** 
- `.env` file: `REPO_OWNER=your_org_name`

**What this does:** Tells the bot which GitHub organization's repositories to monitor for contributions.

1. **Find Your Organization Name:**
   - Go to your organization's repositories page (example: `https://github.com/orgs/ruxailab/repositories`)
   - The organization name is the part after `/orgs/` (example: `ruxailab`)
2. **Set in Configuration:**
   - **Add to `.env`:** `REPO_OWNER=your_org_name` (example: `REPO_OWNER=ruxailab`)
   - **Important:** Use ONLY the organization name, NOT the full URL

---

## 7. Running the Bot Locally (Optional)

If you want to run the bot locally for development:

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

**Note:** Local development won't work for OAuth features since GitHub OAuth needs a public URL.

---

## 8. Test the Bot

1. **Link Your Discord Account:**
   - In your Discord server, type `/link`
   - Click the URL the bot provides
   - You'll be redirected to GitHub to authorize
   - After authorization, you should see a success message
   - You can now close the tab and return to Discord

2. **Test Other Commands:**
   - `/getstats` - View your GitHub contribution stats
   - `/halloffame` - See top contributors
   - `/setup_voice_stats` - Create voice channels showing repo stats

3. **Test Role Updates:**
   ```bash
   # Set your repository as default for GitHub CLI
   gh repo set-default
   
   # Trigger the workflow to fetch data and assign roles
   gh workflow run update-discord-roles.yml
   ```

---

## 9. Troubleshooting

**Common Issues:**

1. **Bot doesn't respond to commands:**
   - Check that all intents are enabled in Discord Developer Portal
   - Verify the bot has proper permissions in your Discord server
   - Check Cloud Run logs for errors

2. **Authentication errors:**
   - Double-check all tokens in your `.env` file
   - Make sure `credentials.json` is in the correct location
   - Redeploy after changing `.env` file

3. **GitHub linking fails with "redirect_uri not associated":**
   - Make sure your GitHub OAuth app's callback URL matches your Cloud Run URL
   - Should be: `YOUR_CLOUD_RUN_URL/login/github/authorized`
   - Redeploy after updating GitHub OAuth settings

4. **Role assignment doesn't work:**
   - Ensure the bot has "Manage Roles" permission
   - Check that the bot's role is higher than the roles it's trying to assign

5. **"Discord bot is running" instead of GitHub OAuth:**
   - This means you're using old code - redeploy with the latest version
   - Make sure your `OAUTH_BASE_URL` is set correctly in `.env`

**Need help?** Contact `onlineee__.` on Discord for support.