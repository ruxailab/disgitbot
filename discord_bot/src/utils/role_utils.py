# Role thresholds and mappings
PR_THRESHOLDS = {
    "Beginner (1-5 PRs)": 1,
    "Contributor (6-15 PRs)": 6,
    "Analyst (16-30 PRs)": 16,
    "Expert (31-50 PRs)": 31,
    "Master (51+ PRs)": 51
}

ISSUE_THRESHOLDS = {
    "Beginner (1-5 Issues)": 1,
    "Contributor (6-15 Issues)": 6,
    "Analyst (16-30 Issues)": 16,
    "Expert (31-50 Issues)": 31,
    "Master (51+ Issues)": 51
}

COMMIT_THRESHOLDS = {
    "Beginner (1-50 Commits)": 1,
    "Contributor (51-100 Commits)": 51,
    "Analyst (101-250 Commits)": 101,
    "Expert (251-500 Commits)": 251,
    "Master (501+ Commits)": 501
}

# Medal roles for top 3 all-time PR contributors
MEDAL_ROLES = [
    "PR Champion",
    "PR Runner-up", 
    "PR Bronze"
]

# Role descriptions
PR_DESCRIPTIONS = {
    "Beginner (1-5 PRs)": "1-5 PRs opened",
    "Contributor (6-15 PRs)": "6-15 PRs opened",
    "Analyst (16-30 PRs)": "16-30 PRs opened",
    "Expert (31-50 PRs)": "31-50 PRs opened",
    "Master (51+ PRs)": "51+ PRs opened"
}

ISSUE_DESCRIPTIONS = {
    "Beginner (1-5 Issues)": "1-5 Issues opened",
    "Contributor (6-15 Issues)": "6-15 Issues opened",
    "Analyst (16-30 Issues)": "16-30 Issues opened",
    "Expert (31-50 Issues)": "31-50 Issues opened",
    "Master (51+ Issues)": "51+ Issues opened"
}

COMMIT_DESCRIPTIONS = {
    "Beginner (1-50 Commits)": "1-50 commits",
    "Contributor (51-100 Commits)": "51-100 commits",
    "Analyst (101-250 Commits)": "101-250 commits",
    "Expert (251-500 Commits)": "251-500 commits",
    "Master (501+ Commits)": "501+ commits"
}

def determine_role(pr_count, issues_count, commits_count):
    """
    Determine the role for a user based on their contribution counts.
    
    Args:
        pr_count: Number of pull requests
        issues_count: Number of issues
        commits_count: Number of commits
        
    Returns:
        tuple: (pr_role, issue_role, commit_role)
    """
    pr_role = None
    issue_role = None
    commit_role = None
    
    # Determine PR role
    for role, threshold in reversed(PR_THRESHOLDS.items()):
        if pr_count >= threshold:
            pr_role = role
            break
    
    # Determine issue role
    for role, threshold in reversed(ISSUE_THRESHOLDS.items()):
        if issues_count >= threshold:
            issue_role = role
            break
    
    # Determine commit role
    for role, threshold in reversed(COMMIT_THRESHOLDS.items()):
        if commits_count >= threshold:
            commit_role = role
            break
    
    return pr_role, issue_role, commit_role

def get_next_role(current_role, stats_type):
    """
    Determine the next role based on the current role and stats type.
    
    Args:
        current_role: The current role of the user
        stats_type: 'pr', 'issue', or 'commit'
        
    Returns:
        A string describing the next role, or a message if the user has reached the highest level
    """
    if stats_type == "pr":
        thresholds = PR_THRESHOLDS
        descriptions = PR_DESCRIPTIONS
    elif stats_type == "issue":
        thresholds = ISSUE_THRESHOLDS
        descriptions = ISSUE_DESCRIPTIONS
    elif stats_type == "commit":
        thresholds = COMMIT_THRESHOLDS
        descriptions = COMMIT_DESCRIPTIONS
    else:
        return "Unknown"
    
    # Handle case where current_role is None or not in thresholds
    if current_role == "None" or current_role is None:
        # Get the first role for this stat type
        if thresholds:
            first_role = list(thresholds.keys())[0]
            return f"@{first_role} ({descriptions[first_role]})"
        return "Unknown"
    
    # Convert thresholds to ordered list of (role, threshold) pairs
    role_list = list(thresholds.items())
    
    # Find current role in the list
    for i, (role, _) in enumerate(role_list):
        if role == current_role:
            # Check if this is the highest role
            if i == len(role_list) - 1:
                return "You've reached the highest level!"
            
            # Return the next role with its description
            next_role = role_list[i + 1][0]
            return f"@{next_role} ({descriptions[next_role]})"
    
    return "Unknown"

def get_medal_assignments(hall_of_fame_data):
    """
    Determine medal role assignments for all-time top 3 PR contributors.
    
    Args:
        hall_of_fame_data: Hall of fame data from Firestore
        
    Returns:
        Dictionary mapping GitHub usernames to medal role names
    """
    medal_assignments = {}
    
    if not hall_of_fame_data or not hall_of_fame_data.get('pr', {}).get('all_time'):
        return medal_assignments
    
    top_3_prs = hall_of_fame_data['pr']['all_time'][:3]  # Get top 3
    
    for i, contributor in enumerate(top_3_prs):
        username = contributor.get('username')
        if username and i < len(MEDAL_ROLES):
            medal_assignments[username] = MEDAL_ROLES[i]
    
    return medal_assignments 