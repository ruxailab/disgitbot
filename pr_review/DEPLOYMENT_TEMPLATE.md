# RUXAILAB PR Automation Deployment Guide

## Overview

This guide shows how to deploy the PR automation system to any RUXAILAB repository using the **reusable workflow** approach.

## Master Workflow Location

The master workflow is located in: `ruxailab/disgitbot/.github/workflows/pr-automation.yml`

## How to Deploy to Other Repos

### Step 1: Create the Workflow File

In any RUXAILAB repository, create this file:
`.github/workflows/pr-automation.yml`

### Step 2: Copy This Template

```yaml
# RUXAILAB PR Automation - Caller Workflow
# This calls the master workflow from ruxailab/disgitbot

name: PR Automation

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  pr-automation:
    uses: ruxailab/disgitbot/.github/workflows/pr-automation.yml@main
    with:
      repository: ${{ github.repository }}
      pr_number: ${{ github.event.pull_request.number }}
      experience_level: 'intermediate'  # Options: beginner, intermediate, advanced
      action: 'process_pr'
    secrets:
      GH_TOKEN: ${{ secrets.GH_TOKEN }}
      GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
```

### Step 3: Set Up Secrets

Each repository needs these secrets:
- `GITHUB_TOKEN` (automatically available)
- `GOOGLE_API_KEY` (add to repository secrets)

## Advanced Usage

### Manual Trigger for Labels Collection

Add this to trigger labels collection manually:

```yaml
name: PR Automation

on:
  pull_request:
    types: [opened, synchronize, reopened]
  workflow_dispatch:
    inputs:
      action:
        description: 'Action to perform'
        required: true
        default: 'process_pr'
        type: choice
        options:
          - process_pr
          - collect_labels
          - update_cache

jobs:
  pr-automation:
    uses: ruxailab/disgitbot/.github/workflows/pr-automation.yml@main
    with:
      repository: ${{ github.repository }}
      pr_number: ${{ github.event.pull_request.number || 0 }}
      experience_level: 'intermediate'
      action: ${{ github.event.inputs.action || 'process_pr' }}
    secrets:
      GH_TOKEN: ${{ secrets.GH_TOKEN }}
      GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
```

## Deployment Status

### Deployed Repositories
- [ ] ruxailab/eye-tracking-analysis
- [ ] ruxailab/sentiment-analysis-tool
- [ ] ruxailab/heuristic-evaluation-framework
- [ ] ruxailab/accessibility-testing-suite
- [ ] ruxailab/figma-integration-plugin
- [ ] ruxailab/vr-ar-research-tools
- [ ] ruxailab/research-data-pipeline

### Benefits of This Approach

1. **Single Source of Truth** - All logic in `ruxailab/disgitbot`
2. **Easy Updates** - Change master workflow, all repos get updates
3. **Minimal Code Duplication** - Each repo has only ~15 lines
4. **Centralized Maintenance** - Fix bugs in one place
5. **Consistent Behavior** - All repos use same AI logic

## Testing

Test the deployment:
1. Create a PR in the target repository
2. Check GitHub Actions tab
3. Verify the workflow runs and processes the PR
4. Check for AI-generated comments, labels, and reviewer assignments

## Troubleshooting

### Common Issues:

1. **Missing GOOGLE_API_KEY**
   - Add the secret to repository settings
   - Use the same key as in `ruxailab/disgitbot`

2. **Workflow not triggering**
   - Check the file is in `.github/workflows/`
   - Verify YAML syntax is correct
   - Ensure the master workflow exists

3. **Permission errors**
   - Verify `GITHUB_TOKEN` has necessary permissions
   - Check if repository is private/public access

## Support

For issues or questions:
- Check the master workflow: `ruxailab/disgitbot/.github/workflows/pr-automation.yml`
- Review logs in GitHub Actions
- Contact the automation team 