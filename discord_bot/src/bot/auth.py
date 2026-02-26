import os
from typing import Optional
from datetime import datetime, timedelta, timezone
from shared.firestore import get_mt_client
import threading
import time
import hmac
import hashlib
import requests
from flask import Flask, redirect, url_for, jsonify, session, request
from flask_dance.contrib.github import make_github_blueprint, github
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

load_dotenv()

# Global state for OAuth sessions (keyed by Discord user ID)
oauth_sessions = {}
oauth_sessions_lock = threading.Lock()

# Event-driven link notification system
# Maps discord_user_id -> asyncio.Event (set when OAuth completes/fails)
_link_events = {}
_link_events_lock = threading.Lock()

def register_link_event(discord_user_id: str, event) -> None:
    """Register an asyncio.Event for a pending /link command."""
    with _link_events_lock:
        _link_events[discord_user_id] = event

def unregister_link_event(discord_user_id: str) -> None:
    """Clean up link event after /link completes or times out."""
    with _link_events_lock:
        _link_events.pop(discord_user_id, None)

def _notify_link_event(discord_user_id: str) -> None:
    """Wake up the waiting /link command from the Flask thread.
    
    Called after oauth_sessions is updated with the result.
    Uses call_soon_threadsafe to safely set the asyncio.Event
    from the Flask (non-asyncio) thread.
    """
    with _link_events_lock:
        event = _link_events.get(discord_user_id)
    if event:
        from . import shared
        if shared.bot_instance and shared.bot_instance.bot:
            shared.bot_instance.bot.loop.call_soon_threadsafe(event.set)

# Background thread to clean up old OAuth sessions (prevents memory leak)
def cleanup_old_oauth_sessions():
    """Clean up OAuth sessions older than 10 minutes to prevent memory leak."""
    while True:
        time.sleep(300)  # Check every 5 minutes
        with oauth_sessions_lock:
            current_time = time.time()
            expired_sessions = [
                user_id for user_id, session_data in oauth_sessions.items()
                if current_time - session_data.get('created_at', current_time) > 600  # 10 min
            ]
            for user_id in expired_sessions:
                del oauth_sessions[user_id]
                print(f"Cleaned up expired OAuth session for user {user_id}")

def notify_setup_complete(guild_id: str, github_org: str):
    """Send a success message to the Discord guild's system channel instantly."""
    from . import shared
    import discord
    
    if not shared.bot_instance or not shared.bot_instance.bot:
        print(f"Warning: Cannot send setup notification to {guild_id} - bot instance not ready")
        return

    bot = shared.bot_instance.bot
    
    async def send_msg():
        try:
            guild = bot.get_guild(int(guild_id))
            if not guild:
                # Try to fetch if not in cache
                guild = await bot.fetch_guild(int(guild_id))
            
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
                    embed.add_field(
                        name="Next Steps", 
                        value="1. Use `/link` to connect your GitHub account\n2. Customize roles with `/configure roles`", 
                        inline=False
                    )
                    embed.set_footer(text="Powered by DisgitBot")
                    
                    await channel.send(embed=embed)
                    print(f"Sent setup success notification to guild {guild_id}")
        except Exception as e:
            print(f"Error sending Discord setup notification: {e}")

    # Schedule the coroutine in the bot's event loop (thread-safe)
    import asyncio
    asyncio.run_coroutine_threadsafe(send_msg(), bot.loop)

def trigger_sync(guild_id: str, org_name: str, installation_id: Optional[int] = None, respect_cooldown: bool = True) -> dict:
    """Trigger the GitHub Actions pipeline using GitHub App identity.
    
    The workflow lives in REPO_OWNER/REPO_NAME, so we always use the
    installation token for REPO_OWNER (the bot developer's org), NOT
    the user's org installation.  The `installation_id` parameter is
    kept for backward-compat but ignored for the dispatch call.
    
    Returns a dict with:
        triggered (bool): Whether the pipeline was dispatched
        error (str|None): Error message if failed
        cooldown_remaining (int|None): Seconds remaining if blocked by cooldown
    """
    from src.services.github_app_service import GitHubAppService
    
    repo_owner = os.getenv("REPO_OWNER", "ruxailab") # Default to ruxailab if not set
    repo_name = os.getenv("REPO_NAME", "disgitbot")
    ref = os.getenv("WORKFLOW_REF", "main")

    mt_client = get_mt_client()
    existing_config = mt_client.get_server_config(guild_id) or {}

    # --- Cooldown check ---
    # Only enforce cooldown after a SUCCESSFUL sync (12h).
    # Failed syncs can be retried immediately.
    if respect_cooldown:
        last_sync_at = existing_config.get("last_sync_at")
        last_sync_status = existing_config.get("last_sync_status")  # "dispatched" or "failed"
        if last_sync_at and last_sync_status == "dispatched":
            try:
                last_dt = datetime.fromisoformat(last_sync_at)
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                elapsed = datetime.now(timezone.utc) - last_dt
                cooldown = timedelta(hours=12)
                
                if elapsed < cooldown:
                    remaining = int((cooldown - elapsed).total_seconds())
                    print(f"Skipping pipeline trigger: cooldown active ({remaining}s remaining)")
                    return {"triggered": False, "error": None, "cooldown_remaining": remaining, "last_sync_status": "dispatched"}
            except ValueError:
                pass

    gh_app = GitHubAppService()
    
    # --- IMPORTANT: Always use the installation for REPO_OWNER ---
    # The workflow dispatch targets REPO_OWNER/REPO_NAME (e.g. ruxailab/disgitbot).
    # The user's org installation token does NOT have access to that repo.
    # We must use the installation on REPO_OWNER itself.
    pipeline_installation_id = gh_app.find_installation_id(repo_owner)
    
    if not pipeline_installation_id:
        error_msg = (
            f"The GitHub App is not installed on '{repo_owner}' (the organization that hosts the pipeline). "
            f"The bot maintainer needs to install the GitHub App on '{repo_owner}' with Actions (read & write) permission."
        )
        print(f"Skipping pipeline trigger: {error_msg}")
        _save_sync_metadata(mt_client, guild_id, existing_config, "failed", error_msg)
        return {"triggered": False, "error": error_msg, "cooldown_remaining": None}

    token = gh_app.get_installation_access_token(pipeline_installation_id)

    if not token:
        error_msg = f"Failed to get access token for the pipeline installation on '{repo_owner}'"
        print(f"Skipping pipeline trigger: {error_msg}")
        _save_sync_metadata(mt_client, guild_id, existing_config, "failed", error_msg)
        return {"triggered": False, "error": error_msg, "cooldown_remaining": None}

    # Dispatch the workflow on REPO_OWNER/REPO_NAME
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/workflows/discord_bot_pipeline.yml/dispatches"
    headers = {
        "Authorization": f"Bearer {token}",
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
            _save_sync_metadata(mt_client, guild_id, existing_config, "dispatched", None)
            return {"triggered": True, "error": None, "cooldown_remaining": None}

        # --- Map common HTTP errors to human-readable messages ---
        status = resp.status_code
        if status == 403:
            error_msg = (
                "The GitHub App does not have permission to trigger workflows. "
                f"Please ensure the App is installed on '{repo_owner}' with **Actions (read & write)** permission enabled."
            )
        elif status == 404:
            error_msg = (
                f"Pipeline workflow not found at '{repo_owner}/{repo_name}'. "
                "The workflow file may have been removed or renamed."
            )
        elif status == 422:
            error_msg = (
                f"The workflow ref '{ref}' is invalid or the workflow is disabled. "
                "Check that the branch/tag exists and the workflow is enabled."
            )
        else:
            error_msg = f"GitHub API returned HTTP {status}. Please try again later."

        print(f"Failed to trigger pipeline: HTTP {status} — {resp.text[:300]}")
        _save_sync_metadata(mt_client, guild_id, existing_config, "failed", error_msg)
        return {"triggered": False, "error": error_msg, "cooldown_remaining": None}
    except requests.exceptions.Timeout:
        error_msg = "The request to GitHub timed out. Please try again in a moment."
        print(f"Error triggering pipeline: timeout")
        _save_sync_metadata(mt_client, guild_id, existing_config, "failed", error_msg)
        return {"triggered": False, "error": error_msg, "cooldown_remaining": None}
    except Exception as exc:
        error_msg = "An unexpected error occurred while contacting GitHub. Please try again later."
        print(f"Error triggering pipeline: {exc}")
        _save_sync_metadata(mt_client, guild_id, existing_config, "failed", error_msg)
        return {"triggered": False, "error": error_msg, "cooldown_remaining": None}


def _save_sync_metadata(mt_client, guild_id: str, existing_config: dict, status: str, error: Optional[str]):
    """Save sync attempt metadata to server config."""
    update = {
        **existing_config,
        "last_sync_at": datetime.now(timezone.utc).isoformat(),
        "last_sync_status": status,
    }
    if error:
        update["last_sync_error"] = error
    elif "last_sync_error" in update:
        del update["last_sync_error"]
    if not mt_client.set_server_config(guild_id, update):
        print(f"Warning: failed to persist sync metadata for guild {guild_id}")


def trigger_initial_sync(guild_id: str, org_name: str, installation_id: Optional[int] = None) -> bool:
    """Convenience wrapper for setup flows — skips cooldown on first setup."""
    result = trigger_sync(guild_id, org_name, installation_id=installation_id, respect_cooldown=False)
    return result["triggered"]

# Start cleanup thread
_cleanup_thread = threading.Thread(target=cleanup_old_oauth_sessions, daemon=True)
_cleanup_thread.start()

def render_status_page(title, subtitle, icon_type="info", instructions=None, button_text=None, button_url=None, footer="You can safely close this window."):
    """Render a consistent status/error page matching /invite and /setup design."""
    from flask import render_template_string

    # Icon colors per type
    icon_colors = {
        "success": "#43b581",
        "error": "#f04747",
        "warning": "#faa61a",
        "info": "#7289da",
    }
    icon_color = icon_colors.get(icon_type, "#7289da")

    # All icons use a simple circle + inner symbol, matching the elegant style
    icons = {
        "success": f'<svg style="width:20px;height:20px;color:{icon_color}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
        "error": f'<svg style="width:20px;height:20px;color:{icon_color}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
        "warning": f'<svg style="width:20px;height:20px;color:{icon_color}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
        "info": f'<svg style="width:20px;height:20px;color:{icon_color}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
    }
    icon_svg = icons.get(icon_type, icons["info"])

    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>{{ title }} — DisgitBot</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
        <style>
            html { background-color: #0f1012; overflow: hidden; }
            @media (max-width: 480px) { html { overflow: auto; } .card { width: 95%; padding: 20px; } }
            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                margin: 0; padding: 15px;
                background: radial-gradient(circle at top left, #2c2e33 0%, #0f1012 100%);
                color: #e1e1e1; height: 100vh;
                display: flex; align-items: center; justify-content: center;
                box-sizing: border-box; line-height: 1.5;
            }
            .card {
                background: rgba(30, 31, 34, 0.8);
                backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
                border: 1px solid rgba(255, 255, 255, 0.08);
                padding: 24px 32px; border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.6);
                width: 100%; max-width: 460px;
                position: relative;
            }
            .header-row { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
            h1 {
                color: #ffffff; margin: 0;
                font-size: 19px; font-weight: 800; letter-spacing: -0.4px;
            }
            .subtitle { color: #b9bbbe; margin: 0 0 0 0; font-size: 13px; font-weight: 400; max-width: 90%; }
            .divider {
                height: 1px; margin: 20px 0;
                background: linear-gradient(90deg, rgba(255,255,255,0.0), rgba(255,255,255,0.1), rgba(255,255,255,0.0));
            }
            .section-title {
                font-size: 12px; text-transform: uppercase; letter-spacing: 0.8px;
                color: #949BA4; margin-bottom: 16px; font-weight: 700;
            }
            .step { display: flex; gap: 12px; margin-bottom: 14px; position: relative; }
            .step-number {
                min-width: 20px; height: 20px;
                background: rgba(255,255,255,0.08);
                color: #fff; border-radius: 50%;
                display: flex; align-items: center; justify-content: center;
                font-size: 11px; font-weight: 700; margin-top: 1px;
            }
            .step-content { font-size: 13px; color: #dcddde; line-height: 1.4; }
            .btn {
                background: linear-gradient(135deg, #5865f2 0%, #4752c4 100%);
                color: white; padding: 11px 20px;
                border: none; border-radius: 10px; font-weight: 600;
                cursor: pointer; font-size: 14px; width: 100%;
                transition: transform 0.2s, box-shadow 0.2s, filter 0.2s;
                text-align: center;
                display: inline-flex; align-items: center; justify-content: center; gap: 8px;
                text-decoration: none;
                box-shadow: 0 6px 16px rgba(88, 101, 242, 0.2);
                box-sizing: border-box; position: relative; overflow: hidden;
            }
            .btn::before {
                content: ''; position: absolute; top: 0; left: -100%;
                width: 100%; height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.25), transparent);
                transition: left 0.5s;
            }
            .btn:hover { transform: translateY(-1px); box-shadow: 0 10px 24px rgba(88,101,242,0.35); filter: brightness(1.1); }
            .btn:hover::before { left: 100%; }
            .footer { margin-top: 20px; font-size: 12px; color: #82858f; }
            code {
                background: rgba(255, 255, 255, 0.08);
                padding: 2px 6px; border-radius: 4px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.9em; color: #dcddde;
                border: 1px solid rgba(255,255,255,0.1);
            }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="header-row">{{ icon_svg|safe }} <h1>{{ title }}</h1></div>
            <p class="subtitle">{{ subtitle|safe }}</p>

            {% if instructions %}
            <div class="divider"></div>
            <div class="section-title">What to do</div>
            {% for instruction in instructions %}
            <div class="step">
                <div class="step-number">{{ loop.index }}</div>
                <div class="step-content">{{ instruction|safe }}</div>
            </div>
            {% endfor %}
            {% endif %}

            {% if button_text and button_url %}
            <div style="margin-top: 20px;">
                <a href="{{ button_url }}" class="btn">{{ button_text }}</a>
            </div>
            {% endif %}

            <p class="footer">{{ footer }}</p>
        </div>
    </body>
    </html>
    """
    return render_template_string(
        template,
        title=title,
        subtitle=subtitle,
        icon_svg=icon_svg,
        instructions=instructions,
        button_text=button_text,
        button_url=button_url,
        footer=footer
    )

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
                "github_app_setup_callback": "/github/app/setup",
                "github_webhook": "/github/webhook"
            }
        })
    
    @app.route("/github/webhook", methods=["POST"])
    def github_webhook():
        """
        GitHub webhook endpoint for SaaS PR automation.
        Processes pull_request events from any org that installs the GitHub App.
        """
        import asyncio
        from threading import Thread
        
        # PR automation is disabled - /set_webhook command removed
        # To re-enable: restore /set_webhook command in notification_commands.py
        print("PR automation is disabled (feature removed)")
        return jsonify({
            "message": "PR automation is not available",
            "status": "not_implemented"
        }), 501
        
        # NOTE: Code below is kept for future re-enablement
        # 1. Verify webhook signature (MANDATORY)
        webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET")
        if not webhook_secret:
            print("ERROR: GITHUB_WEBHOOK_SECRET not configured - rejecting webhook")
            return jsonify({
                "error": "Webhook not configured",
                "message": "GITHUB_WEBHOOK_SECRET environment variable must be set"
            }), 500
        
        # 2. Parse event type
        event_type = request.headers.get("X-GitHub-Event")
        delivery_id = request.headers.get("X-GitHub-Delivery")
        
        print(f"Received webhook: event={event_type}, delivery_id={delivery_id}")
        
        if event_type == "ping":
            return jsonify({"message": "pong", "delivery_id": delivery_id}), 200
        
        # 3. Handle pull_request events
        if event_type != "pull_request":
            print(f"Ignoring event type: {event_type}")
            return jsonify({"message": f"Ignored event: {event_type}"}), 200
        
        try:
            payload = request.get_json()
            action = payload.get("action")
            
            # Only process opened and synchronize (push to PR) actions
            if action not in ["opened", "synchronize", "reopened"]:
                print(f"Ignoring PR action: {action}")
                return jsonify({"message": f"Ignored action: {action}"}), 200
            
            pr = payload.get("pull_request", {})
            repo = payload.get("repository", {})
            
            pr_number = pr.get("number")
            repo_full_name = repo.get("full_name")  # e.g., "owner/repo"
            
            if not pr_number or not repo_full_name:
                return jsonify({"error": "Missing PR number or repo"}), 400
            
            print(f"Processing PR #{pr_number} in {repo_full_name} (action: {action})")
            
            # 4. Trigger PR automation in background thread
            def run_pr_automation():
                try:
                    from pr_review.main import PRReviewSystem
                    
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    system = PRReviewSystem()
                    results = loop.run_until_complete(
                        system.process_pull_request(repo_full_name, pr_number)
                    )
                    
                    print(f"PR automation completed: {results.get('status', 'unknown')}")
                    loop.close()
                    
                except Exception as e:
                    print(f"PR automation failed: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Start background thread for PR processing
            Thread(target=run_pr_automation, daemon=True).start()
            
            return jsonify({
                "message": "PR automation triggered",
                "pr_number": pr_number,
                "repository": repo_full_name,
                "action": action
            }), 202
            
        except Exception as e:
            print(f"Error processing webhook: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500
    
    @app.route("/invite")
    def invite_bot():
        """Discord bot invitation endpoint"""
        
        # Your bot's client ID from Discord Developer Portal
        bot_client_id = os.getenv("DISCORD_BOT_CLIENT_ID", "YOUR_BOT_CLIENT_ID")
        
        # Required permissions for the bot
        permissions = "552172899344"  # Manage Roles + View Channels + Send Messages + Use Slash Commands
        
        discord_invite_url = (
            f"https://discord.com/oauth2/authorize?"
            f"client_id={bot_client_id}&"
            f"permissions={permissions}&"
            f"integration_type=0&"
            f"scope=bot+applications.commands"
        )
        

        
        # Enhanced landing page with modern design
        landing_page = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Add DisgitBot to Discord</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
    
    <style>
        html {{
            background-color: #0f1012;
            overflow: hidden; /* Prevent scrolling on desktop */
        }}
        
        @media (max-width: 480px) {{
            html {{ overflow: auto; }} /* Allow scrolling on mobile */
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            margin: 0; padding: 15px;
            background: radial-gradient(circle at top left, #2c2e33 0%, #0f1012 100%);
            color: #e1e1e1;
            height: 100vh;
            display: flex; align-items: center; justify-content: center;
            box-sizing: border-box;
            line-height: 1.5;
        }}
        
        .card {{
            background: rgba(30, 31, 34, 0.8);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            padding: 24px 32px; border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.6);
            width: 100%; max-width: 460px;
            position: relative;
        }}
        
        h1 {{ 
            color: #ffffff; margin: 0 0 6px 0; 
            font-size: 19px; font-weight: 800;
            letter-spacing: -0.4px;
            background: linear-gradient(90deg, #fff, #b9bbbe);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .subtitle {{ 
            color: #b9bbbe; margin-bottom: 16px; 
            font-size: 13px; font-weight: 400;
            max-width: 90%;
        }}
        
        .btn {{
            background: linear-gradient(135deg, #5865f2 0%, #4752c4 100%);
            color: white; padding: 11px 20px;
            border: none; border-radius: 10px; font-weight: 600;
            cursor: pointer; font-size: 14px; width: 100%;
            outline: none;
            transition: transform 0.2s, box-shadow 0.2s, filter 0.2s;
            text-align: center; 
            display: inline-flex; align-items: center; justify-content: center; gap: 8px;
            text-decoration: none;
            box-shadow: 0 6px 16px rgba(88, 101, 242, 0.2);
            box-sizing: border-box;
            position: relative; 
            overflow: hidden; 
        }}

        .btn::before {{
            content: '';
            position: absolute;
            top: 0;
            left: -100%; 
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.25), transparent);
            transition: left 0.5s; 
        }}
        
        .btn:hover {{
            transform: translateY(-1px);
            box-shadow: 0 10px 24px rgba(88, 101, 242, 0.35);
            filter: brightness(1.1);
        }}

        .btn:hover::before {{
            left: 100%; 
        }}

        .discord-icon {{ width: 20px; height: 20px; fill: white; }}
        
        .steps-container {{
            margin-top: 24px;
            border-top: 1px solid rgba(255,255,255,0.06);
            padding-top: 20px;
        }}

        .section-title {{
            font-size: 12px; text-transform: uppercase; letter-spacing: 0.8px;
            color: #949BA4; margin-bottom: 16px; font-weight: 700;
        }}

        .step {{
            display: flex; gap: 12px; margin-bottom: 14px;
            position: relative;
        }}
        
        .step-number {{
            min-width: 20px; height: 20px;
            background: rgba(255,255,255,0.08);
            color: #fff; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-size: 11px; font-weight: 700;
            margin-top: 1px;
        }}
        
        .step-content {{ font-size: 13px; color: #dcddde; line-height: 1.4; }}
        
        .url-box {{
            background: rgba(88, 101, 242, 0.08);
            border: 1px solid rgba(88, 101, 242, 0.2);
            padding: 4px 10px; border-radius: 6px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px; color: #a4b3ff;
            display: inline-block; margin-top: 4px;
            text-decoration: none;
            word-break: break-all;
        }}
        
        .url-box:hover {{
            background: rgba(88, 101, 242, 0.15);
            border-color: rgba(88, 101, 242, 0.4);
        }}

        .features-grid {{
            display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
            margin-top: 20px;
        }}
        
        .feature-item {{
            background: rgba(255,255,255,0.02);
            padding: 8px 12px; border-radius: 8px;
            font-size: 12px; color: #b9bbbe;
            display: flex; align-items: center; gap: 6px;
            border: 1px solid rgba(255,255,255,0.03);
        }}

        @media (max-width: 480px) {{
            .card {{ padding: 20px; }}
            h1 {{ font-size: 18px; }}
            .features-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="card">
        <h1>Add DisgitBot</h1>
        <p class="subtitle">Track GitHub contributions and manage roles automatically in your Discord server.</p>

        <a href="{discord_invite_url}" class="btn">
            <svg class="discord-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 127.14 96.36">
                <path d="M107.7,8.07A105.15,105.15,0,0,0,81.47,0a72.06,72.06,0,0,0-3.36,6.83A97.68,97.68,0,0,0,49,6.83,72.37,72.37,0,0,0,45.64,0,105.89,105.89,0,0,0,19.39,8.09C2.79,32.65-1.71,56.6.54,80.21h0A105.73,105.73,0,0,0,32.71,96.36,77.11,77.11,0,0,0,39.6,85.25a68.42,68.42,0,0,1-10.85-5.18c.91-.66,1.8-1.34,2.66-2a75.57,75.57,0,0,0,64.32,0c.87.71,1.76,1.39,2.66,2a68.68,68.68,0,0,1-10.87,5.19,77,77,0,0,0,6.89,11.1A105.89,105.89,0,0,0,126.6,80.22c1.24-18.87-3.23-41.61-18.9-72.15ZM42.45,65.69C36.18,65.69,31,60,31,53s5-12.74,11.43-12.74S54,46,53.89,53,48.84,65.69,42.45,65.69Zm42.24,0C78.41,65.69,73.25,60,73.25,53s5-12.74,11.44-12.74S96.23,46,96.12,53,91.08,65.69,84.69,65.69Z"/>
            </svg>
            Add to Discord
        </a>

        <div class="steps-container">
            <div class="section-title">Required Setup Activities</div>
            
            <div class="step">
                <div class="step-number">1</div>
                <div class="step-content">
                    <strong>Authorize:</strong> Click the button above to add the bot.
                </div>
            </div>

            <div class="step">
                <div class="step-number">2</div>
                <div class="step-content">
                    <strong>Configure:</strong> Automatic redirect after authorization.
                </div>
            </div>

            <div class="step">
                <div class="step-number">3</div>
                <div class="step-content">
                    <strong>Track:</strong> Install the App on your repositories.
                </div>
            </div>
            
             <div class="step">
                <div class="step-number">4</div>
                <div class="step-content">
                    <strong>Link:</strong> Users run <code>/link</code> in your Discord server.
                </div>
            </div>
        </div>

        <div class="features-grid">
            <div class="feature-item">📊 Stats</div>
            <div class="feature-item">🤖 Auto Roles</div>
            <div class="feature-item">📈 Analytics</div>
            <div class="feature-item">🔊 Updates</div>
        </div>
    </div>
</body>
</html>
"""
        
        return landing_page
    
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
                return render_status_page(
                    title="Session Not Found",
                    subtitle="We couldn't link your account because the Discord session was missing.",
                    icon_type="error",
                    button_text="Try /link again",
                    button_url="https://discord.com/app"
                ), 400

            if not github.authorized:
                print("GitHub OAuth not authorized")
                with oauth_sessions_lock:
                    oauth_sessions[discord_user_id] = {
                        'status': 'failed',
                        'error': 'GitHub authorization failed'
                    }
                _notify_link_event(discord_user_id)
                return render_status_page(
                    title="Authorization Failed",
                    subtitle="GitHub authorization was denied. Please try the <code>/link</code> command again and approve the request.",
                    icon_type="error"
                ), 400

            resp = github.get("/user")
            if not resp.ok:
                print(f"GitHub API call failed: {resp.status_code}")
                with oauth_sessions_lock:
                    oauth_sessions[discord_user_id] = {
                        'status': 'failed',
                        'error': 'Failed to fetch GitHub user info'
                    }
                _notify_link_event(discord_user_id)
                return render_status_page(
                    title="Profile Fetch Failed",
                    subtitle="We couldn't retrieve your GitHub user information. Please try again later.",
                    icon_type="error"
                ), 400

            github_user = resp.json()
            github_username = github_user.get("login")

            if not github_username:
                print("No GitHub username found")
                with oauth_sessions_lock:
                    oauth_sessions[discord_user_id] = {
                        'status': 'failed',
                        'error': 'No GitHub username found'
                    }
                _notify_link_event(discord_user_id)
                return render_status_page(
                    title="Username Not Found",
                    subtitle="We couldn't find a username for your GitHub account.",
                    icon_type="error"
                ), 400

            with oauth_sessions_lock:
                oauth_sessions[discord_user_id] = {
                    'status': 'completed',
                    'github_username': github_username
                }
            _notify_link_event(discord_user_id)

            session.pop('discord_user_id', None)

            print(f"OAuth completed for {github_username} (Discord: {discord_user_id})")

            return render_status_page(
                title="Authentication Successful!",
                subtitle=f"Your Discord account has been linked to GitHub user: <strong>{github_username}</strong>.",
                icon_type="success",
                instructions=[
                    "Return to Discord to see your linked status.",
                    "You can now use commands like <code>/getstats</code> with your own data."
                ]
            )

        except Exception as e:
            print(f"Error in OAuth callback: {e}")
            return f"Authentication failed: {str(e)}", 500

    @app.route("/github/app/install")
    def github_app_install():
        """Redirect to GitHub to install the DisgitBot GitHub App.
        
        GitHub handles all permission checking natively:
        - Org owners can install directly
        - Non-owners see a 'Request' button → owner gets notified to approve
        - Already-installed orgs show a 'Configure' option
        """
        from flask import request

        guild_id = request.args.get('guild_id')
        guild_name = request.args.get('guild_name', 'your server')

        if not guild_id:
            return render_status_page(
                title="Missing Server Information",
                subtitle="We couldn't determine which Discord server you're trying to set up.",
                icon_type="error",
                button_text="Try /setup again",
                button_url="https://discord.com/app"
            ), 400

        app_slug = os.getenv("GITHUB_APP_SLUG")
        if not app_slug:
            return render_status_page(
                title="Configuration Error",
                subtitle="The bot's <code>GITHUB_APP_SLUG</code> is not configured. Please contact the bot owner.",
                icon_type="error"
            ), 500

        state = state_serializer.dumps({'guild_id': str(guild_id), 'guild_name': guild_name})
        install_url = f"https://github.com/apps/{app_slug}/installations/new?state={state}"

        # Store pending setup so /github/app/setup can recover guild_id if GitHub
        # drops the state param (app already installed → setup_action=update flow).
        try:
            from shared.firestore import get_mt_client as _get_mt
            _get_mt().set_pending_setup(str(guild_id), guild_name)
        except Exception as _e:
            print(f"Warning: could not store pending setup for guild {guild_id}: {_e}")

        return redirect(install_url)

    @app.route("/github/app/setup")
    def github_app_setup():
        """GitHub App 'Setup URL' callback: stores installation ID for a Discord server."""
        from flask import request, render_template_string
        from shared.firestore import get_mt_client
        from datetime import datetime, timedelta, timezone
        from src.services.github_app_service import GitHubAppService

        installation_id = request.args.get('installation_id')
        setup_action = request.args.get('setup_action')
        state = request.args.get('state', '')

        # --- CASE 1: No state parameter ---
        # GitHub drops state in two situations:
        #   (a) Org owner approves a request from the GitHub notification email
        #   (b) App was already installed → GitHub redirects to settings page →
        #       user adds/removes repos → clicks Save → setup_action=update, no state
        # Fix: before redirecting to GitHub we store a pending_setup record in
        # Firestore.  Here we try to recover guild_id from that record and complete
        # setup directly, avoiding an infinite "run /setup again" loop.
        if not state:
            if installation_id:
                gh_app = GitHubAppService()
                installation = gh_app.get_installation(int(installation_id))
                account = (installation.get('account') or {}) if installation else {}
                github_org = account.get('login', '')
                github_account_type = account.get('type', '')

                mt_client = get_mt_client()

                # --- SUB-CASE A: installation already linked to a guild ---
                existing_guild_id = mt_client.find_guild_by_installation_id(int(installation_id))
                if existing_guild_id:
                    if setup_action == 'update':
                        # User updated repo access on an existing installation — nothing to do
                        discord_url = f"https://discord.com/channels/{existing_guild_id}"
                        return render_status_page(
                            title="Repository Access Updated",
                            subtitle=f"<strong>DisgitBot</strong>'s repository access on <strong>{github_org}</strong> has been updated." if github_org else "<strong>DisgitBot</strong>'s repository access has been updated.",
                            icon_type="success",
                            instructions=[
                                "Your Discord server is still connected — no further action needed.",
                                "Run <code>/sync</code> to refresh stats with the updated repository list.",
                            ],
                            button_text="Open Discord",
                            button_url=discord_url
                        )
                    # Already linked, no update action — just confirm
                    discord_url = f"https://discord.com/channels/{existing_guild_id}"
                    return render_status_page(
                        title="Already Connected",
                        subtitle=f"<strong>DisgitBot</strong> is already connected to <strong>{github_org}</strong>.",
                        icon_type="success",
                        instructions=["Your Discord server is already set up. No further action needed."],
                        button_text="Open Discord",
                        button_url=discord_url
                    )

                # --- SUB-CASE B: not yet linked — check for recent pending setup ---
                pending = mt_client.pop_recent_pending_setup(max_age_seconds=600)
                if pending:
                    guild_id = str(pending['guild_id'])
                    guild_name = pending.get('guild_name', 'your server')

                    if not installation:
                        # Couldn't verify with GitHub — restore the record so user can retry
                        mt_client.set_pending_setup(guild_id, guild_name)
                        return render_status_page(
                            title="Installation Not Found",
                            subtitle="We couldn't verify the GitHub installation. Please try again.",
                            icon_type="error",
                            button_text="Try Again",
                            button_url="https://discord.com/app"
                        ), 500

                    save_ok = mt_client.complete_setup_atomically(guild_id, {
                        'github_org': github_org,
                        'github_installation_id': int(installation_id),
                        'github_account': account.get('login'),
                        'github_account_type': github_account_type,
                        'setup_source': 'github_app',
                        'created_at': datetime.now(timezone.utc).isoformat(),
                        'setup_completed': True,
                    })
                    if not save_ok:
                        # Transaction returned False — a racing request already completed setup
                        discord_url = f"https://discord.com/channels/{guild_id}"
                        return render_status_page(
                            title="Already Connected",
                            subtitle=f"<strong>{guild_name}</strong> has already been set up.",
                            icon_type="success",
                            instructions=["No further action needed."],
                            button_text="Open Discord",
                            button_url=discord_url
                        )

                    trigger_initial_sync(guild_id, github_org, int(installation_id))
                    notify_setup_complete(guild_id, github_org)

                    discord_url = f"https://discord.com/channels/{guild_id}"
                    return render_status_page(
                        title="Setup Complete!",
                        subtitle=f"<strong>{guild_name}</strong> is now connected to <strong>{github_org}</strong>.",
                        icon_type="success",
                        instructions=[
                            "Your Discord server is now connected to GitHub.",
                            "Users can run <code>/link</code> to connect their accounts.",
                            "Stats will be ready in 5–10 minutes.",
                        ],
                        button_text="Open Discord",
                        button_url=discord_url
                    )

                # --- SUB-CASE C: no pending setup found (owner approved from email etc.) ---
                return render_status_page(
                    title="Installation Approved!",
                    subtitle=f"<strong>DisgitBot</strong> has been installed on <strong>{github_org}</strong>." if github_org else "<strong>DisgitBot</strong> has been installed successfully.",
                    icon_type="success",
                    instructions=[
                        "Go back to your Discord server.",
                        "An admin or the server owner should run <code>/setup</code> to link this GitHub installation to your server.",
                    ],
                    button_text="Open Discord",
                    button_url="https://discord.com/app"
                )
            else:
                # No state AND no installation_id
                return render_status_page(
                    title="Setup Session Missing",
                    subtitle="This link was opened directly without a valid session.",
                    icon_type="error",
                    instructions=[
                        "Go back to your Discord server.",
                        "Run the <code>/setup</code> command.",
                        "Click the new link provided by the bot.",
                    ],
                    button_text="Open Discord",
                    button_url="https://discord.com/app"
                ), 400

        # --- CASE 2: State exists but no installation_id ---
        if not installation_id:
            if setup_action == 'request':
                # Non-owner clicked "Request" — installation sent to org owner for approval
                try:
                    payload = state_serializer.loads(state, max_age=60 * 60 * 24 * 7)
                    guild_id = str(payload.get('guild_id', ''))
                    guild_name = payload.get('guild_name', 'your server')
                except Exception:
                    return render_status_page(
                        title="Session Expired",
                        subtitle="Your setup session has expired.",
                        icon_type="error",
                        instructions=[
                            "Go back to your Discord server.",
                            "Run <code>/setup</code> again to get a fresh link.",
                        ],
                        button_text="Open Discord",
                        button_url="https://discord.com/app"
                    ), 400

                discord_url = f"https://discord.com/channels/{guild_id}" if guild_id else "https://discord.com/app"
                return render_status_page(
                    title="Request Sent",
                    subtitle="A request to install <strong>DisgitBot</strong> has been sent to the organization owner.",
                    icon_type="success",
                    instructions=[
                        "The organization owner will receive a notification on GitHub to approve the app.",
                        "After approving, the owner (or an admin) should run <code>/setup</code> in Discord to complete the connection.",
                    ],
                    button_text="Open Discord",
                    button_url=discord_url
                )
            
            return render_status_page(
                title="Installation Cancelled",
                subtitle="The installation was not completed. This can happen if the process was cancelled on GitHub.",
                icon_type="error",
                instructions=[
                    "Go back to your Discord server.",
                    "Run <code>/setup</code> and try installing again.",
                    "If you're not an org owner, click <strong>Request</strong> on the GitHub page.",
                ],
                button_text="Open Discord",
                button_url="https://discord.com/app"
            ), 400

        # --- CASE 3: Both state and installation_id present (happy path) ---

        try:
            payload = state_serializer.loads(state, max_age=60 * 60 * 24 * 7)  # 7 days for org approval
        except SignatureExpired:
            return render_status_page(
                title="Setup Link Expired",
                subtitle="The setup link you used is no longer valid (expired after 7 days).",
                icon_type="error",
                button_text="Get New Link",
                button_url="https://discord.com/app"
            ), 400
        except BadSignature:
            return render_status_page(
                title="Invalid Setup State",
                subtitle="The session information is invalid or has been tampered with.",
                icon_type="error",
                button_text="Restart Setup",
                button_url="https://discord.com/app"
            ), 400

        guild_id = str(payload.get('guild_id', ''))
        guild_name = payload.get('guild_name', 'your server')
        if not guild_id:
            return render_status_page(
                title="Invalid Setup State",
                subtitle="The setup session is missing the Discord server ID.",
                icon_type="error",
                button_text="Restart Setup",
                button_url="https://discord.com/app"
            ), 400

        gh_app = GitHubAppService()
        installation = gh_app.get_installation(int(installation_id))
        if not installation:
            return render_status_page(
                title="Installation Not Found",
                subtitle="We couldn't verify the installation with GitHub. It might have been deleted or the GitHub API is temporarily unavailable.",
                icon_type="error",
                button_text="Try Again",
                button_url=f"https://discord.com/channels/{guild_id}"
            ), 500

        account = installation.get('account') or {}
        github_account = account.get('login')
        github_account_type = account.get('type')

        github_org = github_account
        is_personal_install = github_account_type == 'User'

        mt_client = get_mt_client()
        existing_config = mt_client.get_server_config(guild_id) or {}

        # --- Guard: prevent override if already set up with a DIFFERENT installation ---
        existing_install_id = existing_config.get('github_installation_id')
        if existing_config.get('setup_completed') and existing_install_id and existing_install_id != int(installation_id):
            existing_org = existing_config.get('github_org', 'a GitHub account')
            return render_status_page(
                title="Server Already Set Up",
                subtitle=f"This Discord server is already connected to <strong>{existing_org}</strong>. The existing setup was not changed.",
                icon_type="warning",
                instructions=[
                    "If you intended to reconfigure, please contact the server admin.",
                    "Only the server admin can reset and reconnect to a different GitHub organization.",
                ],
                button_text="Open Discord",
                button_url=f"https://discord.com/channels/{guild_id}"
            ), 403

        success = mt_client.complete_setup_atomically(guild_id, {
            'github_org': github_org,
            'github_installation_id': int(installation_id),
            'github_account': github_account,
            'github_account_type': github_account_type,
            'setup_source': 'github_app',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'setup_completed': True
        })

        if not success:
            # Transaction returned False — a racing request already completed setup
            discord_url = f"https://discord.com/channels/{guild_id}"
            return render_status_page(
                title="Already Connected",
                subtitle=f"<strong>{guild_name}</strong> has already been set up.",
                icon_type="success",
                instructions=["No further action needed."],
                button_text="Open Discord",
                button_url=discord_url
            )

        # Trigger initial sync and Discord notification
        sync_triggered = trigger_initial_sync(guild_id, github_org, int(installation_id))
        notify_setup_complete(guild_id, github_org)

        success_page = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Setup Completed!</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
            <style>
                html {
                    background-color: #0f1012;
                }
                
                body {
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                    margin: 0; padding: 20px;
                    background: radial-gradient(circle at top left, #2c2e33 0%, #0f1012 100%);
                    color: #e1e1e1;
                    height: 100vh;
                    overflow: hidden;
                    display: flex; align-items: center; justify-content: center;
                    box-sizing: border-box;
                    line-height: 1.6;
                    
                }
                
                @media (max-width: 550px) {
                    .card { width: 90%; padding: 30px; }
                }

                @media (max-height: 700px) {
                    .card { padding: 25px; }
                }
                
                .card {
                    background: rgba(30, 31, 34, 0.75);
                    backdrop-filter: blur(16px);
                    -webkit-backdrop-filter: blur(16px);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    padding: 40px; 
                    border-radius: 24px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.6);
                    width: 100%; 
                    max-width: 500px;
                    text-align: left;
                    position: relative;
                    
                }

                .card::before {
                    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
                    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
                }
                
                .header-row { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
                
                .success-icon { 
                    color: #43b581; 
                    width: 24px; height: 24px; 
                    animation: popIn 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
                }

                @keyframes popIn {
                    0% { transform: scale(0); opacity: 0; }
                    100% { transform: scale(1); opacity: 1; }
                }

                h1 { 
                    color: #ffffff; margin: 0;
                    font-size: 19px; font-weight: 800;
                    letter-spacing: -0.4px;
                }
                
                .subtitle { 
                    color: #b9bbbe; margin: 0;
                    font-size: 13px; font-weight: 400;
                }
                
                .highlight { color: #fff; font-weight: 600; }

                .divider {
                    height: 1px;
                    background: linear-gradient(90deg, rgba(255,255,255,0.0), rgba(255,255,255,0.1), rgba(255,255,255,0.0));
                    margin: 20px 0;
                }
                
                .section-title { 
                    margin: 0 0 12px 0; 
                    font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px;
                    font-weight: 700; color: #949BA4;
                }
                
                .command-row {
                    display: flex; align-items: center; justify-content: space-between;
                    background: rgba(255,255,255,0.03);
                    border: 1px solid rgba(255,255,255,0.05);
                    padding: 12px 16px;
                    border-radius: 12px;
                    margin-bottom: 10px;
                    transition: background 0.2s;
                }
                
                .command-row:hover {
                    background: rgba(255,255,255,0.05);
                }

                .cmd-desc { font-size: 14px; color: #dbdee1; font-weight: 500; }

                code {
                    background: rgba(88, 101, 242, 0.15);
                    padding: 4px 8px; border-radius: 6px;
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 13px; color: #8ea0e1;
                    border: 1px solid rgba(88, 101, 242, 0.2);
                }
                
                .status-badge {
                    display: inline-flex; align-items: center; gap: 8px;
                    font-size: 13px; color: #43b581;
                    background: rgba(67, 181, 129, 0.1);
                    padding: 8px 12px; border-radius: 20px;
                    margin-top: 10px; font-weight: 500;
                    border: 1px solid rgba(67, 181, 129, 0.1);
                }

                .footer-text {
                    margin-top: 32px; font-size: 13px; color: #82858f;
                    text-align: center;
                }
            </style>
        </head>
        <body>
            <div class="card">
                <div>
                    <div class="header-row">
                        <svg class="success-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                        <h1>Success!</h1>
                    </div>
                    <p class="subtitle"><strong>{{ guild_name }}</strong> is now connected to <span class="highlight">{{ github_org }}</span>.</p>
                </div>

                <div class="divider"></div>

                <div>
                    <h3 class="section-title">Next Steps in Discord</h3>
                    
                    <div class="command-row">
                        <span class="cmd-desc">1. Users link accounts</span>
                        <code>/link</code>
                    </div>

                    <div class="command-row">
                        <span class="cmd-desc">2. View stats</span>
                        <code>/getstats</code>
                    </div>

                    <div class="status-badge">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                        {% if sync_triggered %}
                        Data sync started. Stats appearing shortly.
                        {% else %}
                        Sync scheduled. Contributions ready soon.
                        {% endif %}
                    </div>
                </div>
                
                <p class="footer-text">
                    You can safely close this window and return to Discord.
                </p>
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
            return render_status_page(
                title="Missing Server Information",
                subtitle="We couldn't determine which Discord server you're trying to set up.",
                icon_type="error",
                button_text="Try /setup again",
                button_url="https://discord.com/app"
            ), 400

        # --- Guard: block re-setup if guild is already fully configured ---
        from shared.firestore import get_mt_client as _setup_mt
        _existing = _setup_mt().get_server_config(guild_id) or {}
        if _existing.get('setup_completed'):
            discord_url = f"https://discord.com/channels/{guild_id}"
            existing_org = _existing.get('github_org', 'GitHub')
            return render_status_page(
                title="Server Already Set Up",
                subtitle=f"This Discord server is already connected to <strong>{existing_org}</strong>. Setup cannot be run again from this link.",
                icon_type="info",
                instructions=[
                    "If you need to change the GitHub organization, ask the server admin to run <code>/setup</code> in Discord.",
                    "To update which repositories are tracked, go to your GitHub App installation settings.",
                ],
                button_text="Open Discord",
                button_url=discord_url
            ), 400

        github_app_install_url = f"{base_url}/github/app/install?{urlencode({'guild_id': guild_id, 'guild_name': guild_name})}"

        setup_page = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>DisgitBot Setup</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
            <style>
                html {
                    background-color: #0f1012;
                    overflow: hidden;
                }
                
                body {
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                    margin: 0; padding: 15px;
                    background: radial-gradient(circle at top left, #2c2e33 0%, #0f1012 100%);
                    color: #e1e1e1;
                    height: 100vh;
                    display: flex; align-items: center; justify-content: center;
                    box-sizing: border-box;
                    line-height: 1.5;
                }

                @media (max-width: 480px) {
                    html { overflow: auto; }
                    .card { width: 95%; padding: 20px; }
                }
                
                .card {
                    background: rgba(30, 31, 34, 0.8);
                    backdrop-filter: blur(16px);
                    -webkit-backdrop-filter: blur(16px);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    padding: 24px 32px; border-radius: 20px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.6);
                    width: 100%; max-width: 460px;
                    text-align: left;
                }
                
                h1 { 
                    color: #ffffff; margin: 0 0 6px 0; 
                    font-size: 19px; font-weight: 800;
                    letter-spacing: -0.4px;
                }
                
                .subtitle { 
                    color: #b9bbbe; margin: 0;
                    font-size: 13px; font-weight: 400;
                }
                
                .guild-name {
                    color: #fff;
                    font-weight: 600;
                }

                .divider {
                    height: 1px;
                    background: linear-gradient(90deg, rgba(255,255,255,0.0), rgba(255,255,255,0.1), rgba(255,255,255,0.0));
                    margin: 20px 0;
                }
                
                .section-title { 
                    margin: 0 0 8px 0; 
                    font-size: 15px; 
                    font-weight: 700; color: #ffffff;
                    display: flex; align-items: center; gap: 8px;
                }
                
                .section-desc {
                    color: #b9bbbe; margin-bottom: 16px;
                    font-size: 13px;
                }
                
                .btn {
                    background: linear-gradient(135deg, #5865f2 0%, #4752c4 100%);
                    color: white; padding: 11px 20px;
                    border: none; border-radius: 10px; font-weight: 600;
                    cursor: pointer; font-size: 14px; width: 100%;
                    transition: transform 0.2s, box-shadow 0.2s, filter 0.2s;
                    text-align: center; 
                    display: inline-flex; align-items: center; justify-content: center; gap: 8px;
                    text-decoration: none;
                    box-shadow: 0 6px 16px rgba(88, 101, 242, 0.2);
                    box-sizing: border-box;
                    position: relative; 
                    overflow: hidden;
                }
                
                .btn::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: -100%; 
                    width: 100%;
                    height: 100%;
                    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.25), transparent);
                    transition: left 0.5s; 
                }
                
                .btn:hover {
                    transform: translateY(-1px);
                    box-shadow: 0 10px 24px rgba(88, 101, 242, 0.35);
                    filter: brightness(1.1);
                }
                
                .btn:hover::before {
                    left: 100%; 
                }
                .github-icon { width: 18px; height: 18px; fill: currentColor; }
                
                .footer-text {
                    margin-top: 24px; font-size: 12px; color: #82858f;
                    text-align: center;
                }
                
                code {
                    background: rgba(255, 255, 255, 0.08);
                    padding: 2px 6px; border-radius: 4px;
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 0.9em; color: #dcddde;
                    border: 1px solid rgba(255,255,255,0.1);
                }
            </style>
        </head>
        <body>
            <div class="card">
                <div>
                    <h1>DisgitBot Added!</h1>
                    <p class="subtitle">Bot has been successfully added to <span class="guild-name">{{ guild_name }}</span></p>
                </div>

                <div class="divider"></div>

                <div>
                    <h3 class="section-title">Install the GitHub App</h3>
                    <p class="section-desc">Required: Select which repositories you want the bot to track.</p>
                    
                    <a class="btn" href="{{ github_app_install_url }}">
                        <svg class="github-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                        </svg>
                        Install GitHub App
                    </a>
                </div>
                
                <p class="footer-text">
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
            return render_status_page(
                title="Missing Information",
                subtitle="We couldn't complete the setup because some required information is missing.",
                icon_type="error",
                button_text="Try Again",
                button_url=f"https://discord.com/channels/{guild_id}" if guild_id else "https://discord.com/app"
            ), 400

        # --- Guard: block re-setup if guild is already fully configured ---
        mt_client = get_mt_client()
        existing_config = mt_client.get_server_config(guild_id) or {}
        if existing_config.get('setup_completed'):
            discord_url = f"https://discord.com/channels/{guild_id}"
            existing_org = existing_config.get('github_org', 'GitHub')
            return render_status_page(
                title="Server Already Set Up",
                subtitle=f"This Discord server is already connected to <strong>{existing_org}</strong>.",
                icon_type="info",
                instructions=["Setup cannot be completed again from this route."],
                button_text="Open Discord",
                button_url=discord_url
            ), 400

        # Validate GitHub organization name (basic validation)
        if not github_org.replace('-', '').replace('_', '').isalnum():
            return render_status_page(
                title="Invalid Organization Name",
                subtitle="The GitHub organization name contains invalid characters.",
                icon_type="error",
                button_text="Try Again",
                button_url=f"https://discord.com/channels/{guild_id}"
            ), 400

        try:
            success = mt_client.set_server_config(guild_id, {
                'github_org': github_org,
                'setup_source': setup_source,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'setup_completed': True
            })
            
            if not success:
                return render_status_page(
                    title="Storage Error",
                    subtitle="We couldn't save your server configuration to our database. Please try again in a few moments.",
                    icon_type="error"
                ), 500
            
            # Trigger initial sync and Discord notification
            # Auto-discovery will find the installation ID for the REPO_OWNER
            trigger_initial_sync(guild_id, github_org)
            notify_setup_complete(guild_id, github_org)
            
            success_page = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Setup Completed!</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <link rel="preconnect" href="https://fonts.googleapis.com">
                <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
                <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
                <style>
                    html {
                        background-color: #0f1012;
                        overflow: hidden;
                    }
                    
                    body {
                        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                        margin: 0; padding: 15px;
                        background: radial-gradient(circle at top left, #2c2e33 0%, #0f1012 100%);
                        color: #e1e1e1;
                        height: 100vh;
                        display: flex; align-items: center; justify-content: center;
                        box-sizing: border-box;
                        line-height: 1.5;
                    }

                    @media (max-width: 480px) {
                        html { overflow: auto; }
                        .card { width: 95%; padding: 20px; }
                        h1 { font-size: 18px; }
                    }

                    .card {
                        background: rgba(30, 31, 34, 0.8);
                        backdrop-filter: blur(16px);
                        -webkit-backdrop-filter: blur(16px);
                        border: 1px solid rgba(255, 255, 255, 0.08);
                        padding: 24px 32px; border-radius: 20px;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.6);
                        width: 100%; max-width: 460px;
                        text-align: left;
                        position: relative;
                    }

                    .card::before {
                        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
                        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
                    }
                    
                    .header-row { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
                    
                    .success-icon { 
                        color: #43b581; 
                        width: 24px; height: 24px; 
                        animation: popIn 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
                    }

                    @keyframes popIn {
                        0% { transform: scale(0); opacity: 0; }
                        100% { transform: scale(1); opacity: 1; }
                    }

                    h1 { 
                        color: #ffffff; margin: 0;
                        font-size: 19px; font-weight: 800;
                        letter-spacing: -0.4px;
                    }
                    
                    .subtitle { 
                        color: #b9bbbe; margin: 0;
                        font-size: 13px; font-weight: 400;
                    }
                    
                    .highlight { color: #fff; font-weight: 600; }

                    .divider {
                        height: 1px;
                        background: linear-gradient(90deg, rgba(255,255,255,0.0), rgba(255,255,255,0.1), rgba(255,255,255,0.0));
                        margin: 20px 0;
                    }
                    
                    .section-title { 
                        margin: 0 0 12px 0; 
                        font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px;
                        font-weight: 700; color: #949BA4;
                    }
                    
                    .command-row {
                        display: flex; align-items: center; justify-content: space-between;
                        background: rgba(255,255,255,0.03);
                        border: 1px solid rgba(255,255,255,0.05);
                        padding: 12px 16px;
                        border-radius: 12px;
                        margin-bottom: 10px;
                        transition: background 0.2s;
                    }
                    
                    .command-row:hover {
                        background: rgba(255,255,255,0.05);
                    }

                    .cmd-desc { font-size: 14px; color: #dbdee1; font-weight: 500; }

                    code {
                        background: rgba(88, 101, 242, 0.15);
                        padding: 4px 8px; border-radius: 6px;
                        font-family: 'JetBrains Mono', monospace;
                        font-size: 13px; color: #8ea0e1;
                        border: 1px solid rgba(88, 101, 242, 0.2);
                    }
                    
                    .status-badge {
                        display: inline-flex; align-items: center; gap: 8px;
                        font-size: 13px; color: #43b581;
                        background: rgba(67, 181, 129, 0.1);
                        padding: 8px 12px; border-radius: 20px;
                        margin-top: 10px; font-weight: 500;
                        border: 1px solid rgba(67, 181, 129, 0.1);
                    }

                    .footer-text {
                        margin-top: 32px; font-size: 13px; color: #82858f;
                        text-align: center;
                    }
                </style>
            </head>
            <body>
                <div class="card">
                    <div>
                        <div class="header-row">
                            <svg class="success-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                            <h1>Success!</h1>
                        </div>
                        <p class="subtitle"><strong>{{ guild_name }}</strong> is now connected to <span class="highlight">{{ github_org }}</span>.</p>
                    </div>

                    <div class="divider"></div>

                    <div>
                        <h3 class="section-title">Next Steps in Discord</h3>
                        
                        <div class="command-row">
                            <span class="cmd-desc">1. Users link accounts</span>
                            <code>/link</code>
                        </div>

                        <div class="command-row">
                            <span class="cmd-desc">2. View stats</span>
                            <code>/getstats</code>
                        </div>

                        <div class="status-badge">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                            Data sync started. Stats appearing shortly.
                        </div>
                    </div>
                    
                    <p class="footer-text">
                        You can safely close this window and return to Discord.
                    </p>
                </div>
            </body>
            </html>
            """
            
            return render_template_string(success_page, github_org=github_org)
            
        except Exception as e:
            print(f"Error in complete_setup: {e}")
            return render_status_page(
                title="Setup Failed",
                subtitle="An unexpected error occurred during setup. Please try again.",
                icon_type="error"
            ), 500
    
    return app

def get_github_username_for_user(discord_user_id):
    """Get OAuth URL for a specific Discord user"""
    base_url = os.getenv("OAUTH_BASE_URL")
    if not base_url:
        raise ValueError("OAUTH_BASE_URL environment variable is required")
    
    return f"{base_url}/auth/start/{discord_user_id}"

