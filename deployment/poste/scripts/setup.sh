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
      echo "🗑️  Clean data directory (podman unshare)..."
      podman unshare rm -rf "$DATA_DIR"
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
    create_accounts
    ;;
  clean)
    stop_container
    perform_cleanup
    ;;
  *)
    echo "How to use: $0 {start|stop|restart|clean}"
    exit 1
    ;;
esac