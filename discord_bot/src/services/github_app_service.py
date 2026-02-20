import base64
import os
import time
from typing import Any, Dict, Optional

import requests


class GitHubAppService:
    """GitHub App authentication helpers (JWT + installation access tokens)."""

    def __init__(self):
        self.api_url = "https://api.github.com"
        self.app_id = os.getenv("GITHUB_APP_ID")
        self._private_key_pem = self._load_private_key_pem()

        self._jwt_token: Optional[str] = None
        self._jwt_exp: int = 0

        if not self.app_id:
            raise ValueError("GITHUB_APP_ID environment variable is required for GitHub App auth")
        if not self._private_key_pem:
            raise ValueError("GITHUB_APP_PRIVATE_KEY (or GITHUB_APP_PRIVATE_KEY_B64) is required for GitHub App auth")

    def _load_private_key_pem(self) -> str:
        key = os.getenv("GITHUB_APP_PRIVATE_KEY", "")
        if key:
            return key.replace("\\n", "\n")

        key_b64 = os.getenv("GITHUB_APP_PRIVATE_KEY_B64", "")
        if key_b64:
            return base64.b64decode(key_b64).decode("utf-8")

        return ""

    def get_app_jwt(self) -> str:
        """Create (or reuse) an app JWT."""
        now = int(time.time())
        if self._jwt_token and now < (self._jwt_exp - 60):
            return self._jwt_token

        try:
            import jwt  # PyJWT
        except Exception as e:
            raise RuntimeError("PyJWT is required for GitHub App auth. Install PyJWT[crypto].") from e

        payload = {
            "iat": now - 60,
            "exp": now + 9 * 60,
            "iss": self.app_id,
        }
        token = jwt.encode(payload, self._private_key_pem, algorithm="RS256")
        self._jwt_token = token
        self._jwt_exp = payload["exp"]
        return token

    def _app_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.get_app_jwt()}",
            "Accept": "application/vnd.github+json",
        }

    def get_installation(self, installation_id: int) -> Optional[Dict[str, Any]]:
        """Fetch installation metadata (account login/type)."""
        try:
            url = f"{self.api_url}/app/installations/{installation_id}"
            resp = requests.get(url, headers=self._app_headers(), timeout=30)
            if resp.status_code != 200:
                print(f"Failed to fetch installation {installation_id}: {resp.status_code} {resp.text[:200]}")
                return None
            return resp.json()
        except Exception as e:
            print(f"Error fetching installation {installation_id}: {e}")
            return None

    def get_installation_access_token(self, installation_id: int) -> Optional[str]:
        """Create a short-lived installation access_token."""
        try:
            url = f"{self.api_url}/app/installations/{installation_id}/access_tokens"
            resp = requests.post(url, headers=self._app_headers(), json={}, timeout=30)
            if resp.status_code != 201:
                print(f"Failed to create access token for installation {installation_id}: {resp.status_code} {resp.text[:200]}")
                return None
            data = resp.json()
            return data.get("token")
        except Exception as e:
            print(f"Error creating access token for installation {installation_id}: {e}")
            return None

    def find_installation_id(self, account_name: str) -> Optional[int]:
        """Find installation ID for a specific account name (org or user)."""
        for inst in self.list_installations():
            if inst.get('account', {}).get('login') == account_name:
                return inst.get('id')
        return None

    def list_installations(self) -> list:
        """Return all current installations of this GitHub App."""
        try:
            url = f"{self.api_url}/app/installations"
            params = {"per_page": 100}
            resp = requests.get(url, headers=self._app_headers(), params=params, timeout=30)
            if resp.status_code != 200:
                print(f"Failed to list installations: {resp.status_code} {resp.text[:200]}")
                return []
            return resp.json()
        except Exception as e:
            print(f"Error listing installations: {e}")
            return []

