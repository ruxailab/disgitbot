#!/bin/bash
# Interactive deployment script for Discord bot to Cloud Run

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
    echo -e "${PURPLE}   Discord Bot Deployment Tool   ${NC}"
    echo -e "${PURPLE}================================${NC}\n"
}

print_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DEFAULT_CREDENTIALS_PATH="$ROOT_DIR/config/credentials.json"
ENV_PATH="$ROOT_DIR/config/.env"

print_header

# Check if gcloud is installed and authenticated
print_step "Checking Google Cloud CLI..."
if ! command -v gcloud &> /dev/null; then
    print_error "Google Cloud CLI is not installed. Please install it first:"
    echo "https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check authentication
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1 > /dev/null; then
    print_warning "You're not authenticated with Google Cloud."
    echo "Please run: gcloud auth login"
    exit 1
fi

print_success "Google Cloud CLI is ready!"

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
        echo -e "${PURPLE}   Discord Bot Deployment Tool   ${NC}"
        echo -e "${PURPLE}================================${NC}\n"
        echo -e "${BLUE}$prompt${NC}"
        echo -e "${YELLOW}Use ↑/↓ arrow keys to navigate, SPACE/ENTER to select, q to quit${NC}\n"
        
        for i in "${!options[@]}"; do
            if [ $i -eq $selected ]; then
                echo -e "${GREEN}▶ ${options[i]}${NC}"
            else
                echo -e "  ${options[i]}"
            fi
        done
    }
    
    display_options
    
    while true; do
        # Read a single character
        read -rsn1 key
        
        case $key in
            # Arrow up
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
                echo -e "\n${GREEN}✅ Selected: ${options[$selected]}${NC}\n"
                # Use a global variable to store the selection
                INTERACTIVE_SELECTION=$selected
                return 0
                ;;
            'q'|'Q') # Quit
                clear
                print_warning "Selection cancelled."
                exit 0
                ;;
        esac
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

# Function to handle .env file
handle_env_file() {
    print_step "Environment Configuration"
    
    if [ -f "$ENV_PATH" ]; then
        echo -e "\n${BLUE}Existing .env file found.${NC}"
        echo "Current contents:"
        echo -e "${YELLOW}$(cat "$ENV_PATH")${NC}"
        echo
        
        declare -a env_options=(
            "Use existing .env file"
            "Edit existing .env file"
            "Create new .env file"
        )
        
        interactive_select "What would you like to do with the .env file?" "${env_options[@]}"
        env_choice=$INTERACTIVE_SELECTION
        
        case $env_choice in
            0)
                print_success "Using existing .env file"
                return
                ;;
            1)
                echo -e "\n${BLUE}Current .env contents:${NC}"
                cat -n "$ENV_PATH"
                echo
                edit_env_file
                return
                ;;
            2)
                create_new_env_file
                return
                ;;
        esac
    else
        print_warning ".env file not found. Let's create one!"
        create_new_env_file
    fi
}

create_new_env_file() {
    echo -e "\n${BLUE}Creating new .env file...${NC}"
    echo "Please provide the following tokens and configuration:"
    echo
    
    # Discord Bot Token
    while true; do
        read -p "Discord Bot Token: " discord_token
        if [ -n "$discord_token" ]; then
            break
        fi
        print_warning "Discord Bot Token is required!"
    done
    
    # GitHub Token
    while true; do
        read -p "GitHub Token: " github_token
        if [ -n "$github_token" ]; then
            break
        fi
        print_warning "GitHub Token is required!"
    done
    
    # GitHub Client ID
    read -p "GitHub Client ID: " github_client_id
    
    # GitHub Client Secret
    read -p "GitHub Client Secret: " github_client_secret
    
    # Repository Owner
    read -p "Repository Owner: " repo_owner
    
    # Repository Name  
    read -p "Repository Name: " repo_name
    
    # Ngrok Domain
    read -p "Ngrok Domain : " ngrok_domain
    
    # Create .env file
    cat > "$ENV_PATH" << EOF
DISCORD_BOT_TOKEN=$discord_token
GITHUB_TOKEN=$github_token
GITHUB_CLIENT_ID=$github_client_id
GITHUB_CLIENT_SECRET=$github_client_secret
REPO_OWNER=$repo_owner
REPO_NAME=$repo_name
NGROK_DOMAIN=$ngrok_domain
EOF
    
    print_success ".env file created successfully!"
}

edit_env_file() {
    echo -e "\n${BLUE}Edit each value (press Enter to keep current value):${NC}"
    
    # Read current values
    source "$ENV_PATH"
    
    echo
    read -p "Discord Bot Token [$DISCORD_BOT_TOKEN]: " new_discord_token
    discord_token=${new_discord_token:-$DISCORD_BOT_TOKEN}
    
    read -p "GitHub Token [$GITHUB_TOKEN]: " new_github_token
    github_token=${new_github_token:-$GITHUB_TOKEN}
    
    read -p "GitHub Client ID [$GITHUB_CLIENT_ID]: " new_github_client_id
    github_client_id=${new_github_client_id:-$GITHUB_CLIENT_ID}
    
    read -p "GitHub Client Secret [$GITHUB_CLIENT_SECRET]: " new_github_client_secret
    github_client_secret=${new_github_client_secret:-$GITHUB_CLIENT_SECRET}
    
    read -p "Repository Owner [$REPO_OWNER]: " new_repo_owner
    repo_owner=${new_repo_owner:-$REPO_OWNER}
    
    read -p "Repository Name [$REPO_NAME]: " new_repo_name
    repo_name=${new_repo_name:-$REPO_NAME}
    
    read -p "Ngrok Domain [$NGROK_DOMAIN]: " new_ngrok_domain
    ngrok_domain=${new_ngrok_domain:-$NGROK_DOMAIN}
    
    # Update .env file
    cat > "$ENV_PATH" << EOF
DISCORD_BOT_TOKEN=$discord_token
GITHUB_TOKEN=$github_token
GITHUB_CLIENT_ID=$github_client_id
GITHUB_CLIENT_SECRET=$github_client_secret
REPO_OWNER=$repo_owner
REPO_NAME=$repo_name
NGROK_DOMAIN=$ngrok_domain
EOF
    
    print_success ".env file updated successfully!"
}

# Function to handle credentials file
handle_credentials_file() {
    print_step "Firebase/Google Cloud Credentials Configuration"
    
    # Check if default credentials file exists
    if [ -f "$DEFAULT_CREDENTIALS_PATH" ]; then
        echo -e "\n${GREEN}✅ Found credentials file at default location:${NC}"
        echo -e "${BLUE}$DEFAULT_CREDENTIALS_PATH${NC}"
        echo
        
        declare -a cred_options=(
            "✅ Use default credentials file (recommended)"
            "📁 Specify different credentials file path"
            "❓ What is this file?"
        )
        
        interactive_select "Choose credentials file option:" "${cred_options[@]}"
        cred_choice=$INTERACTIVE_SELECTION
        
        case $cred_choice in
            0)
                CREDENTIALS_PATH="$DEFAULT_CREDENTIALS_PATH"
                print_success "Using default credentials file"
                ;;
            1)
                get_custom_credentials_path
                ;;
            2)
                show_credentials_help
                get_custom_credentials_path
                ;;
        esac
    else
        print_warning "No credentials file found at default location: $DEFAULT_CREDENTIALS_PATH"
        echo
        show_credentials_help
        get_custom_credentials_path
    fi
}

get_custom_credentials_path() {
    echo
    while true; do
        read -p "Enter path to your credentials.json file: " custom_path
        
        # Expand ~ to home directory
        custom_path="${custom_path/#\~/$HOME}"
        
        if [ -f "$custom_path" ]; then
            CREDENTIALS_PATH="$custom_path"
            print_success "Using credentials file: $CREDENTIALS_PATH"
            break
        else
            print_error "File not found: $custom_path"
            echo "Please enter a valid file path or press Ctrl+C to exit"
        fi
    done
}

show_credentials_help() {
    echo -e "\n${BLUE}ℹ️ About the credentials file:${NC}"
    echo "This is your Google Cloud/Firebase service account key file."
    echo "You can download it from:"
    echo "• Google Cloud Console → IAM & Admin → Service Accounts"
    echo "• Firebase Console → Project Settings → Service Accounts"
    echo "• The file is usually named something like 'your-project-12345-abcdef123456.json'"
    echo
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
    
    # Memory and CPU configuration
    declare -a resource_options=(
        "Small (512Mi memory, 1 CPU)"
        "Medium (1Gi memory, 1 CPU)"
        "Large (2Gi memory, 2 CPU)"
        "Custom configuration"
    )
    
    declare -a memory_values=("512Mi" "1Gi" "2Gi" "custom")
    declare -a cpu_values=("1" "1" "2" "custom")
    
    interactive_select "Select Resource Configuration:" "${resource_options[@]}"
    resource_choice=$INTERACTIVE_SELECTION
    
    if [ $resource_choice -eq 3 ]; then  # Custom
        read -p "Memory (e.g., 512Mi, 1Gi): " MEMORY
        read -p "CPU (e.g., 1, 2): " CPU
    else
        MEMORY="${memory_values[$resource_choice]}"
        CPU="${cpu_values[$resource_choice]}"
    fi
    
    print_success "Configuration complete!"
    echo -e "\n${BLUE}Deployment Summary:${NC}"
    echo "Project: $PROJECT_ID"
    echo "Service: $SERVICE_NAME"
    echo "Region: $REGION"
    echo "Memory: $MEMORY"
    echo "CPU: $CPU"
    echo
}

# Main deployment flow
main() {
    select_project
    handle_env_file
    handle_credentials_file
    get_deployment_config
    
    echo
    read -p "Proceed with deployment? (y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        print_warning "Deployment cancelled."
        exit 0
    fi
    
    # Enable required services
    print_step "Enabling required Google Cloud services..."
    gcloud services enable run.googleapis.com \
                           containerregistry.googleapis.com \
                           secretmanager.googleapis.com \
                           --project="$PROJECT_ID"
    
    # Set default project
    gcloud config set project "$PROJECT_ID"
    
    # Setup Firebase credentials secret
    print_step "Setting up Firebase credentials secret..."
    SECRET_NAME="firebase-credentials"
    if ! gcloud secrets describe $SECRET_NAME --project="$PROJECT_ID" &>/dev/null; then
        print_step "Creating secret for Firebase credentials..."
        gcloud secrets create $SECRET_NAME --data-file="$CREDENTIALS_PATH" --project="$PROJECT_ID"
    else
        print_step "Updating existing Firebase credentials secret..."
        gcloud secrets versions add $SECRET_NAME --data-file="$CREDENTIALS_PATH" --project="$PROJECT_ID"
    fi
    
    # Setup IAM permissions
    print_step "Setting up IAM permissions for Secret Manager..."
    PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
    SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
    
    gcloud secrets add-iam-policy-binding $SECRET_NAME \
      --member="serviceAccount:$SERVICE_ACCOUNT" \
      --role="roles/secretmanager.secretAccessor" \
      --project="$PROJECT_ID"
    
    # Prepare environment variables
    print_step "Preparing environment variables..."
    ENV_VARS=""
    while IFS= read -r line; do
        if [[ ! $line =~ ^# && -n $line ]]; then
            clean_line=$(echo "$line" | sed 's/[[:space:]]*=[[:space:]]*/=/g')
            if [ -n "$ENV_VARS" ]; then
                ENV_VARS="$ENV_VARS,$clean_line"
            else
                ENV_VARS="$clean_line"
            fi
        fi
    done < "$ENV_PATH"
    
    # Copy credentials for Docker build
    print_step "Copying credentials file for Docker build..."
    if cp "$CREDENTIALS_PATH" "$ROOT_DIR/config/credentials.json" 2>/dev/null; then
        print_success "Credentials file copied successfully"
    elif [ -f "$ROOT_DIR/config/credentials.json" ]; then
        print_success "Credentials file already exists and is identical"
    else
        print_error "Failed to copy credentials file"
        exit 1
    fi
    
    # Build and push Docker image
    print_step "Building and pushing Docker image..."
    docker buildx build --platform linux/amd64 \
      -t gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
      -f "$SCRIPT_DIR/Dockerfile" \
      --push \
      "$ROOT_DIR"
    
    # Clean up existing service configuration if exists
    if gcloud run services describe $SERVICE_NAME --region=$REGION --project="$PROJECT_ID" &>/dev/null; then
        print_step "Cleaning up existing service configuration..."
        gcloud run services update $SERVICE_NAME \
          --region=$REGION \
          --project="$PROJECT_ID" \
          --clear-env-vars \
          --clear-secrets
    fi
    
    # Deploy to Cloud Run
    print_step "Deploying to Cloud Run..."
    gcloud run deploy $SERVICE_NAME \
      --image=gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
      --platform=managed \
      --region=$REGION \
      --project="$PROJECT_ID" \
      --port=8080 \
      --memory=$MEMORY \
      --cpu=$CPU \
      --min-instances=1 \
      --max-instances=1 \
      --concurrency=80 \
      --timeout=300s \
      --allow-unauthenticated \
      --no-cpu-throttling \
      --execution-environment=gen2 \
      --update-secrets=/secret/firebase-credentials=$SECRET_NAME:latest \
      --set-env-vars="$ENV_VARS"
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
      --region=$REGION \
      --project="$PROJECT_ID" \
      --format="value(status.url)")
    
    print_success "Deployment complete!"
    echo -e "\n${GREEN}🎉 Your Discord bot is now deployed!${NC}"
    echo -e "${BLUE}Service URL:${NC} $SERVICE_URL"
    
    # Check logs
    print_step "Checking deployment logs..."
    sleep 10
    gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME" \
      --limit=20 \
      --format="value(textPayload)" \
      --freshness=10m \
      --project="$PROJECT_ID"
    
    print_success "Deployment process finished!"
}

# Run main function
main 