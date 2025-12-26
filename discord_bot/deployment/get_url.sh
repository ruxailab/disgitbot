#!/bin/bash
# Lightweight URL getter script for Discord bot placeholder deployment

set -e  # Exit on any error

# Colors for better UX
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "\n${PURPLE}================================${NC}"
    echo -e "${PURPLE}   Discord Bot URL Getter Tool   ${NC}"
    echo -e "${PURPLE}================================${NC}\n"
}

print_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}$1${NC}"
}

print_warning() {
    echo -e "${YELLOW}$1${NC}"
}

print_error() {
    echo -e "${RED}$1${NC}"
}

print_header

# Check if gcloud is installed and authenticated
print_step "Checking Google Cloud CLI..."
if ! command -v gcloud &> /dev/null; then
    print_error "Google Cloud CLI is not installed. Please install it first:"
    echo "https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Ensure fzf is available for interactive selection
print_step "Checking fzf (interactive selector)..."
if ! command -v fzf &> /dev/null; then
    print_error "fzf is required for this script's menus. Please install it (see README)."
    exit 1
fi

# Check authentication with better error handling
print_step "Verifying Google Cloud authentication..."
auth_account=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -n1)

if [ -z "$auth_account" ]; then
    print_error "You're not authenticated with Google Cloud."
    echo "Please run: gcloud auth login"
    exit 1
fi

print_success "Authenticated as: $auth_account"
print_success "Google Cloud CLI is ready!"

# Function to select from options with arrow keys
interactive_select() {
    local prompt="$1"
    shift
    local options=("$@")

    echo "$prompt" >&2
    selection=$(printf "%s\n" "${options[@]}" | fzf --prompt="> " --height=10 --border)

    if [ -z "$selection" ]; then
        echo "Cancelled."
        exit 1
    fi

    # Find index
    for i in "${!options[@]}"; do
        if [[ "${options[$i]}" == "$selection" ]]; then
            INTERACTIVE_SELECTION=$i
            return
        fi
    done
}


# Function to select Google Cloud Project
select_project() {
    print_step "Fetching your Google Cloud projects..."
    
    # Get list of projects
    projects=$(gcloud projects list --format="value(projectId,name)" 2>/dev/null)
    
    if [ -z "$projects" ]; then
        print_error "No projects found or unable to fetch projects."
        exit 1
    fi
    
    # Convert projects to array for interactive selection
    declare -a project_options
    declare -a project_ids
    declare -a project_names
    
    while IFS=$'\t' read -r project_id project_name; do
        project_options+=("$project_id - $project_name")
        project_ids+=("$project_id")
        project_names+=("$project_name")
    done <<< "$projects"
    
    # Interactive selection
    interactive_select "Select a Google Cloud Project:" "${project_options[@]}"
    selection=$INTERACTIVE_SELECTION
    
    PROJECT_ID="${project_ids[$selection]}"
    PROJECT_NAME="${project_names[$selection]}"
    
    print_success "Selected project: $PROJECT_ID ($PROJECT_NAME)"
}

# Function to get deployment configuration
get_deployment_config() {
    print_step "Deployment Configuration"
    echo
    
    # Service Name
    read -p "Service name (default: discord-bot): " SERVICE_NAME
    SERVICE_NAME=${SERVICE_NAME:-discord-bot}
    
    # Region selection
    declare -a region_options=(
        "us-central1 (Iowa)"
        "us-east1 (South Carolina)" 
        "us-west1 (Oregon)"
        "europe-west1 (Belgium)"
        "asia-northeast1 (Tokyo)"
        "Custom region"
    )
    
    declare -a region_values=(
        "us-central1"
        "us-east1"
        "us-west1" 
        "europe-west1"
        "asia-northeast1"
        "custom"
    )
    
    interactive_select "Select a Google Cloud Region:" "${region_options[@]}"
    region_choice=$INTERACTIVE_SELECTION
    
    if [ $region_choice -eq 5 ]; then  # Custom region
        read -p "Enter custom region: " REGION
    else
        REGION="${region_values[$region_choice]}"
    fi
    
    print_success "Configuration complete!"
}

# Main deployment flow
main() {
    select_project
    get_deployment_config
    
    # Show deployment summary
    echo -e "\n${PURPLE}================================${NC}"
    echo -e "${PURPLE}   DEPLOYMENT SUMMARY${NC}"
    echo -e "${PURPLE}================================${NC}"
    echo -e "${BLUE}Google Cloud Configuration:${NC}"
    echo "  Project: $PROJECT_ID ($PROJECT_NAME)"
    echo "  Service: $SERVICE_NAME"
    echo "  Region: $REGION"
    echo
    echo -e "${BLUE}What will be deployed:${NC}"
    echo "  • Placeholder Hello World service"
    echo "  • This will generate your Cloud Run URL"
    echo "  • You'll use this URL for GitHub OAuth setup"
    echo
    echo -e "${YELLOW}This will:${NC}"
    echo "  • Deploy a simple Hello World container"
    echo "  • Generate a public Cloud Run URL"
    echo "  • Enable required Google Cloud services"
    echo -e "${PURPLE}================================${NC}"
    echo
    read -p "Proceed with placeholder deployment? (y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        print_warning "Deployment cancelled."
        exit 0
    fi
    
    # Enable required services
    print_step "Enabling required Google Cloud services..."
    gcloud services enable run.googleapis.com \
                           containerregistry.googleapis.com \
                           --project="$PROJECT_ID"
    
    # Set default project
    gcloud config set project "$PROJECT_ID"
    
    # Deploy placeholder service
    print_step "Deploying placeholder service to get URL..."
    gcloud run deploy $SERVICE_NAME \
      --image=gcr.io/cloudrun/hello \
      --platform=managed \
      --region=$REGION \
      --project="$PROJECT_ID" \
      --allow-unauthenticated
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
      --region=$REGION \
      --project="$PROJECT_ID" \
      --format="value(status.url)")
    
    print_success "Placeholder deployment complete!"
    echo -e "\n${GREEN}Your Cloud Run URL is ready!${NC}"
    echo -e "${BLUE}Service URL:${NC} $SERVICE_URL"
    echo
    echo -e "${YELLOW}IMPORTANT: Save this URL!${NC}"
    echo "You'll need this URL for:"
    echo "  • Setting OAUTH_BASE_URL in your .env file"
    echo "  • Configuring GitHub OAuth app callback URL"
    echo "  • The callback URL should be: $SERVICE_URL/login/github/authorized"
    echo
    echo -e "${BLUE}Next steps:${NC}"
    echo "  1. Add this to your .env file: OAUTH_BASE_URL=$SERVICE_URL"
    echo "  2. Set up GitHub OAuth with callback: $SERVICE_URL/login/github/authorized"
    echo "  3. Complete the rest of the setup guide"
    echo "  4. Run the full deployment script when ready"
    
    print_success "URL getter process finished!"
}

# Run main function
main 
