#!/bin/bash
# Complete cleanup - removes ALL resources created by deploy.sh

echo "🔥 Complete takedown of Discord bot resources..."

# Delete Cloud Run service
gcloud run services delete discord-bot --region=us-central1

# Delete container images
gcloud container images delete gcr.io/finaltest-b0895/discord-bot --force-delete-tags

# Delete Secret Manager secrets
gcloud secrets delete firebase-credentials

# Note: IAM permissions are auto-deleted with the secret
# Note: We don't disable services as they might be used by other projects

echo "✅ Complete cleanup finished!"