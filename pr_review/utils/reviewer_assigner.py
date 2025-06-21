#!/usr/bin/env python3
"""
Reviewer Assigner for automatically assigning reviewers to pull requests.
"""

import json
import random
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ReviewerAssigner:
    """Automatically assigns reviewers to pull requests based on expertise and availability."""
    
    def __init__(self, config_path: str = None):
        """Initialize the reviewer assigner with configuration."""
        self.config_path = config_path or "data/reviewers_config.json"
        self.reviewers_config = self._load_reviewers_config()
        
    def _load_reviewers_config(self) -> Dict[str, Any]:
        """Load reviewer configuration."""
        default_config = {
            "reviewers": {
                "marcgc21": {
                    "name": "Marc García",
                    "expertise": ["frontend", "ui/ux", "vue", "javascript", "user-testing"],
                    "max_concurrent_reviews": 3,
                    "availability": "high",
                    "timezone": "Europe/Madrid",
                    "role": "maintainer"
                },
                "xemyst": {
                    "name": "Xemyst",
                    "expertise": ["backend", "python", "api", "database", "security"],
                    "max_concurrent_reviews": 2,
                    "availability": "medium",
                    "timezone": "UTC",
                    "role": "contributor"
                },
                "KarinePistili": {
                    "name": "Karine Pistili",
                    "expertise": ["accessibility", "testing", "documentation", "user-testing"],
                    "max_concurrent_reviews": 2,
                    "availability": "high",
                    "timezone": "America/Sao_Paulo",
                    "role": "contributor"
                },
                "hvini": {
                    "name": "Hvini",
                    "expertise": ["backend", "python", "performance", "ci/cd"],
                    "max_concurrent_reviews": 2,
                    "availability": "medium",
                    "timezone": "America/Sao_Paulo",
                    "role": "contributor"
                },
                "sergiobeltranguerrero": {
                    "name": "Sergio Beltrán",
                    "expertise": ["frontend", "backend", "full-stack", "architecture"],
                    "max_concurrent_reviews": 3,
                    "availability": "high",
                    "timezone": "Europe/Madrid",
                    "role": "maintainer"
                }
            },
            "assignment_rules": {
                "min_reviewers": 1,
                "max_reviewers": 2,
                "require_maintainer_for_high_risk": True,
                "expertise_match_weight": 0.4,
                "availability_weight": 0.3,
                "workload_weight": 0.3
            }
        }
        
        # Try to load custom config if file exists
        if Path(self.config_path).exists():
            try:
                with open(self.config_path, 'r') as f:
                    custom_config = json.load(f)
                    # Merge configs
                    default_config.update(custom_config)
                    logger.info(f"Loaded reviewer config from {self.config_path}")
            except Exception as e:
                logger.warning(f"Failed to load reviewer config: {e}")
        
        return default_config
    
    def assign_reviewers(self, pr_data: Dict[str, Any], repo: str = None) -> Dict[str, Any]:
        """Assign reviewers to a pull request."""
        try:
            # Extract PR information
            author = pr_data.get("user", {}).get("login", "")
            title = pr_data.get("title", "").lower()
            body = pr_data.get("body", "").lower() if pr_data.get("body") else ""
            diff = pr_data.get("diff", "")
            metrics = pr_data.get("metrics", {})
            
            # Determine PR characteristics
            pr_characteristics = self._analyze_pr_characteristics(title, body, diff, metrics)
            
            # Get available reviewers (exclude PR author)
            available_reviewers = {
                username: config for username, config in self.reviewers_config["reviewers"].items()
                if username != author
            }
            
            if not available_reviewers:
                logger.warning("No available reviewers found")
                return {"reviewers": [], "reasoning": "No available reviewers found"}
            
            # Score reviewers based on expertise match and availability
            reviewer_scores = self._score_reviewers(available_reviewers, pr_characteristics)
            
            # Select reviewers based on assignment rules
            selected_reviewers = self._select_reviewers(reviewer_scores, pr_characteristics)
            
            # Format response with detailed reviewer info
            reviewers_info = []
            for username in selected_reviewers:
                reviewer_config = self.reviewers_config["reviewers"].get(username, {})
                reviewers_info.append({
                    "username": username,
                    "name": reviewer_config.get("name", username),
                    "expertise": ", ".join(reviewer_config.get("expertise", [])),
                    "score": reviewer_scores.get(username, 0.0)
                })
            
            result = {
                "reviewers": reviewers_info,
                "reasoning": f"Selected based on expertise match and availability for {repo or 'repository'}",
                "characteristics": pr_characteristics
            }
            
            logger.info(f"Assigned reviewers: {[r['username'] for r in reviewers_info]}")
            return result
            
        except Exception as e:
            logger.error(f"Error assigning reviewers: {e}")
            return {"reviewers": [], "reasoning": f"Error: {str(e)}"}
    
    def _analyze_pr_characteristics(self, title: str, body: str, diff: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze PR characteristics to determine required expertise."""
        characteristics = {
            "risk_level": metrics.get("risk_level", "LOW"),
            "size": "small",
            "expertise_areas": [],
            "requires_security_review": False,
            "requires_accessibility_review": False,
            "is_breaking_change": False
        }
        
        # Determine size
        total_changes = metrics.get("total_changes", 0)
        if total_changes > 500:
            characteristics["size"] = "large"
        elif total_changes > 100:
            characteristics["size"] = "medium"
        
        # Analyze content for expertise areas
        content = f"{title} {body}".lower()
        
        expertise_keywords = {
            "frontend": ["ui", "ux", "css", "html", "vue", "react", "javascript", "typescript"],
            "backend": ["api", "server", "database", "python", "java", "go"],
            "testing": ["test", "testing", "spec", "coverage", "unit", "integration"],
            "security": ["security", "auth", "vulnerability", "encryption", "token"],
            "accessibility": ["accessibility", "a11y", "wcag", "aria", "screen reader"],
            "performance": ["performance", "optimize", "speed", "memory", "cpu"],
            "documentation": ["doc", "readme", "guide", "tutorial"],
            "ci/cd": ["ci", "cd", "pipeline", "workflow", "deploy", "docker"],
            "user-testing": ["user testing", "usability", "user experience", "evaluation"]
        }
        
        for area, keywords in expertise_keywords.items():
            if any(keyword in content for keyword in keywords):
                characteristics["expertise_areas"].append(area)
        
        # Check for special requirements
        if any(keyword in content for keyword in ["security", "auth", "vulnerability"]):
            characteristics["requires_security_review"] = True
        
        if any(keyword in content for keyword in ["accessibility", "a11y", "wcag"]):
            characteristics["requires_accessibility_review"] = True
        
        if any(keyword in content for keyword in ["breaking", "breaking change", "major"]):
            characteristics["is_breaking_change"] = True
        
        # Analyze changed files
        if diff:
            files_changed = self._extract_changed_files(diff)
            for file_path in files_changed:
                if any(ext in file_path for ext in [".vue", ".js", ".ts", ".css", ".html"]):
                    if "frontend" not in characteristics["expertise_areas"]:
                        characteristics["expertise_areas"].append("frontend")
                elif any(ext in file_path for ext in [".py", ".java", ".go", ".php"]):
                    if "backend" not in characteristics["expertise_areas"]:
                        characteristics["expertise_areas"].append("backend")
                elif "test" in file_path.lower():
                    if "testing" not in characteristics["expertise_areas"]:
                        characteristics["expertise_areas"].append("testing")
        
        return characteristics
    
    def _extract_changed_files(self, diff: str) -> List[str]:
        """Extract list of changed files from diff."""
        if not diff:
            return []
        
        files = []
        for line in diff.split('\n'):
            if line.startswith('diff --git'):
                parts = line.split(' ')
                if len(parts) >= 4:
                    file_path = parts[3][2:]  # Remove 'b/' prefix
                    files.append(file_path)
        
        return files
    
    def _score_reviewers(self, reviewers: Dict[str, Any], characteristics: Dict[str, Any]) -> Dict[str, float]:
        """Score reviewers based on expertise match and availability."""
        scores = {}
        rules = self.reviewers_config["assignment_rules"]
        
        for username, config in reviewers.items():
            score = 0
            
            # Expertise match score
            expertise_score = 0
            reviewer_expertise = config.get("expertise", [])
            required_areas = characteristics.get("expertise_areas", [])
            
            if required_areas:
                matches = len(set(reviewer_expertise) & set(required_areas))
                expertise_score = matches / len(required_areas)
            else:
                # If no specific expertise required, give base score
                expertise_score = 0.5
            
            # Availability score
            availability = config.get("availability", "medium")
            availability_scores = {"high": 1.0, "medium": 0.7, "low": 0.3}
            availability_score = availability_scores.get(availability, 0.5)
            
            # Workload score (simplified - in real implementation, check current PRs)
            max_reviews = config.get("max_concurrent_reviews", 2)
            workload_score = 1.0  # Assume not overloaded for now
            
            # Calculate weighted score
            score = (
                expertise_score * rules["expertise_match_weight"] +
                availability_score * rules["availability_weight"] +
                workload_score * rules["workload_weight"]
            )
            
            # Bonus for maintainers on high-risk PRs
            if (characteristics["risk_level"] == "HIGH" and 
                config.get("role") == "maintainer"):
                score += 0.2
            
            # Bonus for security expertise on security PRs
            if (characteristics.get("requires_security_review") and 
                "security" in reviewer_expertise):
                score += 0.3
            
            # Bonus for accessibility expertise on accessibility PRs
            if (characteristics.get("requires_accessibility_review") and 
                "accessibility" in reviewer_expertise):
                score += 0.3
            
            scores[username] = score
        
        return scores
    
    def _select_reviewers(self, scores: Dict[str, float], characteristics: Dict[str, Any]) -> List[str]:
        """Select reviewers based on scores and assignment rules."""
        rules = self.reviewers_config["assignment_rules"]
        
        # Sort reviewers by score
        sorted_reviewers = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        selected = []
        min_reviewers = rules.get("min_reviewers", 1)
        max_reviewers = rules.get("max_reviewers", 2)
        
        # Ensure we have at least one maintainer for high-risk PRs
        if (characteristics["risk_level"] == "HIGH" and 
            rules.get("require_maintainer_for_high_risk", True)):
            
            maintainers = [
                username for username, config in self.reviewers_config["reviewers"].items()
                if config.get("role") == "maintainer" and username in scores
            ]
            
            if maintainers:
                # Select highest-scored maintainer
                maintainer_scores = [(u, scores[u]) for u in maintainers]
                best_maintainer = max(maintainer_scores, key=lambda x: x[1])[0]
                selected.append(best_maintainer)
        
        # Add additional reviewers up to max
        for username, score in sorted_reviewers:
            if len(selected) >= max_reviewers:
                break
            
            if username not in selected and score > 0.3:  # Minimum score threshold
                selected.append(username)
        
        # Ensure minimum reviewers
        if len(selected) < min_reviewers:
            for username, score in sorted_reviewers:
                if len(selected) >= min_reviewers:
                    break
                if username not in selected:
                    selected.append(username)
        
        return selected
    
    def get_reviewer_workload(self, username: str) -> Dict[str, Any]:
        """Get current workload for a reviewer (placeholder for real implementation)."""
        # In a real implementation, this would query GitHub API for current review requests
        return {
            "current_reviews": 0,
            "max_reviews": self.reviewers_config["reviewers"].get(username, {}).get("max_concurrent_reviews", 2),
            "availability": self.reviewers_config["reviewers"].get(username, {}).get("availability", "medium")
        }
    
    def add_reviewer(self, username: str, config: Dict[str, Any]):
        """Add a new reviewer to the configuration."""
        self.reviewers_config["reviewers"][username] = config
        logger.info(f"Added reviewer: {username}")
    
    def update_reviewer_availability(self, username: str, availability: str):
        """Update reviewer availability."""
        if username in self.reviewers_config["reviewers"]:
            self.reviewers_config["reviewers"][username]["availability"] = availability
            logger.info(f"Updated availability for {username}: {availability}")
    
    def save_config(self):
        """Save current configuration to file."""
        try:
            # Ensure directory exists
            Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                json.dump(self.reviewers_config, f, indent=2)
            
            logger.info(f"Saved reviewer config to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save reviewer config: {e}") 