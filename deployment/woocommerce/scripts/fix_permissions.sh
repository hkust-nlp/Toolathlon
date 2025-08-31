#!/bin/bash
# fix_permissions.sh - Fix WooCommerce upload permissions

# read out `podman_or_docker` from global_configs.py
podman_or_docker=$(uv run python -c "import sys; sys.path.append('configs'); from global_configs import global_configs; print(global_configs.podman_or_docker)")


echo "Fixing WooCommerce upload permissions..."

# Check if container is running
if ! $podman_or_docker exec woo-wp wp --version --allow-root --path=/var/www/html &>/dev/null; then
    echo "❌ Error: WooCommerce container 'woo-wp' is not running"
    echo "Please run deployment/woocommerce/scripts/setup.sh first"
    exit 1
fi

echo "1. Ensuring uploads directory exists and creating current month folder..."
CURRENT_YEAR=$(date +%Y)
CURRENT_MONTH=$(date +%m)

$podman_or_docker exec woo-wp bash -c "
    # Create base uploads directory if it doesn't exist
    mkdir -p /var/www/html/wp-content/uploads/
    
    # Create current year/month directory structure
    mkdir -p /var/www/html/wp-content/uploads/$CURRENT_YEAR/$CURRENT_MONTH
    
    echo \"Created directory structure for $CURRENT_YEAR/$CURRENT_MONTH\"
"

echo "2. Setting correct ownership..."
# Set ownership to www-data (Apache user in WordPress container)
$podman_or_docker exec woo-wp bash -c '
    chown -R www-data:www-data /var/www/html/wp-content/uploads/
'

echo "3. Setting correct permissions..."
# Set directories to 755 and files to 644
$podman_or_docker exec woo-wp bash -c '
    find /var/www/html/wp-content/uploads/ -type d -exec chmod 755 {} \;
    find /var/www/html/wp-content/uploads/ -type f -exec chmod 644 {} \;
'

echo "4. Verifying current directory structure and permissions..."
$podman_or_docker exec woo-wp bash -c '
    echo "=== Current uploads directory structure ==="
    find /var/www/html/wp-content/uploads/ -type d | head -10
    echo ""
    echo "=== Permissions for uploads directory ==="
    ls -la /var/www/html/wp-content/
    echo ""
    echo "=== Permissions for current uploads subdirectories ==="
    ls -la /var/www/html/wp-content/uploads/ 2>/dev/null || echo "No subdirectories found"
'

echo "5. Testing upload functionality..."
# Test if WordPress can write to uploads directory
TEST_RESULT=$($podman_or_docker exec woo-wp bash -c '
    if [ -w /var/www/html/wp-content/uploads/ ]; then
        echo "WRITABLE"
    else
        echo "NOT_WRITABLE"
    fi
')

if [ "$TEST_RESULT" = "WRITABLE" ]; then
    echo "✅ Upload directory is now writable"
else
    echo "❌ Upload directory is still not writable"
fi

echo ""
echo "========================================="
echo "Permission fix completed!"
echo "========================================="
echo "If you still get upload errors, try:"
echo "1. Restart the WooCommerce service:"
echo "   deployment/woocommerce/scripts/setup.sh restart"
echo "2. Check container logs:"
echo "   $podman_or_docker logs woo-wp"
echo "========================================="