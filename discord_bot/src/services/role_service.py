"""
Role Service

Handles role determination and medal assignment logic.
"""

from typing import Dict, Any, Optional, Tuple, List



class RoleConfiguration:
    """Configuration for role thresholds and settings."""
    
    def __init__(self):
        # PR Role Thresholds
        self.pr_thresholds = {
            "🌸 1+ PRs": 1,
            "🌺 5+ PRs": 5,
            "🌻 10+ PRs": 10,
            "🌷 25+ PRs": 25,
            "🌹 50+ PRs": 50
        }

        # Issue Role Thresholds
        self.issue_thresholds = {
            "🍃 1+ GitHub Issues Reported": 1,
            "🌿 5+ GitHub Issues Reported": 5,
            "🌱 10+ GitHub Issues Reported": 10,
            "🌾 25+ GitHub Issues Reported": 25,
            "🍀 50+ GitHub Issues Reported": 50
        }

        # Commit Role Thresholds
        self.commit_thresholds = {
            "☁️ 1+ Commits": 1,
            "🌊 25+ Commits": 25,
            "🌈 50+ Commits": 50,
            "🌙 100+ Commits": 100,
            "⭐ 250+ Commits": 250
        }
        
        # Medal roles for top 3 contributors
        self.medal_roles = ["✨ PR Champion", "💫 PR Runner-up", "🔮 PR Bronze"]
        
        # Obsolete role names to clean up
        self.obsolete_roles = {
            "Beginner (1-5 PRs)", "Contributor (6-15 PRs)", "Analyst (16-30 PRs)",
            "Expert (31-50 PRs)", "Master (51+ PRs)", "Beginner (1-5 Issues)",
            "Contributor (6-15 Issues)", "Analyst (16-30 Issues)", "Expert (31-50 Issues)",
            "Master (51+ Issues)", "Beginner (1-50 Commits)", "Contributor (51-100 Commits)",
            "Analyst (101-250 Commits)", "Expert (251-500 Commits)", "Master (501+ Commits)",
            # Old numeric thresholds
            "1+ PR", "6+ PR", "16+ PR", "31+ PR", "51+ PR",
            "1+ Issue", "6+ Issue", "16+ Issue", "31+ Issue", "51+ Issue",
            "1+ Issue Reporter", "6+ Issue Reporter", "16+ Issue Reporter", "31+ Issue Reporter", "51+ Issue Reporter",
            "1+ Bug Hunter", "6+ Bug Hunter", "16+ Bug Hunter", "31+ Bug Hunter", "51+ Bug Hunter",
            "1+ Commit", "51+ Commit", "101+ Commit", "251+ Commit", "501+ Commit",
            "PR Champion", "PR Runner-up", "PR Bronze",
            # Old emoji versions
            "🌸 1+ PR", "🌺 6+ PR", "🌻 16+ PR", "🌷 31+ PR", "🌹 51+ PR",
            "🍃 1+ Issue", "🌿 6+ Issue", "🌱 16+ Issue", "🌾 31+ Issue", "🍀 51+ Issue",
            "🍃 1+ Issue Reporter", "🌿 6+ Issue Reporter", "🌱 16+ Issue Reporter", "🌾 31+ Issue Reporter", "🍀 51+ Issue Reporter",
            "🍃 1+ Bug Hunter", "🌿 6+ Bug Hunter", "🌱 16+ Bug Hunter", "🌾 31+ Bug Hunter", "🍀 51+ Bug Hunter",
            "☁️ 1+ Commit", "🌊 51+ Commit", "🌈 101+ Commit", "🌙 251+ Commit", "⭐ 501+ Commit"
        }
        
        # Role Colors (RGB tuples) - Aesthetic pastels
        self.role_colors = {
            # PR roles - Pink/Rose pastels
            "🌸 1+ PRs": (255, 182, 193),        # Light pink
            "🌺 6+ PRs": (255, 160, 180),        # Soft rose
            "🌻 16+ PRs": (255, 140, 167),       # Medium rose
            "🌷 31+ PRs": (255, 120, 154),       # Deep rose
            "🌹 51+ PRs": (255, 100, 141),       # Rich rose
            
            # Issue roles - Green pastels
            "🍃 1+ GitHub Issues Reported": (189, 252, 201),     # Soft mint
            "🌿 6+ GitHub Issues Reported": (169, 252, 186),     # Light mint
            "🌱 16+ GitHub Issues Reported": (149, 252, 171),    # Medium mint
            "🌾 31+ GitHub Issues Reported": (129, 252, 156),    # Deep mint
            "🍀 51+ GitHub Issues Reported": (109, 252, 141),    # Rich mint
            
            # Commit roles - Blue/Purple pastels
            "☁️ 1+ Commits": (230, 230, 250),    # Lavender
            "🌊 51+ Commits": (173, 216, 230),   # Light blue
            "🌈 101+ Commits": (186, 186, 255),  # Periwinkle
            "🌙 251+ Commits": (221, 160, 221),  # Plum
            "⭐ 501+ Commits": (200, 140, 255),  # Soft purple
            
            # Medal roles - Shimmery pastels
            "✨ PR Champion": (255, 215, 180),   # Champagne
            "💫 PR Runner-up": (220, 220, 220), # Pearl
            "🔮 PR Bronze": (205, 180, 150)     # Rose gold
        }

class RoleService:
    """Service for role determination and management with clean separation of concerns."""
    
    def __init__(self):
        """Initialize role service."""
        self.config = RoleConfiguration()
    
    def determine_roles(self, pr_count: int, issues_count: int, commits_count: int) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Determine roles based on contribution counts."""
        pr_role = self._determine_role_for_threshold(pr_count, self.config.pr_thresholds)
        issue_role = self._determine_role_for_threshold(issues_count, self.config.issue_thresholds)
        commit_role = self._determine_role_for_threshold(commits_count, self.config.commit_thresholds)
        
        return pr_role, issue_role, commit_role

    def determine_custom_roles(self, pr_count: int, issues_count: int, commits_count: int, role_rules: Dict[str, Any]) -> Dict[str, Optional[Dict[str, Any]]]:
        """Determine custom roles from per-server role rules."""
        return {
            'pr': self._select_custom_rule(pr_count, role_rules.get('pr', [])),
            'issue': self._select_custom_rule(issues_count, role_rules.get('issue', [])),
            'commit': self._select_custom_rule(commits_count, role_rules.get('commit', []))
        }

    def _select_custom_rule(self, count: int, rules: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Pick the highest-threshold custom rule that the count satisfies."""
        if not rules:
            return None
        sorted_rules = sorted(rules, key=lambda r: r.get('threshold', 0))
        selected = None
        for rule in sorted_rules:
            if count >= int(rule.get('threshold', 0)):
                selected = rule
        return selected
    
    def _determine_role_for_threshold(self, count: int, thresholds: Dict[str, int]) -> Optional[str]:
        """Determine role for a specific contribution type."""
        for role_name, threshold in reversed(list(thresholds.items())):
            if count >= threshold:
                return role_name
        return None
    
    def get_medal_assignments(self, hall_of_fame_data: Dict[str, Any]) -> Dict[str, str]:
        """Get medal role assignments for top contributors."""
        medal_assignments = {}
        
        if not hall_of_fame_data or not hall_of_fame_data.get('pr', {}).get('all_time'):
            return medal_assignments
        
        top_3_prs = hall_of_fame_data['pr']['all_time'][:3]
        
        for i, contributor in enumerate(top_3_prs):
            username = contributor.get('username')
            if username and i < len(self.config.medal_roles):
                medal_assignments[username] = self.config.medal_roles[i]
        
        return medal_assignments
    
    def get_all_role_names(self) -> List[str]:
        """Get all possible role names for creation."""
        all_roles = []
        all_roles.extend(self.config.pr_thresholds.keys())
        all_roles.extend(self.config.issue_thresholds.keys())
        all_roles.extend(self.config.commit_thresholds.keys())
        all_roles.extend(self.config.medal_roles)
        return list(set(all_roles))  # Remove duplicates
    
    def get_obsolete_role_names(self) -> set:
        """Get obsolete role names that should be cleaned up."""
        return self.config.obsolete_roles
    
    def get_role_color(self, role_name: str) -> Optional[Tuple[int, int, int]]:
        """Get RGB color for a specific role."""
        return self.config.role_colors.get(role_name)
    
    def get_hall_of_fame_data(self, discord_server_id: str) -> Optional[Dict[str, Any]]:
        """Get hall of fame data from storage."""
        from shared.firestore import get_document
        return get_document('repo_stats', 'hall_of_fame', discord_server_id)
    
    def get_next_role(self, current_role: str, stats_type: str) -> str:
        """Determine the next role based on current role and stats type."""
        if stats_type == "pr":
            thresholds = self.config.pr_thresholds
        elif stats_type == "issue":
            thresholds = self.config.issue_thresholds
        elif stats_type == "commit":
            thresholds = self.config.commit_thresholds
        else:
            return "Unknown"
        
        if current_role == "None" or current_role is None:
            if thresholds:
                first_role = list(thresholds.keys())[0]
                return f"@{first_role}"
            return "Unknown"
        
        role_list = list(thresholds.items())
        
        for i, (role, _) in enumerate(role_list):
            if role == current_role:
                if i == len(role_list) - 1:
                    return "You've reached the highest level!"
                
                next_role = role_list[i + 1][0]
                return f"@{next_role}"
        
        return "Unknown" 
