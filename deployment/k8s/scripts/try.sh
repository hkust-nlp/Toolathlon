#!/bin/bash

# ================= 基本变量 =================
k8sconfig_path_dir=deployment/k8s/configs
cluster_name="cluster240"
resource_yaml="deployment/k8s/source_files/try.yaml"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()    { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_batch()   { echo -e "${BLUE}[BATCH]${NC} $1"; }

show_usage() {
  echo "Usage: $0 [start|stop]"
  echo ""
  echo "Parameters:"
  echo "  start - Create and start Kind cluster (default behavior)"
  echo "  stop  - Stop and clean up the Kind cluster and configuration files"
  echo ""
  echo "Examples:"
  echo "  $0 start   # Create cluster"
  echo "  $0 stop    # Clean up cluster"
  echo "  $0         # Default behavior is to start cluster"
}

# =============== 清理相关函数 ===============
cleanup_existing_cluster() {
  log_info "Start cleaning up existing cluster if it exists..."
  if KIND_EXPERIMENTAL_PROVIDER=podman kind get clusters | grep -q "^${cluster_name}$"; then
    log_info "Found existing cluster: ${cluster_name}"
    log_info "Delete cluster: ${cluster_name}"
    KIND_EXPERIMENTAL_PROVIDER=podman kind delete cluster --name "${cluster_name}"
    log_info "Cluster ${cluster_name} has been deleted"
  else
    log_info "No existing cluster ${cluster_name} found"
  fi
}

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
}

stop_operation() {
  log_info "========== Start stopping operation =========="
  cleanup_existing_cluster
  cleanup_config_files
  log_info "========== Stopping operation completed =========="
}

# =============== 创建与验证 ===============
create_cluster() {
  local cluster_name=$1
  local config_path=$2
  log_info "Create cluster: $cluster_name"
  if KIND_EXPERIMENTAL_PROVIDER=podman kind create cluster --name "$cluster_name" --kubeconfig "$config_path"; then
    log_info "Cluster $cluster_name created successfully"
    return 0
  else
    log_error "Cluster $cluster_name creation failed"
    return 1
  fi
}

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
    kubectl --kubeconfig="$config_path" get nodes -o wide || true
    kubectl --kubeconfig="$config_path" wait --for=condition=Ready pods --all -n kube-system --timeout=60s || \
      log_warning "Some system pods are not ready"
    return 0
  else
    log_error "Cannot connect to cluster $cluster_name"
    return 1
  fi
}

# =============== 新增：准备并加载镜像（Podman + kind load） ===============
# 统一在升级前把会用到的改名镜像塞进所有 kind 节点
prepare_and_load_images() {
  local cluster_name=$1

  # 源 -> 目标 镜像映射
  local -a pairs=(
    "docker.io/library/nginx:1.14|mcpbench/payment-gateway:1.14"
    "docker.io/library/nginx:1.15|mcpbench/payment-gateway:1.15"
    "docker.io/library/nginx:1.16|mcpbench/payment-gateway:1.16"
    "docker.io/library/nginx:1.14|mcpbench/user-service:2.3.1"
    "docker.io/library/nginx:1.14|mcpbench/order-processor:1.5.0"
    "docker.io/library/nginx:1.14|mcpbench/inventory-manager:dev-latest"
  )

  # 用一次性目录避免旧包残留
  local tmpdir
  tmpdir=$(mktemp -d /tmp/kind-images-XXXXXX)
  log_info "Use temp dir: $tmpdir"

  for pair in "${pairs[@]}"; do
    IFS='|' read -r src dst <<< "$pair"
    log_batch "Podman pull $src"
    podman pull "$src" || { log_error "Failed to pull $src"; return 1; }

    log_batch "Tag → $dst"
    podman tag "$src" "$dst" || { log_error "Failed to tag $src as $dst"; return 1; }

    local tar_path="$tmpdir/$(echo "$dst" | tr '/:' '__').tar"
    log_batch "Save → $tar_path"
    rm -f "$tar_path" 2>/dev/null || true
    # 显式用 docker-archive 格式，kind 识别最好
    podman save --format docker-archive "$dst" -o "$tar_path" \
      || { log_error "Failed to save $dst"; return 1; }

    log_batch "Kind load → $dst"
    KIND_EXPERIMENTAL_PROVIDER=podman kind load image-archive "$tar_path" --name "$cluster_name" \
      || { log_error "Failed to kind load $dst"; return 1; }
  done

  # 校验所有节点都有关键镜像
  log_info "Verify images exist in all kind nodes"
  local nodes
  nodes=$(KIND_EXPERIMENTAL_PROVIDER=podman kind get nodes --name "$cluster_name")
  for n in $nodes; do
    podman exec "$n" crictl images | grep -q "mcpbench/payment-gateway.*1.15" || { log_error "missing 1.15 on $n"; return 1; }
    podman exec "$n" crictl images | grep -q "mcpbench/payment-gateway.*1.16" || { log_error "missing 1.16 on $n"; return 1; }
  done

  log_info "All images prepared and loaded into KinD"
  return 0
}

# =============== 辅助：诊断函数 ===============
debug_dump_payment_gateway() {
  log_warning "==== DEBUG payment-gateway ===="
  kubectl -n production get rs -l app=payment-gateway -o wide || true
  kubectl -n production get pods -l app=payment-gateway -o wide || true
  local bad
  bad=$(kubectl -n production get pods -l app=payment-gateway --no-headers 2>/dev/null | awk '$3!="Running" || $2!="1/1"{print $1}')
  for p in $bad; do
    echo "----- describe $p -----"
    kubectl -n production describe pod "$p" | tail -n +1 | sed -n '1,200p'
    echo "----- last events -----"
    kubectl -n production get events --sort-by=.lastTimestamp | tail -n 30
  done
}

# =============== 应用资源 ===============
apply_resources() {
  local config_path=$1
  log_info "Applying resources from $resource_yaml"
  export KUBECONFIG="$config_path"
  if kubectl apply -f "$resource_yaml"; then
    log_info "Resources applied successfully"
    kubectl annotate deployment/payment-gateway kubernetes.io/change-cause="stable v0" -n production --overwrite
    log_info "Initial annotation 'stable v0' added"
    return 0
  else
    log_error "Failed to apply resources"
    return 1
  fi
}

# =============== 新增：本地开发强制使用预加载镜像 ===============
set_pull_policy_never() {
  # 仅对 payment-gateway 调整，避免升级时去外网拉
  log_info "Patch payment-gateway imagePullPolicy=Never (local dev)"
  kubectl -n production patch deployment/payment-gateway \
    --type='json' \
    -p='[{"op":"add","path":"/spec/template/spec/containers/0/imagePullPolicy","value":"Never"}]' || true
}

# =============== 升级并带超时/诊断 ===============
update_deployment_version() {
  local config_path=$1
  export KUBECONFIG="$config_path"

  set_pull_policy_never

  log_info "Updating deployment to stable v1"
  if kubectl set image deployment/payment-gateway nginx=mcpbench/payment-gateway:1.15 -n production; then
    kubectl annotate deployment/payment-gateway kubernetes.io/change-cause="stable v1" -n production --overwrite
    log_info "Annotation 'stable v1' added"
    if ! kubectl rollout status deployment/payment-gateway -n production --timeout=120s; then
      log_error "Rollout to v1 timed out"
      debug_dump_payment_gateway
      return 1
    fi
  else
    log_error "Failed to update to stable v1"
    return 1
  fi

  log_info "Updating deployment to beta v2"
  if kubectl set image deployment/payment-gateway nginx=mcpbench/payment-gateway:1.16 -n production; then
    kubectl annotate deployment/payment-gateway kubernetes.io/change-cause="beta v2" -n production --overwrite
    log_info "Annotation 'beta v2' added"
    if ! kubectl rollout status deployment/payment-gateway -n production --timeout=120s; then
      log_error "Rollout to v2 timed out"
      debug_dump_payment_gateway
      return 1
    fi
    return 0
  else
    log_error "Failed to update to beta v2"
    debug_dump_payment_gateway
    return 1
  fi
}

# =============== 可选：查看 inotify 使用情况 ===============
show_inotify_status() {
  local current_instances
  current_instances=$(ls /proc/*/fd/* 2>/dev/null | xargs -I {} readlink {} 2>/dev/null | grep -c inotify || echo "0")
  local max_instances
  max_instances=$(cat /proc/sys/fs/inotify/max_user_instances 2>/dev/null || echo "unknown")
  log_info "Inotify instance usage: $current_instances / $max_instances"
}

# =============== 启动流程 ===============
start_operation() {
  log_info "========== Start Kind cluster deployment =========="
  cleanup_existing_cluster
  cleanup_config_files
  show_inotify_status
  success_count=0
  failed_count=0
  configpath="$k8sconfig_path_dir/${cluster_name}-config.yaml"

  echo ""
  log_info "========== Processing cluster ${cluster_name} =========="

  if create_cluster "${cluster_name}" "$configpath"; then
    sleep 5
    if verify_cluster "${cluster_name}" "$configpath"; then
      # 关键顺序：先把改名镜像塞到每个节点 -> 再 apply -> 再做升级
      if prepare_and_load_images "${cluster_name}"; then
        if apply_resources "$configpath"; then
          update_deployment_version "$configpath" || ((failed_count++))
        else
          ((failed_count++))
        fi
      else
        log_error "Failed to prepare/load images"
        ((failed_count++))
      fi
      ((success_count++))
    else
      ((failed_count++))
      log_error "Cluster ${cluster_name} verification failed"
    fi
  else
    ((failed_count++))
  fi

  echo ""
  log_info "========== Deployment completed =========="
  log_info "Successfully created and verified clusters: $success_count"
  log_error "Failed clusters: $failed_count"
  log_info "All Kind clusters:"
  KIND_EXPERIMENTAL_PROVIDER=podman kind get clusters
  log_info "Generated configuration files:"
  ls -la "$k8sconfig_path_dir"/*.yaml 2>/dev/null || log_warning "No configuration files found"
  show_inotify_status
}

# =============== 入口与依赖检查 ===============
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

check_dependencies() {
  local deps=("kind" "kubectl" "podman")
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

check_dependencies
main "$@"
