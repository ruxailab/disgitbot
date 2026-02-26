# Maintainer Guide

This document explains how to manage the environment variables and how to re-enable features that are currently disabled (commented out) on the `feature/saas-ready` branch.

## Multi-Tenant Architecture

### How GitHub Org ↔ Discord Server Works

- **One GitHub org can be connected to multiple Discord servers.**
- Each Discord server stores its own config in `discord_servers/{guild_id}` with a `github_org` field.
- Org-scoped data (repo stats, PR config, monitoring) is stored under `organizations/{github_org}/...` and shared across all Discord servers connected to the same org.
- The GitHub App only needs to be **installed once per org** on GitHub.

### Setup Flow

| Scenario | Steps | Approval needed? |
|---|---|---|
| **Owner/Admin runs `/setup`** | `/setup` → click link → Install on GitHub → done | No (owner installs directly) |
| **Member runs `/setup`** | `/setup` → click link → "Request" on GitHub → owner approves from GitHub notification → an admin or the owner runs `/setup` in Discord | Yes (first time only) |
| **Second Discord server, same org** | Anyone runs `/setup` → click link → app already installed → done | No (already installed) |

### Key Points

- Only the **first installation** per GitHub org requires the org owner to approve (if initiated by a non-owner member).
- Once a GitHub App is installed on an org, **any Discord server** can connect to it via `/setup` without needing another approval.
- `/add_repo` and `/remove_repo` are **scoped to the configured org** — you can only monitor repos within your connected GitHub organization.

### `/sync` — Per-Server Cooldown, Shared Pipeline

- The **12-hour cooldown is per Discord server** (keyed on `guild_id`). Each server stores its own `last_sync_at` + `last_sync_status` in `discord_servers/{guild_id}/config`.
- Two Discord servers connected to the **same GitHub org** each have independent cooldowns. If both trigger `/sync`, the pipeline runs twice on the same org's data — wasteful but harmless.
- The pipeline itself writes to `organizations/{github_org}/...`, which is shared. Running it twice back-to-back on the same org is safe (idempotent write).
- `trigger_initial_sync()` always bypasses the cooldown (`respect_cooldown=False`) so the first sync after `/setup` always fires.

### Voice Channel Stats — Per-Guild, Updated by Pipeline

- Each Discord server gets its own `REPOSITORY STATS` voice-channel category. The pipeline iterates over **all guilds** the bot is in and updates each one.
- The channels reflect org-level metrics (stars, forks, contributors, PRs, issues, commits) fetched from `organizations/{github_org}/...`.
- **Duplicate category root cause:** `discord.utils.get()` only returns the first matching category. If `/setup_voice_stats` and the pipeline's `_update_channels_for_guild` both run near-simultaneously (e.g., first deploy + immediate pipeline trigger), both find no existing category and both create one, resulting in two `REPOSITORY STATS` categories. The fix: scan for *all* categories with that name, keep the first, delete the rest. `/setup_voice_stats` now also detects and cleans up duplicates automatically.

---

## Environment Variables

### Core Variables (Required for Launch)
These are already in your `.env.example`:
- `DISCORD_BOT_TOKEN`: The bot token from Discord Developer Portal.
- `DISCORD_BOT_CLIENT_ID`: The client ID of your Discord bot.
- `GITHUB_CLIENT_ID`: OAuth client ID from your GitHub App.
- `GITHUB_CLIENT_SECRET`: OAuth client secret from your GitHub App.
- `OAUTH_BASE_URL`: The public URL where the bot is hosted (e.g., `https://your-bot.cloudfunctions.net`).
- `GITHUB_APP_ID`: Your GitHub App ID.
- `GITHUB_APP_PRIVATE_KEY_B64`: Your GitHub App's private key, encoded in Base64.
- `GITHUB_APP_SLUG`: The URL-friendly name of your GitHub App.

### Security Variables (Recommended for Production)
- `SECRET_KEY`: Used by Flask to sign session cookies. 
    - **Usage**: Encrypting the `discord_user_id` during the `/link` flow.
    - **Manual Check**: If you change this key while a user is mid-authentication, their session will be invalidated, and they will see "Authentication failed: No Discord user session".
    - **Generation**: `python3 -c "import secrets; print(secrets.token_hex(32))"`

### Feature-Specific Variables (Optional/Disabled)
- `GITHUB_WEBHOOK_SECRET`: Required ONLY for PR automation. Used to verify that webhooks are actually coming from GitHub.
- `GITHUB_TOKEN`: Original personal access token (largely replaced by GitHub App identity).
- `REPO_OWNER`: The GitHub account/org that **owns the `disgitbot` fork** where the pipeline workflow lives. Defaults to `ruxailab`. Must be set if you are running the bot from a fork.
- `REPO_NAME`: The repository name hosting the pipeline. Defaults to `disgitbot`.
- `WORKFLOW_REF`: The branch/tag to dispatch the workflow on. Defaults to `main`. Set this if your active branch is not `main` (e.g. `feature/saas-ready` during testing).

---

## Setting Up `/sync` (Manual Pipeline Trigger)

The `/sync` command lets Discord admins manually trigger the GitHub Actions data pipeline. It uses the GitHub App's installation token to dispatch a workflow on `REPO_OWNER/REPO_NAME`.

### Required Steps

**1. Set the correct env vars in `.env`:**
```
REPO_OWNER=<org-or-user-that-owns-the-disgitbot-repo>
REPO_NAME=disgitbot
WORKFLOW_REF=main   # or your branch name during testing
```

**2. Enable Actions permission on the GitHub App:**
1. Go to `github.com/organizations/{your-org}/settings/apps/{your-app-slug}`
2. Click **Permissions & events** → **Repository permissions**
3. Find **Actions** (first item — "Workflows, workflow runs and artifacts")
4. Change it from `No access` → **Read & write**
5. Save changes

**3. Accept the updated permissions:**
After saving, GitHub will notify all existing installations to accept the new permission. Go to `github.com/settings/installations` (or org equivalent) and approve the updated permissions for the installation on `REPO_OWNER`.

> **Note:** `REPO_OWNER` must be the account where the GitHub App is **installed** (not just where it was created). If you forked the repo to a different org/account, install the App there first.

---

## Re-enabling PR Automation

PR automation is currently commented out to simplify the SaaS experience. To re-enable it:

### 1. Uncomment Command Registration
In `discord_bot/src/bot/commands/admin_commands.py`:
```python
# In register_commands():
self.bot.tree.add_command(self._add_reviewer_command())
self.bot.tree.add_command(self._remove_reviewer_command())
```

In `discord_bot/src/bot/commands/notification_commands.py`:
```python
# In register_commands():
# self.bot.tree.add_command(self._webhook_status_command())
```

### 2. Configure GitHub App Webhooks
1. Go to your GitHub App settings.
2. Enable **Webhooks**.
3. **Webhook URL**: `{OAUTH_BASE_URL}/github-webhook`
4. **Webhook Secret**: Set a random string and update `GITHUB_WEBHOOK_SECRET` in your `.env`.
5. **Permissions & Events**:
    - Push: `read & write` (checks)
    - Pull Requests: `read & write`
    - Repository metadata: `read-only`
    - Subscribe to: `Pull request`, `Push`, `Workflow run`.

### 3. Performance & Responsiveness
- **Async I/O**: Use `await asyncio.to_thread` for all Firestore and synchronous network calls.
- **CPU-Bound Tasks**: Avoid long-running computations (like image generation) in the main thread. Wrap them in `asyncio.to_thread` to keep the bot responsive.
- **Shared Object Model**: Use the `shared.bot_instance` pattern for cross-thread communication between Flask and Discord.

### 4. Async Architecture Pattern
Always use this pattern for blocking calls:

```python
# Offload to thread to keep event loop free
result = await asyncio.to_thread(get_document, 'collection', 'doc_id', discord_server_id)

# Offload CPU-bound calculations
buffer = await asyncio.to_thread(generate_complex_chart, data)
```
