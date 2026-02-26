"""
User Commands Module

Handles user-related Discord commands like linking, stats, and hall of fame.
"""

import discord
from discord import app_commands
import asyncio
import datetime
from ...services.role_service import RoleService
from ..auth import get_github_username_for_user, register_link_event, unregister_link_event, oauth_sessions, oauth_sessions_lock
from shared.firestore import get_document, set_document, get_mt_client

class UserCommands:
    """Handles user-related Discord commands."""

    def __init__(self, bot):
        self.bot = bot
        self._active_links: set[str] = set()  # Per-user tracking, not global lock

    async def _safe_defer(self, interaction, ephemeral=True):
        """Safely defer interaction with error handling."""
        try:
            if interaction.response.is_done():
                return
            await interaction.response.defer(ephemeral=ephemeral)
        except discord.errors.InteractionResponded:
            # Interaction was already responded to, continue anyway
            pass
        except discord.errors.HTTPException as exc:
            if exc.code == 40060:
                return
            raise

    async def _safe_followup(self, interaction, message, embed=False, ephemeral=True):
        """Safely send followup message with error handling."""
        try:
            if embed:
                await interaction.followup.send(embed=message, ephemeral=ephemeral)
            else:
                await interaction.followup.send(message, ephemeral=ephemeral)
        except discord.errors.InteractionResponded:
            # Interaction was already responded to, continue anyway
            pass
        except discord.errors.HTTPException as exc:
            if exc.code == 40060:
                return
            raise

    async def _ensure_server_registered(self, discord_user_id: str, discord_server_id: str) -> None:
        """Ensure the current server is in the user's servers list.

        A user only runs /link once.  When they later join a new server and
        interact with the bot there, the new server_id is not yet in their
        Firestore document.  This helper silently adds it so that:
          - The pipeline's user-mapping lookup succeeds immediately
          - The user gets roles assigned on the next daily run
        """
        mt_client = get_mt_client()
        user_mapping = await asyncio.to_thread(mt_client.get_user_mapping, discord_user_id) or {}
        github_id = user_mapping.get('github_id')
        if not github_id:
            return  # not linked yet — nothing to do
        existing_servers = user_mapping.get('servers', [])
        if discord_server_id not in existing_servers:
            existing_servers.append(discord_server_id)
            user_mapping['servers'] = existing_servers
            await asyncio.to_thread(mt_client.set_user_mapping, discord_user_id, user_mapping)
            print(f"Auto-registered server {discord_server_id} for GitHub user {github_id}")
    
    def register_commands(self):
        """Register all user commands with the bot."""
        self.bot.tree.add_command(self._help_command())
        self.bot.tree.add_command(self._link_command())
        self.bot.tree.add_command(self._unlink_command())
        self.bot.tree.add_command(self._getstats_command())
        self.bot.tree.add_command(self._halloffame_command())
        self.bot.tree.add_command(self._repos_command())

    def _help_command(self):
        """Create the help command."""
        @app_commands.command(name="help", description="How DisgitBot works and how to get started")
        async def help_cmd(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)

            is_admin = interaction.user.guild_permissions.administrator

            # --- Embed 1: Getting Started ---
            start_embed = discord.Embed(
                title="DisgitBot — Getting Started",
                description=(
                    "DisgitBot tracks GitHub contributions for your organization "
                    "and displays stats, leaderboards, and auto-assigns roles in Discord."
                ),
                color=discord.Color.blurple()
            )
            start_embed.add_field(
                name="1️⃣  Setup (admin, one-time)",
                value=(
                    "`/setup` → click link → install GitHub App on your org\n"
                    "Choose **All repositories** for automatic tracking of new repos."
                ),
                inline=False
            )
            start_embed.add_field(
                name="2️⃣  Link your account",
                value="`/link` → authorize with GitHub → your stats are now tracked",
                inline=False
            )
            start_embed.add_field(
                name="3️⃣  View stats",
                value=(
                    "`/getstats` — your personal contribution stats\n"
                    "`/halloffame` — top 3 contributors leaderboard\n"
                    "`/repos` — list all tracked repositories"
                ),
                inline=False
            )

            # --- Embed 2: Good to Know ---
            faq_embed = discord.Embed(
                title="Good to Know",
                color=discord.Color.greyple()
            )
            faq_embed.add_field(
                name="📊  When does data update?",
                value=(
                    "Automatically every night (midnight UTC).\n"
                    "Admins can force refresh with `/sync`.\n"
                    "After first setup, wait ~5–10 minutes for initial data."
                ),
                inline=False
            )
            faq_embed.add_field(
                name="📦  New repos not showing up?",
                value=(
                    "If the GitHub App was installed with **Selected repositories**, "
                    "new repos won't be tracked automatically.\n"
                    "→ Go to **GitHub → Settings → GitHub Apps → Configure** "
                    "and add the new repo, or switch to **All repositories**."
                ),
                inline=False
            )
            faq_embed.add_field(
                name="👤  My stats are empty?",
                value=(
                    "Make sure you've run `/link` first.\n"
                    "If you just set up, data may not be synced yet — "
                    "try `/sync` (admin) or wait for the next automatic sync."
                ),
                inline=False
            )

            embeds = [start_embed, faq_embed]

            # --- Embed 3: Admin Commands (only shown to admins) ---
            if is_admin:
                admin_embed = discord.Embed(
                    title="Admin Commands",
                    color=discord.Color.orange()
                )
                admin_embed.add_field(
                    name="Commands",
                    value=(
                        "`/setup` — connect or check GitHub org connection\n"
                        "`/sync` — manually trigger data refresh (12h cooldown)\n"
                        "`/configure roles` — auto-assign roles based on contributions\n"
                        "`/setup_voice_stats` — voice channel repo stats display\n"
                        "`/check_permissions` — verify bot has required permissions"
                    ),
                    inline=False
                )
                admin_embed.add_field(
                    name="Setup flow for organizations",
                    value=(
                        "If a **non-owner** member runs `/setup`, GitHub sends "
                        "an install **request** to the org owner.\n"
                        "After the owner approves on GitHub, "
                        "an admin or the owner must run `/setup` again in Discord to complete the link."
                    ),
                    inline=False
                )
                embeds.append(admin_embed)

            await interaction.followup.send(embeds=embeds, ephemeral=True)

        return help_cmd
    
    def _link_command(self):
        """Create the link command."""
        @app_commands.command(name="link", description="Link your Discord to GitHub")
        async def link(interaction: discord.Interaction):
            await self._safe_defer(interaction)

            discord_user_id = str(interaction.user.id)

            if discord_user_id in self._active_links:
                await self._safe_followup(interaction, "You already have a link process in progress. Please complete it or wait for it to expire.")
                return

            self._active_links.add(discord_user_id)
            try:
                discord_server_id = str(interaction.guild.id)
                mt_client = get_mt_client()

                existing_user_data = await asyncio.to_thread(mt_client.get_user_mapping, discord_user_id) or {}
                existing_github = existing_user_data.get('github_id')
                existing_servers = existing_user_data.get('servers', [])

                if existing_github:
                    if discord_server_id not in existing_servers:
                        existing_servers.append(discord_server_id)
                        existing_user_data['servers'] = existing_servers
                        await asyncio.to_thread(mt_client.set_user_mapping, discord_user_id, existing_user_data)

                    await self._safe_followup(
                        interaction,
                        f"Already linked to GitHub user: `{existing_github}`\n"
                        f"Use `/unlink` to disconnect and relink."
                    )
                    return

                oauth_url = get_github_username_for_user(discord_user_id)
                await self._safe_followup(interaction, f"Please complete GitHub authentication: {oauth_url}")

                # Event-driven wait: no threads tied up, Flask callback wakes us instantly
                link_event = asyncio.Event()
                register_link_event(discord_user_id, link_event)
                try:
                    await asyncio.wait_for(link_event.wait(), timeout=300)
                except asyncio.TimeoutError:
                    # Clean up timed-out OAuth session
                    with oauth_sessions_lock:
                        oauth_sessions.pop(discord_user_id, None)
                    await self._safe_followup(interaction, "Authentication timed out or failed. Please try again.")
                    return
                finally:
                    unregister_link_event(discord_user_id)

                # Event fired — read result from oauth_sessions
                github_username = None
                with oauth_sessions_lock:
                    session_data = oauth_sessions.pop(discord_user_id, None)
                if session_data and session_data.get('status') == 'completed':
                    github_username = session_data.get('github_username')
                elif session_data and session_data.get('status') == 'failed':
                    error = session_data.get('error', 'Unknown error')
                    print(f"OAuth failed for {discord_user_id}: {error}")

                if github_username:

                    # Add this server to user's server list
                    servers_list = existing_user_data.get('servers', [])
                    if discord_server_id not in servers_list:
                        servers_list.append(discord_server_id)

                    # Update user mapping with server association
                    user_data = {
                        'github_id': github_username,
                        'servers': servers_list,
                        'pr_count': existing_user_data.get('pr_count', 0),
                        'issues_count': existing_user_data.get('issues_count', 0),
                        'commits_count': existing_user_data.get('commits_count', 0),
                        'role': existing_user_data.get('role', 'member'),
                        'last_linked_server': discord_server_id,
                        'last_updated': str(interaction.created_at)
                    }

                    await asyncio.to_thread(mt_client.set_user_mapping, discord_user_id, user_data)

                    await self._safe_followup(
                        interaction,
                        f"Successfully linked to GitHub user: `{github_username}`\n"
                        f"Use `/getstats` to view your contribution data."
                    )
                else:
                    await self._safe_followup(interaction, "Authentication timed out or failed. Please try again.")

            except Exception as e:
                print("Error in /link:", e)
                await self._safe_followup(interaction, "Failed to link GitHub account.")
            finally:
                self._active_links.discard(discord_user_id)
        
        return link

    def _empty_user_stats(self, last_updated: str | None = None) -> dict:
        """Return an empty stats payload for users with no synced data yet."""
        current_month = datetime.datetime.now(datetime.timezone.utc).strftime("%B")
        return {
            "pr_count": 0,
            "issues_count": 0,
            "commits_count": 0,
            "stats": {
                "current_month": current_month,
                "last_updated": last_updated or "Not synced yet",
                "pr": {
                    "daily": 0,
                    "weekly": 0,
                    "monthly": 0,
                    "all_time": 0,
                    "current_streak": 0,
                    "longest_streak": 0,
                    "avg_per_day": 0
                },
                "issue": {
                    "daily": 0,
                    "weekly": 0,
                    "monthly": 0,
                    "all_time": 0,
                    "current_streak": 0,
                    "longest_streak": 0,
                    "avg_per_day": 0
                },
                "commit": {
                    "daily": 0,
                    "weekly": 0,
                    "monthly": 0,
                    "all_time": 0,
                    "current_streak": 0,
                    "longest_streak": 0,
                    "avg_per_day": 0
                }
            },
            "rankings": {}
        }
    
    def _unlink_command(self):
        """Create the unlink command."""
        @app_commands.command(name="unlink", description="Unlinks your Discord account from your GitHub username")
        async def unlink(interaction: discord.Interaction):
            try:
                await self._safe_defer(interaction)

                discord_user_id = str(interaction.user.id)
                discord_server_id = str(interaction.guild.id)
                mt_client = get_mt_client()

                user_mapping = await asyncio.to_thread(mt_client.get_user_mapping, discord_user_id) or {}
                if not user_mapping.get('github_id'):
                    await self._safe_followup(interaction, "Your Discord account is not linked to any GitHub username.")
                    return

                await asyncio.to_thread(mt_client.set_user_mapping, discord_user_id, {})
                await self._safe_followup(interaction, "Successfully unlinked your Discord account from your GitHub username.")
                print(f"Unlinked Discord user {interaction.user.name}")

            except Exception as e:
                print(f"Error unlinking user: {e}")
                await self._safe_followup(interaction, "An error occurred while unlinking your account.")
        
        return unlink
    
    def _getstats_command(self):
        """Create the getstats command."""
        @app_commands.command(name="getstats", description="Displays your GitHub stats and current role")
        @app_commands.describe(type="Type of stats to display")
        @app_commands.choices(type=[
            app_commands.Choice(name="Pull Requests", value="pr"),
            app_commands.Choice(name="GitHub Issues Reported", value="issue"),
            app_commands.Choice(name="Commits", value="commit")
        ])
        async def getstats(interaction: discord.Interaction, type: str = "pr"):
            try:
                await self._safe_defer(interaction, ephemeral=False)
            except Exception:
                pass

            try:
                stats_type = type.lower().strip()
                if stats_type not in ["pr", "issue", "commit"]:
                    stats_type = "pr"

                user_id = str(interaction.user.id)

                # Check global link mapping first
                discord_server_id = str(interaction.guild.id)
                mt_client = get_mt_client()
                user_mapping = await asyncio.to_thread(mt_client.get_user_mapping, user_id) or {}
                github_username = user_mapping.get('github_id')
                if not github_username:
                    await self._safe_followup(interaction, "Your Discord account is not linked to a GitHub username. Use `/link` to link it.")
                    return

                # Ensure this server is registered in the user's Firestore document
                # so the pipeline can assign roles on the next daily run.
                await self._ensure_server_registered(user_id, discord_server_id)

                github_org = await asyncio.to_thread(mt_client.get_org_from_server, discord_server_id)
                if not github_org:
                    await self._safe_followup(interaction, "This server is not configured yet. Run `/setup` first.")
                    return

                # Fetch org-scoped stats for this GitHub username
                user_data = await asyncio.to_thread(mt_client.get_org_document, github_org, 'contributions', github_username)
                if not user_data:
                    metrics = await asyncio.to_thread(get_document, 'repo_stats', 'metrics', discord_server_id)
                    last_updated = metrics.get('last_updated') if metrics else None
                    user_data = self._empty_user_stats(last_updated)

                # Get stats and create embed
                embed = await self._create_stats_embed(user_data, github_username, stats_type, interaction)
                if embed:
                    await self._safe_followup(interaction, embed, embed=True, ephemeral=False)

            except Exception as e:
                print(f"Error in getstats command: {e}")
                import traceback
                traceback.print_exc()
                await self._safe_followup(interaction, "Unable to retrieve your stats. This might be because you just linked your account and your data isn't populated yet. Please try again in a few minutes!")
        
        return getstats
    
    def _halloffame_command(self):
        """Create the halloffame command."""
        @app_commands.command(name="halloffame", description="Shows top 3 contributors")
        @app_commands.describe(type="Contribution type", period="Time period")
        @app_commands.choices(type=[
            app_commands.Choice(name="Pull Requests", value="pr"),
            app_commands.Choice(name="GitHub Issues Reported", value="issue"),
            app_commands.Choice(name="Commits", value="commit")
        ])
        @app_commands.choices(period=[
            app_commands.Choice(name="All Time", value="all_time"),
            app_commands.Choice(name="Monthly", value="monthly"),
            app_commands.Choice(name="Weekly", value="weekly"),
            app_commands.Choice(name="Daily", value="daily")
        ])
        async def halloffame(interaction: discord.Interaction, type: str = "pr", period: str = "all_time"):
            try:
                await self._safe_defer(interaction, ephemeral=False)
            except Exception:
                pass

            try:
                discord_server_id = str(interaction.guild.id)
                hall_of_fame_data = await asyncio.to_thread(get_document, 'repo_stats', 'hall_of_fame', discord_server_id)

                if not hall_of_fame_data:
                    await self._safe_followup(interaction, "Hall of fame data not available yet.")
                    return

                top_3 = hall_of_fame_data.get(type, {}).get(period, [])

                if not top_3:
                    await self._safe_followup(interaction, f"No data for {type} {period}.")
                    return

                embed = self._create_halloffame_embed(top_3, type, period, hall_of_fame_data.get('last_updated'))
                await self._safe_followup(interaction, embed, embed=True, ephemeral=False)

            except Exception as e:
                print(f"Error in halloffame command: {e}")
                await self._safe_followup(interaction, "Unable to retrieve hall of fame data.")
        
        return halloffame
    
    async def _create_stats_embed(self, user_data, github_username, stats_type, interaction):
        """Create stats embed for user."""
        import datetime
        
        role_service = RoleService()
        
        # Get stats from the detailed structure if available
        pr_all_time = user_data.get("stats", {}).get("pr", {}).get("all_time", user_data.get("pr_count", 0))
        issues_all_time = user_data.get("stats", {}).get("issue", {}).get("all_time", user_data.get("issues_count", 0))
        commits_all_time = user_data.get("stats", {}).get("commit", {}).get("all_time", user_data.get("commits_count", 0))
        
        pr_role, issue_role, commit_role = role_service.determine_roles(pr_all_time, issues_all_time, commits_all_time)
        
        # Set up type-specific variables
        title_prefix = "PR"
        if stats_type == "pr":
            stats_field = "pr"
            role = pr_role
            title_prefix = "PR"
        elif stats_type == "issue":
            stats_field = "issue"
            role = issue_role if issue_role else "None"
            title_prefix = "GitHub Issue Reported"
        elif stats_type == "commit":
            stats_field = "commit"
            role = commit_role if commit_role else "None"
            title_prefix = "Commit"
 
        # Check if stats data exists
        stats = user_data.get("stats")
        if not stats or stats_field not in stats:
            await self._safe_followup(interaction, "Your stats are being collected! Please check back in 5 min after the bot has gathered your contribution data.")
            return None
            
        # Get enhanced stats
        type_stats = stats[stats_field]
        
        # Create enhanced embed
        discord_server_id = str(interaction.guild.id) if interaction.guild else None
        org_name = None
        if discord_server_id:
            try:
                org_name = await asyncio.to_thread(get_mt_client().get_org_from_server, discord_server_id)
            except Exception as e:
                print(f"Error fetching org for server {discord_server_id}: {e}")

        org_label = org_name or "your linked"
        embed = discord.Embed(
            title=f"GitHub Contribution Metrics for {github_username}",
            description=(
                f"Stats tracked across {org_label} repositories. "
                f"Updated daily. Last update: {stats.get('last_updated', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'))}"
            ),
            color=discord.Color.blue()
        )
        
        # Create stats table with customized format
        display_prefix = f"{title_prefix}s"
        # Calculate proper spacing - ensure minimum 25 characters for the longest prefix
        prefix_width = max(25, len(display_prefix) + 2)
        stats_table = f"```\n{display_prefix:<{prefix_width}} Count    Ranking\n"
        stats_table += f"24h:{'':<{prefix_width-4}} {type_stats.get('daily', 0):<8} #{user_data.get('rankings', {}).get(f'{stats_type}_daily', 0)}\n"
        stats_table += f"7 days:{'':<{prefix_width-7}} {type_stats.get('weekly', 0):<8} #{user_data.get('rankings', {}).get(f'{stats_type}_weekly', 0)}\n"
        stats_table += f"30 days:{'':<{prefix_width-8}} {type_stats.get('monthly', 0):<8} #{user_data.get('rankings', {}).get(f'{stats_type}_monthly', 0)}\n"
        stats_table += f"Lifetime:{'':<{prefix_width-9}} {type_stats.get('all_time', 0):<8} #{user_data.get('rankings', {}).get(stats_type, 0)}\n\n"
        
        # Add averages and streaks with customized wording
        stats_table += f"Daily Average ({stats.get('current_month', 'June')}): {type_stats.get('avg_per_day', 0)} {title_prefix}s\n\n"
        stats_table += f"Active {title_prefix} Streak: {type_stats.get('current_streak', 0)} {title_prefix}s\n"
        stats_table += f"Best {title_prefix} Streak: {type_stats.get('longest_streak', 0)} {title_prefix}s\n```"
        
        # Add level information based on role
        embed.add_field(name="Statistics", value=stats_table, inline=False)
        embed.add_field(name="Current level:", value=f"{role}", inline=True)
        
        # Determine next level
        next_level = role_service.get_next_role(role, stats_type)
        
        # Remove @ if present in next_level
        if next_level.startswith('@'):
            next_level = next_level[1:]
            
        embed.add_field(name="Next level:", value=next_level, inline=True)
        
        # Add info about other stat types
        other_types = []
        if stats_type != "pr":
            other_types.append(f"`/getstats type:pr` - View PR stats")
        if stats_type != "issue":
            other_types.append(f"`/getstats type:issue` - View GitHub Issues Reported stats")
        if stats_type != "commit":
            other_types.append(f"`/getstats type:commit` - View Commit stats")
            
        embed.add_field(
            name="Other Statistics:", 
            value="\n".join(other_types),
            inline=False
        )
        
        return embed 
    def _create_halloffame_embed(self, top_3, type, period, last_updated):
        """Create hall of fame embed."""
        type_names = {"pr": "Pull Requests", "issue": "GitHub Issues Reported", "commit": "Commits"}
        period_names = {"all_time": "All Time", "monthly": "Monthly", "weekly": "Weekly", "daily": "Daily"}
        
        embed = discord.Embed(
            title=f"{type_names[type]} Hall of Fame ({period_names[period]})",
            color=discord.Color.gold()
        )
        
        trophies = ["🥇", "🥈", "🥉"]
        for i, contributor in enumerate(top_3[:3]):
            username = contributor.get('username', 'Unknown')
            count = contributor.get('count', 0)  # Changed from 'value' to 'count' to match new structure
            embed.add_field(
                name=f"{trophies[i]} {username}",
                value=f"{count} {type_names[type].lower()}",
                inline=False
            )
        
        embed.set_footer(text=f"Last updated: {last_updated or 'Unknown'}")
        return embed

    def _repos_command(self):
        """Create the repos command to list tracked repositories."""
        @app_commands.command(name="repos", description="List repositories tracked by DisgitBot on this server")
        @app_commands.guild_only()
        async def repos(interaction: discord.Interaction):
            """Shows all repositories the GitHub App can access for this server."""
            await self._safe_defer(interaction)

            try:
                mt_client = get_mt_client()
                guild_id = str(interaction.guild_id)
                server_config = await asyncio.to_thread(mt_client.get_server_config, guild_id) or {}

                if not server_config.get('setup_completed'):
                    await self._safe_followup(
                        interaction,
                        "This server hasn't been set up yet. An admin needs to run `/setup` first."
                    )
                    return

                installation_id = server_config.get('github_installation_id')
                github_org = server_config.get('github_org', 'Unknown')

                if not installation_id:
                    await self._safe_followup(
                        interaction,
                        f"This server is connected to **{github_org}** but has no GitHub App installation ID.\n"
                        f"An admin should run `/setup` to reconnect."
                    )
                    return

                # Get installation access token and fetch repos
                from ...services.github_app_service import GitHubAppService
                from ...services.github_service import GitHubService

                gh_app = GitHubAppService()
                token = await asyncio.to_thread(gh_app.get_installation_access_token, installation_id)

                if not token:
                    await self._safe_followup(
                        interaction,
                        "Couldn't authenticate with GitHub. The app installation may have been removed.\n"
                        "An admin should check the GitHub App settings or run `/setup` again."
                    )
                    return

                gh_service = GitHubService(
                    repo_owner=github_org,
                    token=token,
                    installation_id=installation_id
                )
                repos_list = await asyncio.to_thread(gh_service.fetch_installation_repositories)

                if not repos_list:
                    embed = discord.Embed(
                        title="📂 Tracked Repositories",
                        description=f"Connected to **{github_org}** but no repositories found.",
                        color=0xfee75c  # yellow
                    )
                    embed.set_footer(text="The GitHub App may need repository access permissions updated.")
                    await self._safe_followup(interaction, embed, embed=True)
                    return

                # Build a nice embed
                embed = discord.Embed(
                    title="📂 Tracked Repositories",
                    description=f"**{github_org}** — {len(repos_list)} {'repository' if len(repos_list) == 1 else 'repositories'} tracked",
                    color=0x43b581  # green
                )

                # Show repos in chunks (Discord embed field limit is 1024 chars)
                repo_names = [f"• `{r['owner']}/{r['name']}`" for r in repos_list]
                chunk_size = 20
                for i in range(0, len(repo_names), chunk_size):
                    chunk = repo_names[i:i + chunk_size]
                    field_name = "Repositories" if i == 0 else f"Repositories (cont.)"
                    embed.add_field(
                        name=field_name,
                        value="\n".join(chunk),
                        inline=False
                    )

                embed.set_footer(text="Repos are set in GitHub App installation settings. Stats sync daily at midnight UTC.")
                await self._safe_followup(interaction, embed, embed=True)

            except Exception as e:
                await self._safe_followup(interaction, f"Error fetching repositories: {str(e)}")
                print(f"Error in repos command: {e}")
                import traceback
                traceback.print_exc()

        return repos
