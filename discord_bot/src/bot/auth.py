import os
import threading
import time
from flask import Flask, redirect, url_for, jsonify
from flask_dance.contrib.github import make_github_blueprint, github
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix

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
    base_url = os.getenv("OAUTH_BASE_URL") or "https://discord-bot-999242429166.us-central1.run.app"
    
    # OAuth blueprint with dynamic callback URL
    github_blueprint = make_github_blueprint(
        client_id=os.getenv("GITHUB_CLIENT_ID"),
        client_secret=os.getenv("GITHUB_CLIENT_SECRET"),
        redirect_url=f"{base_url}/auth/callback"
    )
    app.register_blueprint(github_blueprint, url_prefix="/login")
    
    @app.route("/")
    def index():
        return jsonify({
            "service": "Discord Bot with OAuth",
            "status": "running",
            "endpoints": {
                "start_auth": "/auth/start/<discord_user_id>",
                "callback": "/auth/callback",
                "check": "/auth/check/<discord_user_id>"
            }
        })
    
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
            from flask import session
            session['discord_user_id'] = discord_user_id
            
            print(f"Starting OAuth for Discord user: {discord_user_id}")
            
            # Redirect to GitHub OAuth
            return redirect(url_for("github.login"))
            
        except Exception as e:
            print(f"Error starting OAuth: {e}")
            return jsonify({"error": "Failed to start authentication"}), 500
    
    @app.route("/auth/callback")
    def github_callback():
        """Handle GitHub OAuth callback"""
        try:
            from flask import session
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
            if not resp.ok:
                print(f"❌ GitHub API call failed: {resp.status_code}")
                with oauth_sessions_lock:
                    oauth_sessions[discord_user_id] = {
                        'status': 'failed',
                        'error': 'Failed to fetch GitHub user info'
                    }
                return "Failed to fetch GitHub user information", 400
            
            github_user = resp.json()
            github_username = github_user.get("login")
            
            if not github_username:
                print("❌ No GitHub username found")
                with oauth_sessions_lock:
                    oauth_sessions[discord_user_id] = {
                        'status': 'failed',
                        'error': 'No GitHub username found'
                    }
                return "Failed to get GitHub username", 400
            
            # Store successful result
            with oauth_sessions_lock:
                oauth_sessions[discord_user_id] = {
                    'status': 'completed',
                    'github_username': github_username,
                    'github_user_data': github_user
                }
            
            print(f"✅ OAuth completed for {github_username} (Discord: {discord_user_id})")
            
            return f"""
            <html>
            <head><title>Authentication Successful</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h1>✅ Authentication Successful!</h1>
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
            print(f"❌ Error in OAuth callback: {e}")
            return f"Authentication failed: {str(e)}", 500
    
    @app.route("/auth/check/<discord_user_id>")
    def check_oauth_status(discord_user_id):
        """Check OAuth status for a Discord user (for polling)"""
        try:
            with oauth_sessions_lock:
                session_data = oauth_sessions.get(discord_user_id)
                
                if not session_data:
                    return jsonify({"status": "not_found"}), 404
                
                # Check if session is too old (5 minutes)
                if time.time() - session_data.get('created_at', 0) > 300:
                    del oauth_sessions[discord_user_id]
                    return jsonify({"status": "expired"}), 404
                
                if session_data['status'] == 'completed':
                    result = {
                        "status": "completed",
                        "github_username": session_data.get('github_username'),
                        "discord_user_id": discord_user_id
                    }
                    # Clean up completed session
                    del oauth_sessions[discord_user_id]
                    return jsonify(result)
                elif session_data['status'] == 'failed':
                    result = {
                        "status": "failed",
                        "error": session_data.get('error', 'Unknown error')
                    }
                    # Clean up failed session
                    del oauth_sessions[discord_user_id]
                    return jsonify(result)
                else:
                    return jsonify({"status": session_data['status']})
            
        except Exception as e:
            print(f"Error checking OAuth status: {e}")
            return jsonify({"error": "Internal server error"}), 500
    
    return app

# New interface for Discord bot to use
def get_github_username_for_user(discord_user_id, base_url=None):
    """
    Get OAuth URL for a specific Discord user
    """
    if not base_url:
        base_url = os.getenv("OAUTH_BASE_URL") or "https://discord-bot-999242429166.us-central1.run.app"
    
    return f"{base_url}/auth/start/{discord_user_id}"

def wait_for_username(discord_user_id, max_wait_time=300):
    """
    Wait for OAuth completion by polling the status
    """
    start_time = time.time()
    base_url = os.getenv("OAUTH_BASE_URL") or "https://discord-bot-999242429166.us-central1.run.app"
    
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

# Legacy compatibility functions (will be removed later)
def get_github_username():
    """Legacy function - deprecated"""
    print("WARNING: get_github_username() is deprecated. Use get_github_username_for_user() instead.")
    return "https://please-use-new-auth-flow"

def start_flask():
    """Legacy function - deprecated"""
    pass

def start_ngrok():
    """Legacy function - deprecated"""
    pass
