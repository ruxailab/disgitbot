"""
Core Interfaces

Abstract base classes for dependency injection and loose coupling.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, List

class IStorageService(ABC):
    """Interface for data storage services."""
    
    @abstractmethod
    def get_document(self, collection: str, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a document from storage."""
        pass
    
    @abstractmethod
    def set_document(self, collection: str, document_id: str, data: Dict[str, Any], merge: bool = False) -> bool:
        """Set a document in storage."""
        pass
    
    @abstractmethod
    def update_document(self, collection: str, document_id: str, data: Dict[str, Any]) -> bool:
        """Update a document in storage."""
        pass
    
    @abstractmethod
    def query_collection(self, collection: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Query a collection with optional filters."""
        pass

class IDiscordService(ABC):
    """Interface for Discord operations."""
    
    @abstractmethod
    async def update_roles(self, user_mappings: Dict[str, str], contributions: Dict[str, Any]) -> bool:
        """Update user roles based on contributions."""
        pass
    
    @abstractmethod
    async def update_channels(self, metrics: Dict[str, Any]) -> bool:
        """Update channel names with metrics."""
        pass
    
    @abstractmethod
    async def send_notification(self, channel_id: str, message: str) -> bool:
        """Send a notification message."""
        pass

class IRoleService(ABC):
    """Interface for role determination and management."""
    
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

class IDataProcessor(ABC):
    """Interface for data processing operations."""
    
    @abstractmethod
    def process_raw_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process raw data into structured format."""
        pass
    
    @abstractmethod
    def calculate_metrics(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate metrics from processed data."""
        pass
    
    @abstractmethod
    def generate_analytics(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate analytics from processed data."""
        pass

class IGitHubService(ABC):
    """Interface for GitHub API operations."""
    
    @abstractmethod
    def fetch_repository_data(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetch repository data from GitHub."""
        pass
    
    @abstractmethod
    def fetch_contributors(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetch contributors for a repository."""
        pass 