# GSoC 2025
> For deploying the Discord bot on your own server, refer to the [Discord Bot Setup Guide](discord_bot/README.md).

**Repository:** [disgitbot](https://github.com/ruxailab/disgitbot)

**Try the bot:** [RUXAILAB Discord Server](https://discord.gg/VAxzZxVV)

**Student:** Tianqin Meng  
**GitHub:** [@tqmsh](https://github.com/tqmsh)

**Organization:** Uramaki LAB

**Project:** [Integration of GitHub Actions with Discord Role Management](https://summerofcode.withgoogle.com/programs/2025/projects/gZbjuWuX)  
**Inspired by:** [ideas2025](https://github.com/ruxailab/gsoc/blob/main/ideas2025.md)

---

## Project Overview

The Disgitbot project aims to create a comprehensive Discord bot that integrates GitHub activity with Discord communities, providing real-time notifications, contribution analytics, and automated workflow management. The project focuses on enhancing community engagement and streamlining development workflows through intelligent automation.

---

## Timeline & Tasks

| Status     | Task                                             | Week      | Timeline           | Issue / Report Link                                                                                 | Images                | Implementation Diagram |
|------------|--------------------------------------------------|-----------|--------------------|-----------------------------------------------------------------------------------------------------|----------------------|------------------------|
| Completed  | Discord Bot for Real-Time GitHub Contribution Stats | 1-2       | May 27 - June 9, 2025     | [Issue #2](https://github.com/ruxailab/disgitbot/issues/2)                                          | [Discord Command](#image-1-discord-command) • [Data Pipeline](#image-2-data-collection) • [GitHub Actions](#image-3-github-actions) • [Raw Data](#image-4-raw-github-data) • [Data Processing](#image-5-data-processing) • [Data Storage](#image-6-data-storage) • [GitHub OAuth](#image-7-github-oauth) • [Cloud Logs](#image-8-cloud-logs) | [Data Pipeline Architecture](#diagram-1-contribution-stats-pipeline) |
| Completed  | Discord Role Auto-Update Bot                     | 3-4       | June 10 - June 23, 2025    | [Issue #9](https://github.com/ruxailab/disgitbot/issues/9)                                          | [Auto Role Update](#image-9-auto-role-update) • [Role Assignment](#image-10-role-assignment) | [Role Update Workflow](#diagram-2-role-update-system) |
| Completed  | AI-Assisted Pull Request Review Integration       | 5-7       | June 24 - July 14, 2025 | [Issue #3](https://github.com/ruxailab/disgitbot/issues/3)                                          | [PR Review](#image-11-pr-review) | [PR Review Automation](#diagram-3-pr-review-integration) |
| Completed  | Automatic Labelling for PRs Using PR Labeller    | 8         | July 15 - July 21, 2025   | [Issue #4](https://github.com/ruxailab/disgitbot/issues/4)                                          | [PR Labeller](#image-12-pr-labeller) | [AI Labeling System](#diagram-4-pr-labeling-workflow) |
| Completed  | Research Metric Tracking and Channel Creation     | 9-10      | July 22 - August 4, 2025 | [Issue #8](https://github.com/ruxailab/disgitbot/issues/8)                                          | [Metric Tracking](#image-15-metric-tracking) | [Metrics & Channels](#diagram-5-metrics-tracking-system) |
| Completed  | Contributor Analytics and Hall of Fame Visualization | 11-12        | July 29 - August 11, 2025 | [Issue #6](https://github.com/ruxailab/disgitbot/issues/6)                                          | [Analytics](#image-13-analytics) • [Hall of Fame](#image-14-hall-of-fame) | [Analytics & Visualization](#diagram-6-analytics-hall-of-fame) |

---

## Gallery

<div align="center">

<div id="image-1-discord-command">
<img src="images/Screenshot%202025-08-03%20at%207.53.39%E2%80%AFPM.png" width="600" alt="Discord Command"/>
<h4>Image 1: Discord Command</h4>
</div>

<div id="image-2-data-collection">
<img src="images/Screenshot%202025-08-03%20at%207.55.07%E2%80%AFPM.png" width="600" alt="Data Collection Pipeline"/>
<h4>Image 2: Data Collection Pipeline</h4>
</div>

<div id="image-3-github-actions">
<img src="images/Screenshot%202025-08-03%20at%207.53.51%E2%80%AFPM.png" width="600" alt="GitHub Actions Process"/>
<h4>Image 3: GitHub Actions Process</h4>
</div>

<div id="image-4-raw-github-data">
<img src="images/Screenshot%202025-08-03%20at%208.24.03%E2%80%AFPM.png" width="600" alt="Raw GitHub Data"/>
<h4>Image 4: Raw GitHub Data</h4>
</div>

<div id="image-5-data-processing">
<img src="images/Screenshot%202025-08-03%20at%208.24.14%E2%80%AFPM.png" width="600" alt="Data Processing"/>
<h4>Image 5: Data Processing</h4>
</div>

<div id="image-6-data-storage">
<img src="images/Screenshot%202025-08-03%20at%208.24.26%E2%80%AFPM.png" width="600" alt="Data Storage"/>
<h4>Image 6: Data Storage</h4>
</div>

<div id="image-7-github-oauth">
<img src="images/Screenshot%202025-08-03%20at%208.26.40%E2%80%AFPM.png" width="600" alt="GitHub OAuth on Discord"/>
<h4>Image 7: GitHub OAuth on Discord</h4>
</div>

<div id="image-8-cloud-logs">
<img src="images/Screenshot%202025-08-03%20at%208.27.13%E2%80%AFPM.png" width="600" alt="OAuth Cloud Logs"/>
<h4>Image 8: OAuth Cloud Logs</h4>
</div>

<div id="image-9-auto-role-update">
<img src="images/Screenshot%202025-08-03%20at%208.20.08%E2%80%AFPM.png" width="600" alt="Auto Role Update"/>
<h4>Image 9: Auto Role Update</h4>
</div>

<div id="image-10-role-assignment">
<img src="images/Screenshot%202025-08-03%20at%207.55.34%E2%80%AFPM.png" width="600" alt="Role Assignment"/>
<h4>Image 10: Role Assignment</h4>
</div>

<div id="image-11-pr-review">
<img src="images/Screenshot%202025-08-03%20at%207.55.47%E2%80%AFPM.png" width="600" alt="PR Review"/>
<h4>Image 11: PR Review</h4>
</div>

<div id="image-12-pr-labeller">
<img src="images/Screenshot%202025-08-03%20at%208.07.50%E2%80%AFPM.png" width="600" alt="PR Labeller"/>
<h4>Image 12: PR Labeller</h4>
</div>

<div id="image-13-analytics">
<img src="images/Screenshot%202025-08-03%20at%207.55.59%E2%80%AFPM.png" width="600" alt="Analytics"/>
<h4>Image 13: Analytics</h4>
</div>

<div id="image-14-hall-of-fame">
<img src="images/Screenshot%202025-08-03%20at%207.56.18%E2%80%AFPM.png" width="600" alt="Hall of Fame"/>
<h4>Image 14: Hall of Fame</h4>
</div>

<div id="image-15-metric-tracking">
<img src="images/Screenshot%202025-08-03%20at%207.56.28%E2%80%AFPM.png" width="600" alt="Metric Tracking"/>
<h4>Image 15: Metric Tracking</h4>
</div>

</div>

---

## Implementation Diagrams

<div align="center">

<div id="diagram-1-contribution-stats-pipeline">
<h4>Diagram 1: Discord Bot for Real-Time GitHub Contribution Stats - Data Pipeline Architecture</h4>

```mermaid
graph TD
    A["GitHub Repositories<br/>(ruxailab org)"] --> B["GitHub Service<br/>GitHubService.py"]
    B --> C["Raw Data Collection<br/>• PRs, Issues, Commits<br/>• Contributors, Labels<br/>• Repository Info"]
    
    C --> D["Data Processing Pipeline<br/>discord_bot_pipeline.yml"]
    D --> E["Contribution Processor<br/>contribution_processor.py"]
    D --> F["Analytics Processor<br/>analytics_processor.py"]
    D --> G["Metrics Processor<br/>metrics_processor.py"]
    
    E --> H["Processed Contributions<br/>• User stats by time period<br/>• Rankings & streaks<br/>• Activity counts"]
    F --> I["Analytics Data<br/>• Hall of fame rankings<br/>• Top contributors<br/>• Activity summaries"]
    G --> J["Repository Metrics<br/>• Stars, forks, issues<br/>• PR & commit counts<br/>• Contributor totals"]
    
    H --> K["Firestore Database<br/>Collections:<br/>• repo_stats/analytics<br/>• repo_stats/hall_of_fame<br/>• discord/{user_id}"]
    I --> K
    J --> K
    
    K --> L["Discord Bot Commands<br/>• /show-stats<br/>• /show-top-contributors<br/>• /show-activity-comparison"]
    
    L --> M["Discord User Interface<br/>• Real-time contribution stats<br/>• Interactive charts<br/>• Leaderboards"]
    
    style A fill:#e1f5fe
    style K fill:#f3e5f5
    style M fill:#e8f5e8
```
</div>

<div id="diagram-2-role-update-system">
<h4>Diagram 2: Discord Role Auto-Update Bot - Role Update Workflow</h4>

```mermaid
graph TD
    A["GitHub Actions Trigger<br/>Daily at midnight UTC<br/>discord_bot_pipeline.yml"] --> B["Data Collection<br/>GitHubService.collect_organization_data()"]
    
    B --> C["Process Contributions<br/>contribution_processor.py<br/>• Calculate rankings<br/>• Determine role levels"]
    
    C --> D["Role Configuration<br/>RoleService.py<br/>• PR roles: Novice → Expert<br/>• Issue roles: Reporter → Investigator<br/>• Commit roles: Contributor → Architect"]
    
    D --> E["Store in Firestore<br/>repo_stats/contributor_summary<br/>• User contribution levels<br/>• Medal assignments"]
    
    E --> F["Discord Guild Service<br/>GuildService.py<br/>update_roles_and_channels()"]
    
    F --> G["Role Assignment Logic<br/>• Remove outdated roles<br/>• Add new roles based on stats<br/>• Assign medal roles (Champion, Runner-up, Bronze)"]
    
    G --> H["Discord Server Updates<br/>• Automatic role assignment<br/>• Role hierarchy management<br/>• User permission updates"]
    
    I["User Mappings<br/>discord/{user_id}<br/>GitHub username mapping"] --> F
    
    style A fill:#fff3e0
    style E fill:#f3e5f5
    style H fill:#e8f5e8
```
</div>

<div id="diagram-3-pr-review-integration">
<h4>Diagram 3: AI-Assisted Pull Request Review Integration - PR Review Automation</h4>

```mermaid
graph TD
    A["Pull Request Event<br/>opened/synchronize/reopened"] --> B["GitHub Actions Workflow<br/>pr-automation.yml"]
    
    B --> C["PR Review System<br/>PRReviewSystem.py<br/>main.py"]
    
    C --> D["GitHub Client<br/>• Get PR details & diff<br/>• Get PR files<br/>• Fetch repository data"]
    
    C --> E["Metrics Calculator<br/>• Lines changed<br/>• Files modified<br/>• Complexity analysis"]
    
    C --> F["AI PR Labeler<br/>• Google Gemini API<br/>• Analyze PR content<br/>• Predict labels"]
    
    C --> G["Reviewer Assigner<br/>• Load reviewer pool from Firestore<br/>• Random selection (1-2 reviewers)<br/>• Top 8 reviewers based on contributions"]
    
    H["Firestore Database<br/>• pr_config/reviewers<br/>• repository_labels/{repo}<br/>• repo_stats/contributor_summary"] --> G
    H --> F
    
    F --> I["Label Application<br/>• Apply predicted labels to PR<br/>• Confidence threshold: 0.5+"]
    G --> J["Reviewer Assignment<br/>• Request reviewers via GitHub API<br/>• Notify assigned reviewers"]
    
    I --> K["PR Comment<br/>• Metrics summary<br/>• Applied labels<br/>• Assigned reviewers<br/>• Processing status"]
    J --> K
    
    K --> L["Discord Notification<br/>• PR processing complete<br/>• Summary of actions taken"]
    
    style A fill:#fff3e0
    style H fill:#f3e5f5
    style L fill:#e8f5e8
```
</div>

<div id="diagram-4-pr-labeling-workflow">
<h4>Diagram 4: Automatic Labelling for PRs Using PR Labeller - AI Labeling System</h4>

```mermaid
graph TD
    A["Pull Request Trigger<br/>PR opened/updated"] --> B["GitHub Actions<br/>pr-automation.yml"]
    
    B --> C["AI PR Labeler<br/>AIPRLabeler.py"]
    
    C --> D["Load Repository Labels<br/>From Firestore:<br/>repository_labels/{repo_name}"]
    
    D --> E["AI Analysis<br/>Google Gemini API<br/>• Analyze PR title & body<br/>• Review code diff<br/>• Consider PR metrics"]
    
    E --> F["Label Classification<br/>• Use prompt template<br/>• Match against available labels<br/>• Generate confidence scores"]
    
    F --> G["Filter by Confidence<br/>Threshold: 0.5+<br/>Select high-confidence labels"]
    
    G --> H["Apply Labels to PR<br/>GitHub API:<br/>add_labels_to_pull_request()"]
    
    I["Daily Pipeline<br/>discord_bot_pipeline.yml"] --> J["Label Collection<br/>process_repository_labels()<br/>• Fetch all repo labels<br/>• Store label metadata"]
    
    J --> K["Store in Firestore<br/>repository_labels/{repo}<br/>• Label names & descriptions<br/>• Usage statistics"]
    
    K --> D
    
    H --> L["Updated PR<br/>• Labels automatically applied<br/>• Consistent labeling across repos<br/>• Reduced manual effort"]
    
    style A fill:#fff3e0
    style K fill:#f3e5f5
    style L fill:#e8f5e8
```
</div>

<div id="diagram-5-metrics-tracking-system">
<h4>Diagram 5: Research Metric Tracking and Channel Creation - Metrics & Channels</h4>

```mermaid
graph TD
    A["Daily Pipeline Trigger<br/>GitHub Actions<br/>discord_bot_pipeline.yml"] --> B["Metrics Processor<br/>metrics_processor.py<br/>create_repo_metrics()"]
    
    B --> C["Aggregate Repository Data<br/>• Total stars & forks<br/>• Total PRs & issues<br/>• Total commits<br/>• Contributor count"]
    
    C --> D["Store Metrics<br/>Firestore:<br/>repo_stats/metrics"]
    
    D --> E["Guild Service<br/>GuildService.py<br/>_update_channels_for_guild()"]
    
    E --> F["Discord Channel Management<br/>• Find/create 'REPOSITORY STATS' category<br/>• Update voice channel names<br/>• Real-time metric display"]
    
    F --> G["Live Discord Channels<br/>Voice Channels:<br/>• 'Stars: 1,234'<br/>• 'Forks: 567'<br/>• 'Contributors: 89'<br/>• 'PRs: 2,345'<br/>• 'Issues: 678'<br/>• 'Commits: 12,345'"]
    
    H["Raw GitHub Data<br/>• Repository info<br/>• Contribution data<br/>• API responses"] --> B
    
    I["Repository Health<br/>• Last updated timestamps<br/>• Data freshness indicators<br/>• Collection status"] --> D
    
    style A fill:#fff3e0
    style D fill:#f3e5f5
    style G fill:#e8f5e8
```
</div>

<div id="diagram-6-analytics-hall-of-fame">
<h4>Diagram 6: Contributor Analytics and Hall of Fame Visualization - Analytics & Visualization</h4>

```mermaid
graph TD
    A["Contribution Data<br/>From daily pipeline<br/>User stats & rankings"] --> B["Analytics Processor<br/>analytics_processor.py"]
    
    B --> C["Hall of Fame Generator<br/>create_hall_of_fame_data()<br/>• Top 10 per category<br/>• Multiple time periods<br/>• PR/Issue/Commit rankings"]
    
    B --> D["Analytics Data Creator<br/>create_analytics_data()<br/>• Summary statistics<br/>• Top contributors<br/>• Activity trends"]
    
    C --> E["Hall of Fame Data<br/>Leaderboards by period:<br/>• Daily, Weekly, Monthly, All-time<br/>• Separate rankings for PRs, Issues, Commits"]
    
    D --> F["Analytics Data<br/>• Total contributor count<br/>• Active contributor metrics<br/>• Top 5 contributors per category<br/>• Activity summaries"]
    
    E --> G["Firestore Storage<br/>repo_stats/hall_of_fame<br/>repo_stats/analytics"]
    F --> G
    
    G --> H["Discord Commands<br/>• /show-top-contributors<br/>• /show-activity-comparison<br/>• /show-activity-trends<br/>• /show-time-series"]
    
    H --> I["Chart Generation<br/>chart_generators.py<br/>• TopContributorsChart<br/>• ActivityComparisonChart<br/>• TimeSeriesChart"]
    
    I --> J["Visual Analytics<br/>Discord Interface:<br/>• Interactive bar charts<br/>• Time series graphs<br/>• Contributor comparisons<br/>• Hall of fame displays"]
    
    K["Medal System<br/>• PR Champion<br/>• PR Runner-up<br/>• PR Bronze<br/>Auto-assigned roles"] --> G
    
    style A fill:#e1f5fe
    style G fill:#f3e5f5
    style J fill:#e8f5e8
```
</div>

</div>

---

For more details, see the [project documentation](https://github.com/ruxailab/gsoc/blob/main/ideas2025.md).
