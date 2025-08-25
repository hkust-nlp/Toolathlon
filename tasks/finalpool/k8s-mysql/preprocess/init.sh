#!/bin/bash

# 设置变量
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

k8sconfig_path_dir=deployment/k8s/configs
cluster_name="cluster242"

resource_yaml="$SCRIPT_DIR/config.yaml"
dataset_path_dir="$SCRIPT_DIR/../data/f1/."
schema_path="$SCRIPT_DIR/f1_schema.sql"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的信息
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_batch() { echo -e "${BLUE}[BATCH]${NC} $1"; }


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
}

# 创建集群
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

load_f1_csv() {
  local ns="${1:-data}"          # 命名空间
  local loader_pod="${2:-csv-loader}"
  local mysql_svc="${3:-mysql-f1}"
  local db="${4:-f1}"

  log_info "Loading CSVs into '$db' via pod '$loader_pod'..."
  # 说明：如果你的 CSV 是 Windows 换行，请把 LINES TERMINATED BY 改为 '\r\n'
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
  local namespace="${1:-data}"   # 命名空间
  local mysql_sts="${2:-mysql-f1}"  # StatefulSet 名称
  local database="${3:-f1}"      # 数据库名
  local username="${4:-reader}" # 新用户名称
  local password="${5:-mcpbench0606}" # 新用户密码

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

# 启动操作
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
  export MYSQL_ROOT_PASSWORD="mcpbench0606"   # 或从安全位置读取

  # 确保 MySQL StatefulSet 就绪
  kubectl --kubeconfig="$configpath" -n data rollout status statefulset/mysql-f1

  # 确保 csv-loader Pod 就绪
  kubectl --kubeconfig="$configpath" -n data wait --for=condition=Ready pod/csv-loader --timeout=120s

  # 拷贝 CSV 到 csv-loader
  kubectl --kubeconfig="$configpath" -n data cp "$dataset_path_dir" csv-loader:/csv

  kubectl -n data exec -i mysql-f1-0 -- mysql -h mysql-f1 -uroot -p"$MYSQL_ROOT_PASSWORD" f1 < "$schema_path"

  load_f1_csv 

  create_mysql_readonly_user

  log_info "MySQL-f1 initialization completed."

  log_info "========== Deployment completed =========="
  log_info "All Kind clusters:"
  kind get clusters
  log_info "Generated configuration files:"
  ls -la "$k8sconfig_path_dir"/*.yaml 2>/dev/null || log_warning "No configuration files found"
  show_inotify_status
}



# 检查依赖
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

# 脚本入口
check_dependencies
start_operation