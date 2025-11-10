#!/bin/bash

# =============================================================================
# Automated Setup for Additional Services (GitHub, HuggingFace, WandB, Serper)
# =============================================================================
# This script helps set up:
# 1. GitHub Personal Access Token
# 2. HuggingFace token
# 3. WandB API key
# 4. Serper API key
# 5. Auto-fills token_key_session.py
#
# What needs to be done MANUALLY:
# - Creating accounts on each platform (free signups)
# =============================================================================

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}   Automated Setup for Additional Services${NC}"
echo -e "${BLUE}   (GitHub, HuggingFace, WandB, Serper)${NC}"
echo -e "${BLUE}================================================================${NC}"
echo ""

# Track which services to set up
declare -A TOKENS
TOKENS[github]=""
TOKENS[huggingface]=""
TOKENS[wandb]=""
TOKENS[serper]=""

# =============================================================================
# Step 1: GitHub Personal Access Token
# =============================================================================
echo -e "${YELLOW}[Step 1]${NC} GitHub Personal Access Token Setup"
echo ""

# Check if GitHub token is already filled
EXISTING_GITHUB_TOKEN=$(uv run python -c "
import re
try:
    with open('configs/token_key_session.py', 'r') as f:
        content = f.read()
    match = re.search(r'github_token = \"([^\"]+)\"', content)
    if match and match.group(1) not in ['XX', '']:
        print(match.group(1))
except:
    pass
" 2>/dev/null)

if [ -n "$EXISTING_GITHUB_TOKEN" ]; then
    # Mask the token for display (show first 8 and last 4 characters)
    TOKEN_LENGTH=${#EXISTING_GITHUB_TOKEN}
    if [ $TOKEN_LENGTH -gt 12 ]; then
        MASKED_TOKEN="${EXISTING_GITHUB_TOKEN:0:8}...${EXISTING_GITHUB_TOKEN: -4}"
    else
        MASKED_TOKEN="${EXISTING_GITHUB_TOKEN:0:4}...${EXISTING_GITHUB_TOKEN: -2}"
    fi

    echo -e "${GREEN}✓ GitHub token already configured: ${BLUE}$MASKED_TOKEN${NC}"
    echo ""
    read -p "Do you want to skip this step or set up a new token? [Skip/new]: " -r
    echo

    if [[ ! $REPLY =~ ^[Nn] ]]; then
        echo "Skipping GitHub setup (keeping existing token)"
        TOKENS[github]=$EXISTING_GITHUB_TOKEN
    else
        echo "Setting up new GitHub token..."
        echo ""
        # Continue with setup below
    fi
fi

# Only proceed with setup if not skipped
if [ -z "${TOKENS[github]}" ]; then

echo ""
echo "================================================================"
echo "GitHub Account Registration/Login"
echo "================================================================"
echo ""

# Step 1a: Registration/Login
echo "Please sign up a new GitHub account with your Toolathlon-specific gmail"
echo "(you can directly choose 'Continue with Google')"
echo ""
echo "  https://github.com/signup"
echo ""

# Open browser
if command -v xdg-open &> /dev/null; then
    xdg-open "https://github.com/signup" 2>/dev/null &
elif command -v open &> /dev/null; then
    open "https://github.com/signup" 2>/dev/null &
fi

read -p "Press Enter once you've created your GitHub account, or you want to use your existing account (not recommended)..."
echo ""

# Step 1c: Token creation
echo "================================================================"
echo "GitHub Personal Access Token Creation"
echo "================================================================"
echo ""
echo "Opening GitHub token creation page (Please login with your Toolathlon specific gmail)"
echo "  https://github.com/settings/tokens/new?description=Toolathlon+Evaluation&scopes=repo,delete_repo,workflow,admin:org"
echo ""
echo "Steps:"
echo "  1. Make sure you're signed in with the new github account"
echo "  2. Expiration: Choose expiration (recommend: 90 days or No expiration)"
echo "  3. Token name and scopes are already filled, so you can skip filling them"
echo "  4. Click 'Generate token'"
echo "  5. Copy the token (you won't see it again!)"
echo ""

# Open browser
if command -v xdg-open &> /dev/null; then
    xdg-open "https://github.com/settings/tokens/new?description=Toolathlon+Evaluation&scopes=repo,delete_repo,workflow,admin:org,user" 2>/dev/null &
elif command -v open &> /dev/null; then
    open "https://github.com/settings/tokens/new?description=Toolathlon+Evaluation&scopes=repo,delete_repo,workflow,admin:org,user" 2>/dev/null &
fi

echo "Please paste your GitHub personal access token:"
read GITHUB_TOKEN
echo ""

TOKENS[github]=$GITHUB_TOKEN

fi

echo ""

# =============================================================================
# Step 2: HuggingFace Token
# =============================================================================
echo -e "${YELLOW}[Step 2]${NC} HuggingFace Token Setup"
echo ""

# Check if HuggingFace token is already filled
EXISTING_HF_TOKEN=$(uv run python -c "
import re
try:
    with open('configs/token_key_session.py', 'r') as f:
        content = f.read()
    match = re.search(r'huggingface_token = \"([^\"]+)\"', content)
    if match and match.group(1) not in ['XX', '']:
        print(match.group(1))
except:
    pass
" 2>/dev/null)

if [ -n "$EXISTING_HF_TOKEN" ]; then
    # Mask the token for display
    TOKEN_LENGTH=${#EXISTING_HF_TOKEN}
    if [ $TOKEN_LENGTH -gt 12 ]; then
        MASKED_TOKEN="${EXISTING_HF_TOKEN:0:8}...${EXISTING_HF_TOKEN: -4}"
    else
        MASKED_TOKEN="${EXISTING_HF_TOKEN:0:4}...${EXISTING_HF_TOKEN: -2}"
    fi

    echo -e "${GREEN}✓ HuggingFace token already configured: ${BLUE}$MASKED_TOKEN${NC}"
    echo ""
    read -p "Do you want to skip this step or set up a new token? [Skip/new]: " -r
    echo

    if [[ ! $REPLY =~ ^[Nn] ]]; then
        echo "Skipping HuggingFace setup (keeping existing token)"
        TOKENS[huggingface]=$EXISTING_HF_TOKEN
    else
        echo "Setting up new HuggingFace token..."
        echo ""
    fi
fi

# Only proceed with setup if not skipped
if [ -z "${TOKENS[huggingface]}" ]; then

echo ""
echo "================================================================"
echo "HuggingFace Account Registration/Login"
echo "================================================================"
echo ""

# Step 2a: Registration/Login
echo "Please sign up a new HuggingFace account with your Toolathlon-specific gmail"
echo ""
echo "  https://huggingface.co/join"
echo ""

# Open browser
if command -v xdg-open &> /dev/null; then
    xdg-open "https://huggingface.co/join" 2>/dev/null &
elif command -v open &> /dev/null; then
    open "https://huggingface.co/join" 2>/dev/null &
fi

read -p "Press Enter once you've created your HuggingFace account, or you want to use your existing account (not recommended)..."
echo ""

# Step 2b: Token creation
echo "================================================================"
echo "HuggingFace Token Creation"
echo "================================================================"
echo ""
echo "Opening HuggingFace token creation page (Please login with your Toolathlon specific gmail)"
echo "  https://huggingface.co/settings/tokens/new?tokenType=write"
echo ""
echo "Steps:"
echo "  1. Make sure you're signed in with the new HuggingFace account"
echo "  2. Name: Toolathlon Evaluation"
echo "  3. Type: Write (should be pre-selected)"
echo "  4. Click 'Create token'"
echo "  5. Copy the token"
echo ""

# Open browser
if command -v xdg-open &> /dev/null; then
    xdg-open "https://huggingface.co/settings/tokens/new?tokenType=write" 2>/dev/null &
elif command -v open &> /dev/null; then
    open "https://huggingface.co/settings/tokens/new?tokenType=write" 2>/dev/null &
fi

echo "Please paste your HuggingFace token:"
read HF_TOKEN
echo ""

TOKENS[huggingface]=$HF_TOKEN

fi

echo ""

# =============================================================================
# Step 3: WandB API Key
# =============================================================================
echo -e "${YELLOW}[Step 3]${NC} Weights & Biases (WandB) API Key Setup"
echo ""

# Check if WandB API key is already filled
EXISTING_WANDB_KEY=$(uv run python -c "
import re
try:
    with open('configs/token_key_session.py', 'r') as f:
        content = f.read()
    match = re.search(r'wandb_api_key = \"([^\"]+)\"', content)
    if match and match.group(1) not in ['XX', '']:
        print(match.group(1))
except:
    pass
" 2>/dev/null)

if [ -n "$EXISTING_WANDB_KEY" ]; then
    # Mask the key for display
    TOKEN_LENGTH=${#EXISTING_WANDB_KEY}
    if [ $TOKEN_LENGTH -gt 12 ]; then
        MASKED_TOKEN="${EXISTING_WANDB_KEY:0:8}...${EXISTING_WANDB_KEY: -4}"
    else
        MASKED_TOKEN="${EXISTING_WANDB_KEY:0:4}...${EXISTING_WANDB_KEY: -2}"
    fi

    echo -e "${GREEN}✓ WandB API key already configured: ${BLUE}$MASKED_TOKEN${NC}"
    echo ""
    read -p "Do you want to skip this step or set up a new API key? [Skip/new]: " -r
    echo

    if [[ ! $REPLY =~ ^[Nn] ]]; then
        echo "Skipping WandB setup (keeping existing API key)"
        TOKENS[wandb]=$EXISTING_WANDB_KEY
    else
        echo "Setting up new WandB API key..."
        echo ""
    fi
fi

# Only proceed with setup if not skipped
if [ -z "${TOKENS[wandb]}" ]; then

echo ""
echo "================================================================"
echo "WandB Account Registration/Login"
echo "================================================================"
echo ""

# Step 3a: Registration/Login
echo "Please sign up a new WandB account with your Toolathlon-specific gmail"
echo "(you can directly choose 'Continue with Google')"
echo ""
echo "  https://wandb.ai/signup"
echo ""

# Open browser
if command -v xdg-open &> /dev/null; then
    xdg-open "https://wandb.ai/signup" 2>/dev/null &
elif command -v open &> /dev/null; then
    open "https://wandb.ai/signup" 2>/dev/null &
fi

read -p "Press Enter once you've created your WandB account, or you want to use your existing account..."
echo ""

# Step 3b: API key retrieval
echo "================================================================"
echo "WandB API Key"
echo "================================================================"
echo ""
echo "Opening WandB authorization page (Please login with your Toolathlon specific gmail)"
echo "  https://wandb.ai/authorize"
echo ""
echo "Steps:"
echo "  1. Make sure you're signed in with the new WandB account"
echo "  2. Copy the API key shown on the page"
echo ""

# Open browser
if command -v xdg-open &> /dev/null; then
    xdg-open "https://wandb.ai/authorize" 2>/dev/null &
elif command -v open &> /dev/null; then
    open "https://wandb.ai/authorize" 2>/dev/null &
fi

echo "Please paste your WandB API key:"
read WANDB_KEY
echo ""

TOKENS[wandb]=$WANDB_KEY

fi

echo ""

# =============================================================================
# Step 4: Serper API Key
# =============================================================================
echo -e "${YELLOW}[Step 4]${NC} Serper.dev API Key Setup"
echo ""

# Check if Serper API key is already filled
EXISTING_SERPER_KEY=$(uv run python -c "
import re
try:
    with open('configs/token_key_session.py', 'r') as f:
        content = f.read()
    match = re.search(r'serper_api_key = \"([^\"]+)\"', content)
    if match and match.group(1) not in ['XX', '']:
        print(match.group(1))
except:
    pass
" 2>/dev/null)

if [ -n "$EXISTING_SERPER_KEY" ]; then
    # Mask the key for display
    TOKEN_LENGTH=${#EXISTING_SERPER_KEY}
    if [ $TOKEN_LENGTH -gt 12 ]; then
        MASKED_TOKEN="${EXISTING_SERPER_KEY:0:8}...${EXISTING_SERPER_KEY: -4}"
    else
        MASKED_TOKEN="${EXISTING_SERPER_KEY:0:4}...${EXISTING_SERPER_KEY: -2}"
    fi

    echo -e "${GREEN}✓ Serper API key already configured: ${BLUE}$MASKED_TOKEN${NC}"
    echo ""
    read -p "Do you want to skip this step or set up a new API key? [Skip/new]: " -r
    echo

    if [[ ! $REPLY =~ ^[Nn] ]]; then
        echo "Skipping Serper setup (keeping existing API key)"
        TOKENS[serper]=$EXISTING_SERPER_KEY
    else
        echo "Setting up new Serper API key..."
        echo ""
    fi
fi

# Only proceed with setup if not skipped
if [ -z "${TOKENS[serper]}" ]; then

echo ""
echo "================================================================"
echo "Serper Account Registration/Login"
echo "================================================================"
echo ""

# Step 4a: Registration/Login
echo "Please sign up a new Serper account"
echo "This only provides google search APIs for evaluation, so you can use your old account"
echo "as well if you already have the account"
echo "Serper API is a paid service, but don't worry, full evaluation on all Toolathlon tasks"
echo "takes less than 1 USD Serper API credits in our experiments"
echo ""
echo ""
echo "  https://serper.dev/signup"
echo ""

# Open browser
if command -v xdg-open &> /dev/null; then
    xdg-open "https://serper.dev/signup" 2>/dev/null &
elif command -v open &> /dev/null; then
    open "https://serper.dev/signup" 2>/dev/null &
fi

read -p "Press Enter once you've created your Serper account, or you want to use your existing account..."
echo ""

# Step 4b: API key retrieval
echo "================================================================"
echo "Serper API Key"
echo "================================================================"
echo ""
echo "Opening Serper API key page (Please login with your Toolathlon specific gmail)"
echo "  https://serper.dev/api-keys"
echo ""


# Open browser
if command -v xdg-open &> /dev/null; then
    xdg-open "https://serper.dev/api-keys" 2>/dev/null &
elif command -v open &> /dev/null; then
    open "https://serper.dev/api-keys" 2>/dev/null &
fi

echo "Please paste your Serper API key:"
read SERPER_KEY
echo ""

TOKENS[serper]=$SERPER_KEY

fi

echo ""

# =============================================================================
# Step 5: Update token_key_session.py
# =============================================================================

# Check if any tokens were collected
TOKENS_SET=false
for key in "${!TOKENS[@]}"; do
    if [ -n "${TOKENS[$key]}" ]; then
        TOKENS_SET=true
        break
    fi
done

if [ "$TOKENS_SET" = true ]; then
    echo -e "${YELLOW}[Step 5]${NC} Updating token_key_session.py..."

    if [ ! -f "configs/token_key_session.py" ]; then
        echo -e "${RED}ERROR: configs/token_key_session.py not found!${NC}"
        exit 1
    fi

    # Export tokens for Python script
    export GITHUB_TOKEN="${TOKENS[github]}"
    export HF_TOKEN="${TOKENS[huggingface]}"
    export WANDB_KEY="${TOKENS[wandb]}"
    export SERPER_KEY="${TOKENS[serper]}"

    # Update config file
    uv run python << 'EOF'
import re
import os

# Read the file
with open('configs/token_key_session.py', 'r') as f:
    content = f.read()

# Update GitHub token
github_token = os.environ.get('GITHUB_TOKEN', '')
if github_token:
    content = re.sub(
        r'github_token = "[^"]*"',
        f'github_token = "{github_token}"',
        content
    )
    print("✓ Updated GitHub token")

# Update HuggingFace token
hf_token = os.environ.get('HF_TOKEN', '')
if hf_token:
    content = re.sub(
        r'huggingface_token = "[^"]*"',
        f'huggingface_token = "{hf_token}"',
        content
    )
    print("✓ Updated HuggingFace token")

# Update WandB API key
wandb_key = os.environ.get('WANDB_KEY', '')
if wandb_key:
    content = re.sub(
        r'wandb_api_key = "[^"]*"',
        f'wandb_api_key = "{wandb_key}"',
        content
    )
    print("✓ Updated WandB API key")

# Update Serper API key
serper_key = os.environ.get('SERPER_KEY', '')
if serper_key:
    content = re.sub(
        r'serper_api_key = "[^"]*"',
        f'serper_api_key = "{serper_key}"',
        content
    )
    print("✓ Updated Serper API key")

# Write back
with open('configs/token_key_session.py', 'w') as f:
    f.write(content)
EOF

    echo -e "${GREEN}✓ token_key_session.py updated${NC}"
    echo ""
fi

# =============================================================================
# Summary
# =============================================================================
echo -e "${GREEN}================================================================${NC}"
echo -e "${GREEN}       🎉 Github/Huggingface/Wandb/Serper Services Setup Complete! 🎉${NC}"
echo -e "${GREEN}================================================================${NC}"
echo ""
echo -e "${BLUE}Services configured:${NC}"
echo ""

if [ -n "${TOKENS[github]}" ]; then
    echo -e "  ${GREEN}✓${NC} GitHub token"
fi

if [ -n "${TOKENS[huggingface]}" ]; then
    echo -e "  ${GREEN}✓${NC} HuggingFace token"
fi

if [ -n "${TOKENS[wandb]}" ]; then
    echo -e "  ${GREEN}✓${NC} WandB API key"
fi

if [ -n "${TOKENS[serper]}" ]; then
    echo -e "  ${GREEN}✓${NC} Serper API key"
fi
