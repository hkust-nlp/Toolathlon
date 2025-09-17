#!/bin/bash

# read out `podman_or_docker` from global_configs.py
podman_or_docker=$(uv run python -c "import sys; sys.path.append('configs'); from global_configs import global_configs; print(global_configs.podman_or_docker)")


# 配置暴露的端口 - 使用非特权端口
WEB_PORT=10005      # Web 界面端口
SMTP_PORT=2525     # SMTP 端口
IMAP_PORT=1143     # IMAP 端口
SUBMISSION_PORT=1587 # SMTP 提交端口
NUM_USERS=503

# 数据存储目录 - 转换为绝对路径
DATA_DIR="$(pwd)/deployment/poste/data"
CONFIG_DIR="$(pwd)/deployment/poste/configs"

# 获取命令参数
COMMAND=${1:-start}  # 默认为 start

# 停止和删除容器的函数
stop_container() {
  echo "🛑 Stop Poste.io container..."
  $podman_or_docker stop poste 2>/dev/null
  $podman_or_docker rm poste 2>/dev/null
  echo "✅ Container stopped and deleted"
}

# 启动容器的函数
start_container() {
  # 创建数据目录并设置权限
  mkdir -p "$DATA_DIR"
  
  # 设置目录权限 - Poste.io 使用 UID 1001
  chmod -R 777 "$DATA_DIR"
  
  echo "📁 Data directory: $DATA_DIR"
  
 # 启动 Poste.io
echo "🚀 Start Poste.io..."
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

  # 检查启动状态
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

# 修改容器内邮件服务配置以允许明文认证
configure_dovecot() {
  echo "🔧 Configuring mail services to allow plaintext auth..."

  # 等待容器完全启动
  sleep 10

  # 修改 Dovecot SSL 配置，将 ssl = required 改为 ssl = yes
  $podman_or_docker exec poste sed -i 's/ssl = required/ssl = yes/' /etc/dovecot/conf.d/10-ssl.conf

  # 修改 Dovecot 认证配置，允许明文认证
  $podman_or_docker exec poste sed -i 's/auth_allow_cleartext = no/auth_allow_cleartext = yes/' /etc/dovecot/conf.d/10-auth.conf

  # 清理之前错误添加的配置
  $podman_or_docker exec poste sed -i '/disable_plaintext_auth/d' /etc/dovecot/conf.d/10-auth.conf

  # 配置 Haraka SMTP 允许明文认证
  echo "🔧 Configuring Haraka SMTP..."
  $podman_or_docker exec poste sed -i 's/tls_required = true/tls_required = false/' /opt/haraka-smtp/config/auth.ini

  # 配置 Haraka Submission (端口587) 允许明文认证
  echo "🔧 Configuring Haraka Submission (port 587)..."
  $podman_or_docker exec poste sed -i 's/tls_required = true/tls_required = false/' /opt/haraka-submission/config/auth.ini

  # 临时禁用认证插件以测试
  echo "🔧 Temporarily disabling auth plugin for submission..."
  $podman_or_docker exec poste sed -i 's/^auth\/poste/#auth\/poste/' /opt/haraka-submission/config/plugins

  # 配置 relay ACL 允许本地连接
  echo "🔧 Configuring relay ACL..."
  $podman_or_docker exec poste sh -c 'echo "127.0.0.1/8" > /opt/haraka-submission/config/relay_acl_allow'
  $podman_or_docker exec poste sh -c 'echo "192.168.0.0/16" >> /opt/haraka-submission/config/relay_acl_allow'
  $podman_or_docker exec poste sh -c 'echo "172.16.0.0/12" >> /opt/haraka-submission/config/relay_acl_allow'
  $podman_or_docker exec poste sh -c 'echo "10.0.0.0/8" >> /opt/haraka-submission/config/relay_acl_allow'

  # 验证 Dovecot 配置是否正确
  echo "🔍 Verifying Dovecot configuration..."
  if $podman_or_docker exec poste doveconf -n > /dev/null 2>&1; then
    echo "✅ Dovecot configuration is valid"
  else
    echo "❌ Dovecot configuration error, checking..."
    $podman_or_docker exec poste doveconf -n
    return 1
  fi

  # 重新加载服务配置
  echo "🔄 Reloading mail service configurations..."
  $podman_or_docker exec poste doveadm reload 2>/dev/null || \
  $podman_or_docker exec poste kill -HUP $($podman_or_docker exec poste pgrep dovecot | head -1) 2>/dev/null || \
  echo "⚠️  Failed to reload Dovecot"

  # 重启 Haraka SMTP 服务
  echo "🔄 Restarting Haraka services..."
  $podman_or_docker exec poste kill $($podman_or_docker exec poste pgrep -f "haraka.*smtp") 2>/dev/null || true
  $podman_or_docker exec poste kill $($podman_or_docker exec poste pgrep -f "haraka.*submission") 2>/dev/null || true
  sleep 3

  echo "✅ Mail services configured to allow plaintext authentication"
}

# 创建账户的函数
create_accounts() {
  bash deployment/poste/scripts/create_users.sh $NUM_USERS
}

# 定义清理函数
perform_cleanup() {
  echo "🧹 Starting cleanup process..."
  
  # 清理数据目录
  if [ -d "$DATA_DIR" ]; then
    if [ "$podman_or_docker" = "podman" ] && command -v podman >/dev/null 2>&1; then
      # Podman 环境
      # 先尝试能不能直接删，不能再unshare
      if rm -rf "$DATA_DIR"; then
        echo "🗑️  Clean data directory..."
      else
        echo "🗑️  Clean data directory (podman unshare)..."
        podman unshare rm -rf "$DATA_DIR"
      fi
    elif [ "$EUID" -eq 0 ]; then
      # Root 用户
      echo "🗑️  Clean data directory (as root)..."
      rm -rf "$DATA_DIR"
    else
      # 有 sudo 权限
      echo "🗑️  Clean data directory (sudo)..."
      sudo rm -rf "$DATA_DIR"
    fi
  fi
  
  # 清理配置目录（通常不需要特殊权限）
  if [ -d "$CONFIG_DIR" ]; then
    echo "🗑️  Clean configs directory..."
    rm -rf "$CONFIG_DIR"
  fi
  
  echo "✅ Cleanup completed"
}

# 修改主逻辑
case "$COMMAND" in
  start)
    stop_container
    perform_cleanup
    start_container
    sleep 30
    configure_dovecot
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
    sleep 30
    configure_dovecot
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