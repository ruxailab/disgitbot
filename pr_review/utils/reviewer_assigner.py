#!/usr/bin/env python3
"""
Reviewer Assigner for automatically assigning reviewers to pull requests.
"""

import json
import random
import logging
from typing import List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class ReviewerAssigner:
    """Automatically assigns reviewers to pull requests using random selection."""
    
    def __init__(self, config_path: str | None = None):
        """Initialize the reviewer assigner with configuration."""
        self.config_path = config_path if config_path is not None else "data/reviewers_config.json"
        self.reviewers = self._load_reviewers()
        
    def _load_reviewers(self) -> List[str]:
        """Load reviewer pool from configuration."""
        try:
            config_file = Path(self.config_path)
            if not config_file.exists():
                logger.warning(f"Config file {self.config_path} not found, using default reviewers")
                return ["marcgc21", "xemyst", "KarinePistili", "hvini", "sergiobeltranguerrero", "leoruas", "JulioManoel"]
            
            with open(config_file, 'r') as f:
                config = json.load(f)
                
            return config.get('reviewers', [])
            
        except Exception as e:
            logger.error(f"Failed to load reviewers config: {e}")
            return ["marcgc21", "xemyst", "KarinePistili", "hvini", "sergiobeltranguerrero", "leoruas", "JulioManoel"]
    
    def assign_reviewers(self, pr_data: Dict[str, Any], repo: str | None = None) -> Dict[str, Any]:
        """
        Assign reviewers to a pull request using random selection.
        
        Args:
            pr_data: Pull request data from GitHub API
            repo: Repository name (unused in simplified version)
            
        Returns:
            Dictionary containing assigned reviewers
        """
        try:
            if not self.reviewers:
                logger.warning("No reviewers available")
                return {"reviewers": [], "assignment_method": "none"}
            
            # Randomly select 1-2 reviewers
            num_reviewers = random.randint(1, min(2, len(self.reviewers)))
            selected_reviewers = random.sample(self.reviewers, num_reviewers)
            
            # Format response
            reviewers_data = []
            for username in selected_reviewers:
                reviewers_data.append({
                    "username": username,
                    "expertise": "General"
                })
            
            result = {
                "reviewers": reviewers_data,
                "assignment_method": "random",
                "total_available": len(self.reviewers)
            }
            
            logger.info(f"Assigned {len(selected_reviewers)} reviewers: {selected_reviewers}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to assign reviewers: {e}")
            return {"reviewers": [], "assignment_method": "error", "error": str(e)}
    
    def get_available_reviewers(self) -> List[str]:
        """Get list of available reviewers."""
        return self.reviewers.copy()
    
    def add_reviewer(self, username: str):
        """Add a reviewer to the pool."""
        if username not in self.reviewers:
            self.reviewers.append(username)
            self.save_config()
            logger.info(f"Added reviewer: {username}")
    
    def remove_reviewer(self, username: str):
        """Remove a reviewer from the pool."""
        if username in self.reviewers:
            self.reviewers.remove(username)
            self.save_config()
            logger.info(f"Removed reviewer: {username}")
    
    def save_config(self):
        """Save the current reviewer configuration."""
        try:
            config = {"reviewers": self.reviewers}
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info(f"Saved reviewer config to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}") 