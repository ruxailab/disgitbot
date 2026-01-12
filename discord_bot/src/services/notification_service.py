"""
Notification Service

Handles Discord webhook notifications for GitHub events.
Provides unified interface for PR automation and CI/CD notifications.
"""

import aiohttp
import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from shared.firestore import get_document, set_document

logger = logging.getLogger(__name__)

class NotificationService:
    """Manages Discord webhook notifications for GitHub events."""
    
    def __init__(self):
        """Initialize the notification service."""
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def send_pr_automation_notification(self, pr_data: Dict[str, Any], comment_body: str) -> bool:
        """Send PR automation notification."""
        try:
            repo = pr_data.get('repository', '')
            github_org = repo.split('/')[0] if '/' in repo else None
            
            webhook_urls = await self._get_webhook_urls('pr_automation', github_org=github_org)
            if not webhook_urls:
                logger.warning("No webhook URL configured for PR automation notifications")
                return False
            
            embed = self._build_pr_automation_embed(pr_data, comment_body)
            payload = {
                "embeds": [embed],
                "username": "PR Automation Bot",
                "avatar_url": "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"
            }
            
            success = False
            for url in webhook_urls:
                if await self._send_webhook(url, payload):
                    success = True
            return success
            
        except Exception as e:
            logger.error(f"Failed to send PR automation notification: {e}")
            return False
    
    async def send_cicd_notification(self, repo: str, workflow_name: str, status: str, 
                                   run_url: str, commit_sha: str, branch: str) -> bool:
        """Send CI/CD status notification."""
        try:
            github_org = repo.split('/')[0] if '/' in repo else None
            webhook_urls = await self._get_webhook_urls('cicd', github_org=github_org)
            if not webhook_urls:
                logger.warning("No webhook URL configured for CI/CD notifications")
                return False
            
            embed = self._build_cicd_embed(repo, workflow_name, status, run_url, commit_sha, branch)
            payload = {
                "embeds": [embed],
                "username": "CI/CD Monitor",
                "avatar_url": "https://github.githubassets.com/images/modules/logos_page/Octocat.png"
            }
            
            success = False
            for url in webhook_urls:
                if await self._send_webhook(url, payload):
                    success = True
            return success
            
        except Exception as e:
            logger.error(f"Failed to send CI/CD notification: {e}")
            return False
    
    def _build_pr_automation_embed(self, pr_data: Dict[str, Any], comment_body: str) -> Dict[str, Any]:
        """Build Discord embed for PR automation notification."""
        repo = pr_data.get('repository', 'Unknown')
        pr_number = pr_data.get('pr_number', 0)
        status = pr_data.get('status', 'unknown')
        
        # Determine embed color based on status
        color = 0x28a745 if status == 'success' else 0xdc3545  # Green for success, red for error
        
        embed = {
            "title": f"PR #{pr_number} Automation Complete",
            "description": f"Automated processing completed for [{repo}](https://github.com/{repo}/pull/{pr_number})",
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "fields": []
        }
        
        if status == 'success':
            # Add metrics if available
            metrics = pr_data.get('metrics', {})
            if metrics:
                metrics_text = f"""
                **Lines Changed:** {metrics.get('lines_changed', 'N/A')}
                **Files Modified:** {metrics.get('files_changed', 'N/A')}
                **Complexity Score:** {metrics.get('complexity_score', 'N/A')}
                """
                embed["fields"].append({
                    "name": "PR Metrics",
                    "value": metrics_text.strip(),
                    "inline": True
                })
            
            # Add labels if available
            labels = pr_data.get('predicted_labels', [])
            if labels:
                label_names = [f"`{label['name']}`" for label in labels if label.get('confidence', 0) >= 0.5]
                if label_names:
                    embed["fields"].append({
                        "name": "Applied Labels",
                        "value": " ".join(label_names),
                        "inline": True
                    })
            
            # Add reviewers if assigned
            reviewers = pr_data.get('reviewer_assignments', {}).get('reviewers', [])
            if reviewers:
                reviewer_names = [f"@{r['username']}" for r in reviewers]
                embed["fields"].append({
                    "name": "Assigned Reviewers",
                    "value": " ".join(reviewer_names),
                    "inline": True
                })
        else:
            # Error case
            error_msg = pr_data.get('error', 'Unknown error occurred')
            embed["fields"].append({
                "name": "Error Details",
                "value": f"```{error_msg}```",
                "inline": False
            })
        
        # Add truncated comment body
        if comment_body and len(comment_body) > 500:
            truncated = comment_body[:500] + "..."
            embed["fields"].append({
                "name": "GitHub Comment (Truncated)",
                "value": f"```{truncated}```",
                "inline": False
            })
        elif comment_body:
            embed["fields"].append({
                "name": "GitHub Comment",
                "value": f"```{comment_body}```",
                "inline": False
            })
        
        return embed
    
    def _build_cicd_embed(self, repo: str, workflow_name: str, status: str, 
                         run_url: str, commit_sha: str, branch: str) -> Dict[str, Any]:
        """Build Discord embed for CI/CD notification."""
        # Status-based configuration
        status_config = {
            'success': {'color': 0x28a745, 'emoji': '', 'title': 'Workflow Completed'},
            'failure': {'color': 0xdc3545, 'emoji': '', 'title': 'Workflow Failed'},
            'in_progress': {'color': 0xffc107, 'emoji': '', 'title': 'Workflow Running'},
            'cancelled': {'color': 0x6c757d, 'emoji': '️', 'title': 'Workflow Cancelled'}
        }
        
        config = status_config.get(status, {'color': 0x6c757d, 'emoji': '', 'title': 'Workflow Status'})
        
        embed = {
            "title": f"{config['emoji']} {config['title']}",
            "description": f"[{workflow_name}]({run_url}) in [{repo}](https://github.com/{repo})",
            "color": config['color'],
            "timestamp": datetime.utcnow().isoformat(),
            "fields": [
                {
                    "name": "Repository",
                    "value": f"[{repo}](https://github.com/{repo})",
                    "inline": True
                },
                {
                    "name": "Branch",
                    "value": f"`{branch}`",
                    "inline": True
                },
                {
                    "name": "Commit",
                    "value": f"[`{commit_sha[:8]}`](https://github.com/{repo}/commit/{commit_sha})",
                    "inline": True
                }
            ]
        }
        
        return embed
    
    async def _get_webhook_urls(self, notification_type: str, github_org: str = None) -> List[str]:
        """Get all webhook URLs for specified notification type."""
        urls = []
        try:
            # First try org-scoped config
            if github_org:
                webhook_config = get_document('pr_config', 'webhooks', github_org=github_org)
                if webhook_config:
                    # New list format support
                    if 'webhooks' in webhook_config:
                        urls.extend([
                            w['url'] for w in webhook_config['webhooks'] 
                            if w.get('type') == notification_type and w.get('url')
                        ])
                    
                    # Legacy fallback (single string format)
                    legacy_url = webhook_config.get(f'{notification_type}_webhook_url')
                    if legacy_url and legacy_url not in urls:
                        urls.append(legacy_url)
            
            # Fallback to global config (legacy support)
            if not urls:
                webhook_config = get_document('global_config', 'ci_cd_webhooks')
                if webhook_config:
                    legacy_url = webhook_config.get(f'{notification_type}_webhook_url')
                    if legacy_url:
                        urls.append(legacy_url)
            
            return urls
        except Exception as e:
            logger.error(f"Failed to get webhook URL for {notification_type}: {e}")
            return None
    
    async def _send_webhook(self, webhook_url: str, payload: Dict[str, Any]) -> bool:
        """Send payload to Discord webhook."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.post(
                webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'}
            ) as response:
                if response.status == 204:
                    logger.info("Webhook notification sent successfully")
                    return True
                else:
                    logger.error(f"Webhook failed with status {response.status}: {await response.text()}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to send webhook: {e}")
            return False

class WebhookManager:
    """Manages webhook URL configuration and repository monitoring."""
    
    @staticmethod
    def set_webhook_url(notification_type: str, webhook_url: str, discord_server_id: str = None) -> bool:
        """Set webhook URL for specified notification type."""
        try:
            webhook_config = get_document('pr_config', 'webhooks', discord_server_id=discord_server_id) or {}
            
            # Initialize modern list format
            if 'webhooks' not in webhook_config:
                webhook_config['webhooks'] = []
            
            # Remove any existing webhook for THIS server and THIS type to avoid duplicates
            webhook_config['webhooks'] = [
                w for w in webhook_config['webhooks'] 
                if not (w.get('server_id') == discord_server_id and w.get('type') == notification_type)
            ]
            
            # Add new webhook entry
            webhook_config['webhooks'].append({
                'type': notification_type,
                'url': webhook_url,
                'server_id': discord_server_id,
                'last_updated': datetime.utcnow().isoformat()
            })
            
            # Maintain legacy field for backward compatibility
            webhook_config[f'{notification_type}_webhook_url'] = webhook_url
            webhook_config['last_updated'] = datetime.utcnow().isoformat()
            
            return set_document('pr_config', 'webhooks', webhook_config, discord_server_id=discord_server_id)
        except Exception as e:
            logger.error(f"Failed to set webhook URL: {e}")
            return False
    
    @staticmethod
    def get_monitored_repositories(discord_server_id: str = None) -> List[str]:
        """Get list of repositories being monitored for CI/CD notifications."""
        try:
            config = get_document('pr_config', 'monitoring', discord_server_id=discord_server_id)
            if not config:
                return []
            return config.get('repositories', [])
        except Exception as e:
            logger.error(f"Failed to get monitored repositories: {e}")
            return []
    
    @staticmethod
    def add_monitored_repository(repo: str, discord_server_id: str = None) -> bool:
        """Add repository to CI/CD monitoring list."""
        try:
            config = get_document('pr_config', 'monitoring', discord_server_id=discord_server_id) or {'repositories': []}
            repos = config.get('repositories', [])
            
            if repo not in repos:
                repos.append(repo)
                config['repositories'] = repos
                config['last_updated'] = datetime.utcnow().isoformat()
                
                return set_document('pr_config', 'monitoring', config, discord_server_id=discord_server_id)
            return True  # Already exists
        except Exception as e:
            logger.error(f"Failed to add monitored repository: {e}")
            return False
    
    @staticmethod
    def remove_monitored_repository(repo: str, discord_server_id: str = None) -> bool:
        """Remove repository from CI/CD monitoring list."""
        try:
            config = get_document('pr_config', 'monitoring', discord_server_id=discord_server_id)
            if not config:
                return False
            
            repos = config.get('repositories', [])
            if repo in repos:
                repos.remove(repo)
                config['repositories'] = repos
                config['last_updated'] = datetime.utcnow().isoformat()
                
                return set_document('pr_config', 'monitoring', config, discord_server_id=discord_server_id)
            return True  # Already removed
        except Exception as e:
            logger.error(f"Failed to remove monitored repository: {e}")
            return False