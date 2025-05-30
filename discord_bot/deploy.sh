#!/bin/bash
# Simple deployment script for Discord bot to Cloud Run

# Set your Google Cloud project ID
PROJECT_ID="finaltest-b0895"
REGION="us-central1"
SERVICE_NAME="discord-bot"

# Get the directory of this script and set paths accordingly
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
CREDENTIALS_PATH="$ROOT_DIR/credentials.json"
ENV_PATH="$SCRIPT_DIR/.env"

echo "Script directory: $SCRIPT_DIR"
echo "Root directory: $ROOT_DIR"
echo "Credentials path: $CREDENTIALS_PATH"
echo "Env path: $ENV_PATH"

# Enable required services
echo "Enabling required services..."
gcloud services enable run.googleapis.com \
                       containerregistry.googleapis.com \
                       secretmanager.googleapis.com

# Set default project
echo "Setting default project to $PROJECT_ID"
gcloud config set project $PROJECT_ID

# Check if credentials.json exists as a secret, if not create it
echo "Setting up Firebase credentials secret..."
SECRET_NAME="firebase-credentials"
if ! gcloud secrets describe $SECRET_NAME &>/dev/null; then
  echo "Creating secret for Firebase credentials..."
  gcloud secrets create $SECRET_NAME --data-file="$CREDENTIALS_PATH"
else
  echo "Updating existing Firebase credentials secret..."
  gcloud secrets versions add $SECRET_NAME --data-file="$CREDENTIALS_PATH"
fi

# After creating the secret but before deploying
# Get the service account used by Cloud Run
echo "Setting up IAM permissions for Secret Manager..."
SERVICE_ACCOUNT="${PROJECT_NUMBER:-$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')}-compute@developer.gserviceaccount.com"
echo "Cloud Run service account: $SERVICE_ACCOUNT"

# Grant the service account access to the secret
echo "Granting Secret Manager Secret Accessor role to $SERVICE_ACCOUNT..."
gcloud secrets add-iam-policy-binding $SECRET_NAME \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"

# Extract environment variables from .env file
echo "Loading environment variables from .env file..."
if [ -f "$ENV_PATH" ]; then
  # Create a properly formatted environment variable string
  ENV_VARS=""
  while IFS= read -r line; do
    # Skip comments and empty lines
    if [[ ! $line =~ ^# && -n $line ]]; then
      # Remove any whitespace around the equals sign
      clean_line=$(echo "$line" | sed 's/[[:space:]]*=[[:space:]]*/=/g')
      
      # Add to our env vars string
      if [ -n "$ENV_VARS" ]; then
        ENV_VARS="$ENV_VARS,$clean_line"
      else
        ENV_VARS="$clean_line"
      fi
    fi
  done < "$ENV_PATH"
  
  echo "Extracted environment variables from .env"
  echo "ENV_VARS format: ${ENV_VARS:0:20}..." # Print first 20 chars for debugging
else
  echo "Warning: .env file not found at $ENV_PATH!"
  exit 1
fi

# Before running the Docker build command
# Copy credentials.json to the Docker build context
echo "Ensuring credentials.json is available in the build context..."
cp "$CREDENTIALS_PATH" "$SCRIPT_DIR/credentials.json" || echo "Warning: Failed to copy credentials.json"

# Build the Docker image
echo "Building Docker image..."
if docker buildx build --platform linux/amd64 \
  -t gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
  -f "$SCRIPT_DIR/Dockerfile" \
  --push \
  "$SCRIPT_DIR"; then
  echo "✅ Docker image built and pushed successfully!"
else
  echo "❌ Docker build failed. Check the error above."
  exit 1
fi

# Check if the service already exists and clean up any existing configuration
echo "Checking for existing service configuration..."
if gcloud run services describe $SERVICE_NAME --region=$REGION &>/dev/null; then
  echo "Found existing service, cleaning up configuration..."
  
  # Always clear environment variables and secrets for a clean deployment
  echo "Clearing all existing environment variables..."
  gcloud run services update $SERVICE_NAME \
    --region=$REGION \
    --clear-env-vars

  echo "Clearing existing secrets..."
  gcloud run services update $SERVICE_NAME \
    --region=$REGION \
    --clear-secrets
fi

# Now proceed with the deployment with clean configuration
echo "Deploying to Cloud Run..."
echo "Setting up with secret mount for Firebase credentials"
DEPLOY_CMD="gcloud run deploy $SERVICE_NAME \
  --image=gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
  --platform=managed \
  --region=$REGION \
  --port=8080 \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=1 \
  --max-instances=1 \
  --concurrency=80 \
  --timeout=300s \
  --allow-unauthenticated \
  --no-cpu-throttling \
  --execution-environment=gen2 \
  --update-secrets=/secret/firebase-credentials=$SECRET_NAME:latest"

# Add environment variables if we have them
if [ -n "$ENV_VARS" ]; then
  DEPLOY_CMD="$DEPLOY_CMD --set-env-vars=\"$ENV_VARS\""
  echo "Adding environment variables"
else
  echo "No environment variables to add"
fi

# Execute the command
echo "Running: $DEPLOY_CMD"
eval $DEPLOY_CMD

echo "✅ Deployment complete!"
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --format="value(status.url)")

echo "Service URL: $SERVICE_URL"

# Wait a moment for the service to start
echo "Waiting for service to start..."
sleep 10

# Check the logs to verify deployment
echo "Checking logs to verify deployment..."
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME" \
  --limit=20 \
  --format="value(textPayload)" \
  --freshness=10m

echo "✅ Deployment process finished" 