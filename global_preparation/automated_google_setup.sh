#!/bin/bash

# =============================================================================
# Automated Google Cloud Setup for Toolathlon
# =============================================================================
# This script automates the following:
# 1. Google Cloud Project creation (optional)
# 2. Service account creation
# 3. Service account key generation
# 4. API key creation
# 5. Enable all required Google Cloud APIs
# 6. OAuth credentials generation (with automated callback server)
# 7. Auto-filling token_key_session.py with all the credentials
#
# What still needs to be done MANUALLY:
# - Having a Google Account (gmail address) - cannot be automated
# - Creating OAuth client ID in Cloud Console - no CLI support
# - Downloading gcp-oauth.keys.json to configs/
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVICE_ACCOUNT_NAME="toolathlon-service-account"
SERVICE_ACCOUNT_DISPLAY_NAME="Toolathlon Service Account"
API_KEY_DISPLAY_NAME="Toolathlon API Key"
SERVICE_ACCOUNT_KEY_FILE="configs/gcp-service_account.keys.json"

echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}       Automated Google Cloud Setup for Toolathlon${NC}"
echo -e "${BLUE}================================================================${NC}"
echo ""

# =============================================================================
# Step 0: Check prerequisites
# =============================================================================
echo -e "${YELLOW}[Step 0]${NC} Checking prerequisites..."

if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}ERROR: gcloud CLI not found!${NC}"
    echo "Please install it first"
    exit 1
fi

# Check for uv (Python package manager used by Toolathlon)
if ! command -v uv &> /dev/null; then
    echo -e "${RED}ERROR: uv not found!${NC}"
    echo "Please install it: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

# Check if logged in to gcloud
if ! gcloud auth list --format="value(account)" | grep -q .; then
    echo -e "${YELLOW}Not logged in to Google Cloud. Initiating login...${NC}"
    gcloud auth login
else
    # User is already logged in
    CURRENT_ACCOUNT=$(gcloud auth list --format='value(account)' --filter=status:ACTIVE)
    echo -e "${GREEN}✓ Currently logged in to Google Cloud${NC}"
    echo -e "  Account: ${BLUE}$CURRENT_ACCOUNT${NC}"
    echo ""

    # Ask if user wants to use this account or switch
    read -p "Do you want to use this account, or switch to a different one? [use/Switch]: " -r
    echo

    if [[ $REPLY =~ ^[Ss] ]]; then
        echo -e "${YELLOW}Switching Google account...${NC}"
        gcloud auth login
        CURRENT_ACCOUNT=$(gcloud auth list --format='value(account)' --filter=status:ACTIVE)
        echo -e "${GREEN}✓ Now logged in as: ${BLUE}$CURRENT_ACCOUNT${NC}"
    else
        echo -e "${GREEN}✓ Using current account: ${BLUE}$CURRENT_ACCOUNT${NC}"
    fi
fi

echo ""

# Get current project
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)

# Always ask user to confirm or change project
if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" == "(unset)" ]; then
    echo -e "${YELLOW}No Google Cloud project is currently set.${NC}"
    echo ""
    HAS_PROJECT=false
else
    echo -e "${GREEN}Current Google Cloud project: ${BLUE}$PROJECT_ID${NC}"
    echo ""
    HAS_PROJECT=true
fi

echo "What would you like to do?"
echo "  1. Use current project (if set) or enter existing project ID"
echo "  2. Create a new project"
echo ""
read -p "Enter choice [1/2]: " -n 1 -r
echo
echo ""

if [[ $REPLY == "2" ]]; then
    # Create new project
    echo "Creating a new Google Cloud Project..."
    echo ""

    # Generate a unique project ID
    TIMESTAMP=$(date +%s)
    DEFAULT_PROJECT_ID="toolathlon-eval-${TIMESTAMP}"

    echo -e "${BLUE}Suggested project ID: ${DEFAULT_PROJECT_ID}${NC}"
    read -p "Enter project ID (or press Enter to use suggested): " USER_PROJECT_ID

    if [ -z "$USER_PROJECT_ID" ]; then
        PROJECT_ID=$DEFAULT_PROJECT_ID
    else
        PROJECT_ID=$USER_PROJECT_ID
    fi

    echo "Creating project: $PROJECT_ID"
    echo ""

    # Create the project
    if gcloud projects create $PROJECT_ID --name="Toolathlon Evaluation" 2>&1; then
        echo -e "${GREEN}✓ Project created successfully${NC}"

        # Set as default project
        gcloud config set project $PROJECT_ID
        echo -e "${GREEN}✓ Set as default project${NC}"
    else
        echo -e "${RED}ERROR: Failed to create project${NC}"
        echo "The project ID might already exist or be invalid."
        exit 1
    fi
else
    # Use existing project
    if [ "$HAS_PROJECT" = true ]; then
        read -p "Use current project '$PROJECT_ID'? [Y/n]: " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            read -p "Enter project ID to use: " USER_PROJECT_ID
            PROJECT_ID=$USER_PROJECT_ID
            gcloud config set project $PROJECT_ID
        fi
    else
        read -p "Enter project ID to use: " USER_PROJECT_ID
        PROJECT_ID=$USER_PROJECT_ID
        gcloud config set project $PROJECT_ID
    fi
fi

echo ""
echo -e "${GREEN}✓ Using project: ${BLUE}$PROJECT_ID${NC}"
echo ""

# Get current account (in case it changed during login)
CURRENT_ACCOUNT=$(gcloud auth list --format='value(account)' --filter=status:ACTIVE)

# Check and ensure billing is enabled
echo -e "${YELLOW}Checking billing status...${NC}"

# Get billing account linked to project
BILLING_ACCOUNT=$(gcloud billing projects describe $PROJECT_ID --format="value(billingAccountName)" 2>/dev/null)

if [ -z "$BILLING_ACCOUNT" ] || [ "$BILLING_ACCOUNT" == "" ]; then
    echo -e "${RED}⚠️  No billing account linked to this project!${NC}"
    echo ""
    echo "Many Google Cloud APIs require billing to be enabled."
    echo "You need to link a billing account to this project."
    echo ""
    echo -e "${GREEN}💡 Don't worry:${NC} For new Google Cloud accounts, you have over ${BLUE}\$2000 USD${NC} in free credits"
    echo "   after linking a billing account. This is more than enough to evaluate the benchmark"
    echo "   100+ times, so you won't be charged in the beginning."
    echo ""
    echo "Please open the link to link a billing account to this project:"
    echo "  https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID&authuser=$CURRENT_ACCOUNT"
    echo ""

    # Try to open browser
    if command -v xdg-open &> /dev/null; then
        xdg-open "https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID&authuser=$CURRENT_ACCOUNT" 2>/dev/null &
    elif command -v open &> /dev/null; then
        open "https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID&authuser=$CURRENT_ACCOUNT" 2>/dev/null &
    fi

    read -p "Press Enter once you've linked a billing account..."
    echo ""

    # Verify billing is now enabled
    BILLING_ACCOUNT=$(gcloud billing projects describe $PROJECT_ID --format="value(billingAccountName)" 2>/dev/null)
    if [ -z "$BILLING_ACCOUNT" ] || [ "$BILLING_ACCOUNT" == "" ]; then
        echo -e "${RED}ERROR: Billing still not enabled${NC}"
        echo "Cannot proceed without billing enabled."
        exit 1
    fi
fi

echo -e "${GREEN}✓ Billing enabled${NC}"
echo -e "  Billing Account: ${BLUE}$(basename $BILLING_ACCOUNT)${NC}"
echo ""

echo -e "${GREEN}✓ Prerequisites check passed${NC}"
echo -e "  Project ID: ${BLUE}$PROJECT_ID${NC}"
echo -e "  Account: ${BLUE}$(gcloud auth list --format='value(account)' --filter=status:ACTIVE)${NC}"
echo ""

# =============================================================================
# Step 1: Enable Required APIs
# =============================================================================
echo -e "${YELLOW}[Step 1]${NC} Enabling required Google Cloud APIs..."
echo ""
echo "This will enable 40+ APIs required for Toolathlon (YouTube, Gmail, Drive, etc.)"
echo "This may take 1-2 minutes..."
echo ""

if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    echo ""
    echo "Enabling Google Cloud API services..."

    # Core Google APIs
    echo "Enabling core Google APIs..."
    gcloud services enable youtube.googleapis.com            # YouTube Data API v3
    gcloud services enable gmail.googleapis.com              # Gmail API
    gcloud services enable sheets.googleapis.com             # Google Sheets API
    gcloud services enable calendar-json.googleapis.com      # Google Calendar API
    gcloud services enable drive.googleapis.com              # Google Drive API
    gcloud services enable forms.googleapis.com              # Google Forms API

    # Analytics and BigQuery APIs
    echo "Enabling Analytics and BigQuery APIs..."
    gcloud services enable analyticshub.googleapis.com       # Analytics Hub API
    gcloud services enable bigquery.googleapis.com           # BigQuery API
    gcloud services enable bigqueryconnection.googleapis.com # BigQuery Connection API
    gcloud services enable bigquerydatapolicy.googleapis.com # BigQuery Data Policy API
    gcloud services enable bigquerymigration.googleapis.com  # BigQuery Migration API
    gcloud services enable bigqueryreservation.googleapis.com # BigQuery Reservation API
    gcloud services enable bigquerystorage.googleapis.com    # BigQuery Storage API

    # Cloud Platform APIs
    echo "Enabling Cloud Platform APIs..."
    gcloud services enable dataplex.googleapis.com           # Cloud Dataplex API
    gcloud services enable datastore.googleapis.com          # Cloud Datastore API
    gcloud services enable logging.googleapis.com            # Cloud Logging API
    gcloud services enable monitoring.googleapis.com         # Cloud Monitoring API
    gcloud services enable oslogin.googleapis.com            # Cloud OS Login API
    gcloud services enable sqladmin.googleapis.com           # Cloud SQL
    gcloud services enable storage.googleapis.com            # Cloud Storage
    gcloud services enable storage-component.googleapis.com  # Cloud Storage API
    gcloud services enable cloudtrace.googleapis.com         # Cloud Trace API
    gcloud services enable compute.googleapis.com            # Compute Engine API

    # Search and Maps APIs
    echo "Enabling Search and Maps APIs..."
    gcloud services enable customsearch.googleapis.com       # Custom Search API
    gcloud services enable directions-backend.googleapis.com # Directions API
    gcloud services enable distance-matrix-backend.googleapis.com # Distance Matrix API
    gcloud services enable mapsgrounding.googleapis.com      # Maps Grounding API
    gcloud services enable places-backend.googleapis.com     # Places API
    gcloud services enable routes.googleapis.com             # Routes API
    gcloud services enable geocoding-backend.googleapis.com  # Geocoding API
    gcloud services enable elevation-backend.googleapis.com  # Elevation API

    # Data and Document APIs
    echo "Enabling Data and Document APIs..."
    gcloud services enable dataform.googleapis.com           # Dataform API
    gcloud services enable driveactivity.googleapis.com      # Drive Activity API
    gcloud services enable docs.googleapis.com               # Google Docs API
    gcloud services enable slides.googleapis.com             # Google Slides API

    # Service Management APIs
    echo "Enabling Service Management APIs..."
    gcloud services enable privilegedaccessmanager.googleapis.com # Privileged Access Manager API
    gcloud services enable servicemanagement.googleapis.com  # Service Management API
    gcloud services enable serviceusage.googleapis.com       # Service Usage API

    echo ""
    echo -e "${GREEN}✓ All Google Cloud API services have been enabled${NC}"
else
    echo ""
    echo -e "${YELLOW}⚠ Skipping API enablement${NC}"
    echo "You can enable them later by running:"
    echo "  bash global_preparation/batch_enable_gloud_apis.sh $PROJECT_ID"
fi

echo ""

# =============================================================================
# Step 2: Create Service Account
# =============================================================================
echo -e "${YELLOW}[Step 2]${NC} Creating service account..."

# Check if service account already exists
if gcloud iam service-accounts list --format="value(email)" | grep -q "${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}"; then
    echo -e "${GREEN}✓ Service account already exists: ${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com${NC}"
    SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
else
    echo "Creating service account: $SERVICE_ACCOUNT_NAME"
    gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
        --display-name="$SERVICE_ACCOUNT_DISPLAY_NAME" \
        --project=$PROJECT_ID

    SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
    echo -e "${GREEN}✓ Service account created: $SERVICE_ACCOUNT_EMAIL${NC}"
fi
echo ""

# =============================================================================
# Step 3: Grant roles to Service Account
# =============================================================================
echo -e "${YELLOW}[Step 3]${NC} Granting Owner role to service account..."

# Grant Owner role (required for BigQuery, GCS, etc.)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/owner" \
    --quiet

echo -e "${GREEN}✓ Owner role granted to service account${NC}"
echo ""

# =============================================================================
# Step 4: Create Service Account Key
# =============================================================================
echo -e "${YELLOW}[Step 4]${NC} Creating service account key..."

# Create configs directory if it doesn't exist
mkdir -p configs

# Check if key file already exists
if [ -f "$SERVICE_ACCOUNT_KEY_FILE" ]; then
    echo -e "${YELLOW}⚠ Service account key file already exists: $SERVICE_ACCOUNT_KEY_FILE${NC}"
    read -p "Do you want to create a new key? (This will overwrite the existing file) [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping service account key creation."
    else
        gcloud iam service-accounts keys create $SERVICE_ACCOUNT_KEY_FILE \
            --iam-account=$SERVICE_ACCOUNT_EMAIL \
            --project=$PROJECT_ID
        echo -e "${GREEN}✓ Service account key created: $SERVICE_ACCOUNT_KEY_FILE${NC}"
    fi
else
    gcloud iam service-accounts keys create $SERVICE_ACCOUNT_KEY_FILE \
        --iam-account=$SERVICE_ACCOUNT_EMAIL \
        --project=$PROJECT_ID
    echo -e "${GREEN}✓ Service account key created: $SERVICE_ACCOUNT_KEY_FILE${NC}"
fi
echo ""

# =============================================================================
# Step 5: Create API Key
# =============================================================================
echo -e "${YELLOW}[Step 5]${NC} Creating API key..."

# Check if API key with this name already exists
EXISTING_KEY=$(gcloud services api-keys list --format="value(name)" --filter="displayName:$API_KEY_DISPLAY_NAME" 2>/dev/null | head -1)

if [ -n "$EXISTING_KEY" ]; then
    echo -e "${GREEN}✓ API key already exists with display name: $API_KEY_DISPLAY_NAME${NC}"
    # Get the key string
    API_KEY=$(gcloud services api-keys get-key-string $EXISTING_KEY --format="value(keyString)")
else
    echo "Creating new API key..."

    # Create API key and get the full response (includes operation name)
    CREATE_OUTPUT=$(gcloud services api-keys create \
        --display-name="$API_KEY_DISPLAY_NAME" \
        --project=$PROJECT_ID \
        --format="json")

    # Extract the operation name and key resource name
    OPERATION_NAME=$(echo "$CREATE_OUTPUT" | uv run python -c "import sys, json; data=json.load(sys.stdin); print(data.get('name', ''))")

    if [[ "$OPERATION_NAME" == operations/* ]]; then
        echo "Waiting for API key creation to complete..."

        # Wait for operation to complete (up to 2 minutes)
        for i in {1..120}; do
            sleep 1

            # Check operation status
            OP_STATUS=$(gcloud services operations describe "$OPERATION_NAME" --format="json" 2>/dev/null)

            if echo "$OP_STATUS" | grep -q '"done": true'; then
                # Operation complete, extract the key resource name
                API_KEY_RESOURCE=$(echo "$OP_STATUS" | uv run python -c "import sys, json; data=json.load(sys.stdin); print(data.get('response', {}).get('name', ''))")

                if [ -n "$API_KEY_RESOURCE" ]; then
                    echo -e "${GREEN}✓ API key created${NC}"
                    break
                fi
            fi

            if [ $i -eq 120 ]; then
                echo -e "${RED}ERROR: API key creation timed out${NC}"
                exit 1
            fi
        done
    else
        # If not an operation, use the name directly (older gcloud versions)
        API_KEY_RESOURCE=$(echo "$CREATE_OUTPUT" | uv run python -c "import sys, json; data=json.load(sys.stdin); print(data.get('name', ''))")
    fi

    # Now get the actual key string
    if [ -n "$API_KEY_RESOURCE" ]; then
        API_KEY=$(gcloud services api-keys get-key-string "$API_KEY_RESOURCE" --format="value(keyString)")

        if [ -z "$API_KEY" ]; then
            echo -e "${RED}ERROR: Could not retrieve API key string${NC}"
            exit 1
        fi
    else
        echo -e "${RED}ERROR: Could not get API key resource name${NC}"
        exit 1
    fi
fi

echo -e "  API Key: ${BLUE}${API_KEY:0:30}...${NC}"
echo ""

# =============================================================================
# Step 6: OAuth Credentials (User Authentication)
# =============================================================================
echo -e "${YELLOW}[Step 6]${NC} Setting up OAuth credentials..."

# Check if OAuth keys file exists
if [ ! -f "configs/gcp-oauth.keys.json" ]; then
    echo -e "${YELLOW}OAuth keys not found. Starting interactive OAuth setup...${NC}"
    echo ""
    echo "Unfortunately, Google doesn't provide CLI/API for OAuth client creation"
    echo "for regular Gmail accounts. This requires manual steps in the console."
    echo ""
    echo "This helper will guide you through the 3-minute setup process."
    echo ""
    read -p "Press Enter to begin OAuth setup, or Ctrl+C to exit..."
    echo ""
    NEED_OAUTH_SETUP=true
else
    echo -e "${GREEN}✓ OAuth keys file found: configs/gcp-oauth.keys.json${NC}"
    echo ""
    read -p "Do you want to redo OAuth setup (will overwrite existing keys)? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Removing old OAuth keys file...${NC}"
        rm -f "configs/gcp-oauth.keys.json"
        echo ""
        echo "Starting interactive OAuth setup..."
        echo ""
        echo "Unfortunately, Google doesn't provide CLI/API for OAuth client creation"
        echo "for regular Gmail accounts. This requires manual steps in the console."
        echo ""
        echo "This helper will guide you through the 3-minute setup process."
        echo ""
        read -p "Press Enter to begin OAuth setup, or Ctrl+C to exit..."
        echo ""
        NEED_OAUTH_SETUP=true
    else
        echo "Using existing OAuth keys."
        NEED_OAUTH_SETUP=false
    fi
fi

if [ "$NEED_OAUTH_SETUP" = true ]; then
    # Step 6.1: Configure OAuth Consent Screen
    echo "================================================================"
    echo "STEP 6.1: Configure OAuth Consent Screen"
    echo "================================================================"
    echo ""
    echo "Opening URL in your browser..."
    echo "  https://console.cloud.google.com/apis/credentials/consent?project=$PROJECT_ID&authuser=$CURRENT_ACCOUNT"
    echo ""
    echo "In the browser, please do the following:"
    echo "  1. Click 'get started'"
    echo "  2. Fill in the form:"
    echo "     - App name: Toolathlon Evaluation"
    echo "     - User support email: $CURRENT_ACCOUNT"
    echo "     - Audience: External"
    echo "  3. Proceed to finish this"
    echo ""

    # Try to open browser
    if command -v xdg-open &> /dev/null; then
        xdg-open "https://console.cloud.google.com/apis/credentials/consent?project=$PROJECT_ID&authuser=$CURRENT_ACCOUNT" 2>/dev/null &
    elif command -v open &> /dev/null; then
        open "https://console.cloud.google.com/apis/credentials/consent?project=$PROJECT_ID&authuser=$CURRENT_ACCOUNT" 2>/dev/null &
    fi

    read -p "Press Enter when Step 6.1 is complete..."
    echo ""

    # Step 6.2: Publish the App
    echo "================================================================"
    echo "STEP 6.2: Publish the App (IMPORTANT!)"
    echo "================================================================"
    echo ""
    echo "Opening URL in your browser..."
    echo "  https://console.cloud.google.com/auth/audience?project=$PROJECT_ID&authuser=$CURRENT_ACCOUNT"
    echo ""
    echo "In the browser, please do the following:"
    echo "  1. Click 'PUBLISH APP' button"
    echo "  2. Click 'Confirm' in the popup"
    echo ""
    echo -e "${YELLOW}⚠️  Why is this important?${NC}"
    echo "   Without publishing, your OAuth tokens will expire every 7 days!"
    echo "   You'll have to re-authenticate weekly (very annoying)."
    echo ""

    # Try to open browser
    if command -v xdg-open &> /dev/null; then
        xdg-open "https://console.cloud.google.com/auth/audience?project=$PROJECT_ID&authuser=$CURRENT_ACCOUNT" 2>/dev/null &
    elif command -v open &> /dev/null; then
        open "https://console.cloud.google.com/auth/audience?project=$PROJECT_ID&authuser=$CURRENT_ACCOUNT" 2>/dev/null &
    fi

    read -p "Press Enter when Step 6.2 is complete..."
    echo ""

    # Step 6.3: Create OAuth Client ID
    echo "================================================================"
    echo "STEP 6.3: Create OAuth Client ID"
    echo "================================================================"
    echo ""
    echo "Opening URL in your browser..."
    echo "  https://console.cloud.google.com/auth/clients/create?project=$PROJECT_ID&authuser=$CURRENT_ACCOUNT"
    echo ""
    echo "In the browser, please do the following:"
    echo "  1. Application type: Web application"
    echo "  2. Name: Web client 1"
    echo "  3. Add authorized redirect URIs: http://localhost:3000/oauth2callback"
    echo "  4. Click 'CREATE'"
    echo "  5. Click 'DOWNLOAD JSON' (or if it doesn't work, click 'OK', then click into the client you just created,"
    echo "     and click the download icon in the 'Client secret' field)"
    echo "  6. Rename and Save the file to: $(pwd)/configs/gcp-oauth.keys.json"
    echo ""

    # Create configs directory
    mkdir -p configs

    # Try to open browser
    if command -v xdg-open &> /dev/null; then
        xdg-open "https://console.cloud.google.com/auth/clients/create?project=$PROJECT_ID&authuser=$CURRENT_ACCOUNT" 2>/dev/null &
    elif command -v open &> /dev/null; then
        open "https://console.cloud.google.com/auth/clients/create?project=$PROJECT_ID&authuser=$CURRENT_ACCOUNT" 2>/dev/null &
    fi

    read -p "Press Enter when you've downloaded the JSON file..."
    echo ""

    # Verify file exists
    if [ ! -f "configs/gcp-oauth.keys.json" ]; then
        echo -e "${RED}ERROR: configs/gcp-oauth.keys.json not found!${NC}"
        echo ""
        echo "Please make sure you:"
        echo "  1. Downloaded the JSON file from the browser"
        echo "  2. Saved it as: $(pwd)/configs/gcp-oauth.keys.json"
        echo ""
        echo "Then run this script again:"
        echo "  bash global_preparation/automated_google_setup.sh"
        exit 1
    fi

    echo -e "${GREEN}✓ OAuth keys file found!${NC}"
    echo ""
fi

# Check if credentials already exist
if [ -f "configs/google_credentials.json" ]; then
    echo -e "${GREEN}✓ OAuth credentials already exist: configs/google_credentials.json${NC}"
    read -p "Do you want to regenerate OAuth credentials? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Running OAuth flow..."
        uv run global_preparation/simple_google_auth.py
    else
        echo "Using existing OAuth credentials."
    fi
else
    echo "Running OAuth flow (browser will open for authentication)..."
    uv run global_preparation/simple_google_auth.py
fi

echo ""

# =============================================================================
# Step 7: Auto-fill token_key_session.py
# =============================================================================
echo -e "${YELLOW}[Step 7]${NC} Updating token_key_session.py with credentials..."

# Read OAuth credentials using uv run python
if [ -f "configs/google_credentials.json" ]; then
    GOOGLE_CLIENT_ID=$(uv run python -c "import json; print(json.load(open('configs/google_credentials.json'))['client_id'])")
    GOOGLE_CLIENT_SECRET=$(uv run python -c "import json; print(json.load(open('configs/google_credentials.json'))['client_secret'])")
    GOOGLE_REFRESH_TOKEN=$(uv run python -c "import json; print(json.load(open('configs/google_credentials.json'))['refresh_token'])")
else
    echo -e "${RED}ERROR: configs/google_credentials.json not found!${NC}"
    echo "OAuth credentials generation failed."
    exit 1
fi

# Create Python script to update token_key_session.py using uv
uv run python << EOF
import re

# Read the file
with open('configs/token_key_session.py', 'r') as f:
    content = f.read()

# Update Google-related fields
content = re.sub(
    r'google_cloud_console_api_key = "[^"]*"',
    f'google_cloud_console_api_key = "${API_KEY}"',
    content
)

content = re.sub(
    r'gcp_project_id = "[^"]*"',
    f'gcp_project_id = "${PROJECT_ID}"',
    content
)

content = re.sub(
    r'gcp_service_account_path = "[^"]*"',
    f'gcp_service_account_path = "${SERVICE_ACCOUNT_KEY_FILE}"',
    content
)

# Write back
with open('configs/token_key_session.py', 'w') as f:
    f.write(content)

print("✓ Updated token_key_session.py")
EOF

echo -e "${GREEN}✓ token_key_session.py updated with Google credentials${NC}"
echo ""

# =============================================================================
# Summary
# =============================================================================
echo -e "${GREEN}================================================================${NC}"
echo -e "${GREEN}       🎉 Google Cloud Setup Complete! 🎉${NC}"
echo -e "${GREEN}================================================================${NC}"
echo ""
echo -e "${BLUE}Summary of what was configured:${NC}"
echo ""
echo -e "  ${GREEN}✓${NC} Project ID: ${BLUE}$PROJECT_ID${NC}"
echo -e "  ${GREEN}✓${NC} Google Account: ${BLUE}$(gcloud auth list --format='value(account)' --filter=status:ACTIVE)${NC}"
echo -e "  ${GREEN}✓${NC} APIs Enabled: ${BLUE}40+ services${NC}"
echo -e "  ${GREEN}✓${NC} Service Account: ${BLUE}$SERVICE_ACCOUNT_EMAIL${NC}"
echo -e "  ${GREEN}✓${NC} Service Account Key: ${BLUE}$SERVICE_ACCOUNT_KEY_FILE${NC}"
echo -e "  ${GREEN}✓${NC} API Key: ${BLUE}${API_KEY:0:30}...${NC}"
echo -e "  ${GREEN}✓${NC} OAuth Credentials: ${BLUE}configs/google_credentials.json${NC}"
echo -e "  ${GREEN}✓${NC} token_key_session.py: ${BLUE}Updated${NC}"
echo ""
echo -e "${GREEN}================================================================${NC}"
