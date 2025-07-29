#!/bin/bash
# setup-wordpress.sh

### launch the pod, enable multisite, and create 20 sub sites for task use

# Configuration variables
PORT=10002
WP_URL="http://localhost:$PORT"
WP_TITLE="My WooCommerce Store"
WP_ADMIN_USER="mcpwoocommerce"
WP_ADMIN_PASS="mcpwoocommerce"
WP_ADMIN_EMAIL="woocommerce@mcp.com"
PRESET_NUM_SITES=20

# 1. Clean up and create new deployment
echo "Cleaning up old containers..."
podman pod rm -f woo-pod 2>/dev/null

echo "Creating new pod..."
podman pod create --name woo-pod -p ${PORT}:80

# 2. Start MySQL
echo "Starting MySQL..."
podman run -d \
  --pod woo-pod \
  --name woo-db \
  -e MYSQL_ROOT_PASSWORD=rootpass123 \
  -e MYSQL_DATABASE=wordpress \
  -e MYSQL_USER=wordpress \
  -e MYSQL_PASSWORD=wppass123 \
  mysql:8.0

# 3. Wait for MySQL to be ready
echo "Waiting for MySQL to start..."
for i in {1..30}; do
  if podman exec woo-db mysql -u wordpress -pwppass123 -e "SELECT 1" &>/dev/null; then
    echo "MySQL is ready"
    break
  fi
  sleep 1
done

# 4. Start WordPress
echo "Starting WordPress..."
podman run -d \
  --pod woo-pod \
  --name woo-wp \
  -e WORDPRESS_DB_HOST=127.0.0.1 \
  -e WORDPRESS_DB_USER=wordpress \
  -e WORDPRESS_DB_PASSWORD=wppass123 \
  -e WORDPRESS_DB_NAME=wordpress \
  wordpress:6.8.2-php8.2-apache

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

# 检查本地是否已有 wp-cli.phar
mkdir -p deployment/woocommerce/cache

if [ -f "./deployment/woocommerce/cache/wp-cli.phar" ]; then
    echo "Using local wp-cli.phar..."
    podman cp deployment/woocommerce/cache/wp-cli.phar woo-wp:/tmp/wp-cli.phar
    podman exec woo-wp bash -c '
        chmod +x /tmp/wp-cli.phar
        mv /tmp/wp-cli.phar /usr/local/bin/wp
    '
else
    echo "Downloading wp-cli.phar..."
    # 先下载到本地
    curl -o deployment/woocommerce/cache/wp-cli.phar https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar
    
    # 复制到容器
    podman cp deployment/woocommerce/cache/wp-cli.phar woo-wp:/tmp/wp-cli.phar
    podman exec woo-wp bash -c '
        chmod +x /tmp/wp-cli.phar
        mv /tmp/wp-cli.phar /usr/local/bin/wp
    '
fi

# 7. Install WordPress
echo "Configuring WordPress..."
podman exec woo-wp wp core install \
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
podman exec woo-wp wp plugin install woocommerce --activate --allow-root --path=/var/www/html

# 8.5 Set permalinks (new)
echo "Configuring permalinks..."
podman exec woo-wp wp rewrite structure '/%postname%/' --allow-root --path=/var/www/html
podman exec woo-wp wp rewrite flush --allow-root --path=/var/www/html

# Ensure .htaccess file is writable
podman exec woo-wp bash -c 'chmod 644 /var/www/html/.htaccess 2>/dev/null || touch /var/www/html/.htaccess && chmod 644 /var/www/html/.htaccess'

# 8.6 Configure HTTP authentication (new)
# ref: https://www.schakko.de/2020/09/05/fixing-http-401-unauthorized-when-calling-woocommerces-rest-api/#:~:text=The%20most%20obvious%20fix%20is%20to%20check%20that,a%20length%20of%2038%20bytes%20%28or%20ASCII%20characters%29.
echo "Configuring HTTP authentication support..."
podman exec woo-wp bash -c 'echo "SetEnvIf Authorization (.+) HTTPS=on" >> /var/www/html/.htaccess'

# 9. Generate REST API keys
echo "Generating WooCommerce REST API keys..."
API_CREDS=$(podman exec woo-wp wp eval '
$user_id = 1;
$consumer_key = "ck_" . wc_rand_hash();
$consumer_secret = "cs_" . wc_rand_hash();

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
cat deployment/woocommerce/configs/wc-api-credentials.json | python -m json.tool
echo "========================================="

# 11. Test API
echo ""
echo "Testing REST API..."
if [ -f deployment/woocommerce/configs/wc-api-credentials.json ]; then
    CONSUMER_KEY=$(cat deployment/woocommerce/configs/wc-api-credentials.json | python -c "import json,sys;print(json.load(sys.stdin)['consumer_key'])")
    CONSUMER_SECRET=$(cat deployment/woocommerce/configs/wc-api-credentials.json | python -c "import json,sys;print(json.load(sys.stdin)['consumer_secret'])")
    
    echo "Getting WooCommerce system status:"
    # Note: added -L parameter and trailing slash
    curl -s -L -u "$CONSUMER_KEY:$CONSUMER_SECRET" "$WP_URL/wp-json/wc/v3/system_status/tools/" | python -m json.tool | head -20
fi

# 12. Print service management hints
echo ""
echo "========================================="
echo "Service Management Commands:"
echo "  Stop service: podman pod stop woo-pod"
echo "  Start service: podman pod start woo-pod"
echo "  Remove completely: podman pod rm -f woo-pod"
echo "========================================="

echo "Starting to convert to multisite..."

# 13. 转换为多站点

podman exec woo-wp wp core multisite-convert --title="My Multisite Network" --allow-root --path=/var/www/html

# 14. 更新.htaccess文件（子文件夹模式）

podman exec woo-wp bash -c 'cat > /var/www/html/.htaccess << '\''EOF'\''
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

# 15. 网络激活WooCommerce插件

podman exec woo-wp wp plugin activate woocommerce --network --allow-root --path=/var/www/html

# 16. 验证多站点配置

# 16.1 检查多站点状态
podman exec woo-wp wp eval "echo is_multisite() ? 'Multisite enabled' : 'Single site';" --allow-root --path=/var/www/html

# 16.2 列出所有站点
podman exec woo-wp wp site list --allow-root --path=/var/www/html

# 16.3 检查插件状态
podman exec woo-wp wp plugin list --network --allow-root --path=/var/www/html

echo "========================================="
echo "Multisite configuration verified"
echo "========================================="

echo "Staring to to create multisite stores, we create $PRESET_NUM_SITES stores ..."

NUM_SITES=$PRESET_NUM_SITES
PORT=10002
BASE_URL="http://localhost:$PORT"
OUTPUT_FILE="deployment/woocommerce/configs/multisite-api-keys.json"

# 验证输入是数字
if ! [[ "$NUM_SITES" =~ ^[0-9]+$ ]] || [ "$NUM_SITES" -lt 1 ]; then
    echo "Error: Please provide a positive integer for number of sites"
    exit 1
fi

# 检查容器是否运行
if ! podman exec woo-wp wp --version --allow-root --path=/var/www/html &>/dev/null; then
    echo "Error: WooCommerce container is not running or wp-cli is not available"
    echo "Please run setup-woocommerce.sh first"
    exit 1
fi

# 检查是否已经转换为多站点
if ! podman exec woo-wp wp eval "echo is_multisite() ? 'true' : 'false';" --allow-root --path=/var/www/html 2>/dev/null | grep -q "true"; then
    echo "Error: WordPress is not configured as multisite"
    echo "Please convert to multisite first using: wp core multisite-convert"
    exit 1
fi

echo "Creating $NUM_SITES WooCommerce subsites..."
echo "Base URL: $BASE_URL"
echo ""

# 创建输出目录
mkdir -p deployment/woocommerce/configs

# 开始JSON数组
echo "[" > "$OUTPUT_FILE"

# 创建子站点并生成API密钥
CURRENT_SITE_NUM=1
CREATED_COUNT=0

while [ $CREATED_COUNT -lt $NUM_SITES ]; do
    SITE_SLUG="store$CURRENT_SITE_NUM"
    SITE_TITLE="Store $CURRENT_SITE_NUM"
    SITE_EMAIL="admin@store$CURRENT_SITE_NUM.com"
    SITE_URL="$BASE_URL/$SITE_SLUG/"
    
    echo "Creating site: $SITE_SLUG"
    
    # 创建子站点
    SITE_RESULT=$(podman exec woo-wp wp site create \
        --slug="$SITE_SLUG" \
        --title="$SITE_TITLE" \
        --email="$SITE_EMAIL" \
        --allow-root \
        --path=/var/www/html 2>&1)
    
    if echo "$SITE_RESULT" | grep -q "Success"; then
        echo "  ✓ Site created successfully"
        
        # 生成API密钥
        echo "  Generating API keys..."
        API_CREDS=$(podman exec woo-wp wp eval '
$user_id = 1;
$consumer_key = "ck_" . wc_rand_hash();
$consumer_secret = "cs_" . wc_rand_hash();

global $wpdb;
$wpdb->insert(
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

echo json_encode(array(
    "consumer_key" => $consumer_key,
    "consumer_secret" => $consumer_secret
));
' --url="$SITE_URL" --allow-root --path=/var/www/html 2>/dev/null)
        
        if [ $? -eq 0 ] && [ -n "$API_CREDS" ]; then
            echo "  ✓ API keys generated"
            
            # 解析API凭据
            CONSUMER_KEY=$(echo "$API_CREDS" | python -c "import json,sys;print(json.load(sys.stdin)['consumer_key'])" 2>/dev/null)
            CONSUMER_SECRET=$(echo "$API_CREDS" | python -c "import json,sys;print(json.load(sys.stdin)['consumer_secret'])" 2>/dev/null)
            
            # 添加到JSON文件
            if [ $CREATED_COUNT -gt 0 ]; then
                echo "," >> "$OUTPUT_FILE"
            fi
            
            cat >> "$OUTPUT_FILE" << EOF
  {
    "site_id": $CURRENT_SITE_NUM,
    "site_slug": "$SITE_SLUG",
    "site_title": "$SITE_TITLE",
    "site_url": "$SITE_URL",
    "api_base_url": "${SITE_URL}wp-json/wc/v3/",
    "consumer_key": "$CONSUMER_KEY",
    "consumer_secret": "$CONSUMER_SECRET",
    "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  }
EOF
            
            CREATED_COUNT=$((CREATED_COUNT + 1))
            echo "  ✓ Added to configuration file"
        else
            echo "  ✗ Failed to generate API keys"
        fi
    else
        echo "  ⚠ Site already exists, trying next number..."
    fi
    
    CURRENT_SITE_NUM=$((CURRENT_SITE_NUM + 1))
    echo ""
done

# 结束JSON数组
echo "" >> "$OUTPUT_FILE"
echo "]" >> "$OUTPUT_FILE"

echo "========================================="
echo "Batch creation completed!"
echo "========================================="
echo "Created $NUM_SITES subsites with WooCommerce API keys"
echo "Configuration saved to: $OUTPUT_FILE"
echo ""
echo "Site URLs:"
for i in $(seq 1 $NUM_SITES); do
    echo "  Store $i: $BASE_URL/store$i/"
done
echo ""
echo "API Configuration:"
cat "$OUTPUT_FILE" | python -m json.tool 2>/dev/null || cat "$OUTPUT_FILE"
echo ""
echo "========================================="
echo "Usage Examples:"
echo "# Test Store 1 API:"
if [ -f "$OUTPUT_FILE" ]; then
    FIRST_KEY=$(cat "$OUTPUT_FILE" | python -c "import json,sys;data=json.load(sys.stdin);print(data[0]['consumer_key'] if data else '')" 2>/dev/null)
    FIRST_SECRET=$(cat "$OUTPUT_FILE" | python -c "import json,sys;data=json.load(sys.stdin);print(data[0]['consumer_secret'] if data else '')" 2>/dev/null)
    if [ -n "$FIRST_KEY" ] && [ -n "$FIRST_SECRET" ]; then
        echo "curl -u \"$FIRST_KEY:$FIRST_SECRET\" \"$BASE_URL/store1/wp-json/wc/v3/products\""
    fi
fi
echo "========================================="

# 12. Print service management hints
echo ""
echo "========================================="
echo "[Print Again] Service Management Commands:"
echo "  Stop service: podman pod stop woo-pod"
echo "  Start service: podman pod start woo-pod"
echo "  Remove completely: podman pod rm -f woo-pod"
echo "========================================="