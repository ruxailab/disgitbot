# Metrics Documentation

## Overview

This document provides comprehensive information about the metrics system implemented in the PR Review Automation and Discord Bot pipeline. The system tracks various code quality and contribution metrics across GitHub repositories.

## Current Metrics Implementation

### 1. PR (Pull Request) Metrics

**Data Collected:**
- Lines added/deleted
- Files changed
- Functions added
- Cyclomatic complexity increase
- Fan-In and Fan-Out coupling metrics
- Design principles analysis
- Risk level assessment
- Risk factors identification

**Risk Assessment Algorithm:**
```python
# Risk Level Calculation
risk_score = 0
risk_factors = []

# Large changes
if lines_added > 500:
    risk_score += 3
    risk_factors.append("Large addition (>500 lines)")

if files_changed > 15:
    risk_score += 2
    risk_factors.append("Many files changed (>15)")

# Complexity factors
if functions_added > 10:
    risk_score += 2
    risk_factors.append("Many new functions (>10)")

if cyclomatic_complexity > 50:
    risk_score += 3
    risk_factors.append("High complexity increase")

# Risk levels: LOW (0-2), MEDIUM (3-5), HIGH (6+)
```

**Design Principles Analysis:**
- **SOLID Principles Compliance**: Checks for Single Responsibility, Open/Closed, Interface Segregation, Dependency Inversion violations
- **God Classes Detection**: Identifies classes that are too large or have too many responsibilities
- **Long Functions**: Flags functions that exceed recommended length limits
- **Parameter Count**: Detects functions with excessive parameters
- **Tight Coupling**: Identifies direct instantiation and dependency issues
- **Magic Values**: Detects hardcoded numbers and strings that should be constants
- **Design Score**: Overall assessment (EXCELLENT, GOOD, FAIR, POOR)

**Fan-In and Fan-Out Metrics:**
- **Fan-Out**: Number of dependencies this module has on other modules
- **Fan-In**: Number of modules that depend on this module
- **Coupling Factor**: Fan-Out / (Fan-In + Fan-Out) - measures dependency direction
- **Imports Added**: Count of new import/include statements
- **Exports Added**: Count of new export/public declarations

**Output Example:**
```json
{
  "lines_added": 245,
  "lines_deleted": 12,
  "files_changed": 8,
  "functions_added": 3,
  "cyclomatic_complexity_added": 15,
  "fan_out": 8,
  "fan_in": 3,
  "coupling_factor": 0.73,
  "imports_added": 8,
  "exports_added": 3,
  "design_issues_found": 2,
  "design_score": "GOOD",
  "high_severity_issues": 0,
  "medium_severity_issues": 2,
  "low_severity_issues": 0,
  "issues": [
    {
      "principle": "Single Responsibility Principle",
      "description": "Function 'process_data' is too long (65 lines)",
      "code_snippet": "def process_data(self, data):\n    # Complex processing logic...",
      "suggestions": [
        "Break process_data into smaller, focused functions",
        "Extract complex logic into separate helper methods"
      ],
      "severity": "MEDIUM"
    }
  ],
  "risk_level": "MEDIUM",
  "risk_factors": ["Large addition (>200 lines)", "Medium coupling (8 dependencies)", "Design issues detected (2)"]
}
```

### 2. Contributor Metrics

**Individual Contributor Tracking:**
- Pull requests (daily, weekly, monthly, all-time)
- GitHub issues reported (daily, weekly, monthly, all-time)
- Commits (daily, weekly, monthly, all-time)
- Activity streaks and averages
- Rankings across all time periods

**Data Structure:**
```json
{
  "username": "contributor_name",
  "stats": {
    "pr": {
      "daily": 2,
      "weekly": 8,
      "monthly": 25,
      "all_time": 150,
      "current_streak": 3,
      "longest_streak": 12,
      "avg_per_day": 1.2
    },
    "issue": {
      "daily": 1,
      "weekly": 4,
      "monthly": 15,
      "all_time": 89
    },
    "commit": {
      "daily": 5,
      "weekly": 35,
      "monthly": 120,
      "all_time": 2500
    }
  },
  "rankings": {
    "pr": 3,
    "pr_daily": 1,
    "pr_weekly": 2,
    "pr_monthly": 3
  }
}
```

### 3. Repository Metrics

**Aggregate Repository Data:**
- Total stars, forks, contributors
- Combined PR, issue, and commit counts
- Repository health indicators
- Label distribution analysis

**Discord Integration:**
- Automated voice channel updates with live stats
- Channel names display real-time metrics
- Daily pipeline updates

### 4. Hall of Fame System

**Leaderboard Categories:**
- Pull Requests (all-time, monthly, weekly, daily)
- GitHub Issues Reported (all-time, monthly, weekly, daily)
- Commits (all-time, monthly, weekly, daily)

**Medal System:**
- PR Champion, PR Runner-up, PR Bronze roles
- Automatic role assignment based on all-time PR rankings
- Aesthetic themed roles with emojis and pastel colors

## Configuration

### 1. Firestore Collections

**Structure:**
```
repo_stats/
├── metrics              # Repository aggregate metrics
├── hall_of_fame         # Leaderboard data
├── analytics           # Processed analytics data
└── contributor_summary  # Top contributor rankings

discord/
└── {user_id}           # Individual user contribution data

pr_config/
└── reviewers           # PR reviewer pool configuration

repository_labels/
└── {repo_name}         # Repository-specific label data
```

### 2. Pipeline Configuration

**Data Flow:**
1. **Data Collection**: GitHub API calls for repositories, PRs, issues, commits
2. **Processing**: Raw data → structured contributions → rankings → analytics
3. **Storage**: Firestore collections updated with processed data
4. **Discord Updates**: Roles and channel names updated automatically

**Update Frequency:**
- Currently: Daily via GitHub Actions
- Configurable: Can be adjusted to any frequency (5-minute intervals supported)

### 3. Role Configuration

**Badge System:**
```python
# PR Roles (Flower theme, pink pastels)
"🌸 1+ PRs": 1,
"🌺 6+ PRs": 6,
"🌻 16+ PRs": 16,
"🌷 31+ PRs": 31,
"🌹 51+ PRs": 51

# Issue Roles (Plant theme, green pastels)  
"🍃 1+ GitHub Issues Reported": 1,
"🌿 6+ GitHub Issues Reported": 6,
"🌱 16+ GitHub Issues Reported": 16,
"🌾 31+ GitHub Issues Reported": 31,
"🍀 51+ GitHub Issues Reported": 51

# Commit Roles (Sky theme, blue/purple pastels)
"☁️ 1+ Commits": 1,
"🌊 51+ Commits": 51,
"🌈 101+ Commits": 101,
"🌙 251+ Commits": 251,
"⭐ 501+ Commits": 501
```