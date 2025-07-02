from auth import create_oauth_app
import os

if __name__ == "__main__":
    app = create_oauth_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
