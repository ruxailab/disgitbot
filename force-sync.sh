#!/bin/bash

# Exit immediately if any command fails
set -e

echo "Switching to main branch..."
git checkout main

echo "Resetting local changes..."
git reset --hard

echo "Removing untracked files and directories..."
git clean -fd

echo "Fetching latest from origin..."
git fetch origin

echo "Hard resetting to origin/main..."
git reset --hard origin/main

echo "Your main branch is now clean and synced with origin/main."
