#!/bin/bash

agent_workspace=$2

# 设置变量
SCRIPT_DIR=$(dirname "$0")
k8sconfig_path_dir=${agent_workspace}/k8s_configs
# backup_k8sconfig_path_dir=deployment/k8s/configs
backup_k8sconfig_path_dir=${SCRIPT_DIR}/../k8s_configs
mkdir -p $backup_k8sconfig_path_dir
cluster_name="cluster-cleanup"
resource_yaml="${SCRIPT_DIR}/../k8s_resources/k8s_deployment_cleanup.yaml"

# 确认资源文件存在
if [ ! -f "$resource_yaml" ]; then
  log_error "Resource file does not exist: $resource_yaml"
  exit 1
fi

podman_or_docker=$(uv run python -c "import sys; sys.path.append('configs'); from global_configs import global_configs; print(global_configs.podman_or_docker)")

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 显示配置信息
echo -e "${GREEN}[INFO]${NC} Configuration:"
echo -e "${GREEN}[INFO]${NC}   AGENT_WORKSPACE: ${agent_workspace}"
echo -e "${GREEN}[INFO]${NC}   CONTAINER_RUNTIME: ${podman_or_docker}"

# 打印带颜色的信息
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_batch() { echo -e "${BLUE}[BATCH]${NC} $1"; }

# 显示使用说明
show_usage() {
  echo "Usage: $0 [OPERATION] [AGENT_WORKSPACE]"
  echo ""
  echo "Parameters:"
  echo "  OPERATION       - start|stop (default: start)"
  echo "  AGENT_WORKSPACE - Workspace directory path"
  echo ""
  echo "Examples:"
  echo "  $0 start /path/to/workspace   # Create cluster"
  echo "  $0 stop /path/to/workspace    # Clean up cluster"
  echo "  $0                            # Use defaults"
}

# 清理函数（仅针对指定集群）
cleanup_existing_cluster() {
  log_info "Start cleaning up existing cluster if it exists..."
  if kind get clusters | grep -q "^${cluster_name}$"; then
    log_info "Found existing cluster: ${cluster_name}"
    log_info "Delete cluster: ${cluster_name}"
    kind delete cluster --name "${cluster_name}"
    log_info "Cluster ${cluster_name} has been deleted"
  else
    log_info "No existing cluster ${cluster_name} found"
  fi
}

# 清理配置文件（仅针对指定配置文件）
cleanup_config_files() {
  local config_path="$k8sconfig_path_dir/${cluster_name}-config.yaml"
  log_info "Clean up configuration file: $config_path"
  if [ -f "$config_path" ]; then
    rm -f "$config_path"
    log_info "Configuration file cleaned up"
  else
    log_info "No configuration file found for ${cluster_name}"
  fi
  mkdir -p "$k8sconfig_path_dir"
  local backup_config_path="$backup_k8sconfig_path_dir/${cluster_name}-config.yaml"
  log_info "Clean up backup configuration file: $backup_config_path"
  if [ -f "$backup_config_path" ]; then
    rm -f "$backup_config_path"
    log_info "Backup configuration file cleaned up"
  else
    log_info "No backup configuration file found for ${cluster_name}"
  fi
  mkdir -p "$backup_k8sconfig_path_dir"
}

# 停止操作
stop_operation() {
  log_info "========== Start stopping operation =========="
  cleanup_existing_cluster
  cleanup_config_files
  log_info "========== Stopping operation completed =========="
}

# 创建集群
create_cluster() {
  local cluster_name=$1
  local config_path=$2
  log_info "Create cluster: $cluster_name"
  if KIND_EXPERIMENTAL_PROVIDER=${podman_or_docker} kind create cluster --name "$cluster_name" --kubeconfig "$config_path"; then
    log_info "Cluster $cluster_name created successfully"
    return 0
  else
    log_error "Cluster $cluster_name creation failed"
    return 1
  fi
}

# 验证集群
verify_cluster() {
  local cluster_name=$1
  local config_path=$2
  log_info "Verify cluster: $cluster_name"
  if [ ! -f "$config_path" ]; then
    log_error "Configuration file does not exist: $config_path"
    return 1
  fi
  if kubectl --kubeconfig="$config_path" cluster-info &>/dev/null; then
    log_info "Cluster $cluster_name is running normally"
    nodes=$(kubectl --kubeconfig="$config_path" get nodes -o wide 2>/dev/null)
    if [ $? -eq 0 ]; then
      echo "Node information:"
      echo "$nodes"
    fi
    kubectl --kubeconfig="$config_path" wait --for=condition=Ready pods --all -n kube-system --timeout=60s &>/dev/null
    if [ $? -eq 0 ]; then
      log_info "All system pods are ready"
    else
      log_warning "Some system pods are not ready"
    fi
    return 0
  else
    log_error "Cannot connect to cluster $cluster_name"
    return 1
  fi
}

# 显示 inotify 状态
show_inotify_status() {
  local current_instances=$(ls /proc/*/fd/* 2>/dev/null | xargs -I {} readlink {} 2>/dev/null | grep -c inotify || echo "0")
  local max_instances=$(cat /proc/sys/fs/inotify/max_user_instances 2>/dev/null || echo "unknown")
  log_info "Inotify instance usage: $current_instances / $max_instances"
}

# 应用资源YAML
apply_resources() {
  local config_path=$1
  log_info "Applying resources from $resource_yaml"
  export KUBECONFIG="$config_path"
  if kubectl apply -f "$resource_yaml"; then
    log_info "Resources applied successfully"
    return 0
  else
    log_error "Failed to apply resources"
    return 1
  fi
}

# 修改部署的时间戳，模拟老旧的部署
set_deployment_timestamps() {
  local config_path=$1
  export KUBECONFIG="$config_path"
  
  log_info "Setting deployment timestamps to simulate old deployments..."
  
  # 获取当前时间
  current_date=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  
  # 设置老旧部署的时间戳（使用kubectl patch来修改lastUpdateTime）
  # old-frontend-prototype: 62 days old
  date=$(date -u -d "62 days ago" +"%Y-%m-%dT%H:%M:%SZ")
  kubectl -n dev-frontend patch deployment frontend-prototype \
    --type='json' -p='[{"op": "add", "path": "/metadata/annotations/app-version-release-date", "value": "'$date'"}]'
  
  # legacy-auth-service: 88 days old  
  date=$(date -u -d "88 days ago" +"%Y-%m-%dT%H:%M:%SZ")
  kubectl -n dev-backend patch deployment auth-service \
    --type='json' -p='[{"op": "add", "path": "/metadata/annotations/app-version-release-date", "value": "'$date'"}]'
  
  # old-model-trainer: 76 days old
  date=$(date -u -d "76 days ago" +"%Y-%m-%dT%H:%M:%SZ")
  kubectl -n dev-ml patch deployment model-trainer \
    --type='json' -p='[{"op": "add", "path": "/metadata/annotations/app-version-release-date", "value": "'$date'"}]'
  
  # experimental-feature-alpha: 98 days old
  date=$(date -u -d "98 days ago" +"%Y-%m-%dT%H:%M:%SZ")
  kubectl -n dev-experimental patch deployment experimental-feature-alpha \
    --type='json' -p='[{"op": "add", "path": "/metadata/annotations/app-version-release-date", "value": "'$date'"}]'
  
  # abandoned-poc: 114 days old
  date=$(date -u -d "114 days ago" +"%Y-%m-%dT%H:%M:%SZ")
  kubectl -n dev-experimental patch deployment alpha-dataset-poc \
    --type='json' -p='[{"op": "add", "path": "/metadata/annotations/app-version-release-date", "value": "'$date'"}]'
  
  # active-api-service: 5 days old (recent, should not be cleaned)
  recent_date=$(date -u -d "5 days ago" +"%Y-%m-%dT%H:%M:%SZ")
  kubectl -n dev-backend patch deployment pod-api-service \
    --type='json' -p='[{"op": "add", "path": "/metadata/annotations/app-version-release-date", "value": "'$recent_date'"}]'
  
  # === 干扰项部署 ===
  # staging-app: 45 days old (old, should be cleaned)
  date=$(date -u -d "45 days ago" +"%Y-%m-%dT%H:%M:%SZ")
  kubectl -n staging patch deployment staging-app \
    --type='json' -p='[{"op": "add", "path": "/metadata/annotations/app-version-release-date", "value": "'$date'"}]'
    
  # prometheus-old: 82 days old (old, should be cleaned)
  date=$(date -u -d "82 days ago" +"%Y-%m-%dT%H:%M:%SZ")
  kubectl -n monitoring patch deployment prometheus-old \
    --type='json' -p='[{"op": "add", "path": "/metadata/annotations/app-version-release-date", "value": "'$date'"}]'
    
  # log-collector: 67 days old (old, should be cleaned)
  date=$(date -u -d "67 days ago" +"%Y-%m-%dT%H:%M:%SZ")
  kubectl -n logging patch deployment log-collector \
    --type='json' -p='[{"op": "add", "path": "/metadata/annotations/app-version-release-date", "value": "'$date'"}]'
    
  # web-server: 12 days old (recent, should not be cleaned - production)
  recent_date=$(date -u -d "12 days ago" +"%Y-%m-%dT%H:%M:%SZ")
  kubectl -n production patch deployment web-server \
    --type='json' -p='[{"op": "add", "path": "/metadata/annotations/app-version-release-date", "value": "'$recent_date'"}]'
    
  # backup-service: 8 days old (recent, should not be cleaned)
  recent_date=$(date -u -d "8 days ago" +"%Y-%m-%dT%H:%M:%SZ")
  kubectl -n backup patch deployment backup-service \
    --type='json' -p='[{"op": "add", "path": "/metadata/annotations/app-version-release-date", "value": "'$recent_date'"}]'
  
  log_info "Deployment timestamps have been set"
  
  # 显示所有部署的状态
  log_info "Current deployments in dev-* namespaces:"
  for ns in dev-frontend dev-backend dev-ml dev-experimental; do
    echo "Namespace: $ns"
    kubectl -n $ns get deployments -o wide
  done
  
  # 显示干扰项部署的状态
  log_info "Current deployments in non-dev namespaces (干扰项):"
  for ns in production staging monitoring logging backup; do
    echo "Namespace: $ns"
    kubectl -n $ns get deployments -o wide 2>/dev/null || echo "No deployments in $ns"
  done
}

# 启动操作
start_operation() {
  log_info "========== Start Kind cluster deployment =========="
  cleanup_existing_cluster
  cleanup_config_files
  show_inotify_status
  configpath="$k8sconfig_path_dir/${cluster_name}-config.yaml"
  backup_configpath="$backup_k8sconfig_path_dir/${cluster_name}-config.yaml"

  echo ""
  log_info "========== Processing cluster ${cluster_name} =========="

  create_cluster "${cluster_name}" "$configpath"
  verify_cluster "${cluster_name}" "$configpath"
  apply_resources "$configpath"
  
  # 等待所有部署就绪
  log_info "Waiting for all deployments to be ready..."
  sleep 10
  
  # 设置部署的时间戳
  set_deployment_timestamps "$configpath"

  # 复制配置文件到备份目录
  cp "$configpath" "$backup_configpath"
  log_info "Configuration file backed up to: $backup_configpath"

  log_info "========== Deployment completed =========="
  log_info "All Kind clusters:"
  kind get clusters
  log_info "Generated configuration files:"
  ls -la "$k8sconfig_path_dir"/*.yaml 2>/dev/null || log_warning "No configuration files found"
  log_info "Backup configuration files:"
  ls -la "$backup_k8sconfig_path_dir"/*.yaml 2>/dev/null || log_warning "No backup configuration files found"
  show_inotify_status
  
  log_info "========== K8s Deployment Cleanup Task Initialization Complete =========="
  log_info "The cluster has been set up with old deployments in dev-* namespaces."
  log_info "These deployments are ready to be cleaned up by the task."
}

# 主函数
main() {
  local operation=${1:-start}
  case "$operation" in
    "start") start_operation ;;
    "stop") stop_operation ;;
    *)
      log_error "Invalid operation: $operation"
      show_usage
      exit 1
      ;;
  esac
}

# 检查依赖
check_dependencies() {
  local deps=("kind" "kubectl" "${podman_or_docker}")
  local missing=()
  for cmd in "${deps[@]}"; do
    if ! command -v "$cmd" &> /dev/null; then
      missing+=("$cmd")
    fi
  done
  if [ ${#missing[@]} -gt 0 ]; then
    log_error "Missing required commands: ${missing[*]}"
    log_info "Please install these tools first"
    exit 1
  fi
}

# 脚本入口
check_dependencies
main "$@"