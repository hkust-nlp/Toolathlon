#!/bin/bash

agent_workspace=$3

# 设置变量
k8sconfig_path_dir=${agent_workspace}/k8s_configs
backup_k8sconfig_path_dir=deployment/k8s/configs
cluster_name="cluster-redis-helm"
resource_yaml="${agent_workspace}/k8s_configs/redis_helm_namespace.yaml"
helm_repo_name="bitnami"
helm_repo_url="https://charts.bitnami.com/bitnami"
helm_chart_name="redis"
helm_release_name="redis"
namespace="shared-services"
initial_version="19.0.0"  # Initial version to deploy

# values_file="tasks/zhaochen/k8s_redis_helm_upgrade/initial_workspace/config/redis-values.yaml"
# values_file will be set based on operation and parameters

podman_or_docker=$(uv run python -c "import sys; sys.path.append('configs'); from global_configs import global_configs; print(global_configs.podman_or_docker)")

echo "podman_or_docker: $podman_or_docker"

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

# 显示使用说明
show_usage() {
  echo "Usage: $0 [start|stop] [values_file]"
  echo ""
  echo "Parameters:"
  echo "  start values_file - Create and start Kind cluster with Redis Helm deployment using specified values file"
  echo "  stop              - Stop and clean up the Kind cluster and configuration files"
  echo ""
  echo "Examples:"
  echo "  $0 start /path/to/redis-values.yaml   # Create cluster and deploy Redis with custom values"
  echo "  $0 stop                               # Clean up cluster"
  echo ""
  echo "Note: values_file is required when using 'start' operation"
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
  if KIND_EXPERIMENTAL_PROVIDER=$podman_or_docker kind create cluster --name "$cluster_name" --kubeconfig "$config_path"; then
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
    kubectl --kubeconfig="$config_path" wait --for=condition=Ready pods --all -n kube-system --timeout=120s &>/dev/null
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

# 创建命名空间
create_namespace() {
  local config_path=$1
  log_info "Creating namespace: $namespace"
  
  # Create namespace YAML if it doesn't exist
  mkdir -p ${agent_workspace}/k8s_configs
  cat > "$resource_yaml" <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: shared-services
  labels:
    name: shared-services
EOF
  
  export KUBECONFIG="$config_path"
  if kubectl apply -f "$resource_yaml"; then
    log_info "Namespace created successfully"
    return 0
  else
    log_error "Failed to create namespace"
    return 1
  fi
}

# 配置 Helm
setup_helm() {
  local config_path=$1
  export KUBECONFIG="$config_path"
  
  log_info "Setting up Helm repository..."
  
  # Add Helm repository
  if helm repo add "$helm_repo_name" "$helm_repo_url"; then
    log_info "Helm repository $helm_repo_name added successfully"
  else
    log_warning "Helm repository $helm_repo_name might already exist, updating..."
  fi
  
  # Update Helm repositories
  if helm repo update; then
    log_info "Helm repositories updated successfully"
  else
    log_error "Failed to update Helm repositories"
    return 1
  fi
  
  return 0
}

# 部署 Redis with Helm
deploy_redis_helm() {
  local config_path=$1
  export KUBECONFIG="$config_path"
  
  log_info "Deploying Redis using Helm chart version $initial_version..."
  
  # Check if values file exists
  if [ ! -f "$values_file" ]; then
    log_error "Values file not found: $values_file"
    return 1
  fi
  
  # Deploy Redis with specific version
  # 记录开始时间
  start_time=$(date +%s)

  if helm install "$helm_release_name" "$helm_repo_name/$helm_chart_name" \
    --namespace "$namespace" \
    --version "$initial_version" \
    --values "$values_file" \
    --wait \
    --timeout 5m; then
    log_info "Redis deployed successfully with version $initial_version"
  else
    log_error "Failed to deploy Redis"
    # log_info "========== 开始详细调试信息 =========="
    
    # # 检查Pod状态
    # log_info "检查Pod状态："
    # kubectl --kubeconfig="$config_path" -n "$namespace" get pods -o wide
    
    # # 检查Pod详细信息
    # log_info "检查Pod详细描述："
    # kubectl --kubeconfig="$config_path" -n "$namespace" describe pods
    
    # # 检查Events
    # log_info "检查命名空间Events："
    # kubectl --kubeconfig="$config_path" -n "$namespace" get events --sort-by='.lastTimestamp'
    
    # # 检查PVC状态
    # log_info "检查PVC状态："
    # kubectl --kubeconfig="$config_path" -n "$namespace" get pvc
    
    # # 检查Helm状态
    # log_info "检查Helm发布状态："
    # helm --kubeconfig="$config_path" list -n "$namespace" -a
    
    # # 检查节点资源
    # log_info "检查节点资源："
    # kubectl --kubeconfig="$config_path" top nodes || echo "metrics-server未安装，无法显示资源使用情况"
    # kubectl --kubeconfig="$config_path" describe nodes
    
    # log_info "========== 调试信息结束 =========="
    return 1
  fi
  # 记录结束时间
  end_time=$(date +%s)
  elapsed_time=$((end_time - start_time))
  log_info "Redis deployment took $elapsed_time seconds"
  
  # Show deployment status
  log_info "Checking Redis deployment status..."
  kubectl --kubeconfig="$config_path" -n "$namespace" get pods
  kubectl --kubeconfig="$config_path" -n "$namespace" get svc
  
  # Get the deployed version
  log_info "Deployed Redis Helm release information:"
  helm --kubeconfig="$config_path" list -n "$namespace"
  helm --kubeconfig="$config_path" get values "$helm_release_name" -n "$namespace" > /tmp/deployed-redis-values.yaml
  log_info "Current deployed values saved to /tmp/deployed-redis-values.yaml"
  
  return 0
}

# Copy values file to user home config directory
copy_values_to_home() {
  local user_home_config="$HOME/config"
  
  log_info "Copying Redis values file to user home directory..."
  
  # Create config directory in user home if it doesn't exist
  mkdir -p "$user_home_config"
  
  # Copy the values file
  if cp "$values_file" "$user_home_config/redis-values.yaml"; then
    log_info "Values file copied to $user_home_config/redis-values.yaml"
  else
    log_error "Failed to copy values file to user home directory"
    return 1
  fi
  
  return 0
}

# 部署轻量级干扰项
deploy_lightweight_distractors() {
  local config_path=$1
  export KUBECONFIG="$config_path"
  
  log_info "Deploying lightweight distractor resources..."
  
  # 创建额外命名空间
  log_info "Creating additional namespaces for complexity..."
  kubectl create namespace monitoring-services --dry-run=client -o yaml | kubectl apply -f - &>/dev/null || true
  kubectl create namespace dev-environment --dry-run=client -o yaml | kubectl apply -f - &>/dev/null || true
  
  # 创建一些ConfigMaps和Secrets作为干扰项
  log_info "Creating distractor ConfigMaps and Secrets..."
  kubectl create configmap redis-monitoring-config -n monitoring-services --from-literal=host=localhost --from-literal=port=6379 &>/dev/null || true
  kubectl create configmap cache-config -n dev-environment --from-literal=type=redis --from-literal=ttl=3600 &>/dev/null || true
  kubectl create configmap redisinsight-config -n shared-services --from-literal=database_url=redis://localhost:6379 &>/dev/null || true
  kubectl create secret generic redis-backup-creds -n shared-services --from-literal=access_key=fake_key --from-literal=secret_key=fake_secret &>/dev/null || true
  kubectl create secret generic monitoring-tokens -n monitoring-services --from-literal=prometheus_token=fake_token &>/dev/null || true
  
  # 创建一个简单的redis-exporter Deployment作为干扰项
  log_info "Creating redis-exporter deployment as distractor..."
  cat <<EOF | kubectl apply -f - &>/dev/null || true
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis-exporter
  namespace: monitoring-services
  labels:
    app: redis-exporter
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis-exporter
  template:
    metadata:
      labels:
        app: redis-exporter
    spec:
      containers:
      - name: redis-exporter
        image: oliver006/redis_exporter:v1.45.0
        ports:
        - containerPort: 9121
          name: metrics
        env:
        - name: REDIS_ADDR
          value: "redis://localhost:6379"
        resources:
          requests:
            memory: "32Mi"
            cpu: "10m"
          limits:
            memory: "64Mi"
            cpu: "50m"
---
apiVersion: v1
kind: Service
metadata:
  name: redis-exporter-svc
  namespace: monitoring-services
  labels:
    app: redis-exporter
spec:
  ports:
  - port: 9121
    targetPort: 9121
    name: metrics
  selector:
    app: redis-exporter
EOF

  # 创建一个nginx deployment作为另一个干扰项
  log_info "Creating nginx deployment as additional distractor..."
  cat <<EOF | kubectl apply -f - &>/dev/null || true
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cache-proxy
  namespace: dev-environment
  labels:
    app: cache-proxy
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cache-proxy
  template:
    metadata:
      labels:
        app: cache-proxy
    spec:
      containers:
      - name: nginx
        image: nginx:1.21-alpine
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "16Mi"
            cpu: "5m"
          limits:
            memory: "32Mi"
            cpu: "20m"
---
apiVersion: v1
kind: Service
metadata:
  name: cache-proxy-svc
  namespace: dev-environment
spec:
  ports:
  - port: 80
    targetPort: 80
  selector:
    app: cache-proxy
EOF

  log_info "Lightweight distractors deployed successfully"
  return 0
}

# 启动操作
start_operation() {
  log_info "========== Start Kind cluster deployment with Redis Helm =========="
  cleanup_existing_cluster
  cleanup_config_files
  show_inotify_status
  configpath="$k8sconfig_path_dir/${cluster_name}-config.yaml"
  backup_configpath="$backup_k8sconfig_path_dir/${cluster_name}-config.yaml"

  echo ""
  log_info "========== Processing cluster ${cluster_name} =========="

  # Create cluster
  create_cluster "${cluster_name}" "$configpath"
  verify_cluster "${cluster_name}" "$configpath"
  
  # Create namespace
  create_namespace "$configpath"
  
  # Setup Helm
  setup_helm "$configpath"
  
  # Deploy Redis with Helm
  deploy_redis_helm "$configpath"
  
  # Deploy lightweight distractors
  # 加了干扰项会导致内存exhausted重启，所以先注释掉
  # deploy_lightweight_distractors "$configpath"
  
  # # Copy values file to user home
  # Update: no need to do so I think
  # copy_values_to_home
  
  # 复制配置文件到备份目录
  cp "$configpath" "$backup_configpath"

  log_info "========== Redis Helm deployment completed =========="
  log_info "Cluster: $cluster_name"  # 应该加上这行
  log_info "Redis has been deployed to namespace: $namespace"
  log_info "Redis version: $initial_version"
  log_info "Values file available at: $values_file"
  log_info "Cluster config: $configpath"  # 也应该显示具体的配置文件路径
  log_info "To check the deployment: helm list -n $namespace"
  log_info "To get Redis password: kubectl get secret --namespace $namespace redis -o jsonpath=\"{.data.redis-password}\" | base64 -d"
  
  log_info "========== Deployment completed =========="
  log_info "All Kind clusters:"
  kind get clusters
  log_info "Generated configuration files:"
  ls -la "$k8sconfig_path_dir"/*.yaml 2>/dev/null || log_warning "No configuration files found"
  ls -la "$backup_k8sconfig_path_dir"/*.yaml 2>/dev/null || log_warning "No backup configuration files found"
  show_inotify_status
}

# 主函数
main() {
  local operation=${1:-start}
  local values_file_param=$2
  
  case "$operation" in
    "start") 
      if [ -z "$values_file_param" ]; then
        log_error "Values file is required for start operation"
        show_usage
        exit 1
      fi
      if [ ! -f "$values_file_param" ]; then
        log_error "Values file not found: $values_file_param"
        exit 1
      fi
      values_file="$values_file_param"
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

# 检查依赖
check_dependencies() {
  local deps=("kind" "kubectl" "helm" "$podman_or_docker")
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