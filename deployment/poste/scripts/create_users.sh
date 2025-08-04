#!/bin/bash

# Batch create Poste.io users script
# Domain: mcp.com
# Creates 1 admin + configurable number of regular users

# set -e  # Commented out to prevent immediate exit on error

DOMAIN="mcp.com"
CONTAINER_NAME="poste"
CONFIG_DIR="$(dirname "$0")/../configs"
ACCOUNTS_FILE="$CONFIG_DIR/created_accounts.json"

# Default number of users to create
DEFAULT_USER_COUNT=100

# Adjectives and nouns for realistic usernames
ADJECTIVES=("happy" "clever" "bright" "swift" "calm" "bold" "gentle" "brave" "wise" "kind" 
           "quick" "smart" "cool" "warm" "fresh" "clean" "clear" "sharp" "smooth" "strong"
           "light" "dark" "fast" "slow" "big" "small" "young" "old" "new" "good"
           "blue" "red" "green" "yellow" "orange" "purple" "pink" "brown" "gray" "black")

NOUNS=("cat" "dog" "bird" "fish" "lion" "tiger" "bear" "wolf" "fox" "deer"
       "tree" "flower" "star" "moon" "sun" "cloud" "rain" "snow" "wind" "fire"
       "book" "pen" "car" "bike" "boat" "plane" "train" "house" "door" "window"
       "apple" "orange" "banana" "grape" "cherry" "berry" "cake" "bread" "milk" "tea")

# Function to show usage
show_usage() {
    echo "Usage: $0 [number_of_users]"
    echo "  number_of_users: Number of regular users to create (default: $DEFAULT_USER_COUNT)"
    echo ""
    echo "Environment variables:"
    echo "  DEBUG=1   # Show detailed error messages"
    echo ""
    echo "Example:"
    echo "  $0 50         # Create 1 admin + 50 users"
    echo "  DEBUG=1 $0 10 # Create 10 users with debug output"
    echo "  $0            # Create 1 admin + $DEFAULT_USER_COUNT users (default)"
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

# Function to generate random username
generate_username() {
    local id=$1
    local adj_count=${#ADJECTIVES[@]}
    local noun_count=${#NOUNS[@]}
    
    local adj_index=$((RANDOM % adj_count))
    local noun_index=$((RANDOM % noun_count))
    
    local adjective=${ADJECTIVES[$adj_index]}
    local noun=${NOUNS[$noun_index]}
    local formatted_id=$(printf "%03d" $id)
    
    echo "${adjective}${noun}${formatted_id}"
}

# Parse command line arguments
USER_COUNT=$DEFAULT_USER_COUNT
if [ $# -eq 1 ]; then
    if [[ "$1" =~ ^[0-9]+$ ]] && [ "$1" -gt 0 ]; then
        USER_COUNT=$1
    else
        echo "Error: Invalid number of users. Must be a positive integer."
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
if ! podman ps | grep -q "$CONTAINER_NAME"; then
    echo "❌ Error: Container $CONTAINER_NAME is not running"
    echo "Please run: ./setup.sh start"
    exit 1
fi

# Ensure domain exists
echo "🌐 Checking domain $DOMAIN..."
if ! podman exec --user=8 $CONTAINER_NAME php /opt/admin/bin/console domain:list | grep -q "$DOMAIN"; then
    echo "📝 Creating domain: $DOMAIN"
    podman exec --user=8 $CONTAINER_NAME php /opt/admin/bin/console domain:create "$DOMAIN"
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
if podman exec --user=8 $CONTAINER_NAME php /opt/admin/bin/console email:create "$ADMIN_EMAIL" "$ADMIN_PASSWORD" "$ADMIN_NAME" &>/dev/null; then
    echo "🔐 Setting admin privileges..."
    podman exec --user=8 $CONTAINER_NAME php /opt/admin/bin/console email:admin "$ADMIN_EMAIL" &>/dev/null
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
echo "👥 Creating $USER_COUNT regular users..."
SUCCESS_COUNT=0
FAILED_COUNT=0

# Array to store user data for JSON
declare -a USER_DATA=()

for i in $(seq 1 $USER_COUNT); do
    USERNAME=$(generate_username $i)
    USER_EMAIL="${USERNAME}@$DOMAIN"
    USER_PASSWORD="pass$(printf "%03d" $i)"
    USER_NAME="$(echo ${USERNAME:0:1} | tr '[:lower:]' '[:upper:]')${USERNAME:1}"  # Capitalize first letter
    
    # Show progress bar
    draw_progress_bar $i $USER_COUNT
    
    # Create user with error handling
    CREATE_RESULT=$(podman exec --user=8 $CONTAINER_NAME php /opt/admin/bin/console email:create "$USER_EMAIL" "$USER_PASSWORD" "$USER_NAME" 2>&1)
    if [ $? -eq 0 ]; then
        ((SUCCESS_COUNT++))
        # Store user data for JSON
        USER_DATA+=("{\"email\":\"$USER_EMAIL\",\"password\":\"$USER_PASSWORD\",\"name\":\"$USER_NAME\",\"username\":\"$USERNAME\",\"is_admin\":false}")
    else
        ((FAILED_COUNT++))
        # If in debug mode, show the error
        if [ "${DEBUG:-}" = "1" ]; then
            echo ""
            echo "❌ Failed to create $USER_EMAIL: $CREATE_RESULT"
        fi
    fi
done

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
echo "   ❌ Failed to create: $FAILED_COUNT users"
echo ""

# Show final user count
echo "📋 Current total users:"
TOTAL_USERS=$(podman exec --user=8 $CONTAINER_NAME php /opt/admin/bin/console email:list | wc -l)
echo "   Total: $TOTAL_USERS users"

echo ""
echo "🔑 Admin login credentials:"
echo "   Email: $ADMIN_EMAIL"
echo "   Password: $ADMIN_PASSWORD"
echo "   URL: http://localhost:10005"

echo ""
echo "👤 Regular user login format:"
echo "   Email: [adjective][noun][001-$(printf "%03d" $USER_COUNT)]@$DOMAIN"
echo "   Password: pass001, pass002, ..., pass$(printf "%03d" $USER_COUNT)"
echo "   Example: ${USER_DATA[0]}" 2>/dev/null | jq -r '.email + " / " + .password' 2>/dev/null || echo "   Check $ACCOUNTS_FILE for details"

echo ""
echo "📄 Account details saved in: $ACCOUNTS_FILE"
echo "✨ Script execution completed!"