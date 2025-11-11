#!/bin/bash

# Batch create Poste.io users script
# Domain: mcp.com
# Creates 1 admin + configurable number of regular users

# set -e  # Commented out to prevent immediate exit on error

# read out `podman_or_docker` from global_configs.py
podman_or_docker=$(uv run python -c "import sys; sys.path.append('configs'); from global_configs import global_configs; print(global_configs.podman_or_docker)")

DOMAIN="mcp.com"
CONTAINER_NAME="poste"
CONFIG_DIR="$(dirname "$0")/../configs"
ACCOUNTS_FILE="$CONFIG_DIR/created_accounts.json"

# Default number of users to create (will be overridden by JSON file)
DEFAULT_USER_COUNT=503
# Batch size for concurrent execution
MAX_CONCURRENT=50

# Function to show usage
show_usage() {
    echo "Usage: $0 [number_of_users]"
    echo "  number_of_users: Number of users to create from configs/users_data.json (default: all available)"
    echo ""
    echo "Environment variables:"
    echo "  DEBUG=1   # Show detailed error messages"
    echo ""
    echo "Example:"
    echo "  $0 50         # Create 1 admin + first 50 users from JSON"
    echo "  DEBUG=1 $0 10 # Create 10 users with debug output"
    echo "  $0            # Create 1 admin + all users from JSON file"
    echo ""
    echo "Note: Users are loaded from configs/users_data.json"
    exit 1
}

# Function to draw progress bar
draw_progress_bar() {
    local current=$1
    local total=$2
    local width=50
    local percentage=$((current * 100 / total))
    local filled=$((current * width / total))
    
    printf "\r["
    for ((i=0; i<filled; i++)); do printf "="; done
    for ((i=filled; i<width; i++)); do printf " "; done
    printf "] %d/%d (%d%%)" "$current" "$total" "$percentage"
}

# Function to load user data from JSON
load_users_from_json() {
    local users_file="configs/users_data.json"
    
    if [ ! -f "$users_file" ]; then
        echo "❌ Error: $users_file not found"
        exit 1
    fi
    
    # Extract users data from JSON file
    jq -r '.users[] | "\(.id)|\(.first_name)|\(.last_name)|\(.full_name)|\(.email)|\(.password)"' "$users_file"
}

# Parse command line arguments
# Get total users from JSON file
TOTAL_JSON_USERS=$(jq '.users | length' configs/users_data.json 2>/dev/null || echo "0")

if [ "$TOTAL_JSON_USERS" -eq 0 ]; then
    echo "❌ Error: No users found in configs/users_data.json"
    exit 1
fi

USER_COUNT=$TOTAL_JSON_USERS
if [ $# -eq 1 ]; then
    if [[ "$1" =~ ^[0-9]+$ ]] && [ "$1" -gt 0 ] && [ "$1" -le "$TOTAL_JSON_USERS" ]; then
        USER_COUNT=$1
    else
        echo "Error: Invalid number of users. Must be between 1 and $TOTAL_JSON_USERS."
        show_usage
    fi
elif [ $# -gt 1 ]; then
    show_usage
fi

echo "🚀 Starting batch user creation..."
echo "📧 Domain: $DOMAIN"
echo "👤 Creating: 1 admin + $USER_COUNT regular users"
echo ""

# Check if container is running
if ! $podman_or_docker ps | grep -q "$CONTAINER_NAME"; then
    echo "❌ Error: Container $CONTAINER_NAME is not running"
    echo "Please run: ./setup.sh start"
    exit 1
fi

# Ensure domain exists
echo "🌐 Checking domain $DOMAIN..."
if ! $podman_or_docker exec --user=8 $CONTAINER_NAME php /opt/admin/bin/console domain:list | grep -q "$DOMAIN"; then
    echo "📝 Creating domain: $DOMAIN"
    $podman_or_docker exec --user=8 $CONTAINER_NAME php /opt/admin/bin/console domain:create "$DOMAIN"
else
    echo "✅ Domain already exists: $DOMAIN"
fi

echo ""

# Create configs directory if it doesn't exist
mkdir -p "$CONFIG_DIR"

# Initialize JSON structure
echo "📄 Initializing accounts file: $ACCOUNTS_FILE"
cat > "$ACCOUNTS_FILE" << EOF
{
  "domain": "$DOMAIN",
  "created_date": "$(date -Iseconds)",
  "admin_account": {},
  "regular_accounts": [],
  "total_accounts": 0,
  "statistics": {
    "admin_created": 0,
    "users_created": 0,
    "users_failed": 0
  }
}
EOF

# Create admin account
echo "👑 Creating admin account..."
ADMIN_EMAIL="mcpposte_admin@$DOMAIN"
ADMIN_PASSWORD="mcpposte"
ADMIN_NAME="System Administrator"

echo "📧 Creating: $ADMIN_EMAIL"
if $podman_or_docker exec --user=8 $CONTAINER_NAME php /opt/admin/bin/console email:create "$ADMIN_EMAIL" "$ADMIN_PASSWORD" "$ADMIN_NAME" &>/dev/null; then
    echo "🔐 Setting admin privileges..."
    $podman_or_docker exec --user=8 $CONTAINER_NAME php /opt/admin/bin/console email:admin "$ADMIN_EMAIL" &>/dev/null
    echo "✅ Admin created successfully!"
    echo "   Email: $ADMIN_EMAIL"
    echo "   Password: $ADMIN_PASSWORD"
    
    # Save admin account to JSON
    jq --arg email "$ADMIN_EMAIL" --arg password "$ADMIN_PASSWORD" --arg name "$ADMIN_NAME" \
       '.admin_account = {email: $email, password: $password, name: $name, is_admin: true} | .statistics.admin_created = 1' \
       "$ACCOUNTS_FILE" > "${ACCOUNTS_FILE}.tmp" && mv "${ACCOUNTS_FILE}.tmp" "$ACCOUNTS_FILE"
else
    echo "⚠️  Admin might already exist, skipping creation"
fi

echo ""

# Create regular users
echo "👥 Creating $USER_COUNT regular users from JSON data..."
SUCCESS_COUNT=0
FAILED_COUNT=0

# Array to store user data for JSON
declare -a USER_DATA=()

# Create temporary file to store user data from JSON
TEMP_USERS=$(mktemp)
load_users_from_json > "$TEMP_USERS"

# Create temporary directory for results
TEMP_RESULTS_DIR="$(dirname "$0")/../tmpfiles"
rm -rf "$TEMP_RESULTS_DIR"
mkdir -p "$TEMP_RESULTS_DIR"

# Process users
counter=0
batch_count=0
while IFS='|' read -r id first_name last_name full_name email password; do
    counter=$((counter + 1))

    # Only create the requested number of users
    if [ $counter -gt $USER_COUNT ]; then
        break
    fi

    # Show progress bar
    draw_progress_bar $counter $USER_COUNT

    # Create user in background with error handling
    (
        RESULT_FILE="$TEMP_RESULTS_DIR/user_${counter}.result"
        CREATE_RESULT=$($podman_or_docker exec --user=8 $CONTAINER_NAME php /opt/admin/bin/console email:create "$email" "$password" "$full_name" 2>&1)
        if [ $? -eq 0 ]; then
            echo "success|$email|$password|$full_name|$first_name|$last_name" > "$RESULT_FILE"
        else
            echo "failed|$email|$CREATE_RESULT" > "$RESULT_FILE"
        fi
    ) &

    batch_count=$((batch_count + 1))

    # Wait for each batch of MAX_CONCURRENT to complete
    if [ $((batch_count % MAX_CONCURRENT)) -eq 0 ]; then
        wait
    fi

done < "$TEMP_USERS"

# Wait for the last batch to complete
wait

# Process results from temporary files
for result_file in "$TEMP_RESULTS_DIR"/*.result; do
    if [ -f "$result_file" ]; then
        IFS='|' read -r status email password full_name first_name last_name < "$result_file"
        if [ "$status" = "success" ]; then
            ((SUCCESS_COUNT++))
            USER_DATA+=("{\"email\":\"$email\",\"password\":\"$password\",\"name\":\"$full_name\",\"first_name\":\"$first_name\",\"last_name\":\"$last_name\",\"is_admin\":false}")
        else
            ((FAILED_COUNT++))
            # If in debug mode, show the error
            if [ "${DEBUG:-}" = "1" ]; then
                echo ""
                echo "❌ Failed to create $email: $password"  # $password contains error message in failed case
            fi
        fi
    fi
done

# Clean up temp files
rm -f "$TEMP_USERS"
rm -rf "$TEMP_RESULTS_DIR"

# Complete progress bar
draw_progress_bar $USER_COUNT $USER_COUNT
echo ""
echo ""

# Save all user data to JSON
if [ ${#USER_DATA[@]} -gt 0 ]; then
    echo "💾 Saving account data to JSON file..."
    
    # Create JSON array from user data
    USERS_JSON="[$(IFS=','; echo "${USER_DATA[*]}")]"
    
    # Update JSON file with user data and statistics
    jq --argjson users "$USERS_JSON" --arg success "$SUCCESS_COUNT" --arg failed "$FAILED_COUNT" --arg total "$((SUCCESS_COUNT + FAILED_COUNT + 1))" \
       '.regular_accounts = $users | .statistics.users_created = ($success | tonumber) | .statistics.users_failed = ($failed | tonumber) | .total_accounts = ($total | tonumber)' \
       "$ACCOUNTS_FILE" > "${ACCOUNTS_FILE}.tmp" && mv "${ACCOUNTS_FILE}.tmp" "$ACCOUNTS_FILE"
    
    echo "✅ Account data saved to: $ACCOUNTS_FILE"
fi

echo ""
echo "🎉 Batch user creation completed!"
echo "📊 Statistics:"
echo "   ✅ Successfully created: $SUCCESS_COUNT users"
if [ "$FAILED_COUNT" -gt 0 ]; then
    echo "   ❌ Failed to create: $FAILED_COUNT users"
fi
echo ""

# Show final user count
echo "📋 Current total users:"
TOTAL_USERS=$($podman_or_docker exec --user=8 $CONTAINER_NAME php /opt/admin/bin/console email:list | wc -l)
echo "   Total: $TOTAL_USERS users"

echo ""
echo "🔑 Admin login credentials:"
echo "   Email: $ADMIN_EMAIL"
echo "   Password: $ADMIN_PASSWORD"
echo "   URL: http://localhost:10005"

echo ""
echo "👤 Regular user login details:"
echo "   Users loaded from: configs/users_data.json"
echo "   Total users available: $TOTAL_JSON_USERS"
echo "   Users created: $SUCCESS_COUNT"
if [ ${#USER_DATA[@]} -gt 0 ]; then
    echo "   First user example: $(echo "${USER_DATA[0]}" | jq -r '.email + " / " + .password' 2>/dev/null || echo "Check $ACCOUNTS_FILE for details")"
fi

echo ""
echo "📄 Account details saved in: $ACCOUNTS_FILE"
echo "✨ Script execution completed!"