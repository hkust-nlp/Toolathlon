#!/bin/bash
# setup-wordpress.sh

### launch the pod, enable multisite, and create 20 sub sites for task use

# read out `podman_or_docker` from global_configs.py
podman_or_docker=$(uv run python -c "import sys; sys.path.append('configs'); from global_configs import global_configs; print(global_configs.podman_or_docker)")


# Function to show usage
show_usage() {
    echo "How to use: $0 [command] [start_user] [count]"
    echo ""
    echo "Command:"
    echo "  start    Start WooCommerce service (default)"
    echo "  stop     Stop WooCommerce service"
    echo "  restart  Restart WooCommerce service"
    echo ""
    echo "Optional parameters for start/restart:"
    echo "  start_user  Starting user index (1-based, default: 1)"
    echo "  count       Number of users to create sites for (default: 20)"
    echo ""
    echo "Example:"
    echo "  $0                    # Start service with users 1-20"
    echo "  $0 start              # Start service with users 1-20"
    echo "  $0 start 81 20        # Start service with users 81-100"
    echo "  $0 stop               # Stop service"
    echo "  $0 restart 50 10      # Restart service with users 50-59"
}

# Function to stop services
stop_services() {
    echo "Stopping WooCommerce service..."
    
    if [ "$podman_or_docker" = "podman" ]; then
        # Podman: stop and remove pod
        podman pod stop woo-pod 2>/dev/null
        podman pod rm -f woo-pod 2>/dev/null
    else
        # Docker: stop and remove containers and network
        docker stop woo-wp woo-db 2>/dev/null
        docker rm -f woo-wp woo-db 2>/dev/null
        docker network rm woo-net 2>/dev/null
    fi
    
    echo "✓ WooCommerce service stopped"
}

# Parse command line arguments
COMMAND=${1:-start}
START_USER=${2:-1}
USER_COUNT=${3:-20}

case $COMMAND in
    "stop")
        stop_services
        exit 0
        ;;
    "start"|"restart")
        # Stop first to ensure clean state
        stop_services
        echo "Starting WooCommerce service..."
        echo "Will create sites for users $START_USER to $((START_USER + USER_COUNT - 1))"
        ;;
    "help"|"-h"|"--help")
        show_usage
        exit 0
        ;;
    *)
        echo "Error: Unknown command '$COMMAND'"
        echo ""
        show_usage
        exit 1
        ;;
esac

# Configuration variables
PORT=10003
WP_URL="http://localhost:$PORT"
WP_TITLE="My WooCommerce Store"
WP_ADMIN_USER="mcpwoocommerce"
WP_ADMIN_PASS="mcpwoocommerce"
WP_ADMIN_EMAIL="woocommerce@mcp.com"
# this account is not activated in poste, we just use it as a admin
PRESET_NUM_SITES=20

# 1. Create new deployment
echo "Creating new pod/network..."
# original podman pod create
if [ "$podman_or_docker" = "podman" ]; then
    # Podman: create pod
    podman pod create --name woo-pod -p ${PORT}:80
else
    # Docker: create network (because docker has no pod concept)
    docker network create woo-net 2>/dev/null
fi

# 2. Start MySQL
echo "Starting MySQL..."
if [ "$podman_or_docker" = "podman" ]; then
    # Podman: use --pod
    podman run -d \
      --pod woo-pod \
      --name woo-db \
      -e MYSQL_ROOT_PASSWORD=rootpass123 \
      -e MYSQL_DATABASE=wordpress \
      -e MYSQL_USER=wordpress \
      -e MYSQL_PASSWORD=wppass123 \
      mysql:8.0
    
    # Podman pod internal use 127.0.0.1
    DB_HOST="127.0.0.1"
else
    # Docker: use --network
    docker run -d \
      --network woo-net \
      --name woo-db \
      -e MYSQL_ROOT_PASSWORD=rootpass123 \
      -e MYSQL_DATABASE=wordpress \
      -e MYSQL_USER=wordpress \
      -e MYSQL_PASSWORD=wppass123 \
      mysql:8.0
    
    # Docker network use container name
    DB_HOST="woo-db"
fi

# 3. Wait for MySQL to be ready
echo "Waiting for MySQL to start..."
for i in {1..30}; do
  if  $podman_or_docker exec woo-db mysql -u wordpress -pwppass123 -e "SELECT 1" &>/dev/null; then
    echo "MySQL is ready"
    break
  fi
  sleep 1
done

# 4. Start WordPress
echo "Starting WordPress..."
if [ "$podman_or_docker" = "podman" ]; then
    # Podman: use --pod (port is already mapped in pod)
    podman run -d \
      --pod woo-pod \
      --name woo-wp \
      -e WORDPRESS_DB_HOST=$DB_HOST \
      -e WORDPRESS_DB_USER=wordpress \
      -e WORDPRESS_DB_PASSWORD=wppass123 \
      -e WORDPRESS_DB_NAME=wordpress \
      wordpress:6.8.2-php8.2-apache
else
    # Docker: use --network and need to map port separately
    docker run -d \
      --network woo-net \
      --name woo-wp \
      -p ${PORT}:80 \
      -e WORDPRESS_DB_HOST=$DB_HOST \
      -e WORDPRESS_DB_USER=wordpress \
      -e WORDPRESS_DB_PASSWORD=wppass123 \
      -e WORDPRESS_DB_NAME=wordpress \
      wordpress:6.8.2-php8.2-apache
fi

# 5. Wait for WordPress to be ready
echo "Waiting for WordPress to start..."
for i in {1..30}; do
  if curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT | grep -q "302\|200"; then
    echo "WordPress is ready"
    break
  fi
  sleep 1
done

# 6. Install WP-CLI
echo "Installing WP-CLI..."

# Check if local already has wp-cli.phar
mkdir -p deployment/woocommerce/cache

if [ -f "./deployment/woocommerce/cache/wp-cli.phar" ]; then
    echo "Using local wp-cli.phar..."
    $podman_or_docker cp deployment/woocommerce/cache/wp-cli.phar woo-wp:/tmp/wp-cli.phar
    $podman_or_docker exec woo-wp bash -c '
        chmod +x /tmp/wp-cli.phar
        mv /tmp/wp-cli.phar /usr/local/bin/wp
    '
else
    echo "Downloading wp-cli.phar..."
    # Download to local first
    curl -o deployment/woocommerce/cache/wp-cli.phar https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar
    
    # Copy to container
    $podman_or_docker cp deployment/woocommerce/cache/wp-cli.phar woo-wp:/tmp/wp-cli.phar
    $podman_or_docker exec woo-wp bash -c '
        chmod +x /tmp/wp-cli.phar
        mv /tmp/wp-cli.phar /usr/local/bin/wp
    '
fi

# 7. Install WordPress
echo "Configuring WordPress..."
$podman_or_docker exec woo-wp wp core install \
  --url="$WP_URL" \
  --title="$WP_TITLE" \
  --admin_user="$WP_ADMIN_USER" \
  --admin_password="$WP_ADMIN_PASS" \
  --admin_email="$WP_ADMIN_EMAIL" \
  --skip-email \
  --allow-root \
  --path=/var/www/html

# 8. Install WooCommerce
echo "Installing WooCommerce..."
$podman_or_docker exec woo-wp wp plugin install woocommerce --activate --allow-root --path=/var/www/html

# 8.5 Set permalinks (new)
echo "Configuring permalinks..."
$podman_or_docker exec woo-wp wp rewrite structure '/%postname%/' --allow-root --path=/var/www/html
$podman_or_docker exec woo-wp wp rewrite flush --allow-root --path=/var/www/html

# Ensure .htaccess file is writable
$podman_or_docker exec woo-wp bash -c 'chmod 644 /var/www/html/.htaccess 2>/dev/null || touch /var/www/html/.htaccess && chmod 644 /var/www/html/.htaccess'

# 8.6 Configure HTTP authentication (new)
# ref: https://www.schakko.de/2020/09/05/fixing-http-401-unauthorized-when-calling-woocommerces-rest-api/#:~:text=The%20most%20obvious%20fix%20is%20to%20check%20that,a%20length%20of%2038%20bytes%20%28or%20ASCII%20characters%29.
echo "Configuring HTTP authentication support..."
$podman_or_docker exec woo-wp bash -c 'echo "SetEnvIf Authorization (.+) HTTPS=on" >> /var/www/html/.htaccess'

# 8.7 Add WooCommerce product sales display hooks to functions.php
echo "Adding WooCommerce sales display hooks..."
$podman_or_docker exec woo-wp bash -c 'cat >> /var/www/html/wp-content/themes/twentytwentyfive/functions.php << "EOF"

// Display total sales in shop page
add_action( '\''woocommerce_after_shop_loop_item_title'\'', '\''wc_product_sold_count'\'', 5 );
// Display total sales in product detail page
add_action( '\''woocommerce_single_product_summary'\'', '\''wc_product_sold_count'\'', 11 );
function wc_product_sold_count() {
    global $product;
    $units_sold = get_post_meta( $product->id, '\''total_sales'\'', true );
    echo '\''<p>'\'' . sprintf( __( '\''Total Sales: %s'\'', '\''woocommerce'\'' ), $units_sold ) . '\''</p>'\'';
}
EOF'

# 9. Generate REST API keys
echo "Generating WooCommerce REST API keys..."
API_CREDS=$($podman_or_docker exec woo-wp wp eval '
$user_id = 1;
$consumer_key = "ck_woocommerce_token_admin";
$consumer_secret = "cs_woocommerce_token_admin";

global $wpdb;
$wpdb->insert(
    $wpdb->prefix . "woocommerce_api_keys",
    array(
        "user_id" => $user_id,
        "description" => "Auto Generated API Key",
        "permissions" => "read_write",
        "consumer_key" => wc_api_hash($consumer_key),
        "consumer_secret" => $consumer_secret,
        "truncated_key" => substr($consumer_key, -7)
    )
);

echo json_encode(array(
    "consumer_key" => $consumer_key,
    "consumer_secret" => $consumer_secret
));
' --allow-root --path=/var/www/html 2>/dev/null)

# Save credentials
mkdir -p deployment/woocommerce/configs && echo "$API_CREDS" > deployment/woocommerce/configs/wc-api-credentials.json

# 10. Display results
echo ""
echo "========================================="
echo "Installation completed!"
echo "========================================="
echo "WordPress Access Information:"
echo "  Frontend: $WP_URL"
echo "  Admin Panel: $WP_URL/wp-admin"
echo "  Username: $WP_ADMIN_USER"
echo "  Password: $WP_ADMIN_PASS"
echo ""
echo "WooCommerce REST API Credentials:"
cat deployment/woocommerce/configs/wc-api-credentials.json | uv run python -m json.tool
echo "========================================="

# 11. Test API
echo ""
echo "Testing REST API..."
if [ -f deployment/woocommerce/configs/wc-api-credentials.json ]; then
    CONSUMER_KEY=$(cat deployment/woocommerce/configs/wc-api-credentials.json | uv run python -c "import json,sys;print(json.load(sys.stdin)['consumer_key'])")
    CONSUMER_SECRET=$(cat deployment/woocommerce/configs/wc-api-credentials.json | uv run python -c "import json,sys;print(json.load(sys.stdin)['consumer_secret'])")
    
    echo "Getting WooCommerce system status:"
    # Note: added -L parameter and trailing slash
    curl -s -L -u "$CONSUMER_KEY:$CONSUMER_SECRET" "$WP_URL/wp-json/wc/v3/system_status/tools/" | uv run python -m json.tool | head -20
fi

# 12. Print service management hints
echo ""
echo "========================================="
echo "Available Commands:"
echo "  Stop Service: $0 stop"
echo "  Start Service: $0 start"
echo "  Restart Service: $0 restart"
echo "  Show Help: $0 help"
echo "========================================="

echo "Starting to convert to multisite..."

# 13. Convert to multisite

$podman_or_docker exec woo-wp wp core multisite-convert --title="My Multisite Network" --allow-root --path=/var/www/html

# 14. Update .htaccess file (subfolder mode)

$podman_or_docker exec woo-wp bash -c 'cat > /var/www/html/.htaccess << '\''EOF'\''
# BEGIN WordPress Multisite
# Using subfolder network type
RewriteEngine On
RewriteRule .* - [E=HTTP_AUTHORIZATION:%{HTTP:Authorization}]
RewriteBase /
RewriteRule ^index\.php$ - [L]

# add a trailing slash to /wp-admin
RewriteRule ^([_0-9a-zA-Z-]+/)?wp-admin$ $1wp-admin/ [R=301,L]

RewriteCond %{REQUEST_FILENAME} -f [OR]
RewriteCond %{REQUEST_FILENAME} -d
RewriteRule ^ - [L]
RewriteRule ^([_0-9a-zA-Z-]+/)?(wp-(content|admin|includes).*) $2 [L]
RewriteRule ^([_0-9a-zA-Z-]+/)?(.*\.php)$ $2 [L]
RewriteRule . index.php [L]

# END WordPress Multisite
SetEnvIf Authorization (.+) HTTPS=on
EOF'

# 15. Network activate WooCommerce plugin

$podman_or_docker exec woo-wp wp plugin activate woocommerce --network --allow-root --path=/var/www/html

# 16. Verify multisite configuration

# 16.1 Check multisite status
$podman_or_docker exec woo-wp wp eval "echo is_multisite() ? 'Multisite enabled' : 'Single site';" --allow-root --path=/var/www/html

# 16.2 List all sites
$podman_or_docker exec woo-wp wp site list --allow-root --path=/var/www/html

# 16.3 Check plugin status
$podman_or_docker exec woo-wp wp plugin list --network --allow-root --path=/var/www/html

echo "========================================="
echo "Multisite configuration verified"
echo "========================================="

# Function to load user data from JSON
load_users_from_json() {
    local users_file="configs/users_data.json"
    local start_index=${1:-1}  # Default start from user 1
    local count=${2:-20}       # Default count 20
    
    if [ ! -f "$users_file" ]; then
        echo "❌ Error: $users_file not found"
        exit 1
    fi
    
    # Extract users data from JSON file, starting from specified index
    # Note: jq array indexing is 0-based, so we subtract 1 from start_index
    local jq_start=$((start_index - 1))
    local jq_end=$((jq_start + count - 1))
    
    jq -r ".users[${jq_start}:${jq_end}] | .[] | \"\(.id)|\(.first_name)|\(.last_name)|\(.full_name)|\(.email)|\(.password)|\(.woocommerce_consumer_key)|\(.woocommerce_consumer_secret)\"" "$users_file"
}

echo "Staring to create multisite stores using user data from configs/users_data.json..."

# Get total users from JSON file
TOTAL_JSON_USERS=$(jq '.users | length' configs/users_data.json 2>/dev/null || echo "0")

if [ "$TOTAL_JSON_USERS" -eq 0 ]; then
    echo "❌ Error: No users found in configs/users_data.json"
    exit 1
fi

# Validate start user and count
if [ "$START_USER" -lt 1 ] || [ "$START_USER" -gt "$TOTAL_JSON_USERS" ]; then
    echo "❌ Error: Start user $START_USER is out of range (1-$TOTAL_JSON_USERS)"
    exit 1
fi

if [ "$((START_USER + USER_COUNT - 1))" -gt "$TOTAL_JSON_USERS" ]; then
    echo "⚠ Warning: Requested range exceeds available users, adjusting count"
    USER_COUNT=$((TOTAL_JSON_USERS - START_USER + 1))
fi

# Use specified user range
NUM_SITES=$USER_COUNT
echo "Creating $NUM_SITES sites using users $START_USER to $((START_USER + NUM_SITES - 1))"

BASE_URL="http://localhost:$PORT"
OUTPUT_FILE="deployment/woocommerce/configs/multisite-api-keys.json"

# Validate input is a positive integer
if ! [[ "$NUM_SITES" =~ ^[0-9]+$ ]] || [ "$NUM_SITES" -lt 1 ]; then
    echo "Error: Please provide a positive integer for number of sites"
    exit 1
fi

# Check if container is running
if ! $podman_or_docker exec woo-wp wp --version --allow-root --path=/var/www/html &>/dev/null; then
    echo "Error: WooCommerce container is not running or wp-cli is not available"
    echo "Please run setup-woocommerce.sh first"
    exit 1
fi

# Check if already converted to multisite
if ! $podman_or_docker exec woo-wp wp eval "echo is_multisite() ? 'true' : 'false';" --allow-root --path=/var/www/html 2>/dev/null | grep -q "true"; then
    echo "Error: WordPress is not configured as multisite"
    echo "Please convert to multisite first using: wp core multisite-convert"
    exit 1
fi

echo "Creating $NUM_SITES WooCommerce subsites..."
echo "Base URL: $BASE_URL"
echo ""

# Create output directory
mkdir -p deployment/woocommerce/configs

# Start JSON array
echo "[" > "$OUTPUT_FILE"

# Create subsites and generate API keys
echo "Creating $NUM_SITES WooCommerce subsites using real user data..."

# Create temporary file to store user data from JSON
TEMP_USERS=$(mktemp)
load_users_from_json "$START_USER" "$USER_COUNT" > "$TEMP_USERS"

CREATED_COUNT=0

while IFS='|' read -r user_id first_name last_name full_name email password consumer_key consumer_secret; do
    SITE_SLUG="store$user_id"
    SITE_TITLE="$first_name $last_name's Store"  # Use first name for store title
    SITE_EMAIL="$email"  # Use real email from JSON
    SITE_URL="$BASE_URL/$SITE_SLUG/"
    
    echo "Creating site: $SITE_SLUG ($SITE_TITLE)"
    
    # Create subsites
    SITE_RESULT=$($podman_or_docker exec woo-wp wp site create \
        --slug="$SITE_SLUG" \
        --title="$SITE_TITLE" \
        --email="$SITE_EMAIL" \
        --allow-root \
        --path=/var/www/html 2>&1)
    
    if echo "$SITE_RESULT" | grep -q "Success"; then
        echo "  ✓ Site created successfully"
        
        # Use predefined API keys instead of randomly generating
        echo "  Using predefined API keys..."
        
        # Use predefined API keys from JSON
        CONSUMER_KEY="$consumer_key"
        CONSUMER_SECRET="$consumer_secret"
        
        # Insert API keys into database
        API_INSERT_RESULT=$($podman_or_docker exec woo-wp wp eval '
$user_id = 1;
$consumer_key = "'"$CONSUMER_KEY"'";
$consumer_secret = "'"$CONSUMER_SECRET"'";

global $wpdb;
$result = $wpdb->insert(
    $wpdb->prefix . "woocommerce_api_keys",
    array(
        "user_id" => $user_id,
        "description" => "'"$SITE_SLUG"' API Key",
        "permissions" => "read_write",
        "consumer_key" => wc_api_hash($consumer_key),
        "consumer_secret" => $consumer_secret,
        "truncated_key" => substr($consumer_key, -7)
    )
);

if($result === false) {
    echo "ERROR";
} else {
    echo "SUCCESS";
}
' --url="$SITE_URL" --allow-root --path=/var/www/html 2>/dev/null)
        
        if [ "$API_INSERT_RESULT" = "SUCCESS" ]; then
            echo "  ✓ API keys configured"
            
            # Add to JSON file
            if [ $CREATED_COUNT -gt 0 ]; then
                echo "," >> "$OUTPUT_FILE"
            fi
            
            cat >> "$OUTPUT_FILE" << EOF
  {
    "user_id": $user_id,
    "site_slug": "$SITE_SLUG",
    "site_title": "$SITE_TITLE",
    "site_url": "$SITE_URL",
    "owner_name": "$full_name",
    "owner_email": "$SITE_EMAIL",
    "api_base_url": "${SITE_URL}wp-json/wc/v3/",
    "consumer_key": "$CONSUMER_KEY",
    "consumer_secret": "$CONSUMER_SECRET",
    "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  }
EOF
            
            CREATED_COUNT=$((CREATED_COUNT + 1))
            echo "  ✓ Added to configuration file"
        else
            echo "  ✗ Failed to configure API keys"
        fi
    else
        echo "  ⚠ Site creation failed or already exists: $SITE_RESULT"
    fi
    
    echo ""
done < "$TEMP_USERS"

# Clean up temp file
rm -f "$TEMP_USERS"

# End JSON array
echo "" >> "$OUTPUT_FILE"
echo "]" >> "$OUTPUT_FILE"

echo "========================================="
echo "Batch creation completed!"
echo "========================================="
echo "Created $CREATED_COUNT subsites with WooCommerce API keys using real user data"
echo "User range: $START_USER to $((START_USER + CREATED_COUNT - 1))"
echo "Configuration saved to: $OUTPUT_FILE"
echo ""
echo "Sample Store URLs:"
# Show first few stores created
count=0
while IFS='|' read -r user_id first_name last_name full_name email password consumer_key consumer_secret && [ $count -lt 5 ]; do
    if [ $count -lt $CREATED_COUNT ]; then
        echo "  $first_name's Store: $BASE_URL/store$user_id/"
    fi
    count=$((count + 1))
done < "$TEMP_USERS"
echo ""
echo "API Configuration:"
cat "$OUTPUT_FILE" | uv run python -m json.tool 2>/dev/null || cat "$OUTPUT_FILE"
echo ""
echo "========================================="
echo "Usage Examples:"
echo "# Test first store API (if available):"
if [ -f "$OUTPUT_FILE" ]; then
    FIRST_KEY=$(cat "$OUTPUT_FILE" | uv run python -c "import json,sys;data=json.load(sys.stdin);print(data[0]['consumer_key'] if data else '')" 2>/dev/null)
    FIRST_SECRET=$(cat "$OUTPUT_FILE" | uv run python -c "import json,sys;data=json.load(sys.stdin);print(data[0]['consumer_secret'] if data else '')" 2>/dev/null)
    FIRST_SLUG=$(cat "$OUTPUT_FILE" | uv run python -c "import json,sys;data=json.load(sys.stdin);print(data[0]['site_slug'] if data else '')" 2>/dev/null)
    FIRST_TITLE=$(cat "$OUTPUT_FILE" | uv run python -c "import json,sys;data=json.load(sys.stdin);print(data[0]['site_title'] if data else '')" 2>/dev/null)
    if [ -n "$FIRST_KEY" ] && [ -n "$FIRST_SECRET" ] && [ -n "$FIRST_SLUG" ]; then
        echo "# Test $FIRST_TITLE API:"
        echo "curl -u \"$FIRST_KEY:$FIRST_SECRET\" \"$BASE_URL/$FIRST_SLUG/wp-json/wc/v3/products\""
    fi
fi
echo "========================================="

# 12. Print service management hints
echo ""
echo "========================================="
echo "Available Commands:"
echo "  Stop Service: $0 stop"
echo "  Start Service: $0 start"
echo "  Restart Service: $0 restart"
echo "  Show Help: $0 help"
echo "========================================="

echo "fix premissions ..."
bash deployment/woocommerce/scripts/fix_permissions.sh