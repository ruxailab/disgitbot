#!/bin/bash
# Interactive cleanup script - removes ALL resources created by deploy.sh

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
    echo -e "${PURPLE}   Discord Bot Cleanup Tool      ${NC}"
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

# Check authentication
print_step "Verifying Google Cloud authentication..."
auth_account=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -n1)

if [ -z "$auth_account" ]; then
    print_error "You're not authenticated with Google Cloud."
    echo "Please run: gcloud auth login"
    exit 1
fi

print_success "Authenticated as: $auth_account"

# Function to select from options with arrow keys
interactive_select() {
    local prompt="$1"
    local options=("${@:2}")
    local selected=0
    local num_options=${#options[@]}
    
    # Function to display options
    display_options() {
        clear
        echo -e "\n${PURPLE}================================${NC}"
        echo -e "${PURPLE}   Discord Bot Cleanup Tool      ${NC}"
        echo -e "${PURPLE}================================${NC}\n"
        echo -e "${BLUE}$prompt${NC}"
        echo -e "${YELLOW}Use ↑/↓ arrow keys to navigate, SPACE/ENTER to select, q to quit${NC}\n"
        
        for i in "${!options[@]}"; do
            if [ $i -eq $selected ]; then
                echo -e "${GREEN}${options[i]}${NC}"
            else
                echo -e "  ${options[i]}"
            fi
        done
    }
    
    display_options
    
    while true; do
        read -rsn1 key
        
        case $key in
            $'\x1b')
                read -rsn2 key
                case $key in
                    '[A') # Up arrow
                        ((selected--))
                        if [ $selected -lt 0 ]; then
                            selected=$((num_options - 1))
                        fi
                        display_options
                        ;;
                    '[B') # Down arrow
                        ((selected++))
                        if [ $selected -ge $num_options ]; then
                            selected=0
                        fi
                        display_options
                        ;;
                esac
                ;;
            ' '|'') # Space or Enter
                clear
                echo -e "\n${GREEN}Selected: ${options[$selected]}${NC}\n"
                INTERACTIVE_SELECTION=$selected
                return 0
                ;;
            'q'|'Q') # Quit
                clear
                print_warning "Cleanup cancelled."
                exit 0
                ;;
        esac
    done
}

# Function to select Google Cloud Project
select_project() {
    print_step "Fetching your Google Cloud projects..."
    
    projects=$(gcloud projects list --format="value(projectId,name)" 2>/dev/null)
    
    if [ -z "$projects" ]; then
        print_error "No projects found or unable to fetch projects."
        exit 1
    fi
    
    declare -a project_options
    declare -a project_ids
    declare -a project_names
    
    while IFS=$'\t' read -r project_id project_name; do
        project_options+=("$project_id - $project_name")
        project_ids+=("$project_id")
        project_names+=("$project_name")
    done <<< "$projects"
    
    interactive_select "Select a Google Cloud Project to clean up:" "${project_options[@]}"
    selection=$INTERACTIVE_SELECTION
    
    PROJECT_ID="${project_ids[$selection]}"
    PROJECT_NAME="${project_names[$selection]}"
    
    print_success "Selected project: $PROJECT_ID ($PROJECT_NAME)"
}

# Function to get cleanup configuration
get_cleanup_config() {
    print_step "Cleanup Configuration"
    
    # Service Name
    read -p "Service name to delete (default: discord-bot): " SERVICE_NAME
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
    
    interactive_select "Select the region where your service is deployed:" "${region_options[@]}"
    region_choice=$INTERACTIVE_SELECTION
    
    if [ $region_choice -eq 5 ]; then
        read -p "Enter custom region: " REGION
    else
        REGION="${region_values[$region_choice]}"
    fi
    
    print_success "Configuration complete!"
}

# Main cleanup function
main() {
    select_project
    get_cleanup_config
    
    # Show cleanup summary
    echo -e "\n${PURPLE}================================${NC}"
    echo -e "${PURPLE}   CLEANUP SUMMARY${NC}"
    echo -e "${PURPLE}================================${NC}"
    echo -e "${BLUE}Target Configuration:${NC}"
    echo "  Project: $PROJECT_ID ($PROJECT_NAME)"
    echo "  Service: $SERVICE_NAME"
    echo "  Region: $REGION"
    echo
    echo -e "${BLUE}Resources to be deleted:${NC}"
    echo "  • Cloud Run service: $SERVICE_NAME"
    echo "  • Container images: gcr.io/$PROJECT_ID/$SERVICE_NAME"
    echo "  • Secret Manager secret: firebase-credentials"
    echo "  • All associated IAM permissions"
    echo
    echo -e "${RED}WARNING: This action cannot be undone!${NC}"
    echo -e "${PURPLE}================================${NC}"
    echo
    read -p "Proceed with cleanup? (y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        print_warning "Cleanup cancelled."
        exit 0
    fi
    
    # Set project context
    gcloud config set project "$PROJECT_ID"
    
    echo "Complete takedown of Discord bot resources..."
    
    # Delete Cloud Run service
    print_step "Deleting Cloud Run service..."
    if gcloud run services describe $SERVICE_NAME --region=$REGION --project="$PROJECT_ID" &>/dev/null; then
        gcloud run services delete $SERVICE_NAME --region=$REGION --project="$PROJECT_ID" --quiet
        print_success "Cloud Run service deleted"
    else
        print_warning "Cloud Run service not found or already deleted"
    fi
    
    # Delete container images
    print_step "Deleting container images..."
    if gcloud container images describe gcr.io/$PROJECT_ID/$SERVICE_NAME:latest --project="$PROJECT_ID" &>/dev/null; then
        gcloud container images delete gcr.io/$PROJECT_ID/$SERVICE_NAME --force-delete-tags --project="$PROJECT_ID" --quiet
        print_success "Container images deleted"
    else
        print_warning "Container images not found or already deleted"
    fi
    
    # Delete Secret Manager secrets
    print_step "Deleting Secret Manager secrets..."
    if gcloud secrets describe firebase-credentials --project="$PROJECT_ID" &>/dev/null; then
        gcloud secrets delete firebase-credentials --project="$PROJECT_ID" --quiet
        print_success "Secrets deleted"
    else
        print_warning "Secrets not found or already deleted"
    fi
    
    # Note: IAM permissions are auto-deleted with the secret
    # Note: We don't disable services as they might be used by other projects
    
    echo "Complete cleanup finished!"
}

# Run main function
main