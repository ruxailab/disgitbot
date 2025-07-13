#!/usr/bin/env python3
"""
Main PR Review Automation System
"""

import os
import sys
import logging
from typing import Dict, Any, List
import json

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import GITHUB_TOKEN, GOOGLE_API_KEY, REPO_OWNER
from utils.github_client import GitHubClient
from utils.metrics_calculator import MetricsCalculator
from utils.ai_pr_labeler import AIPRLabeler
from utils.reviewer_assigner import ReviewerAssigner


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PRReviewSystem:
    """Main PR Review Automation System"""
    
    def __init__(self):
        """Initialize the PR review system"""
        try:
            # Initialize components
            self.github_client = GitHubClient()
            self.metrics_calculator = MetricsCalculator()
            self.ai_labeler = AIPRLabeler()
            self.reviewer_assigner = ReviewerAssigner()

            
            logger.info("PR Review System initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize PR Review System: {e}")
            raise
    
    def process_pull_request(self, repo: str, pr_number: int, experience_level: str = "intermediate") -> Dict[str, Any]:
        """
        Process a pull request with full automation pipeline
        
        Args:
            repo: Repository name in format "owner/repo"
            pr_number: Pull request number
            experience_level: Developer experience level for AI review
            
        Returns:
            Processing results
        """
        try:
            logger.info(f"Processing PR #{pr_number} in {repo}")
            
            # Step 1: Get PR details and diff
            pr_details = self.github_client.get_pull_request_details(repo, pr_number)
            pr_diff = self.github_client.get_pull_request_diff(repo, pr_number)
            pr_files = self.github_client.get_pull_request_files(repo, pr_number)
            
            # Step 2: Calculate metrics
            logger.info("Calculating PR metrics...")
            metrics = self.metrics_calculator.calculate_pr_metrics(pr_diff, pr_files)
            
            # Step 3: AI-based label prediction
            logger.info("Predicting labels with AI...")
            pr_data = {
                'title': pr_details.get('title', ''),
                'body': pr_details.get('body', ''),
                'diff': pr_diff,
                'metrics': metrics
            }
            predicted_labels = self.ai_labeler.predict_labels(pr_data, repo)
            
            # Step 4: Assign reviewers
            logger.info("Assigning reviewers...")
            reviewer_assignments = self.reviewer_assigner.assign_reviewers(pr_data, repo)
            
            # Step 5: Skip AI review generation (not needed per mentor requirements)
            ai_review = {"summary": "AI review disabled - focusing on metrics and automation"}
            
            # Step 6: Apply labels to PR
            if predicted_labels:
                label_names = [label['name'] for label in predicted_labels if label['confidence'] >= 0.5]
                if label_names:
                    logger.info(f"Applying labels: {label_names}")
                    self.github_client.add_labels_to_pull_request(repo, pr_number, label_names)
            
            # Step 7: Request reviewers
            if reviewer_assignments.get('reviewers'):
                reviewers = [r['username'] for r in reviewer_assignments['reviewers']]
                logger.info(f"Requesting reviewers: {reviewers}")
                self.github_client.request_reviewers(repo, pr_number, reviewers)
            
            # Step 8: Post comprehensive comment
            comment_body = self._build_comprehensive_comment(
                metrics, predicted_labels, reviewer_assignments, ai_review
            )
            
            self.github_client.create_issue_comment(repo, pr_number, comment_body)
            
            # Return processing results
            results = {
                'pr_number': pr_number,
                'repository': repo,
                'metrics': metrics,
                'predicted_labels': predicted_labels,
                'reviewer_assignments': reviewer_assignments,
                'ai_review_summary': ai_review.get('summary', ''),
                'status': 'success'
            }
            
            logger.info(f"Successfully processed PR #{pr_number}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to process PR #{pr_number}: {e}")
            return {
                'pr_number': pr_number,
                'repository': repo,
                'status': 'error',
                'error': str(e)
            }
    
    def _build_comprehensive_comment(self, metrics: Dict, labels: List[Dict], reviewers: Dict, ai_review: Dict) -> str:
        """Build a focused comment with metrics and automation info"""
        
        comment = "# Automated PR Analysis\n\n"
        
        # Add metrics section
        comment += "## Code Metrics\n"
        comment += f"In this PR introducing {metrics.get('functions_added', 0)} more functions:\n\n"
        comment += f"- Cyclomatic complexity will increase by: {metrics.get('cyclomatic_complexity_added', 0)}\n"
        comment += f"- Line number will increase by: {metrics.get('lines_added', 0)}\n"
        comment += f"- Files changed: {metrics.get('files_changed', 0)}\n"
        comment += f"- Risk Level: {metrics.get('risk_level', 'UNKNOWN')}\n\n"
        
        # Risk factors (if any)
        if metrics.get('risk_factors'):
            comment += "**Risk Factors:**\n"
            for factor in metrics['risk_factors']:
                comment += f"- {factor}\n"
            comment += "\n"
        
        # Add labels section
        comment += "## Auto-Applied Labels\n"
        
        # AI-predicted labels
        if labels:
            for label in labels:
                confidence_percent = int(label["confidence"] * 100)
                comment += f"- {label['name']} ({confidence_percent}% confidence)\n"
            comment += "\n"
        
        # Add reviewers section
        comment += "## Auto-Assigned Reviewers\n"
        
        # Reviewer assignments
        if reviewers.get('reviewers'):
            for reviewer in reviewers['reviewers']:
                comment += f"- @{reviewer['username']} "
                comment += f"({reviewer.get('expertise', 'General')} expertise)\n"
            comment += "\n"
        
        comment += "---\n"
        comment += f"*Automated analysis by {REPO_OWNER.upper()} PR System*"
        
        return comment
    
    def update_repository_labels_cache(self, repo: str) -> Dict[str, Any]:
        """
        Update the repository labels cache for a specific repo
        
        Args:
            repo: Repository name in format "owner/repo"
            
        Returns:
            Cache update results
        """
        try:
            logger.info(f"Updating labels cache for {repo}")
            labels = self.ai_labeler.update_repository_labels_cache(repo)
            
            return {
                'repository': repo,
                'labels_count': len(labels),
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Failed to update labels cache for {repo}: {e}")
            return {
                'repository': repo,
                'status': 'error',
                'error': str(e)
            }

def main():
    """Main entry point for testing"""
    if len(sys.argv) < 3:
        print("Usage: python main.py <repo> <pr_number> [experience_level]")
        print(f"Example: python main.py {REPO_OWNER}/test-repo 123 intermediate")
        sys.exit(1)
    
    repo = sys.argv[1]
    pr_number = int(sys.argv[2])
    experience_level = sys.argv[3] if len(sys.argv) > 3 else "intermediate"
    
    # Initialize system
    system = PRReviewSystem()
    
    # Process the PR
    results = system.process_pull_request(repo, pr_number, experience_level)
    
    # Print results
    print("\n" + "="*50)
    print("PR PROCESSING RESULTS")
    print("="*50)
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main() 