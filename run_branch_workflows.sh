#!/bin/bash
# Run GitHub Workflows on Current Branch
# Simple script to trigger workflows regardless of branch restrictions

set -e

# Get current branch
CURRENT_BRANCH=$(git branch --show-current)
echo "Current branch: $CURRENT_BRANCH"

# Function to run a workflow
run_workflow() {
    local workflow_file="$1"
    local workflow_name="$2"
    
    echo ""
    echo "Triggering: $workflow_name"
    echo "   File: $workflow_file"
    echo "   Branch: $CURRENT_BRANCH"
    
    # Try to run the workflow
    if gh workflow run "$workflow_file" --ref "$CURRENT_BRANCH"; then
        echo "Successfully triggered: $workflow_name"
    else
        echo "Failed to trigger: $workflow_name"
        return 1
    fi
}

# Main execution
echo "============================================================"
echo "GitHub Workflows Runner - Current Branch Edition"
echo "============================================================"

# Check if GitHub CLI is available
if ! command -v gh &> /dev/null; then
    echo "GitHub CLI (gh) not found. Install from: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "GitHub CLI not authenticated. Run: gh auth login"
    exit 1
fi

echo "GitHub CLI is ready"

# Run all workflows
echo ""
echo "Running all available workflows..."

# Discord Bot Pipeline
run_workflow "discord_bot_pipeline.yml" "Discord Bot Data Pipeline"

# PR Automation (if you want to run it)
# run_workflow "pr-automation.yml" "PR Automation System"

echo ""
echo "============================================================"
echo "All workflows triggered on branch: $CURRENT_BRANCH"
echo "============================================================"
echo ""
echo "Check workflow status:"
echo "   gh run list --branch $CURRENT_BRANCH"
echo ""
echo "Watch workflow logs:"
echo "   gh run watch" 