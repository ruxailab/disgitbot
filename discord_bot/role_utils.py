PR_THRESHOLDS = {
    "⚪ Member (General)": 0,
    "🟣 Entry": 1,
    "🔵 Intermediate": 4,
    "🔵 Proficient": 7,
    "🟢 Advanced": 10,
    "🟡 Expert": 20,
    "🟠 Master": 40,
    "🔴 Grandmaster": 60
}

ISSUE_THRESHOLDS = {
    "📝 Bug Reporter": 1,
    "🔍 Debugger": 3,
    "🕵️‍♂️ Investigator": 7
}

COMMIT_THRESHOLDS = {
    "🔧 Committer": 10,
    "🚀 Commit Machine": 30
}

# Add role descriptions with thresholds
PR_DESCRIPTIONS = {
    "⚪ Member (General)": "0 approved PRs",
    "🟣 Entry": "1-3 approved PRs",
    "🔵 Intermediate": "4-6 approved PRs",
    "🔵 Proficient": "7-10 approved PRs",
    "🟢 Advanced": "11-20 approved PRs",
    "🟡 Expert": "21-40 approved PRs",
    "🟠 Master": "41-60 approved PRs",
    "🔴 Grandmaster": "61-80 approved PRs"
}

ISSUE_DESCRIPTIONS = {
    "📝 Bug Reporter": "1-3 Issues opened",
    "🔍 Debugger": "4-6 Issues",
    "🕵️‍♂️ Investigator": "7-9 Issues"
}

COMMIT_DESCRIPTIONS = {
    "🔧 Committer": "10-29 commits",
    "🚀 Commit Machine": "30+ commits"
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