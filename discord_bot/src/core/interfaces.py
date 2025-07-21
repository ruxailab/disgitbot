"""
Core Interfaces

Only necessary abstractions for role logic configuration.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, List

class IRoleService(ABC):
    """Interface for role determination logic - allows different role strategies."""
    
    @abstractmethod
    def determine_roles(self, pr_count: int, issues_count: int, commits_count: int) -> Tuple[str, str, str]:
        """Determine roles based on contribution counts."""
        pass
    
    @abstractmethod
    def get_medal_assignments(self, hall_of_fame_data: Dict[str, Any]) -> Dict[str, str]:
        """Get medal role assignments for top contributors."""
        pass
    
    @abstractmethod
    def get_all_role_names(self) -> List[str]:
        """Get all possible role names for creation."""
        pass
    
    @abstractmethod
    def get_role_color(self, role_name: str) -> Optional[Tuple[int, int, int]]:
        """Get RGB color for a specific role."""
        pass 