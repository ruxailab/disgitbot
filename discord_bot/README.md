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

### Step 4: Get Cloud Run URL (Placeholder Deployment)

**What this configures:** 
- `.env` file: `OAUTH_BASE_URL=YOUR_CLOUD_RUN_URL` 

**What this does:** Creates a placeholder Cloud Run service to get your stable URL, which you'll need for GitHub OAuth setup.

1. **Deploy placeholder service to get URL:**
   ```bash
   gcloud run deploy discord-bot \
     --image gcr.io/cloudrun/hello \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```

2. **Get Your Cloud Run URL:**
   - After deployment completes, you'll see a URL like: `https://discord-bot-abcd1234-uc.a.run.app`
   - **IMPORTANT: Copy this exact URL** - you'll use it multiple times!
   
   **Alternative way to find your URL:**
   - Go to [Google Cloud Run Console](https://console.cloud.google.com/run)
   - Click on your service name (`discord-bot`)
   - Copy the URL shown at the top of the page

3. **Save Your URL to .env file:**
   - **Add to `.env`:** `OAUTH_BASE_URL=YOUR_CLOUD_RUN_URL`
   - **Example:** `OAUTH_BASE_URL=https://discord-bot-abcd1234-uc.a.run.app`

4. **Keep Your URL Handy:**
   - **Save this URL somewhere** - you'll need it for GitHub OAuth setup in the next step!

**Note:** This placeholder will be replaced with your actual bot in Step 7.

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

## 7. Final Deployment

Now that all your environment variables and GitHub OAuth settings are configured, deploy your bot:

```bash
# Deploy your bot with all settings configured
./discord_bot/deployment/deploy.sh
```

The deployment script will:
- Build your Docker image with the updated `.env` file
- Deploy to Cloud Run with your `OAUTH_BASE_URL` configured
- Set up all environment variables and secrets

**After deployment completes, your bot will be fully functional with OAuth!**

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

---

## 10. Understanding the Networking Architecture (For Developers)

### **🏗️ How Discord Bot + Flask OAuth Works Together**

This section explains the technical details of how our Discord bot serves both Discord commands AND web OAuth on the same Cloud Run service.

### **📁 File Structure Overview**

```
discord_bot/
├── main.py                          # Entry point - orchestrates everything
├── src/bot/
│   ├── init_discord_bot.py         # Discord bot with all commands
│   └── auth.py                     # Flask OAuth server
└── deployment/
    └── entrypoint.sh               # Container startup script
```

### **🚀 Container Startup Flow**

**File: `discord_bot/deployment/entrypoint.sh` (Lines 42-47)**
```bash
echo "Command: python -u main.py"
echo "Command executed at: $(date)" >> discord_bot_status.log

# Run the new main.py which includes both Discord bot and Flask OAuth
python -u main.py 2>&1 | tee -a discord_bot.log
```

**File: `discord_bot/main.py` (Lines 15-31)**
```python
def run_discord_bot_async():
    """Run the Discord bot asynchronously using existing bot setup"""
    print("🤖 Starting Discord bot...")
    
    try:
        # Import the existing Discord bot with all commands
        print("📦 Importing existing Discord bot setup...")
        import src.bot.init_discord_bot as discord_bot_module
        
        print("✅ Discord bot setup imported successfully")
        
        # Get the bot instance and run it
        print("🤖 Starting Discord bot connection...")
        discord_bot_module.bot.run(discord_bot_module.TOKEN)
```

### **🧵 Threading Architecture**

**File: `discord_bot/main.py` (Lines 64-75)**
```python
# Start Discord bot in a separate thread
print("🧵 Setting up Discord bot thread...")
def start_discord_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        print("🤖 Starting Discord bot in thread...")
        run_discord_bot_async()
    except Exception as e:
        print(f"❌ Discord bot error: {e}")
        import traceback
        traceback.print_exc()

discord_thread = threading.Thread(target=start_discord_bot, daemon=True)
discord_thread.start()
```

**File: `discord_bot/main.py` (Lines 85-94)**
```python
# Run Flask web server in main thread
oauth_app.run(
    host="0.0.0.0",    # Listen on all network interfaces
    port=port,         # Cloud Run sets PORT=8080
    debug=True,        # Enable debug for more logging
    use_reloader=False,
    threaded=True      # Handle multiple requests simultaneously
)
```

### **🌐 Flask OAuth Route Definitions**

**File: `discord_bot/src/bot/auth.py` (Lines 40-49)**
```python
@app.route("/")
def index():
    return jsonify({
        "service": "Discord Bot with OAuth",
        "status": "running",
        "endpoints": {
            "start_auth": "/auth/start/<discord_user_id>",
            "callback": "/auth/callback"
        }
    })
```

**File: `discord_bot/src/bot/auth.py` (Lines 51-70)**
```python
@app.route("/auth/start/<discord_user_id>")
def start_oauth(discord_user_id):
    """Start OAuth flow for a specific Discord user"""
    try:
        with oauth_sessions_lock:
            # Clear any existing session for this user
            oauth_sessions[discord_user_id] = {
                'status': 'pending',
                'created_at': time.time()
            }
        
        # Store user ID in session for callback
        session['discord_user_id'] = discord_user_id
        
        print(f"Starting OAuth for Discord user: {discord_user_id}")
        
        # Redirect to GitHub OAuth
        return redirect(url_for("github.login"))
```

### **🔄 GitHub OAuth Callback Processing**

**File: `discord_bot/src/bot/auth.py` (Lines 75-95)**
```python
@app.route("/auth/callback")
def github_callback():
    """Handle GitHub OAuth callback - original working version"""
    try:
        discord_user_id = session.get('discord_user_id')
        
        if not discord_user_id:
            return "Authentication failed: No Discord user session", 400
        
        if not github.authorized:
            print("❌ GitHub OAuth not authorized")
            with oauth_sessions_lock:
                oauth_sessions[discord_user_id] = {
                    'status': 'failed',
                    'error': 'GitHub authorization failed'
                }
            return "GitHub authorization failed", 400
        
        # Get GitHub user info
        resp = github.get("/user")
```

### **💾 Inter-Thread Communication**

**File: `discord_bot/src/bot/auth.py` (Lines 11-13)**
```python
# Global state for OAuth sessions (keyed by Discord user ID)
oauth_sessions = {}
oauth_sessions_lock = threading.Lock()
```

**File: `discord_bot/src/bot/auth.py` (Lines 170-185)**
```python
def wait_for_username(discord_user_id, max_wait_time=300):
    """Wait for OAuth completion by polling the status"""
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        with oauth_sessions_lock:
            session_data = oauth_sessions.get(discord_user_id)
            
            if session_data:
                if session_data['status'] == 'completed':
                    github_username = session_data.get('github_username')
                    # Clean up
                    del oauth_sessions[discord_user_id]
                    return github_username
```

### **🌍 The Network Magic: How Cloud Run URL → Flask App**

**Key Question:** How does `https://discord-bot-999242429166.us-central1.run.app/auth/start/123` actually reach your Flask code?

### **🔧 Step 1: Cloud Run Sets Up a Reverse Proxy**

When you deploy, Cloud Run automatically creates a **reverse proxy**:

```bash
# Your deployment command:
gcloud run deploy discord-bot --port=8080

# Cloud Run thinks: "I'll listen on the public URL and forward to port 8080 inside the container"
```

### **🚪 Step 2: Flask Binds to Port 8080 Inside Container**

**File: `discord_bot/main.py` (Lines 85-90)**
```python
# Get port from environment (Cloud Run sets PORT=8080)
port = int(os.environ.get("PORT", 8080))

# Flask says: "I'm listening on ALL network interfaces, port 8080"
oauth_app.run(
    host="0.0.0.0",    # ← Listen on ALL interfaces (not just localhost)
    port=port,         # ← 8080
)
```

### **🌐 Step 3: The Network Translation**

```
User types: https://discord-bot-999242429166.us-central1.run.app/auth/start/123
     ↓
Google DNS: "discord-bot-999242429166.us-central1.run.app = Load Balancer IP 34.102.136.180"
     ↓
Load Balancer: "This request is for service 'discord-bot' in us-central1"
     ↓
Container Router: "discord-bot service → Container Instance #abc123"
     ↓
Network Namespace: "Forward to container internal IP 10.4.0.15:8080"
     ↓
Container Network: "localhost:8080/auth/start/123"
     ↓
Flask App: "@app.route('/auth/start/<id>') matches! Call start_oauth(id='123')"
```

### **🔍 The Actual HTTP Translation**

**What the user sends:**
```http
GET /auth/start/123 HTTP/1.1
Host: discord-bot-999242429166.us-central1.run.app
```

**What Cloud Run forwards to your Flask app:**
```http
GET /auth/start/123 HTTP/1.1
Host: localhost:8080                    # ← Changed!
X-Forwarded-Host: discord-bot-999242429166.us-central1.run.app  # ← Original host saved
X-Forwarded-Proto: https               # ← Original protocol saved
```

### **🏠 Why `host="0.0.0.0"` is Critical**

**File: `discord_bot/main.py` (Line 87)**
```python
oauth_app.run(host="0.0.0.0", port=8080)
             # ↑ THIS IS KEY!
```

- **If you used `host="127.0.0.1"`**: Flask only listens on localhost interface
- **With `host="0.0.0.0"`**: Flask listens on ALL network interfaces, including container's external interface

### **🐳 Inside the Container Network**

```bash
# Inside your container, this is what the network looks like:
$ ip addr show
1: lo: 127.0.0.1        # localhost
2: eth0: 10.4.0.15      # container's internal IP

$ netstat -ln
tcp  0.0.0.0:8080  LISTEN   # Flask listening on ALL interfaces

# Cloud Run forwards from eth0 (10.4.0.15:8080) to your Flask app
```

### **🎯 The Complete Flow**

```
1. 🌍 Public Internet
   User: "I want https://discord-bot-999242429166.us-central1.run.app/auth/start/123"
   
2. 🌐 Google's Load Balancer  
   LB: "discord-bot-999242429166 → Container cluster in us-central1"
   
3. ⚙️ Container Orchestrator
   K8s: "discord-bot service → Pod #abc123 at IP 10.4.0.15"
   
4. 🔌 Network Proxy
   Proxy: "Forward HTTP to 10.4.0.15:8080/auth/start/123"
   
5. 🐳 Container Network
   Container: "Incoming request on eth0:8080"
   
6. 🌶️ Flask Application
   Flask: "@app.route('/auth/start/<id>') → start_oauth(id='123')"
```

**The KEY insight:** Your Flask app never knows about the public domain! It just sees `localhost:8080/auth/start/123` and Cloud Run handles all the networking magic invisibly.

### **🤖 Discord Command Integration**

**File: `discord_bot/src/bot/init_discord_bot.py` (Lines 74-85)**
```python
@bot.tree.command(name="link", description="Link your Discord to GitHub")
async def link(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    # Attempt to acquire the lock
    if not verification_lock.acquire(blocking=False):
        await interaction.followup.send("The verification process is currently busy. Please try again later.", ephemeral=True)
        return

    try:
        discord_user_id = str(interaction.user.id)
        
        # Get the OAuth URL for this specific user
        oauth_url = get_github_username_for_user(discord_user_id)
```

### **🌍 Cloud Run Environment Configuration**

**File: `discord_bot/main.py` (Lines 42-49)**
```python
# Check required environment variables
required_vars = [
    "DISCORD_BOT_TOKEN", 
    "GITHUB_TOKEN", 
    "GITHUB_CLIENT_ID", 
    "GITHUB_CLIENT_SECRET",
    "OAUTH_BASE_URL"      # ← This is your Cloud Run URL
]
```

**File: `discord_bot/src/bot/auth.py` (Lines 27-35)**
```python
# Get the base URL for OAuth callbacks (Cloud Run URL)
base_url = os.getenv("OAUTH_BASE_URL")
if not base_url:
    raise ValueError("OAUTH_BASE_URL environment variable is required")

# OAuth blueprint with custom callback URL (avoiding Flask-Dance auto routes)
github_blueprint = make_github_blueprint(
    client_id=os.getenv("GITHUB_CLIENT_ID"),
    client_secret=os.getenv("GITHUB_CLIENT_SECRET"),
    redirect_url=f"{base_url}/auth/callback"  # ← GitHub will redirect here
)
```

### **🎯 Key Networking Concepts Demonstrated**

1. **Single Process, Multiple Services**: `main.py` Lines 64-94 show how one container runs both Discord bot (background thread) and Flask (main thread)

2. **Shared Memory Communication**: `auth.py` Lines 11-13 and 170-185 show how threads communicate via the `oauth_sessions` dictionary

3. **URL Routing**: `auth.py` Lines 51-70 demonstrate Flask's `@app.route` decorator for handling different URL paths

4. **Environment-Based Configuration**: `main.py` Lines 42-49 show how Cloud Run URLs are configured via environment variables

5. **OAuth Flow State Management**: `auth.py` Lines 55-65 show how user sessions are tracked across HTTP requests

6. **Thread-Safe Operations**: `auth.py` Lines 56-60 and 174-178 demonstrate proper locking for shared data structures

### **🔍 Debugging Your Networking**

- **View Flask logs**: Check Cloud Run logs for HTTP request patterns
- **Inspect OAuth sessions**: Add debug prints in `auth.py` Lines 56 and 110
- **Monitor thread health**: Add logging to `main.py` Lines 70-73
- **Test routes directly**: Visit `YOUR_CLOUD_RUN_URL/` to see the Flask index page

This architecture allows a single Cloud Run service to handle both Discord WebSocket connections and HTTP OAuth requests efficiently!