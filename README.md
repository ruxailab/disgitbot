# DisGitBot - Discord GitHub Bot

A Discord bot that automatically assigns roles based on GitHub contributions to the RUXAILAB project.

## 🎯 Overview  
This bot enables automatic Discord role assignment based on GitHub contributions. It allows contributors in our Discord server to get roles based on their activity (merged PRs, issues opened, commits) in the `ruxailab/RUXAILAB` repo. This encourages engagement and gives visibility to active contributors.

## 📹 Demo  
- **Firestore, Workflow, Data Fetching, Auto Role Update**  
  [![Firestore Demo](https://img.youtube.com/vi/AGuPckbdqdY/0.jpg)](https://youtu.be/AGuPckbdqdY)
- **GitHub Link Integration & OAuth**  
  [![GitHub OAuth Demo](https://img.youtube.com/vi/3uSMN4r4Af0/0.jpg)](https://youtu.be/3uSMN4r4Af0)  
  _Note: Used a different GitHub account here because my main got rate limited (tested the API too many times)._

## 🔧 Setup  
To use this, set the following repository secrets:

- `DISCORD_BOT_TOKEN`: Token for Discord bot
- `GH_TOKEN`: GitHub token with repo scope (needed for fetching contributions)
- `GOOGLE_CREDENTIALS_JSON`: JSON credentials for Firebase service account

## 🧠 How It Works

### 1. GitHub Workflow: `.github/workflows/update_discord_roles.yml`  
Runs daily (cron job at midnight) and manually via `workflow_dispatch`

**Steps:**
- Checkout the repo  
- Set up Python  
- Install dependencies  
- Set up Google Credentials for Firestore  
- Run `fetch_contributors.py` to update contributions in Firestore  
- Run `update_discord_roles.py` to update user roles in Discord  

### 2. Contribution Tracker: `discord_bot/fetch_contributors.py`  
Uses GitHub API to collect:
- Merged PR count  
- Issues opened  
- Commits  

Updates Firestore with all contributors' data

### 3. Discord Bot Logic

#### `update_discord_roles.py`:
- Reads contribution data from Firestore  
- Iterates over server members, assigns roles based on contribution thresholds  

#### `init_discord_bot.py`:
Adds Discord commands:
- `/link [GitHub username]`: Links Discord account to GitHub and updates Firestore  
- `/unlink`: Unlinks account  
- `/getstats`: Shows GitHub stats & Discord roles

#### `auth.py`:
- Implements GitHub OAuth to verify user identity.
- Uses Flask-Dance to handle OAuth flow.
- Retrieves GitHub username securely and updates Firestore.
- **Ngrok Integration**: Automatically starts ngrok to expose the Flask-Dance server for OAuth callbacks, allowing external users to authenticate via GitHub.

### 4. Data Management:
- Contributions and user mappings are stored in Firestore, eliminating the need for local JSON files.  
- Firestore structure:  
  - Collection: `discord`  
  - Document ID: Discord user ID  
  - Fields: `github_id`, `pr_count`, `issues_count`, `commits_count`, `role`

## 💭 Future Work
- Enhance role assignment logic based on additional contribution metrics  
- Implement more detailed analytics and reporting features
