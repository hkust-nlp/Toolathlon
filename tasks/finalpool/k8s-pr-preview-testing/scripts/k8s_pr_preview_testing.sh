#!/bin/bash

agent_workspace=$3

# Set variables
SCRIPT_DIR=$(dirname "$0")
KIND_IMAGE_LOADER="${SCRIPT_DIR}/../../../../scripts/lib/kind_image_loader.sh"
if ! source "$KIND_IMAGE_LOADER"; then
  echo "Failed to load shared Kind image loader: $KIND_IMAGE_LOADER" >&2
  exit 1
fi
PORT=${1:-30123}  # Default port is 30123, can be overridden by the first argument
k8sconfig_path_dir=${agent_workspace}/k8s_configs
backup_k8sconfig_path_dir=${SCRIPT_DIR}/../k8s_configs
mkdir -p $backup_k8sconfig_path_dir
cluster_name="cluster-pr-preview"

podman_or_docker=$(uv run python -c "import sys; sys.path.append('configs'); from global_configs import global_configs; print(global_configs.podman_or_docker)")
instance_suffix=$(uv run python -c "
import yaml
try:
    with open('configs/ports_config.yaml', 'r') as f:
        config = yaml.safe_load(f) or {}
        print(config.get('instance_suffix', ''))
except Exception:
    print('')
" 2>/dev/null || echo "")
cluster_name="${cluster_name}${instance_suffix}"

# Color output definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Show configuration info
echo -e "${GREEN}[INFO]${NC} Configuration:"
echo -e "${GREEN}[INFO]${NC}   PORT: ${PORT}"
echo -e "${GREEN}[INFO]${NC}   AGENT_WORKSPACE: ${agent_workspace}"
echo -e "${GREEN}[INFO]${NC}   CONTAINER_RUNTIME: ${podman_or_docker}"

# Colorful logger functions
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_batch() { echo -e "${BLUE}[BATCH]${NC} $1"; }

show_usage() {
  echo "Usage: $0 [PORT] [OPERATION] [AGENT_WORKSPACE]"
  echo ""
  echo "Parameters:"
  echo "  PORT            - Port to map (default: 30123)"
  echo "  OPERATION       - start|stop (default: start)"
  echo "  AGENT_WORKSPACE - Workspace directory path"
  echo ""
  echo "Examples:"
  echo "  $0 30123 start /path/to/workspace   # Create cluster with port 30123"
  echo "  $0 8080 start /path/to/workspace    # Create cluster with port 8080"
  echo "  $0 30123 stop /path/to/workspace    # Clean up cluster"
  echo "  $0                                  # Use defaults (30123, start)"
}

# Remove existing cluster (only the specified cluster)
cleanup_existing_cluster() {
  log_info "Start cleaning up existing cluster if it exists..."
  if kind get clusters | grep -q "^${cluster_name}$"; then
    log_info "Found existing cluster: ${cluster_name}"
    log_info "Deleting cluster: ${cluster_name}"
    kind delete cluster --name "${cluster_name}"
    log_info "Cluster ${cluster_name} has been deleted"
  else
    log_info "No existing cluster ${cluster_name} found"
  fi
}

# Remove the exact kind node container created by this script if a prior
# run left it orphaned after the kind cluster record disappeared.
# For a single-node kind cluster, the runtime container name is
# ``${cluster_name}-control-plane``.
cleanup_agent_host_artifacts() {
  log_info "Cleaning up orphaned kind control-plane container if it exists..."
  local kind_container="${cluster_name}-control-plane"

  if "$podman_or_docker" ps -a --format '{{.Names}}' 2>/dev/null | grep -qx "$kind_container"; then
    log_info "  Removing kind container: $kind_container"
    "$podman_or_docker" rm -f "$kind_container" 2>&1 | sed 's/^/    /' || true
  else
    log_info "  No orphan kind container found: $kind_container"
  fi

  if ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
    log_warning "  Host port ${PORT} still bound after cleanup (non-container process?):"
    ss -tlnp 2>/dev/null | grep ":${PORT} " | sed 's/^/    /' || true
  fi
}

# Remove config files (only the specified config file)
cleanup_config_files() {
  local config_path="$k8sconfig_path_dir/${cluster_name}-config.yaml"
  log_info "Cleaning up configuration file: $config_path"
  if [ -f "$config_path" ]; then
    rm -f "$config_path"
    log_info "Configuration file cleaned up"
  else
    log_info "No configuration file found for ${cluster_name}"
  fi
  mkdir -p "$k8sconfig_path_dir"
  local backup_config_path="$backup_k8sconfig_path_dir/${cluster_name}-config.yaml"
  log_info "Cleaning up backup configuration file: $backup_config_path"
  if [ -f "$backup_config_path" ]; then
    rm -f "$backup_config_path"
    log_info "Backup configuration file cleaned up"
  else
    log_info "No backup configuration file found for ${cluster_name}"
  fi
  mkdir -p "$backup_k8sconfig_path_dir"
}

# Stop operation
stop_operation() {
  log_info "========== Start stopping operation =========="
  cleanup_existing_cluster
  cleanup_config_files
  log_info "========== Stopping operation completed =========="
}

# Create kind cluster
create_cluster() {
  local cluster_name=$1
  local config_path=$2
  log_info "Creating cluster: $cluster_name"
  cat <<EOF | KIND_EXPERIMENTAL_PROVIDER=${podman_or_docker} kind create cluster --name "$cluster_name" --kubeconfig "$config_path" --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  extraPortMappings:
  - containerPort: ${PORT}
    hostPort: ${PORT}
    listenAddress: "0.0.0.0"
    protocol: TCP
EOF
  if [ $? -eq 0 ]; then
    log_info "Cluster $cluster_name created successfully"
    return 0
  else
    log_error "Cluster $cluster_name creation failed"
    return 1
  fi
}

# Verify cluster
verify_cluster() {
  local cluster_name=$1
  local config_path=$2
  log_info "Verifying cluster: $cluster_name"
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


# Start operation (main deployment logic)
start_operation() {
  log_info "========== Start Kind cluster deployment for PR Preview Testing =========="
  cleanup_existing_cluster
  cleanup_config_files
  # Must run BEFORE create_cluster — otherwise an orphan forwarder/etc
  # still owns host port ${PORT} and the kind create step fails.
  cleanup_agent_host_artifacts
  show_inotify_status
  configpath="$k8sconfig_path_dir/${cluster_name}-config.yaml"
  backup_configpath="$backup_k8sconfig_path_dir/${cluster_name}-config.yaml"

  echo ""
  log_info "========== Processing cluster ${cluster_name} =========="

  # Propagate exit codes — a silent create/verify failure used to leave
  # preprocess reporting "done" while no cluster actually existed,
  # which then deadlocked the k8s MCP server at gateway_boot.
  if ! create_cluster "${cluster_name}" "$configpath"; then
    log_error "Aborting start_operation: kind create cluster failed for ${cluster_name}"
    return 1
  fi
  if ! verify_cluster "${cluster_name}" "$configpath"; then
    log_error "Aborting start_operation: cluster verification failed for ${cluster_name}"
    return 1
  fi

  # Pre-load the image referenced by preview.yaml on the agent's
  # feature/pr-123 branch (verified against
  # Toolathlon-Archive/SimpleShopping@feature/pr-123) so the agent's
  # ``kubectl apply -f preview.yaml`` doesn't have to pull from
  # Docker Hub.  If preview.yaml ever changes to a different image
  # tag, kubelet will simply fall back to a live pull.
  REQUIRED_IMAGES=(nginx:1.25-alpine)
  for _img in "${REQUIRED_IMAGES[@]}"; do
    if ! "$podman_or_docker" image inspect "$_img" >/dev/null 2>&1; then
      log_info "Host $podman_or_docker cache missing $_img — attempting $podman_or_docker pull..."
      if ! "$podman_or_docker" pull "$_img" 2>&1 | tail -3; then
        log_warning "$podman_or_docker pull $_img returned non-zero (rate limit/offline?)"
      fi
    fi
    if "$podman_or_docker" image inspect "$_img" >/dev/null 2>&1; then
      log_info "Loading $_img into cluster $cluster_name for the node platform (offline)..."
      toolathlon_kind_load_image "$podman_or_docker" "$cluster_name" "$_img" || \
        log_warning "Image preload failed for $_img"
    else
      log_warning "$_img unavailable on host after pull attempt — agent's kubectl apply will need to pull from upstream"
    fi
  done

  log_info "========== Cluster ready for deployment =========="
  log_info "KUBECONFIG is set to: $configpath"
  log_info "You can now deploy your services using:"
  log_info "  kubectl --kubeconfig=\"$configpath\" apply -f <your-yaml-file>"
  log_info "Or export KUBECONFIG to use kubectl directly:"
  log_info "  export KUBECONFIG=\"$configpath\""
  
  # Copy config to backup directory
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
  
  log_info "========== Kind Cluster Ready =========="
  log_info "Cluster is ready for your deployment"
  log_info "Port mapping configured: localhost:${PORT} -> container:${PORT}"
}

# Main function
main() {
  local operation=${2:-start}
  case "$operation" in
    "start") start_operation || exit 1 ;;
    "stop")  stop_operation  || exit 1 ;;
    *)
      log_error "Invalid operation: $operation"
      show_usage
      exit 1
      ;;
  esac
}

# Dependency check
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

# Script entry point
check_dependencies
main "$@"
