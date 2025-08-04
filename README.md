# GSoC 2025 Report

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

| Status     | Task                                             | Week      | Timeline           | Issue / Report Link                                                                                 | Images                |
|------------|--------------------------------------------------|-----------|--------------------|-----------------------------------------------------------------------------------------------------|-----------------------|
| Completed  | Discord Bot for Real-Time GitHub Contribution Stats | 1-2       | June 2-7, 2025     | [Issue #2](https://github.com/ruxailab/disgitbot/issues/2)                                          | [Image 1: Discord Command](#image-1-discord-command)<br/>[Image 2: Data Collection](#image-2-data-collection)<br/>[Image 3: OAuth Process](#image-3-oauth-process)<br/>[Image 4: Authentication](#image-4-authentication)<br/>[Image 5: Data Processing](#image-5-data-processing)<br/>[Image 6: Discord Integration](#image-6-discord-integration)<br/>[Image 7: Cloud Logs](#image-7-cloud-logs) |
| Completed  | Discord Role Auto-Update Bot                     | 3-4       | June 7-18, 2025    | [Issue #9](https://github.com/ruxailab/disgitbot/issues/9)                                          | [Image 8: Role System](#image-8-role-system)<br/>[Image 9: Auto Update](#image-9-auto-update)<br/>[Image 10: Role Assignment](#image-10-role-assignment) |
| Completed  | AI-Assisted Pull Request Review Integration       | 5-7       | June 18-July 5, 2025 | [Issue #3](https://github.com/ruxailab/disgitbot/issues/3)                                          | [Image 11: PR Review](#image-11-pr-review) |
| Completed  | Automatic Labelling for PRs Using PR Labeller    | 8         | July 14-20, 2025   | [Issue #4](https://github.com/ruxailab/disgitbot/issues/4)                                          | [Image 12: PR Labeller](#image-12-pr-labeller) |
| Completed  | Contributor Analytics and Hall of Fame Visualization | 12        | July 27-August 5, 2025 | [Issue #6](https://github.com/ruxailab/disgitbot/issues/6)                                          | [Image 13: Analytics](#image-13-analytics)<br/>[Image 14: Hall of Fame](#image-14-hall-of-fame) |
| Completed  | Research Metric Tracking and Channel Creation     | 9-10      | August 15-25, 2025 | [Issue #8](https://github.com/ruxailab/disgitbot/issues/8)                                          | [Image 15: Metric Tracking](#image-15-metric-tracking) |

---

## Gallery

<div align="center">

<div id="image-1-discord-command">
<img src="images/Screenshot%202025-08-03%20at%207.53.39%E2%80%AFPM.png" width="600" alt="Discord Command"/>
<h4>Image 1: Discord Command</h4>
</div>

<div id="image-2-data-collection">
<img src="images/Screenshot%202025-08-03%20at%207.55.07%E2%80%AFPM.png" width="600" alt="Data Collection"/>
<h4>Image 2: Data Collection</h4>
</div>

<div id="image-3-oauth-process">
<img src="images/Screenshot%202025-08-03%20at%208.24.03%E2%80%AFPM.png" width="600" alt="OAuth Process"/>
<h4>Image 3: OAuth Process</h4>
</div>

<div id="image-4-authentication">
<img src="images/Screenshot%202025-08-03%20at%208.24.14%E2%80%AFPM.png" width="600" alt="Authentication"/>
<h4>Image 4: Authentication</h4>
</div>

<div id="image-5-data-processing">
<img src="images/Screenshot%202025-08-03%20at%208.24.26%E2%80%AFPM.png" width="600" alt="Data Processing"/>
<h4>Image 5: Data Processing</h4>
</div>

<div id="image-6-discord-integration">
<img src="images/Screenshot%202025-08-03%20at%208.26.40%E2%80%AFPM.png" width="600" alt="Discord Integration"/>
<h4>Image 6: Discord Integration</h4>
</div>

<div id="image-7-cloud-logs">
<img src="images/Screenshot%202025-08-03%20at%208.27.13%E2%80%AFPM.png" width="600" alt="Cloud Logs"/>
<h4>Image 7: Cloud Logs</h4>
</div>

<div id="image-8-role-system">
<img src="images/Screenshot%202025-08-03%20at%207.53.51%E2%80%AFPM.png" width="600" alt="Role System"/>
<h4>Image 8: Role System</h4>
</div>

<div id="image-9-auto-update">
<img src="images/Screenshot%202025-08-03%20at%208.20.08%E2%80%AFPM.png" width="600" alt="Auto Update"/>
<h4>Image 9: Auto Update</h4>
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

For more details, see the [project documentation](https://github.com/ruxailab/gsoc/blob/main/ideas2025.md).
