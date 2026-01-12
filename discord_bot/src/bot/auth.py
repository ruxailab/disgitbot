import os
import threading
import time
import requests
from flask import Flask, redirect, url_for, jsonify, session
from flask_dance.contrib.github import make_github_blueprint, github
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

load_dotenv()

# Global state for OAuth sessions (keyed by Discord user ID)
oauth_sessions = {}
oauth_sessions_lock = threading.Lock()

def create_oauth_app():
    """
    Create and configure the Flask OAuth application.
    This returns a Flask app that can be run alongside the Discord bot.
    """
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "super-secret-oauth-key")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Set OAuth transport to allow HTTP in development, HTTPS in production
    if os.getenv("DEVELOPMENT"):
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    
    # Get the base URL for OAuth callbacks (Cloud Run URL)
    base_url = os.getenv("OAUTH_BASE_URL")
    if not base_url:
        raise ValueError("OAUTH_BASE_URL environment variable is required")
    
    # OAuth blueprint with custom callback URL (avoiding Flask-Dance auto routes)
    github_blueprint = make_github_blueprint(
        client_id=os.getenv("GITHUB_CLIENT_ID"),
        client_secret=os.getenv("GITHUB_CLIENT_SECRET"),
        redirect_url=f"{base_url}/auth/callback",
        scope="read:org"
    )
    app.register_blueprint(github_blueprint, url_prefix="/login")

    state_serializer = URLSafeTimedSerializer(app.secret_key, salt="github-app-install")
    
    @app.route("/")
    def index():
        return jsonify({
            "service": "DisgitBot - GitHub Discord Integration",
            "status": "Ready",
            "endpoints": {
                "invite_bot": "/invite",
                "setup": "/setup",
                "github_auth": "/auth/start/<discord_user_id>",
                "github_app_install": "/github/app/install",
                "github_app_setup_callback": "/github/app/setup"
            }
        })

    @app.route("/debug/servers")
    def debug_servers():
        """Debug endpoint to see registered servers (Protected)"""
        admin_token = os.getenv("ADMIN_TOKEN")
        if not admin_token or request.args.get("token") != admin_token:
            return jsonify({"error": "Unauthorized"}), 401
        try:
            from shared.firestore import get_mt_client

            mt_client = get_mt_client()

            # Get all servers
            servers_ref = mt_client.db.collection('discord_servers')
            servers = []

            for doc in servers_ref.stream():
                server_data = doc.to_dict()
                servers.append({
                    'server_id': doc.id,
                    'data': server_data
                })

            return jsonify({
                "total_servers": len(servers),
                "servers": servers
            })

        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route("/invite")
    def invite_bot():
        """Discord bot invitation endpoint"""
        from flask import render_template_string
        
        # Your bot's client ID from Discord Developer Portal
        bot_client_id = os.getenv("DISCORD_BOT_CLIENT_ID", "YOUR_BOT_CLIENT_ID")
        
        # Required permissions for the bot
        # Updated permissions to match working invite link
        permissions = "552172899344"  # Manage Roles + View Channels + Send Messages + Use Slash Commands
        
        discord_invite_url = (
            f"https://discord.com/oauth2/authorize?"
            f"client_id={bot_client_id}&"
            f"permissions={permissions}&"
            f"integration_type=0&"
            f"scope=bot+applications.commands"
        )
        
        # Enhanced landing page with clear instructions
        landing_page = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Add DisgitBot to Discord</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    max-width: 600px; margin: 50px auto; padding: 20px;
                    background: #36393f; color: #dcddde;
                }}
                .card {{
                    background: #2f3136; padding: 30px; border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                }}
                .btn {{
                    background: #5865f2; color: white; padding: 12px 24px;
                    text-decoration: none; border-radius: 4px; display: inline-block;
                    margin: 10px 0; font-weight: 600;
                }}
                .btn:hover {{ background: #4752c4; }}
                h1 {{ color: #ffffff; margin-top: 0; }}
                .feature {{ margin: 15px 0; }}
                .emoji {{ font-size: 1.2em; margin-right: 8px; }}
                .warning {{
                    background: #faa61a; color: #2f3136; padding: 15px;
                    border-radius: 4px; margin: 20px 0; font-weight: 600;
                }}
                .steps {{ background: #40444b; padding: 20px; border-radius: 4px; margin: 20px 0; }}
                .step {{ margin: 10px 0; }}
                .code {{
                    background: #2f3136; padding: 8px 12px; border-radius: 4px;
                    font-family: monospace; display: inline-block; margin: 5px 0;
                }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1>Add DisgitBot to Discord</h1>
                <p>Track GitHub contributions and manage roles automatically in your Discord server.</p>

                <div class="warning">
                    Important: Setup Required After Adding Bot
                </div>

                <a href="{discord_invite_url}" class="btn">Add Bot to Discord</a>

                <div class="steps">
                    <h3>Setup Instructions (Required)</h3>
                    <div class="step">
                        <strong>Step 1:</strong> Click "Add Bot to Discord" above
                    </div>
                <div class="step">
                    <strong>Step 2:</strong> After adding the bot, visit this setup URL:
                    <div class="code">{base_url}/setup</div>
                </div>
                <div class="step">
                        <strong>Step 3:</strong> Install the GitHub App and select repositories
                </div>
                <div class="step">
                        <strong>Step 4:</strong> Users can link GitHub accounts with <span class="code">/link</span> in Discord
                </div>
                </div>

                <h3>Features:</h3>
                <div class="feature">
                    <span class="emoji"></span> Real-time GitHub statistics
                </div>
                <div class="feature">
                    <span class="emoji"></span> Automated role assignment
                </div>
                <div class="feature">
                    <span class="emoji"></span> Contribution analytics & charts
                </div>
                <div class="feature">
                    <span class="emoji"></span> Auto-updating voice channels
                </div>

                <p style="font-size: 0.9em; color: #b9bbbe; margin-top: 30px;">
                    Compatible with any GitHub organization. Setup takes 30 seconds.
                </p>
            </div>
        </body>
        </html>
        """
        
        return render_template_string(landing_page, discord_invite_url=discord_invite_url)
    
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
            
        except Exception as e:
            print(f"Error starting OAuth: {e}")
            return jsonify({"error": "Failed to start authentication"}), 500
    
    @app.route("/auth/callback")
    def github_callback():
        """Handle GitHub OAuth callback for user account linking."""
        try:
            discord_user_id = session.get('discord_user_id')
            
            if not discord_user_id:
                return "Authentication failed: No Discord user session", 400

            if not github.authorized:
                print("GitHub OAuth not authorized")
                with oauth_sessions_lock:
                    oauth_sessions[discord_user_id] = {
                        'status': 'failed',
                        'error': 'GitHub authorization failed'
                    }
                return "GitHub authorization failed", 400

            resp = github.get("/user")
            if not resp.ok:
                print(f"GitHub API call failed: {resp.status_code}")
                with oauth_sessions_lock:
                    oauth_sessions[discord_user_id] = {
                        'status': 'failed',
                        'error': 'Failed to fetch GitHub user info'
                    }
                return "Failed to fetch GitHub user information", 400

            github_user = resp.json()
            github_username = github_user.get("login")

            if not github_username:
                print("No GitHub username found")
                with oauth_sessions_lock:
                    oauth_sessions[discord_user_id] = {
                        'status': 'failed',
                        'error': 'No GitHub username found'
                    }
                return "Failed to get GitHub username", 400

            with oauth_sessions_lock:
                oauth_sessions[discord_user_id] = {
                    'status': 'completed',
                    'github_username': github_username
                }

            session.pop('discord_user_id', None)

            print(f"OAuth completed for {github_username} (Discord: {discord_user_id})")

            return f"""
            <html>
            <head><title>Authentication Successful</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h1>Authentication Successful!</h1>
                <p>Your Discord account has been linked to GitHub user: <strong>{github_username}</strong></p>
                <p>You can now close this tab and return to Discord.</p>
                <script>
                    // Auto-close after 3 seconds
                    setTimeout(function() {{
                        window.close();
                    }}, 3000);
                </script>
            </body>
            </html>
            """

        except Exception as e:
            print(f"Error in OAuth callback: {e}")
            return f"Authentication failed: {str(e)}", 500

    @app.route("/github/app/install")
    def github_app_install():
        """Redirect server owners to install the DisgitBot GitHub App."""
        from flask import request

        guild_id = request.args.get('guild_id')
        guild_name = request.args.get('guild_name', 'your server')

        if not guild_id:
            return "Error: No Discord server information received", 400

        app_slug = os.getenv("GITHUB_APP_SLUG")
        if not app_slug:
            return "Server configuration error: missing GITHUB_APP_SLUG", 500

        state = state_serializer.dumps({'guild_id': str(guild_id), 'guild_name': guild_name})

        install_url = f"https://github.com/apps/{app_slug}/installations/new?state={state}"
        return redirect(install_url)

    @app.route("/github/app/setup")
    def github_app_setup():
        """GitHub App 'Setup URL' callback: stores installation ID for a Discord server."""
        from flask import request, render_template_string
        from shared.firestore import get_mt_client
        from datetime import datetime, timedelta
        from src.services.github_app_service import GitHubAppService

        installation_id = request.args.get('installation_id')
        state = request.args.get('state', '')

        if not installation_id or not state:
            return "Missing installation_id or state", 400

        try:
            payload = state_serializer.loads(state, max_age=60 * 30)
        except SignatureExpired:
            return "Setup link expired. Please restart setup from Discord.", 400
        except BadSignature:
            return "Invalid setup state. Please restart setup from Discord.", 400

        guild_id = str(payload.get('guild_id', ''))
        guild_name = payload.get('guild_name', 'your server')
        if not guild_id:
            return "Invalid setup state (missing guild_id). Please restart setup from Discord.", 400

        gh_app = GitHubAppService()
        installation = gh_app.get_installation(int(installation_id))
        if not installation:
            return "Failed to fetch installation details from GitHub.", 500

        account = installation.get('account') or {}
        github_account = account.get('login')
        github_account_type = account.get('type')

        github_org = github_account
        is_personal_install = github_account_type == 'User'

        mt_client = get_mt_client()
        existing_config = mt_client.get_server_config(guild_id) or {}
        success = mt_client.set_server_config(guild_id, {
            **existing_config,
            'github_org': github_org,
            'github_installation_id': int(installation_id),
            'github_account': github_account,
            'github_account_type': github_account_type,
            'setup_source': 'github_app',
            'created_at': datetime.now().isoformat(),
            'setup_completed': True
        })

        if not success:
            return "Error: Failed to save configuration", 500

        def trigger_initial_sync(org_name: str) -> bool:
            """Trigger the GitHub Actions pipeline once after setup."""
            token = os.getenv("GITHUB_TOKEN")
            repo_owner = os.getenv("REPO_OWNER")
            repo_name = os.getenv("REPO_NAME", "disgitbot")
            ref = os.getenv("WORKFLOW_REF", "main")

            if not token or not repo_owner:
                print("Skipping pipeline trigger: missing GITHUB_TOKEN or REPO_OWNER")
                return False

            existing_config = mt_client.get_server_config(guild_id) or {}
            last_trigger = existing_config.get("initial_sync_triggered_at")
            if last_trigger:
                try:
                    last_dt = datetime.fromisoformat(last_trigger)
                    if datetime.now() - last_dt < timedelta(minutes=10):
                        print("Skipping pipeline trigger: recent sync already triggered")
                        return False
                except ValueError:
                    pass

            url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/workflows/discord_bot_pipeline.yml/dispatches"
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github+json",
            }
            payload = {
                "ref": ref,
                "inputs": {
                    "organization": org_name
                }
            }

            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=20)
                if resp.status_code in (201, 204):
                    mt_client.set_server_config(guild_id, {
                        **existing_config,
                        "initial_sync_triggered_at": datetime.now().isoformat()
                    })
                    if github_org:
                        try:
                            # Trigger Discord notification
                            import asyncio
                            from threading import Thread
                            
                            def run_async_notification():
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                loop.run_until_complete(send_discord_setup_notification(guild_id, github_org))
                                loop.close()
                            
                            Thread(target=run_async_notification).start()
                            
                            # Trigger initial data collection for this organization
                            trigger_data_pipeline_for_org(github_org)
                        except Exception as e:
                            print(f"Warning: Failed to trigger setup notifications: {e}")
                    return True
                print(f"Failed to trigger pipeline: {resp.status_code} {resp.text[:200]}")
            except Exception as exc:
                print(f"Error triggering pipeline: {exc}")
            return False

        async def send_discord_setup_notification(guild_id: str, github_org: str):
            """Send a success message to the Discord guild's system channel."""
            import discord
            import os
            
            token = os.getenv('DISCORD_BOT_TOKEN')
            if not token:
                return
                
            intents = discord.Intents.default()
            client = discord.Client(intents=intents)
            
            @client.event
            async def on_ready():
                try:
                    guild = client.get_guild(int(guild_id))
                    if guild:
                        channel = guild.system_channel
                        if not channel:
                            channel = next((ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages), None)
                        
                        if channel:
                            embed = discord.Embed(
                                title="✅ DisgitBot Setup Complete!",
                                description=f"This server is now connected to the GitHub organization: **{github_org}**",
                                color=0x43b581
                            )
                            embed.add_field(name="Next Steps", value="1. Use `/link` to connect your GitHub account\n2. Configure webhooks with `/set_webhook`", inline=False)
                            embed.set_footer(text="Powered by DisgitBot SaaS")
                            
                            await channel.send(embed=embed)
                            print(f"Sent setup success notification to guild {guild_id}")
                    
                except Exception as e:
                    print(f"Error sending Discord setup notification: {e}")
                finally:
                    await client.close()
                    
            try:
                await client.start(token)
            except Exception as e:
                print(f"Failed to start Discord client for notification: {e}")

        def trigger_data_pipeline_for_org(github_org):
            # Placeholder for triggering a data pipeline for the given GitHub organization
            # This would typically involve calling an external service or another part of the system
            print(f"Triggering data pipeline for GitHub organization: {github_org}")
            # Example: You might want to add a task to a queue here
            pass

        sync_triggered = trigger_initial_sync(github_org)

        success_page = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>GitHub Connected!</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    max-width: 650px; margin: 50px auto; padding: 20px;
                    background: #36393f; color: #dcddde;
                }
                .card {
                    background: #2f3136; padding: 30px; border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.2); text-align: center;
                }
                h1 { color: #43b581; margin-top: 0; }
                .command {
                    background: #40444b; padding: 10px; border-radius: 4px;
                    font-family: monospace; margin: 10px 0;
                }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>GitHub Connected!</h1>
                <p><strong>{{ guild_name }}</strong> is now connected to GitHub <strong>{{ github_org }}</strong>.</p>
                {% if is_personal_install %}
                <p style="color: #faa61a; font-weight: 600;">
                    Heads up: you installed the app on a personal account. If you need org repos,
                    reinstall the app on your organization.
                </p>
                {% endif %}

                <h3>Next Steps in Discord</h3>
                <p>1) Users link their GitHub accounts:</p>
                <div class="command">/link</div>
                <p>2) Configure custom roles:</p>
                <div class="command">/configure roles</div>
                {% if sync_triggered %}
                <p>✅ Initial sync started. Stats will appear shortly.</p>
                {% else %}
                <p>⏳ Initial sync will run on the next scheduled pipeline.</p>
                {% endif %}
                <p>3) Try these commands:</p>
                <div class="command">/getstats</div>
                <div class="command">/halloffame</div>
            </div>
        </body>
        </html>
        """

        return render_template_string(
            success_page,
            guild_name=guild_name,
            github_org=github_org,
            is_personal_install=is_personal_install,
            sync_triggered=sync_triggered
        )

    @app.route("/setup")
    def setup():
        """Setup page after Discord bot is added to server"""
        from flask import request, render_template_string
        from urllib.parse import urlencode

        # Get Discord server info from OAuth callback
        guild_id = request.args.get('guild_id')
        guild_name = request.args.get('guild_name', 'your server')

        if not guild_id:
            return "Error: No Discord server information received", 400

        github_app_install_url = f"{base_url}/github/app/install?{urlencode({'guild_id': guild_id, 'guild_name': guild_name})}"

        setup_page = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>DisgitBot Setup</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    max-width: 600px; margin: 50px auto; padding: 20px;
                    background: #36393f; color: #dcddde;
                }
                .card {
                    background: #2f3136; padding: 30px; border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                }
                .form-group { margin: 20px 0; }
                label { display: block; margin-bottom: 8px; font-weight: 600; }
                input[type="text"] {
                    width: 100%; padding: 12px; border: 1px solid #40444b;
                    background: #40444b; color: #dcddde; border-radius: 4px;
                    font-size: 16px; box-sizing: border-box;
                }
                input[type="text"]:focus {
                    outline: none; border-color: #5865f2;
                }
                .btn {
                    background: #5865f2; color: white; padding: 12px 24px;
                    border: none; border-radius: 4px; font-weight: 600;
                    cursor: pointer; font-size: 16px; width: 100%;
                }
                .btn:hover { background: #4752c4; }
                h1 { color: #ffffff; margin-top: 0; }
                .example { color: #b9bbbe; font-size: 0.9em; }
                .section-title { margin-top: 30px; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>DisgitBot Added Successfully!</h1>
                <p>Bot has been added to <strong>{{ guild_name }}</strong></p>

                <h3 class="section-title">Recommended: Install the GitHub App</h3>
                <p>Install the DisgitBot GitHub App and pick which repositories to track.</p>
                <a class="btn" href="{{ github_app_install_url }}">Install GitHub App</a>

                <h3 class="section-title">Manual Setup (disabled)</h3>
                <p class="example">
                    Manual setup is disabled in the hosted version. Please use
                    <strong>Install GitHub App</strong> above to connect your repositories.
                </p>

                <p style="margin-top: 30px; font-size: 0.9em; color: #b9bbbe;">
                    After setup, users can link their GitHub accounts using <code>/link</code> in Discord.
                </p>
            </div>
        </body>
        </html>
        """

        return render_template_string(
            setup_page,
            guild_id=guild_id,
            guild_name=guild_name,
            github_app_install_url=github_app_install_url
        )
    
    @app.route("/complete_setup", methods=["POST"])
    def complete_setup():
        """Complete the setup process"""
        from flask import request, render_template_string
        from shared.firestore import get_mt_client
        from datetime import datetime
        
        guild_id = request.form.get('guild_id')
        selected_org = request.form.get('github_org', '').strip()
        manual_org = request.form.get('manual_org', '').strip()
        github_org = manual_org or selected_org
        setup_source = request.form.get('setup_source', 'manual').strip() or 'manual'
        
        if not guild_id or not github_org:
            return "Error: Missing required information", 400
        
        # Validate GitHub organization name (basic validation)
        if not github_org.replace('-', '').replace('_', '').isalnum():
            return "Error: Invalid GitHub organization name", 400
        
        try:
            # Store server configuration
            mt_client = get_mt_client()
            success = mt_client.set_server_config(guild_id, {
                'github_org': github_org,
                'setup_source': setup_source,
                'created_at': datetime.now().isoformat(),
                'setup_completed': True
            })
            
            if not success:
                return "Error: Failed to save configuration", 500
            
            
            success_page = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Setup Complete!</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { 
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        max-width: 600px; margin: 50px auto; padding: 20px;
                        background: #36393f; color: #dcddde;
                    }
                    .card { 
                        background: #2f3136; padding: 30px; border-radius: 8px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.2); text-align: center;
                    }
                    h1 { color: #43b581; margin-top: 0; }
                    .command { 
                        background: #40444b; padding: 10px; border-radius: 4px;
                        font-family: monospace; margin: 10px 0;
                    }
                </style>
            </head>
            <body>
                <div class="card">
                    <h1>Setup Complete!</h1>
                    <p>DisgitBot is now configured to track <strong>{{ github_org }}</strong> repositories.</p>
                    
                    <h3>Next Steps:</h3>
                    <p>1. Return to Discord</p>
                    <p>2. Users can link their GitHub accounts with:</p>
                    <div class="command">/link</div>
                    
                    <p>3. Try these commands:</p>
                    <div class="command">/getstats</div>
                    <div class="command">/halloffame</div>
                    
                    <p style="margin-top: 30px; font-size: 0.9em; color: #b9bbbe;">
                        Data collection will begin shortly. Stats will be available within 5-10 minutes.
                    </p>
                </div>
            </body>
            </html>
            """
            
            return render_template_string(success_page, github_org=github_org)
            
        except Exception as e:
            print(f"Error in complete_setup: {e}")
            return f"Error: Setup failed - {str(e)}", 500
    
    return app

def get_github_username_for_user(discord_user_id):
    """Get OAuth URL for a specific Discord user"""
    base_url = os.getenv("OAUTH_BASE_URL")
    if not base_url:
        raise ValueError("OAUTH_BASE_URL environment variable is required")
    
    return f"{base_url}/auth/start/{discord_user_id}"

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
                elif session_data['status'] == 'failed':
                    error = session_data.get('error', 'Unknown error')
                    print(f"OAuth failed for {discord_user_id}: {error}")
                    # Clean up
                    del oauth_sessions[discord_user_id]
                    return None
        
        time.sleep(2)  # Poll every 2 seconds
    
    print(f"OAuth timeout for Discord user: {discord_user_id}")
    # Clean up timeout session
    with oauth_sessions_lock:
        if discord_user_id in oauth_sessions:
            del oauth_sessions[discord_user_id]
    
    return None
