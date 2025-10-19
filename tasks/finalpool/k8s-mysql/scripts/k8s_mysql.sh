#!/bin/bash

agent_workspace=$2

# Set the dirname of the absolute path of this script
SCRIPT_DIR=$(dirname "$0")

k8sconfig_path_dir=${agent_workspace}/k8s_configs
backup_k8sconfig_path_dir=${SCRIPT_DIR}/../k8s_configs
mkdir -p $backup_k8sconfig_path_dir
cluster_name="cluster-mysql"

resource_yaml="${SCRIPT_DIR}/../k8s_resources/k8s_mysql.yaml"
dataset_path_dir="$SCRIPT_DIR/../data"
podman_or_docker=$(uv run python -c "import sys; sys.path.append('configs'); from global_configs import global_configs; print(global_configs.podman_or_docker)")

echo "podman_or_docker: $podman_or_docker"
schema_path="$SCRIPT_DIR/../data/f1_schema.sql"

# Color output settings
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Output log functions with color
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_batch() { echo -e "${BLUE}[BATCH]${NC} $1"; }


# Cleanup function (targeting only the specified cluster)
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

# Cleanup config files (targeting only the specified config file)
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

# Verify cluster
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

# Show inotify status
show_inotify_status() {
  local current_instances=$(ls /proc/*/fd/* 2>/dev/null | xargs -I {} readlink {} 2>/dev/null | grep -c inotify || echo "0")
  local max_instances=$(cat /proc/sys/fs/inotify/max_user_instances 2>/dev/null || echo "unknown")
  log_info "Inotify instance usage: $current_instances / $max_instances"
}

# Apply resource YAML
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

load_f1_csv() {
  local ns="${1:-data}"
  local loader_pod="${2:-csv-loader}"
  local mysql_svc="${3:-mysql-f1}"
  local db="${4:-f1}"

  log_info "Loading CSVs into '$db' via pod '$loader_pod'..."
  # Note: If your CSVs use Windows line endings, change LINES TERMINATED BY to '\r\n'
  if ! kubectl -n "$ns" exec -i "$loader_pod" -- sh -lc '
mysql -h '"$mysql_svc"' -uroot -p"$MYSQL_ROOT_PASSWORD" --local-infile=1 '"$db"' <<'"'"'SQL'"'"'
SET NAMES utf8mb4;
SET GLOBAL local_infile = 1;
SET FOREIGN_KEY_CHECKS = 0;

TRUNCATE TABLE seasons;
LOAD DATA LOCAL INFILE "/csv/seasons.csv"
INTO TABLE seasons
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ","
OPTIONALLY ENCLOSED BY "\""
LINES TERMINATED BY "\n"
IGNORE 1 LINES;

TRUNCATE TABLE circuits;
LOAD DATA LOCAL INFILE "/csv/circuits.csv"
INTO TABLE circuits
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ","
OPTIONALLY ENCLOSED BY "\""
LINES TERMINATED BY "\n"
IGNORE 1 LINES;

TRUNCATE TABLE constructors;
LOAD DATA LOCAL INFILE "/csv/constructors.csv"
INTO TABLE constructors
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ","
OPTIONALLY ENCLOSED BY "\""
LINES TERMINATED BY "\n"
IGNORE 1 LINES;

TRUNCATE TABLE drivers;
LOAD DATA LOCAL INFILE "/csv/drivers.csv"
INTO TABLE drivers
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ","
OPTIONALLY ENCLOSED BY "\""
LINES TERMINATED BY "\n"
IGNORE 1 LINES;

TRUNCATE TABLE races;
LOAD DATA LOCAL INFILE "/csv/races.csv"
INTO TABLE races
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ","
OPTIONALLY ENCLOSED BY "\""
LINES TERMINATED BY "\n"
IGNORE 1 LINES;

TRUNCATE TABLE status;
LOAD DATA LOCAL INFILE "/csv/status.csv"
INTO TABLE status
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ","
OPTIONALLY ENCLOSED BY "\""
LINES TERMINATED BY "\n"
IGNORE 1 LINES;

TRUNCATE TABLE results;
LOAD DATA LOCAL INFILE "/csv/results.csv"
INTO TABLE results
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ","
OPTIONALLY ENCLOSED BY "\""
LINES TERMINATED BY "\n"
IGNORE 1 LINES;

TRUNCATE TABLE constructor_results;
LOAD DATA LOCAL INFILE "/csv/constructor_results.csv"
INTO TABLE constructor_results
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ","
OPTIONALLY ENCLOSED BY "\""
LINES TERMINATED BY "\n"
IGNORE 1 LINES;

TRUNCATE TABLE constructor_standings;
LOAD DATA LOCAL INFILE "/csv/constructor_standings.csv"
INTO TABLE constructor_standings
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ","
OPTIONALLY ENCLOSED BY "\""
LINES TERMINATED BY "\n"
IGNORE 1 LINES;

TRUNCATE TABLE driver_standings;
LOAD DATA LOCAL INFILE "/csv/driver_standings.csv"
INTO TABLE driver_standings
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ","
OPTIONALLY ENCLOSED BY "\""
LINES TERMINATED BY "\n"
IGNORE 1 LINES;

TRUNCATE TABLE lap_times;
LOAD DATA LOCAL INFILE "/csv/lap_times.csv"
INTO TABLE lap_times
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ","
OPTIONALLY ENCLOSED BY "\""
LINES TERMINATED BY "\n"
IGNORE 1 LINES;

TRUNCATE TABLE pit_stops;
LOAD DATA LOCAL INFILE "/csv/pit_stops.csv"
INTO TABLE pit_stops
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ","
OPTIONALLY ENCLOSED BY "\""
LINES TERMINATED BY "\n"
IGNORE 1 LINES;

TRUNCATE TABLE qualifying;
LOAD DATA LOCAL INFILE "/csv/qualifying.csv"
INTO TABLE qualifying
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ","
OPTIONALLY ENCLOSED BY "\""
LINES TERMINATED BY "\n"
IGNORE 1 LINES;

TRUNCATE TABLE sprint_results;
LOAD DATA LOCAL INFILE "/csv/sprint_results.csv"
INTO TABLE sprint_results
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ","
OPTIONALLY ENCLOSED BY "\""
LINES TERMINATED BY "\n"
IGNORE 1 LINES;

SET FOREIGN_KEY_CHECKS = 1;
SQL
'; then
    log_error "CSV loading failed."
    return 1
  fi

  log_info "CSV loading completed."
}

create_mysql_readonly_user() {
  local namespace="${1:-data}"
  local mysql_sts="${2:-mysql-f1}"
  local database="${3:-f1}"
  local username="${4:-reader}"
  local password="${5:-mcpbench0606}"

  log_info "Creating read-only MySQL user '$username' for database '$database' in ns=$namespace..."

  if kubectl -n "$namespace" exec -i statefulset/"$mysql_sts" -- sh -lc "
    mysql -uroot -p\"\$MYSQL_ROOT_PASSWORD\" -e \"
      CREATE USER IF NOT EXISTS '$username'@'%' IDENTIFIED BY '$password';
      GRANT SELECT ON \\\`$database\\\`.* TO '$username'@'%';
      FLUSH PRIVILEGES;
    \"
  "; then
    log_info "Read-only user '$username' created successfully."
  else
    log_error "Failed to create read-only user '$username'."
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

# Show usage instructions
show_usage() {
  echo "Usage: $0 [start|stop] [agent_workspace]"
  echo ""
  echo "Parameters:"
  echo "  start - Create and start Kind cluster with MySQL f1 database"
  echo "  stop  - Stop and clean up the Kind cluster and configuration files"
  echo "  agent_workspace - Path to agent workspace directory (optional for start)"
  echo ""
  echo "Examples:"
  echo "  $0 start /path/to/workspace   # Create cluster and deploy MySQL with f1 data"
  echo "  $0 stop                      # Clean up cluster"
}

# Start operation
start_operation() {
  log_info "========== Start Kind cluster deployment =========="
  cleanup_existing_cluster
  cleanup_config_files
  show_inotify_status
  configpath="$k8sconfig_path_dir/${cluster_name}-config.yaml"

  echo ""
  log_info "========== Processing cluster ${cluster_name} =========="

  create_cluster "${cluster_name}" "$configpath"
  verify_cluster "${cluster_name}" "$configpath"
  apply_resources "$configpath"

  log_info "========== Initializing MySQL-f1 database =========="
  export MYSQL_ROOT_PASSWORD="mcpbench0606"   # Or load securely as needed

  # Ensure MySQL StatefulSet is ready
  kubectl --kubeconfig="$configpath" -n data rollout status statefulset/mysql-f1

  # Ensure csv-loader Pod is ready
  kubectl --kubeconfig="$configpath" -n data wait --for=condition=Ready pod/csv-loader --timeout=120s

  # Copy CSV files to csv-loader
  kubectl --kubeconfig="$configpath" -n data cp "$dataset_path_dir/f1/." csv-loader:/csv

  kubectl -n data exec -i mysql-f1-0 -- mysql -h mysql-f1 -uroot -p"$MYSQL_ROOT_PASSWORD" f1 < "$schema_path"

  load_f1_csv

  create_mysql_readonly_user

  # Copy the config file to the backup directory
  mkdir -p "$backup_k8sconfig_path_dir"
  backup_configpath="$backup_k8sconfig_path_dir/${cluster_name}-config.yaml"
  cp "$configpath" "$backup_configpath"

  log_info "MySQL-f1 initialization completed."

  echo ""
  log_info "========== MySQL cluster deployment completed =========="
  log_info "Cluster: $cluster_name"
  log_info "MySQL database deployed with f1 data"
  log_info "Cluster config: $configpath"
  log_info "Backup config: $backup_configpath"

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

# Check dependencies
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

# Script entrypoint
check_dependencies
main "$@"