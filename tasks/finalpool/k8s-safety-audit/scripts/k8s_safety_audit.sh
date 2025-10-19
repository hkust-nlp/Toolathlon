#!/bin/bash

agent_workspace=$2

# Set variables
SCRIPT_DIR=$(dirname "$0")

k8sconfig_path_dir=${agent_workspace}/k8s_configs
backup_k8sconfig_path_dir=${SCRIPT_DIR}/../k8s_configs
mkdir -p $backup_k8sconfig_path_dir
cluster_name="cluster-safety-audit"
resource_yaml="${SCRIPT_DIR}/../k8s_resources/k8s_safety_audit.yaml"

podman_or_docker=$(uv run python -c "import sys; sys.path.append('configs'); from global_configs import global_configs; print(global_configs.podman_or_docker)")

echo "podman_or_docker: $podman_or_docker"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Colored logging functions
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_batch() { echo -e "${BLUE}[BATCH]${NC} $1"; }

# Clean up existing cluster if it exists (only for the designated cluster)
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

# Clean up config files (only for the designated config)
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
}

# Create cluster
create_cluster() {
  local cluster_name=$1
  local config_path=$2
  log_info "Create cluster: $cluster_name"
  if KIND_EXPERIMENTAL_PROVIDER=$podman_or_docker kind create cluster --name "$cluster_name" --kubeconfig "$config_path"; then
    log_info "Cluster $cluster_name created successfully"
    return 0
  else
    log_error "Cluster $cluster_name creation failed"
    return 1
  fi
}

# Verify cluster status
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

# Show inotify usage status
show_inotify_status() {
  local current_instances=$(ls /proc/*/fd/* 2>/dev/null | xargs -I {} readlink {} 2>/dev/null | grep -c inotify || echo "0")
  local max_instances=$(cat /proc/sys/fs/inotify/max_user_instances 2>/dev/null || echo "unknown")
  log_info "Inotify instance usage: $current_instances / $max_instances"
}

# Apply resources YAML
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

# Stop operation
stop_operation() {
  log_info "========== Start stopping operation =========="
  cleanup_existing_cluster
  cleanup_config_files
  log_info "========== Stopping operation completed =========="
}

# Show help
show_usage() {
  echo "Usage: $0 [start|stop]"
  echo ""
  echo "Parameters:"
  echo "  start - Create and start Kind cluster with security audit resources"
  echo "  stop  - Stop and clean up the Kind cluster and configuration files"
  echo ""
  echo "Examples:"
  echo "  $0 start   # Create cluster and deploy security audit resources"
  echo "  $0 stop    # Clean up cluster"
}

# Start operation
start_operation() {
  log_info "========== Start Kind cluster deployment for security audit =========="
  cleanup_existing_cluster
  cleanup_config_files
  show_inotify_status

  configpath="$k8sconfig_path_dir/${cluster_name}-config.yaml"
  backup_configpath="$backup_k8sconfig_path_dir/${cluster_name}-config.yaml"

  echo ""
  log_info "========== Processing cluster ${cluster_name} =========="

  create_cluster "$cluster_name" "$configpath"
  verify_cluster "${cluster_name}" "$configpath"
  apply_resources "$configpath"

  # Copy the config file to the backup directory
  cp "$configpath" "$backup_configpath"

  echo ""
  log_info "========== Security audit cluster deployment completed =========="
  log_info "Cluster: $cluster_name"
  log_info "Security audit resources deployed"
  log_info "Cluster config: $configpath"

  log_info "========== Deployment completed =========="
  log_info "All Kind clusters:"
  kind get clusters
  log_info "Generated configuration files:"
  ls -la "$k8sconfig_path_dir"/*.yaml 2>/dev/null || log_warning "No configuration files found"
  ls -la "$backup_k8sconfig_path_dir"/*.yaml 2>/dev/null || log_warning "No backup configuration files found"
  show_inotify_status
}

# Main function
main() {
  local operation=${1:-start}

  case "$operation" in
    "start")
      start_operation
      ;;
    "stop")
      stop_operation
      ;;
    *)
      log_error "Invalid operation: $operation"
      show_usage
      exit 1
      ;;
  esac
}

# Dependency check
check_dependencies() {
  local deps=("kind" "kubectl" "$podman_or_docker")
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

# Script entry
check_dependencies
main "$@"