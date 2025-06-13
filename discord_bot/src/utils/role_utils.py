PR_THRESHOLDS = {
    "⚪ Member (0 PRs)": 0,
    "◯ Contributor (1-2 PRs)": 1,
    "⚫ Developer (3-5 PRs)": 3,
    "◼️ Advanced (6-10 PRs)": 6,
    "⬛ Expert (11-20 PRs)": 11,
    "🔘 Master (21+ PRs)": 21
}

ISSUE_THRESHOLDS = {
    "🟣 Reporter (1-5 Issues)": 1,
    "🔵 Tracker (6-15 Issues)": 6,
    "🟢 Analyst (16-30 Issues)": 16,
    "🟡 Expert (31-50 Issues)": 31,
    "🟠 Specialist (51+ Issues)": 51
}

COMMIT_THRESHOLDS = {
    "⚫ Committer (10-50 Commits)": 10,
    "⬛ Active (51-150 Commits)": 51,
    "◼️ Developer (151-300 Commits)": 151,
    "🖤 Expert (301-500 Commits)": 301,
    "⚡ Master (501+ Commits)": 501
}

# Medal roles for all-time top 3 PR contributors
MEDAL_ROLES = ["🥇 PR Champion", "🥈 PR Runner-up", "🥉 PR Bronze"]

# Add role descriptions with thresholds
PR_DESCRIPTIONS = {
    "⚪ Member (0 PRs)": "0 approved PRs",
    "◯ Contributor (1-2 PRs)": "1-2 approved PRs", 
    "⚫ Developer (3-5 PRs)": "3-5 approved PRs",
    "◼️ Advanced (6-10 PRs)": "6-10 approved PRs",
    "⬛ Expert (11-20 PRs)": "11-20 approved PRs",
    "🔘 Master (21+ PRs)": "21+ approved PRs"
}

ISSUE_DESCRIPTIONS = {
    "🟣 Reporter (1-5 Issues)": "1-5 Issues opened",
    "🔵 Tracker (6-15 Issues)": "6-15 Issues opened",
    "🟢 Analyst (16-30 Issues)": "16-30 Issues opened",
    "🟡 Expert (31-50 Issues)": "31-50 Issues opened",
    "🟠 Specialist (51+ Issues)": "51+ Issues opened"
}

COMMIT_DESCRIPTIONS = {
    "⚫ Committer (10-50 Commits)": "10-50 commits",
    "⬛ Active (51-150 Commits)": "51-150 commits", 
    "◼️ Developer (151-300 Commits)": "151-300 commits",
    "🖤 Expert (301-500 Commits)": "301-500 commits",
    "⚡ Master (501+ Commits)": "501+ commits"
}

def determine_role(pr_count, issues_count, commits_count):
    # Determine PR role
    pr_role = "⚪ Member (General)"
    for role, threshold in PR_THRESHOLDS.items():
        if pr_count >= threshold:
            pr_role = role

    # Determine issue role
    issue_role = None
    for role, threshold in ISSUE_THRESHOLDS.items():
        if issues_count >= threshold:
            issue_role = role

    # Determine commit role
    commit_role = None
    for role, threshold in COMMIT_THRESHOLDS.items():
        if commits_count >= threshold:
            commit_role = role

    # Return the highest role in each category
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