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

FZF_AVAILABLE=0
if command -v fzf &>/dev/null; then
    FZF_AVAILABLE=1
fi

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
    echo -e "${GREEN}$1${NC}"
}

print_warning() {
    echo -e "${YELLOW}$1${NC}"
}

print_error() {
    echo -e "${RED}$1${NC}"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DEFAULT_CREDENTIALS_PATH="$ROOT_DIR/config/credentials.json"
ENV_PATH="$ROOT_DIR/config/.env"

print_header

if [ "$FZF_AVAILABLE" -eq 1 ]; then
    print_success "fzf detected: you can type to filter options in selection menus."
else
    print_warning "fzf not detected; falling back to arrow-key menu navigation."
fi

# Check if gcloud is installed and authenticated
print_step "Checking Google Cloud CLI..."
if ! command -v gcloud &> /dev/null; then
    print_error "Google Cloud CLI is not installed. Please install it first:"
    echo "https://cloud.google.com/sdk/docs/install"
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
                echo -e "${GREEN}${options[i]}${NC}"
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
                echo -e "\n${GREEN}Selected: ${options[$selected]}${NC}\n"
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

fuzzy_select_or_fallback() {
    local prompt="$1"
    shift
    local options=("$@")

    if [ "$FZF_AVAILABLE" -eq 1 ]; then
        local selection
        selection=$(printf '%s\n' "${options[@]}" | fzf --prompt="$prompt> " --height=15 --border --exit-0)
        if [ -z "$selection" ]; then
            print_warning "Selection cancelled."
            exit 0
        fi
        for i in "${!options[@]}"; do
            if [[ "${options[$i]}" == "$selection" ]]; then
                INTERACTIVE_SELECTION=$i
                return
            fi
        done
        print_error "Unable to match selection."
        exit 1
    else
        interactive_select "$prompt" "${options[@]}"
    fi
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
    fuzzy_select_or_fallback "Select a Google Cloud Project" "${project_options[@]}"
    selection=$INTERACTIVE_SELECTION
    
    PROJECT_ID="${project_ids[$selection]}"
    PROJECT_NAME="${project_names[$selection]}"
    
    print_success "Selected project: $PROJECT_ID ($PROJECT_NAME)"
}

# Function to validate .env file using Python helper
validate_env_file() {
    print_step "Validating .env file format and content..."
    
    # Paths
    EXAMPLE_PATH="$ROOT_DIR/config/.env.example"
    VALIDATOR_PATH="$ROOT_DIR/src/utils/env_validator.py"
    
    # Check if validator exists
    if [ ! -f "$VALIDATOR_PATH" ]; then
        print_error "Env validator not found: $VALIDATOR_PATH"
        exit 1
    fi
    
    # Check if .env.example exists
    if [ ! -f "$EXAMPLE_PATH" ]; then
        print_error ".env.example file not found: $EXAMPLE_PATH"
        exit 1
    fi
    
    # Check if .env exists
    if [ ! -f "$ENV_PATH" ]; then
        print_error ".env file not found: $ENV_PATH"
        exit 1
    fi
    
    # Run Python validator and capture output (disable set -e temporarily)
    echo "Running strict format validation..."
    set +e  # Temporarily disable exit on error
    VALIDATOR_OUTPUT=$(python3 "$VALIDATOR_PATH" "$EXAMPLE_PATH" "$ENV_PATH" 2>&1)
    VALIDATOR_EXIT_CODE=$?
    set -e  # Re-enable exit on error
    
    if [ $VALIDATOR_EXIT_CODE -eq 0 ]; then
        # Check if there are warnings in the output
        if echo "$VALIDATOR_OUTPUT" | grep -q " Warnings:"; then
            # Show output only if there are warnings
            echo "$VALIDATOR_OUTPUT"
            echo
            print_warning "Validation passed but with warnings!"
            echo -e "${YELLOW}Please review the warnings above.${NC}"
            echo -e "${BLUE}This is often normal for optional configuration fields.${NC}"
            echo -e "${BLUE}Check each warning to ensure it's expected for your deployment.${NC}"
            echo
            read -p "Press Enter to continue with deployment, or Ctrl+C to cancel..." dummy
        fi
        print_success ".env file validation passed!"
        sleep 1  # Brief pause so users can see the success message
        return 0
    else
        # Show validator output only on failure
        echo "$VALIDATOR_OUTPUT"
        echo
        declare -a fix_options=(
            "Edit the .env file now"
            "Exit and fix manually"
        )
        
        echo -e "${RED}Press Enter to continue and choose how to fix this...${NC}"
        read -p "" dummy
        
        interactive_select "How would you like to fix this?" "${fix_options[@]}"
        fix_choice=$INTERACTIVE_SELECTION
        
        if [ $fix_choice -eq 0 ]; then
            edit_env_file
            validate_env_file  # Re-validate after editing
        else
            print_warning "Please fix your .env file and run the script again."
            exit 1
        fi
    fi
}

# Function to handle .env file
handle_env_file() {
    print_step "Environment Configuration"
    
    if [ -f "$ENV_PATH" ]; then
        echo -e "\n${BLUE}Existing .env file found.${NC}"
        echo "Current contents:"
        echo -e "${YELLOW}$(cat "$ENV_PATH")${NC}"
        echo
        sleep 1  # Brief pause so users can read the .env contents
        
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
                validate_env_file
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
    
    # GitHub Client ID
    read -p "GitHub Client ID: " github_client_id
    
    # GitHub Client Secret
    read -p "GitHub Client Secret: " github_client_secret
    
    # OAuth Base URL (optional - will auto-detect on Cloud Run)
    read -p "OAuth Base URL (optional): " oauth_base_url

    # Discord Bot Client ID
    read -p "Discord Bot Client ID: " discord_bot_client_id

    # GitHub App configuration (invite-only mode)
    read -p "GitHub App ID: " github_app_id
    read -p "GitHub App Private Key (base64): " github_app_private_key_b64
    read -p "GitHub App Slug: " github_app_slug

    # SECRET_KEY (auto-generate if left blank)
    echo -e "${BLUE}SECRET_KEY is used to sign session cookies (required for security).${NC}"
    read -p "SECRET_KEY (leave blank to auto-generate): " secret_key
    if [ -z "$secret_key" ]; then
        secret_key=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        print_success "Auto-generated SECRET_KEY"
    fi

    # /sync optional vars
    echo -e "\n${BLUE}Optional: /sync command (manually trigger the data pipeline).${NC}"
    echo -e "${BLUE}Leave blank to use defaults (REPO_OWNER=ruxailab, REPO_NAME=disgitbot, WORKFLOW_REF=main).${NC}"
    read -p "REPO_OWNER (GitHub org that owns the pipeline repo) [ruxailab]: " repo_owner
    read -p "REPO_NAME (pipeline repo name) [disgitbot]: " repo_name
    read -p "WORKFLOW_REF (branch/tag to dispatch on) [main]: " workflow_ref

    # Create .env file
    cat > "$ENV_PATH" << EOF
DISCORD_BOT_TOKEN=$discord_token
GITHUB_CLIENT_ID=$github_client_id
GITHUB_CLIENT_SECRET=$github_client_secret
OAUTH_BASE_URL=$oauth_base_url
DISCORD_BOT_CLIENT_ID=$discord_bot_client_id
GITHUB_APP_ID=$github_app_id
GITHUB_APP_PRIVATE_KEY_B64=$github_app_private_key_b64
GITHUB_APP_SLUG=$github_app_slug
SECRET_KEY=$secret_key
REPO_OWNER=$repo_owner
REPO_NAME=$repo_name
WORKFLOW_REF=$workflow_ref
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
    
    read -p "GitHub Client ID [$GITHUB_CLIENT_ID]: " new_github_client_id
    github_client_id=${new_github_client_id:-$GITHUB_CLIENT_ID}
    
    read -p "GitHub Client Secret [$GITHUB_CLIENT_SECRET]: " new_github_client_secret
    github_client_secret=${new_github_client_secret:-$GITHUB_CLIENT_SECRET}
    
    read -p "OAuth Base URL [$OAUTH_BASE_URL]: " new_oauth_base_url
    oauth_base_url=${new_oauth_base_url:-$OAUTH_BASE_URL}

    read -p "Discord Bot Client ID [$DISCORD_BOT_CLIENT_ID]: " new_discord_bot_client_id
    discord_bot_client_id=${new_discord_bot_client_id:-$DISCORD_BOT_CLIENT_ID}

    read -p "GitHub App ID [$GITHUB_APP_ID]: " new_github_app_id
    github_app_id=${new_github_app_id:-$GITHUB_APP_ID}

    read -p "GitHub App Private Key (base64) [$GITHUB_APP_PRIVATE_KEY_B64]: " new_github_app_private_key_b64
    github_app_private_key_b64=${new_github_app_private_key_b64:-$GITHUB_APP_PRIVATE_KEY_B64}

    read -p "GitHub App Slug [$GITHUB_APP_SLUG]: " new_github_app_slug
    github_app_slug=${new_github_app_slug:-$GITHUB_APP_SLUG}

    read -p "SECRET_KEY [$SECRET_KEY]: " new_secret_key
    secret_key=${new_secret_key:-$SECRET_KEY}
    
    # Auto-generate if still empty (e.g. key was missing in old .env and user pressed Enter)
    if [ -z "$secret_key" ]; then
        echo -e "${BLUE}SECRET_KEY is empty. Auto-generating a secure key...${NC}"
        secret_key=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        print_success "Generated: $secret_key"
    fi

    # /sync optional vars
    echo -e "\n${BLUE}Optional: /sync vars (press Enter to keep current or use default).${NC}"
    read -p "REPO_OWNER [${REPO_OWNER:-ruxailab}]: " new_repo_owner
    repo_owner=${new_repo_owner:-${REPO_OWNER:-}}
    read -p "REPO_NAME [${REPO_NAME:-disgitbot}]: " new_repo_name
    repo_name=${new_repo_name:-${REPO_NAME:-}}
    read -p "WORKFLOW_REF [${WORKFLOW_REF:-main}]: " new_workflow_ref
    workflow_ref=${new_workflow_ref:-${WORKFLOW_REF:-}}

    # Update .env file
    cat > "$ENV_PATH" << EOF
DISCORD_BOT_TOKEN=$discord_token
GITHUB_CLIENT_ID=$github_client_id
GITHUB_CLIENT_SECRET=$github_client_secret
OAUTH_BASE_URL=$oauth_base_url
DISCORD_BOT_CLIENT_ID=$discord_bot_client_id
GITHUB_APP_ID=$github_app_id
GITHUB_APP_PRIVATE_KEY_B64=$github_app_private_key_b64
GITHUB_APP_SLUG=$github_app_slug
SECRET_KEY=$secret_key
REPO_OWNER=$repo_owner
REPO_NAME=$repo_name
WORKFLOW_REF=$workflow_ref
EOF
    
    print_success ".env file updated successfully!"
}

# Function to handle credentials file
handle_credentials_file() {
    print_step "Firebase/Google Cloud Credentials Configuration"
    
    # Check if default credentials file exists
    if [ -f "$DEFAULT_CREDENTIALS_PATH" ]; then
        echo -e "\n${GREEN} Found credentials file at default location:${NC}"
        echo -e "${BLUE}$DEFAULT_CREDENTIALS_PATH${NC}"
        echo
        
        declare -a cred_options=(
            " Use default credentials file (recommended)"
            " Specify different credentials file path"
            " What is this file?"
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
                echo
                read -p "Press Enter to continue..." dummy
                handle_credentials_file
                return
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
    echo -e "\n${BLUE}ℹ About the credentials file:${NC}"
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
    
    fuzzy_select_or_fallback "Select a Google Cloud Region" "${region_options[@]}"
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
    
    fuzzy_select_or_fallback "Select Resource Configuration" "${resource_options[@]}"
    resource_choice=$INTERACTIVE_SELECTION
    
    if [ $resource_choice -eq 3 ]; then  # Custom
        read -p "Memory (e.g., 512Mi, 1Gi): " MEMORY
        read -p "CPU (e.g., 1, 2): " CPU
    else
        MEMORY="${memory_values[$resource_choice]}"
        CPU="${cpu_values[$resource_choice]}"
    fi
    
    print_success "Configuration complete!"
}

# Main deployment flow
main() {
    select_project
    handle_env_file
    handle_credentials_file
    get_deployment_config
    
    # Show comprehensive deployment summary
    echo -e "\n${PURPLE}================================${NC}"
    echo -e "${PURPLE}   DEPLOYMENT SUMMARY${NC}"
    echo -e "${PURPLE}================================${NC}"
    echo -e "${BLUE}Google Cloud Configuration:${NC}"
    echo "  Project: $PROJECT_ID ($PROJECT_NAME)"
    echo "  Service: $SERVICE_NAME"
    echo "  Region: $REGION"
    echo "  Memory: $MEMORY"
    echo "  CPU: $CPU"
    echo
    echo -e "${BLUE}Environment Configuration:${NC}"
    echo "  .env file: $ENV_PATH"
    echo "  Credentials: $CREDENTIALS_PATH"
    echo
    echo -e "${BLUE}What will be deployed:${NC}"
    echo "  • Discord bot with Flask OAuth integration"
    echo "  • Firebase/Firestore database connection"
    echo "  • GitHub OAuth authentication"
    echo "  • Cloud Run service with public URL"
    echo
    echo -e "${YELLOW}This will:${NC}"
    echo "  • Build and push Docker image using Google Cloud Build (no local Docker needed!)"
    echo "  • Deploy to Cloud Run with REQUEST-BASED BILLING (cost optimized!)"
    echo "  • Set up secrets and environment variables"
    echo "  • Enable required Google Cloud services"
    echo "  • Generate a public URL for your bot"
    echo
    echo -e "${GREEN}COST OPTIMIZATION:${NC}"
    echo "  • Uses REQUEST-BASED billing (only pay when processing requests)"
    echo "  • Scales to zero when not in use (no charges during idle time)"
    echo "  • Estimated cost: ~$0.000024 per 100ms of CPU time + $0.00000240 per 100ms of memory"
    echo -e "${PURPLE}================================${NC}"
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
                           cloudbuild.googleapis.com \
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
    echo " DEBUG: Processing .env file line by line:"
    
    # Ensure file ends with newline to avoid last line parsing issues
    echo "" >> "$ENV_PATH"
    
    while IFS= read -r line || [[ -n "$line" ]]; do
        echo "  Raw line: '$line'"
        if [[ ! $line =~ ^# && -n $line ]]; then
            clean_line=$(echo "$line" | sed 's/[[:space:]]*=[[:space:]]*/=/g')
            echo "   Adding: '$clean_line'"
            if [ -n "$ENV_VARS" ]; then
                ENV_VARS="$ENV_VARS,$clean_line"
            else
                ENV_VARS="$clean_line"
            fi
        else
            echo "   Skipping: comment or empty"
        fi
    done < "$ENV_PATH"
    
    # Debug: Show what we parsed
    echo -e "\n${BLUE} DEBUG: Environment variables parsing:${NC}"
    echo "ENV_VARS length: ${#ENV_VARS}"
    echo "ENV_VARS content: '$ENV_VARS'"
    echo "Number of variables: $(echo "$ENV_VARS" | tr ',' '\n' | wc -l)"
    echo
    
    # Final check - ensure we have environment variables
    if [ -z "$ENV_VARS" ]; then
        print_error "No valid environment variables found!"
        echo -e "\n${YELLOW}This error occurs when your .env file is empty or contains only comments.${NC}"
        echo -e "${BLUE}This usually happens because:${NC}"
        echo "  • The .env file validation was skipped"
        echo "  • The .env file was modified after validation"
        echo "  • The .env file contains only comments or empty lines"
        echo "  • Hidden characters or encoding issues"
        echo "  • Different shell/platform behavior"
        echo
        echo -e "${BLUE} Let's debug the .env file:${NC}"
        echo "File exists: $([ -f "$ENV_PATH" ] && echo 'YES' || echo 'NO')"
        echo "File size: $(wc -c < "$ENV_PATH" 2>/dev/null || echo 'ERROR')"
        echo "File encoding: $(file "$ENV_PATH" 2>/dev/null || echo 'UNKNOWN')"
        echo
        echo -e "${BLUE}Raw file contents with line numbers:${NC}"
        cat -n "$ENV_PATH"
        echo
        echo -e "${BLUE}File with visible characters (showing spaces/tabs):${NC}"
        cat -A "$ENV_PATH"
        echo
        echo -e "${RED}Cannot deploy without environment variables!${NC}"
        echo -e "${BLUE}Please run the script again and ensure your .env file has the required variables.${NC}"
        exit 1
    fi
    
    print_success "Environment variables prepared successfully (${#ENV_VARS} characters)"
    
    # Copy credentials for Cloud Build
    print_step "Copying credentials file for Cloud Build..."
    if cp "$CREDENTIALS_PATH" "$ROOT_DIR/config/credentials.json" 2>/dev/null; then
        print_success "Credentials file copied successfully"
    elif [ -f "$ROOT_DIR/config/credentials.json" ]; then
        print_success "Credentials file already exists and is identical"
    else
        print_error "Failed to copy credentials file"
        exit 1
    fi
    
    # Build and push Docker image using Google Cloud Build
    print_step "Building and pushing Docker image using Google Cloud Build..."
    print_step "This eliminates the need for local Docker daemon - building in the cloud! "
    
    # Copy Dockerfile to root directory for Cloud Build
    print_step "Preparing Dockerfile for Cloud Build..."
    cp "$SCRIPT_DIR/Dockerfile" "$ROOT_DIR/Dockerfile"
    
    # Copy shared directory into build context so Docker can access it
    print_step "Copying shared directory into build context..."
    if [ -d "$(dirname "$ROOT_DIR")/shared" ]; then
        cp -r "$(dirname "$ROOT_DIR")/shared" "$ROOT_DIR/shared"
        print_success "Shared directory copied successfully"
    else
        print_warning "Shared directory not found - skipping shared copy"
    fi
    
    # Copy pr_review directory into build context for PR automation
    print_step "Copying pr_review directory into build context..."
    if [ -d "$(dirname "$ROOT_DIR")/pr_review" ]; then
        cp -r "$(dirname "$ROOT_DIR")/pr_review" "$ROOT_DIR/pr_review"
        print_success "pr_review directory copied successfully"
    else
        print_warning "pr_review directory not found - skipping pr_review copy"
    fi
    
    # Use Cloud Build to build and push the image
    gcloud builds submit \
      --tag gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
      --project="$PROJECT_ID" \
      "$ROOT_DIR"
    
    # Clean up temporary files
    rm -f "$ROOT_DIR/Dockerfile"
    if [ -d "$ROOT_DIR/shared" ]; then
        rm -rf "$ROOT_DIR/shared"
        print_step "Cleaned up temporary shared directory"
    fi
    if [ -d "$ROOT_DIR/pr_review" ]; then
        rm -rf "$ROOT_DIR/pr_review"
        print_step "Cleaned up temporary pr_review directory"
    fi
    print_success "Build completed and temporary files cleaned up!"
    
    # Clean up existing service configuration if exists
    if gcloud run services describe $SERVICE_NAME --region=$REGION --project="$PROJECT_ID" &>/dev/null; then
        print_step "Cleaning up existing service configuration..."
        gcloud run services update $SERVICE_NAME \
          --region=$REGION \
          --project="$PROJECT_ID" \
          --clear-env-vars \
          --clear-secrets
    fi
    
    # Deploy to Cloud Run with REQUEST-BASED BILLING (cost optimized)
    print_step "Deploying to Cloud Run with REQUEST-BASED BILLING..."
    print_step "This will scale to zero when not in use, significantly reducing costs!"
    gcloud run deploy $SERVICE_NAME \
      --image=gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
      --platform=managed \
      --region=$REGION \
      --project="$PROJECT_ID" \
      --port=8080 \
      --memory=$MEMORY \
      --cpu=$CPU \
      --min-instances=0 \
      --max-instances=1 \
      --concurrency=80 \
      --timeout=300s \
      --allow-unauthenticated \
      --cpu-throttling \
      --execution-environment=gen2 \
      --update-secrets=/secret/firebase-credentials=$SECRET_NAME:latest \
      --set-env-vars="$ENV_VARS"
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
      --region=$REGION \
      --project="$PROJECT_ID" \
      --format="value(status.url)")
    
    print_success "Deployment complete!"
    echo -e "\n${GREEN} Your Discord bot is now deployed!${NC}"
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
