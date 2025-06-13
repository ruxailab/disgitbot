#!/bin/bash
# Simple takedown script for Discord bot on Cloud Run

echo "🔥 Taking down Discord bot from Google Cloud..."

# Delete the Cloud Run service
echo "Deleting Cloud Run service..."
gcloud run services delete discord-bot --region=us-central1

# Delete the container images
echo "Deleting container images..."
gcloud container images delete gcr.io/finaltest-b0895/discord-bot --force-delete-tags

echo "✅ Takedown complete!" 