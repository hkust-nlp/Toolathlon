#!/bin/bash

# Read `podman_or_docker` from global_configs.py
podman_or_docker=$(uv run python -c "import sys; sys.path.append('configs'); from global_configs import global_configs; print(global_configs.podman_or_docker)")

# Exposed ports - use unprivileged ports
WEB_PORT=10005        # Web interface port
SMTP_PORT=2525        # SMTP port
IMAP_PORT=1143        # IMAP port
SUBMISSION_PORT=1587  # SMTP submission port
NUM_USERS=503

# Data storage directories - convert to absolute path
DATA_DIR="$(pwd)/deployment/poste/data"
CONFIG_DIR="$(pwd)/deployment/poste/configs"

# Get command arguments
COMMAND=${1:-start}            # Default is start
CONFIGURE_DOVECOT=${2:-true}   # Default is true

# Function to stop and remove container
stop_container() {
  echo "🛑 Stopping Poste.io container..."
  $podman_or_docker stop poste 2>/dev/null
  $podman_or_docker rm poste 2>/dev/null
  echo "✅ Container stopped and removed"
}

# Function to start container
start_container() {
  # Create data directory and set permissions
  mkdir -p "$DATA_DIR"
  
  # Set directory permissions - Poste.io uses UID 1001
  chmod -R 777 "$DATA_DIR"
  
  echo "📁 Data directory: $DATA_DIR"
  
  # Start Poste.io
  echo "🚀 Starting Poste.io..."
  $podman_or_docker run -d \
    --name poste \
    --cap-add NET_ADMIN \
    --cap-add NET_RAW \
    --cap-add NET_BIND_SERVICE \
    --cap-add SYS_PTRACE \
    -p ${WEB_PORT}:80 \
    -p ${SMTP_PORT}:25 \
    -p ${IMAP_PORT}:143 \
    -p ${SUBMISSION_PORT}:587 \
    -e "DISABLE_CLAMAV=TRUE" \
    -e "DISABLE_RSPAMD=TRUE" \
    -e "DISABLE_P0F=TRUE" \
    -e "HTTPS_FORCE=0" \
    -e "HTTPS=OFF" \
    -v ${DATA_DIR}:/data:Z \
    --hostname mcp.com \
    analogic/poste.io:2.5.5

  # Check start status
  if [ $? -eq 0 ]; then
    echo "✅ Poste.io started successfully!"
    echo "📧 Web interface: http://localhost:${WEB_PORT}"
    echo "📁 Data directory: ${DATA_DIR}"
    echo ""
    echo "⚠️  Note: Non-standard ports are used"
    echo "   SMTP: localhost:${SMTP_PORT}"
    echo "   IMAP: localhost:${IMAP_PORT}"
    echo "   Submission: localhost:${SUBMISSION_PORT}"
    echo ""
    echo "First visit please go to: http://localhost:${WEB_PORT}/admin/install"
    echo "View logs please run: $podman_or_docker logs -f poste"
  else
    echo "❌ Start failed!"
    exit 1
  fi
}

# Function to modify mail service config in container to allow plaintext auth
configure_dovecot() {
  echo "🔧 Configuring mail services to allow plaintext authentication..."

  # Modify Dovecot SSL config: change ssl = required to ssl = yes
  $podman_or_docker exec poste sed -i 's/ssl = required/ssl = yes/' /etc/dovecot/conf.d/10-ssl.conf

  # Modify Dovecot auth config to allow cleartext authentication
  $podman_or_docker exec poste sed -i 's/auth_allow_cleartext = no/auth_allow_cleartext = yes/' /etc/dovecot/conf.d/10-auth.conf

  # Clean up previously added wrong config
  $podman_or_docker exec poste sed -i '/disable_plaintext_auth/d' /etc/dovecot/conf.d/10-auth.conf

  # Configure Haraka SMTP to allow plaintext auth
  echo "🔧 Configuring Haraka SMTP..."
  $podman_or_docker exec poste sed -i 's/tls_required = true/tls_required = false/' /opt/haraka-smtp/config/auth.ini

  # Configure Haraka Submission (port 587) to allow plaintext auth
  echo "🔧 Configuring Haraka Submission (port 587)..."
  $podman_or_docker exec poste sed -i 's/tls_required = true/tls_required = false/' /opt/haraka-submission/config/auth.ini

  # Temporarily disable auth plugin for submission for testing
  echo "🔧 Temporarily disabling auth plugin for submission..."
  $podman_or_docker exec poste sed -i 's/^auth\/poste/#auth\/poste/' /opt/haraka-submission/config/plugins

  # Configure relay ACL to allow local connections
  echo "🔧 Configuring relay ACL..."
  $podman_or_docker exec poste sh -c 'echo "127.0.0.1/8" > /opt/haraka-submission/config/relay_acl_allow'
  $podman_or_docker exec poste sh -c 'echo "192.168.0.0/16" >> /opt/haraka-submission/config/relay_acl_allow'
  $podman_or_docker exec poste sh -c 'echo "172.16.0.0/12" >> /opt/haraka-submission/config/relay_acl_allow'
  $podman_or_docker exec poste sh -c 'echo "10.0.0.0/8" >> /opt/haraka-submission/config/relay_acl_allow'

  # Verify Dovecot config
  echo "🔍 Verifying Dovecot configuration..."
  if $podman_or_docker exec poste doveconf -n > /dev/null 2>&1; then
    echo "✅ Dovecot configuration is valid"
  else
    echo "❌ Dovecot configuration error, checking..."
    $podman_or_docker exec poste doveconf -n
    return 1
  fi

  # Reload service config
  echo "🔄 Reloading mail service configurations..."
  $podman_or_docker exec poste doveadm reload 2>/dev/null || \
  $podman_or_docker exec poste kill -HUP $($podman_or_docker exec poste pgrep dovecot | head -1) 2>/dev/null || \
  echo "⚠️  Failed to reload Dovecot"

  # Restart Haraka SMTP services
  echo "🔄 Restarting Haraka services..."
  $podman_or_docker exec poste kill $($podman_or_docker exec poste pgrep -f "haraka.*smtp") 2>/dev/null || true
  $podman_or_docker exec poste kill $($podman_or_docker exec poste pgrep -f "haraka.*submission") 2>/dev/null || true
  sleep 3

  echo "✅ Mail services configured to allow plaintext authentication"
}

# Function to create accounts
create_accounts() {
  bash deployment/poste/scripts/create_users.sh $NUM_USERS
}

# Function to perform cleanup
perform_cleanup() {
  echo "🧹 Starting cleanup process..."
  
  # Clean data directory
  if [ -d "$DATA_DIR" ]; then
    if [ "$podman_or_docker" = "podman" ] && command -v podman >/dev/null 2>&1; then
      # Podman environment
      # Try direct removal first, if fails then use unshare
      if rm -rf "$DATA_DIR" >/dev/null 2>&1; then
        echo "🗑️  Cleaned data directory..."
      else
        echo "🗑️  Cleaned data directory (podman unshare)..."
        podman unshare rm -rf "$DATA_DIR"
      fi
    elif [ "$EUID" -eq 0 ]; then
      # Root user
      echo "🗑️  Cleaned data directory (as root)..."
      rm -rf "$DATA_DIR"
    else
      # Use sudo
      echo "🗑️  Cleaned data directory (sudo)..."
      sudo rm -rf "$DATA_DIR"
    fi
  fi
  
  # Clean config directory (usually doesn't need special permissions)
  if [ -d "$CONFIG_DIR" ]; then
    echo "🗑️  Cleaned configs directory..."
    rm -rf "$CONFIG_DIR"
  fi
  
  echo "✅ Cleanup completed"
}

# Main logic
case "$COMMAND" in
  start)
    stop_container
    perform_cleanup
    start_container
    sleep 10
    if [ "$CONFIGURE_DOVECOT" = "true" ]; then
      configure_dovecot
    fi
    create_accounts
    ;;
  stop)
    stop_container
    perform_cleanup
    ;;
  restart)
    stop_container
    perform_cleanup
    start_container
    sleep 10
    if [ "$CONFIGURE_DOVECOT" = "true" ]; then
      configure_dovecot
    fi
    create_accounts
    ;;
  clean)
    stop_container
    perform_cleanup
    ;;
  config)
    configure_dovecot
    ;;
  *)
    echo "How to use: $0 {start|stop|restart|clean|config}"
    echo "  start   - Stop old container and start new container"
    echo "  stop    - Just stop and delete container"
    echo "  restart - Restart container"
    echo "  config  - Configure Dovecot to allow plaintext auth"
    echo "  All above operations will clear old data and configs"
    exit 1
    ;;
esac