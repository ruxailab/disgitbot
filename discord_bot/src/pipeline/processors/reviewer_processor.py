"""
Reviewer Processing Functions

Functions for processing contributor data to generate reviewer pools.
"""

import time
from typing import Dict, Any, List, Optional

from shared.firestore import get_mt_client


def generate_reviewer_pool(
    all_contributions: Dict[str, Any],
    max_reviewers: int = 7,
    github_org: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate reviewer pool with separate top contributor and manual pools."""
    print("Generating reviewer pool from top contributors...")

    if not all_contributions:
        return {}

    if not github_org:
        raise ValueError("github_org is required to load reviewer config")

    existing_config = (
        get_mt_client().get_org_document(github_org, 'pr_config', 'reviewers') or {}
    )
    manual_reviewers = existing_config.get('manual_reviewers', [])

    # Get contributors sorted by PR count (all-time)
    top_contributors = sorted(
        all_contributions.items(),
        key=lambda x: x[1].get('stats', {}).get('pr', {}).get('all_time', x[1].get('pr_count', 0)),
        reverse=True,
    )[:max_reviewers]

    # Create top contributor reviewer list
    top_contributor_reviewers: List[str] = []
    for contributor, data in top_contributors:
        pr_count = data.get('stats', {}).get('pr', {}).get('all_time', data.get('pr_count', 0))
        if pr_count > 0:  # Only include contributors with at least 1 PR
            top_contributor_reviewers.append(contributor)

    # Combine both pools for total reviewer list
    all_reviewers = list(set(top_contributor_reviewers + manual_reviewers))

    return {
        'reviewers': all_reviewers,
        'top_contributor_reviewers': top_contributor_reviewers,
        'manual_reviewers': manual_reviewers,
        'count': len(all_reviewers),
        'selection_criteria': 'top_pr_contributors_plus_manual',
        'last_updated': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
        'generated_from_total': len(all_contributions),
    }

def get_contributor_summary(all_contributions: Dict[str, Any]) -> Dict[str, Any]:
    """Get summary of all contributors for reviewer selection context."""
    if not all_contributions:
        return {}
    
    contributors_by_prs = []
    for username, data in all_contributions.items():
        pr_count = data.get('stats', {}).get('pr', {}).get('all_time', data.get('pr_count', 0))
        if pr_count > 0:
            contributors_by_prs.append({
                'username': username,
                'pr_count': pr_count,
                'issues_count': data.get('stats', {}).get('issue', {}).get('all_time', data.get('issues_count', 0)),
                'commits_count': data.get('stats', {}).get('commit', {}).get('all_time', data.get('commits_count', 0))
            })
    
    # Sort by PR count
    contributors_by_prs.sort(key=lambda x: x['pr_count'], reverse=True)
    
    return {
        'top_contributors': contributors_by_prs[:15],
        'total_contributors': len(contributors_by_prs),
        'criteria': 'sorted_by_pr_count'
    } 
