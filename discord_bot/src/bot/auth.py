import os
import threading
import time
from flask import Flask, redirect, url_for, jsonify, session, request, has_request_context
from flask_dance.contrib.github import make_github_blueprint, github
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix

load_dotenv()

# Global state for OAuth sessions (keyed by Discord user ID)
oauth_sessions = {}
oauth_sessions_lock = threading.Lock()

def get_base_url():
    """
    Returns the base URL for OAuth redirection.
    If OAUTH_BASE_URL is set, use it.
    If not, try to infer from the request context.
    """
    base_url = os.getenv("OAUTH_BASE_URL")
    if base_url:
        return base_url.rstrip("/")
    
    if has_request_context():
        return f"{request.scheme}://{request.host}"
    
    print("⚠️ Warning: No OAUTH_BASE_URL and no request context. Callback URLs may fail.")
    return None  # Allow app to start, even if not usable yet

def create_oauth_app():
    """
    Create and configure the Flask OAuth application.
    This returns a Flask app that can be run alongside the Discord bot.
    """
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "super-secret-oauth-key")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Set OAuth transport to allow HTTP in development
    if os.getenv("DEVELOPMENT"):
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    
    base_url = get_base_url()
    if not base_url:
        print("⚠️ OAuth redirect URL may not work correctly until a request is available.")
        base_url = ""  # Avoid crash
    
    # OAuth blueprint
    github_blueprint = make_github_blueprint(
        client_id=os.getenv("GITHUB_CLIENT_ID"),
        client_secret=os.getenv("GITHUB_CLIENT_SECRET"),
        redirect_url=f"{base_url}/auth/callback" if base_url else None
    )
    app.register_blueprint(github_blueprint, url_prefix="/login")
    
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
    
    @app.route("/auth/start/<discord_user_id>")
    def start_oauth(discord_user_id):
        try:
            with oauth_sessions_lock:
                oauth_sessions[discord_user_id] = {
                    'status': 'pending',
                    'created_at': time.time()
                }
            
            session['discord_user_id'] = discord_user_id
            print(f"Starting OAuth for Discord user: {discord_user_id}")
            return redirect(url_for("github.login"))
            
        except Exception as e:
            print(f"Error starting OAuth: {e}")
            return jsonify({"error": "Failed to start authentication"}), 500
    
    @app.route("/auth/callback")
    def github_callback():
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
    
    return app

def get_github_username_for_user(discord_user_id):
    base_url = get_base_url()
    if not base_url:
        raise ValueError("Unable to determine base URL. Set OAUTH_BASE_URL or ensure request context is available.")
    
    return f"{base_url}/auth/start/{discord_user_id}"

def wait_for_username(discord_user_id, max_wait_time=300):
    start_time = time.time()
    while time.time() - start_time < max_wait_time:
        with oauth_sessions_lock:
            session_data = oauth_sessions.get(discord_user_id)
            if session_data:
                if session_data['status'] == 'completed':
                    github_username = session_data.get('github_username')
                    del oauth_sessions[discord_user_id]
                    return github_username
                elif session_data['status'] == 'failed':
                    print(f"OAuth failed for {discord_user_id}: {session_data.get('error', 'Unknown error')}")
                    del oauth_sessions[discord_user_id]
                    return None
        time.sleep(2)
    
    print(f"OAuth timeout for Discord user: {discord_user_id}")
    with oauth_sessions_lock:
        if discord_user_id in oauth_sessions:
            del oauth_sessions[discord_user_id]
    return None