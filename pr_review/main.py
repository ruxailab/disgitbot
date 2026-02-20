#!/usr/bin/env python3
"""
Main PR Review Automation System
"""

import os
import sys
import logging
from typing import Dict, Any, List
import json
import asyncio
from pathlib import Path

# Add project root to sys.path to allow importing from 'shared'
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

try:
    # When run as a package (from pr_review.main import ...)
    from pr_review.config import GITHUB_TOKEN, GOOGLE_API_KEY, REPO_OWNER
    from pr_review.utils.github_client import GitHubClient
    from pr_review.utils.metrics_calculator import MetricsCalculator
    from pr_review.utils.ai_pr_labeler import AIPRLabeler
    from pr_review.utils.reviewer_assigner import ReviewerAssigner
    from pr_review.utils.design_formatter import format_design_analysis, format_metrics_summary
except ImportError:
    # When run standalone (python main.py)
    from config import GITHUB_TOKEN, GOOGLE_API_KEY, REPO_OWNER
    from utils.github_client import GitHubClient
    from utils.metrics_calculator import MetricsCalculator
    from utils.ai_pr_labeler import AIPRLabeler
    from utils.reviewer_assigner import ReviewerAssigner
    from utils.design_formatter import format_design_analysis, format_metrics_summary


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
            self.reviewer_assigner = None # Will be initialized per request

            
            logger.info("PR Review System initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize PR Review System: {e}")
            raise
    
    async def process_pull_request(self, repo: str, pr_number: int, experience_level: str = "intermediate") -> Dict[str, Any]:
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
            repo_owner = repo.split('/')[0] if '/' in repo else repo
            self.reviewer_assigner = ReviewerAssigner(github_org=repo_owner)
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
            
            # Prepare results
            results = {
                'pr_number': pr_number,
                'repository': repo,
                'metrics': metrics,
                'predicted_labels': predicted_labels,
                'reviewer_assignments': reviewer_assignments,
                'ai_review_summary': ai_review.get('summary', ''),
                'status': 'success'
            }
            
            # Send Discord notification
            try:
                # In CLI/Action mode, we await to ensure it's sent before process exits
                await self._send_discord_notification(results, comment_body)
            except Exception as e:
                logger.error(f"Failed to send Discord notification: {e}")
            
            logger.info(f"Successfully processed PR #{pr_number}")
            return results

        except Exception as e:
            logger.error(f"Failed to process PR #{pr_number}: {e}")
            import traceback
            traceback.print_exc()
            
            # Send notification for failure
            error_results = {
                'pr_number': pr_number,
                'repository': repo,
                'status': 'error',
                'error': str(e)
            }
            try:
                await self._send_discord_notification(error_results, None)
            except Exception:
                pass
                
            return error_results
    
    def _build_comprehensive_comment(self, metrics: Dict, labels: List[Dict], reviewers: Dict, ai_review: Dict) -> str:
        """Build clean, well-organized PR comment"""
        
        comment_parts = []
        
        # Metrics section - condensed into 2 lines
        comment_parts.append("## Metrics")
        comment_parts.append(format_metrics_summary(metrics))
        
        # Labels and Reviewers section - parallel structure
        assignment_parts = []
        
        if labels:
            label_names = []
            for label in labels:
                confidence = int(label["confidence"] * 100)
                if confidence >= 80:
                    label_names.append(label['name'])
                elif confidence >= 60:
                    label_names.append(f"{label['name']}*")
            if label_names:
                assignment_parts.append(f"**Labels**: {', '.join(label_names)}")
        
        if reviewers.get('reviewers'):
            reviewer_names = [r['username'] for r in reviewers['reviewers']]
            assignment_parts.append(f"**Reviewers**: {', '.join(reviewer_names)}")
        
        if assignment_parts:
            comment_parts.append("\n## Labels & Reviewers")
            comment_parts.extend(assignment_parts)
        
        # Design analysis at the end (harder to read stuff)
        if metrics.get('design_issues_found', 0) > 0:
            comment_parts.append("\n## Design")
            comment_parts.append(format_design_analysis(metrics))
        
        # Footer
        comment_parts.append(f"\nAutomated analysis · {REPO_OWNER}")
        
        return '\n'.join(comment_parts)
    
    async def _send_discord_notification(self, pr_data: Dict[str, Any], comment_body: str):
        """Send Discord notification for PR automation."""
        try:
            # Import here to avoid circular dependencies
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'discord_bot'))
            from src.services.notification_service import NotificationService
            
            async with NotificationService() as notification_service:
                await notification_service.send_pr_automation_notification(pr_data, comment_body)
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")


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
    
    # Process the pull request
    try:
        results = asyncio.run(system.process_pull_request(repo, pr_number, experience_level))
        
        # Exit with error code if processing failed
        if results.get('status') == 'error':
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    
    # Print results in clean format
    print("\n" + "="*60)
    print("PR ANALYSIS RESULTS")
    print("="*60)
    
    # Format metrics summary
    if 'metrics' in results:
        print(format_metrics_summary(results['metrics']))
        print(format_design_analysis(results['metrics']))
    
    # Print raw JSON for debugging (optional)
    print("\nDetailed Results:")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main() 