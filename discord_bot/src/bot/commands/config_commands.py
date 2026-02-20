"""
Configuration Commands Module

Server configuration commands for role mappings and setup checks.
"""

import asyncio
import logging
import discord
from discord import app_commands
from shared.firestore import get_mt_client

logger = logging.getLogger(__name__)


class ConfigCommands:
    """Handles configuration commands for server administrators."""

    def __init__(self, bot):
        self.bot = bot

    def register_commands(self):
        """Register configuration commands with the bot."""
        configure_group = app_commands.Group(
            name="configure",
            description="Configure DisgitBot settings for this server"
        )

        @configure_group.command(
            name="roles",
            description="Manage custom role mappings by contributions"
        )
        @app_commands.describe(
            action="Choose an action",
            metric="Contribution type to map",
            threshold="Minimum count required",
            role="Discord role to grant"
        )
        @app_commands.choices(
            action=[
                app_commands.Choice(name="list", value="list"),
                app_commands.Choice(name="add", value="add"),
                app_commands.Choice(name="remove", value="remove"),
                app_commands.Choice(name="reset", value="reset"),
            ],
            metric=[
                app_commands.Choice(name="prs", value="pr"),
                app_commands.Choice(name="issues", value="issue"),
                app_commands.Choice(name="commits", value="commit"),
            ]
        )
        async def configure_roles(
            interaction: discord.Interaction,
            action: app_commands.Choice[str],
            metric: app_commands.Choice[str] | None = None,
            threshold: int | None = None,
            role: discord.Role | None = None
        ):
            await interaction.response.defer(ephemeral=True)

            if not interaction.user.guild_permissions.administrator:
                await interaction.followup.send("Only server administrators can configure roles.", ephemeral=True)
                return

            guild = interaction.guild
            if not guild:
                await interaction.followup.send("This command can only be used in a server.", ephemeral=True)
                return

            mt_client = get_mt_client()
            server_config = await asyncio.to_thread(mt_client.get_server_config, str(guild.id)) or {}
            if not server_config.get('setup_completed'):
                await interaction.followup.send("Run `/setup` first to connect GitHub.", ephemeral=True)
                return

            role_rules = server_config.get('role_rules') or {
                'pr': [],
                'issue': [],
                'commit': []
            }

            action_value = action.value

            if action_value == "list":
                await interaction.followup.send(self._format_role_rules(role_rules), ephemeral=True)
                return

            if action_value == "reset":
                role_rules = {'pr': [], 'issue': [], 'commit': []}
                server_config['role_rules'] = role_rules
                await asyncio.to_thread(mt_client.set_server_config, str(guild.id), server_config)
                await interaction.followup.send("Role rules reset to defaults.", ephemeral=True)
                return

            if action_value == "add":
                if not metric or threshold is None or not role:
                    await interaction.followup.send(
                        "Usage: `/configure roles action:add metric:<prs|issues|commits> threshold:<number> role:@Role`",
                        ephemeral=True
                    )
                    return

                if threshold <= 0:
                    await interaction.followup.send("Threshold must be a positive number.", ephemeral=True)
                    return

                # Role hierarchy validation: bot must be able to manage this role
                bot_member = guild.me
                if bot_member is None:
                    try:
                        bot_member = await guild.fetch_member(self.bot.user.id)
                    except Exception:
                        logger.warning(f"Could not fetch bot member in guild {guild.id}")
                        await interaction.followup.send(
                            "❌ Unable to verify role permissions. Please ensure I have the Manage Roles permission.",
                            ephemeral=True
                        )
                        return
                if bot_member.top_role.position <= role.position:
                    await interaction.followup.send(
                        f"❌ Cannot add rule for @{role.name}.\n"
                        f"This role is positioned **equal to or higher** than my top role (@{bot_member.top_role.name}).\n"
                        f"Please move my role higher in Server Settings → Roles, or choose a lower role.",
                        ephemeral=True
                    )
                    return

                metric_key = metric.value
                rules = role_rules.get(metric_key, [])

                # Remove existing rule for this role to avoid duplicates
                rules = [rule for rule in rules if str(rule.get('role_id')) != str(role.id)]

                rules.append({
                    'threshold': int(threshold),
                    'role_id': str(role.id),
                    'role_name': role.name
                })

                rules = sorted(rules, key=lambda r: r.get('threshold', 0))
                role_rules[metric_key] = rules

                server_config['role_rules'] = role_rules
                await asyncio.to_thread(mt_client.set_server_config, str(guild.id), server_config)

                await interaction.followup.send(
                    f"Added rule: {metric.name} {threshold}+ -> @{role.name}",
                    ephemeral=True
                )
                return

            if action_value == "remove":
                if not role:
                    await interaction.followup.send(
                        "Usage: `/configure roles action:remove role:@Role`",
                        ephemeral=True
                    )
                    return

                removed = False
                for key in ('pr', 'issue', 'commit'):
                    rules = role_rules.get(key, [])
                    new_rules = [rule for rule in rules if str(rule.get('role_id')) != str(role.id)]
                    if len(new_rules) != len(rules):
                        removed = True
                    role_rules[key] = new_rules

                if not removed:
                    await interaction.followup.send("That role is not in your custom rules.", ephemeral=True)
                    return

                server_config['role_rules'] = role_rules
                await asyncio.to_thread(mt_client.set_server_config, str(guild.id), server_config)

                await interaction.followup.send(f"Removed custom rules for @{role.name}.", ephemeral=True)
                return

            await interaction.followup.send("Unknown action. Use list, add, remove, or reset.", ephemeral=True)

        self.bot.tree.add_command(configure_group)

    def _format_role_rules(self, role_rules: dict) -> str:
        sections = []
        for key, label in (('pr', 'PRs'), ('issue', 'Issues'), ('commit', 'Commits')):
            rules = role_rules.get(key, [])
            if not rules:
                sections.append(f"{label}: (no custom rules)")
                continue
            lines = [f"{label}:"]
            for rule in sorted(rules, key=lambda r: r.get('threshold', 0)):
                threshold = rule.get('threshold', 0)
                role_name = rule.get('role_name', 'Unknown')
                lines.append(f"  - {threshold}+ -> @{role_name}")
            sections.append("\n".join(lines))

        return "Custom role rules:\n" + "\n\n".join(sections)
