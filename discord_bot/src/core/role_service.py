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
            "Beginner (1-5 PRs)": 1,
            "Contributor (6-15 PRs)": 6,
            "Analyst (16-30 PRs)": 16,
            "Expert (31-50 PRs)": 31,
            "Master (51+ PRs)": 51
        }
        
        # Issue Role Thresholds  
        self.issue_thresholds = {
            "Beginner (1-5 Issues)": 1,
            "Contributor (6-15 Issues)": 6,
            "Analyst (16-30 Issues)": 16,
            "Expert (31-50 Issues)": 31,
            "Master (51+ Issues)": 51
        }
        
        # Commit Role Thresholds
        self.commit_thresholds = {
            "Beginner (1-50 Commits)": 1,
            "Contributor (51-100 Commits)": 51,
            "Analyst (101-250 Commits)": 101,
            "Expert (251-500 Commits)": 251,
            "Master (501+ Commits)": 501
        }
        
        # Medal roles for top 3 contributors
        self.medal_roles = ["PR Champion", "PR Runner-up", "PR Bronze"]
        
        # Role Colors (RGB tuples)
        self.role_colors = {
            "PR Champion": (255, 215, 0),      # Gold
            "PR Runner-up": (192, 192, 192),   # Silver
            "PR Bronze": (205, 127, 50)        # Bronze
        }

class RoleService:
    """Service for role determination and management with clean separation of concerns."""
    
    def __init__(self, storage_service):
        """Initialize with a storage service for data access."""
        self.storage = storage_service
        self.config = RoleConfiguration()
    
    def determine_roles(self, pr_count: int, issues_count: int, commits_count: int) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Determine roles based on contribution counts."""
        pr_role = self._determine_role_for_threshold(pr_count, self.config.pr_thresholds)
        issue_role = self._determine_role_for_threshold(issues_count, self.config.issue_thresholds)
        commit_role = self._determine_role_for_threshold(commits_count, self.config.commit_thresholds)
        
        return pr_role, issue_role, commit_role
    
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
    
    def get_role_color(self, role_name: str) -> Optional[Tuple[int, int, int]]:
        """Get RGB color for a specific role."""
        return self.config.role_colors.get(role_name)
    
    def get_hall_of_fame_data(self) -> Optional[Dict[str, Any]]:
        """Get hall of fame data from storage."""
        return self.storage.get_document('repo_stats', 'hall_of_fame')
    
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