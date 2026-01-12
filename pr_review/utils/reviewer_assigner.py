#!/usr/bin/env python3
"""
Reviewer Assigner for automatically assigning reviewers to pull requests.
"""

import random
import logging
import time
from typing import List, Dict, Any, Optional
from shared.firestore import get_document, set_document

logger = logging.getLogger(__name__)

class ReviewerAssigner:
    """Automatically assigns reviewers to pull requests using random selection."""
    
    def __init__(self, github_org: Optional[str] = None):
        """Initialize the reviewer assigner with Firestore configuration."""
        self.github_org = github_org
        self.reviewers = self._load_reviewers()
        
    def _load_reviewers(self) -> List[str]:
        """Load reviewer pool from Firestore configuration."""
        try:
            logger.info(f"REVIEWER DEBUG: Attempting to load reviewers for org: {self.github_org}")
            reviewer_data = get_document('pr_config', 'reviewers', github_org=self.github_org)
            
            if reviewer_data and 'reviewers' in reviewer_data:
                reviewers = reviewer_data['reviewers']
                logger.info(f"REVIEWER DEBUG: Successfully loaded {len(reviewers)} reviewers")
                return reviewers
            
            logger.error(f"REVIEWER DEBUG: No reviewer configuration found for org {self.github_org} in pr_config/reviewers")
            logger.error(f"REVIEWER DEBUG: Retrieved data: {reviewer_data}")
            return []
              
        except Exception as e:
            logger.error(f"REVIEWER DEBUG: Failed to load reviewers from Firestore: {e}")
            return []
    
    def assign_reviewers(self, pr_data: Dict[str, Any], repo: Optional[str] = None) -> Dict[str, Any]:
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
        """Save the current reviewer configuration to Firestore."""
        try:
            reviewer_data = {
                'reviewers': self.reviewers,
                'count': len(self.reviewers),
                'last_updated': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
            }
            success = set_document('pr_config', 'reviewers', reviewer_data, github_org=self.github_org)
            if success:
                logger.info(f"Saved {len(self.reviewers)} reviewers to Firestore")
            else:
                logger.error("Failed to save reviewer config to Firestore")
        except Exception as e:
            logger.error(f"Failed to save config: {e}") 