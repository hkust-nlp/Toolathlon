#!/bin/bash

# read out `podman_or_docker` from global_configs.py
podman_or_docker=$(uv run python -c "import sys; sys.path.append('configs'); from global_configs import global_configs; print(global_configs.podman_or_docker)")


# 设置变量
k8sconfig_path_dir=deployment/k8s/configs
cluster_prefix="cluster"
cluster_count=1
batch_size=3  # 每批创建3个集群
batch_delay=5  # 批次之间等待30秒

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的信息
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_batch() {
    echo -e "${BLUE}[BATCH]${NC} $1"
}

# 显示使用说明
show_usage() {
    echo "Usage: $0 [start|stop]"
    echo ""
    echo "Parameters:"
    echo "  start  - Create and start Kind clusters (default behavior)"
    echo "  stop   - Stop and clean up all Kind clusters and configuration files"
    echo ""
    echo "Examples:"
    echo "  $0 start    # Create clusters"
    echo "  $0 stop     # Clean up clusters"
    echo "  $0          # Default behavior is to start clusters"
}

# 清理函数
cleanup_existing_clusters() {
    log_info "Start cleaning up existing clusters..."
    
    # 获取所有 kind 集群
    existing_clusters=$(kind get clusters 2>/dev/null)
    
    if [ -n "$existing_clusters" ]; then
        log_info "Found the following clusters:"
        echo "$existing_clusters"
        
        # 删除每个集群
        while IFS= read -r cluster; do
            log_info "Delete cluster: $cluster"
            kind delete cluster --name "$cluster"
        done <<< "$existing_clusters"
        
        log_info "All clusters have been deleted"
    else
        log_info "No existing clusters found"
    fi
}

# 清理配置文件
cleanup_config_files() {
    log_info "Clean up configuration file directory: $k8sconfig_path_dir"
    
    if [ -d "$k8sconfig_path_dir" ]; then
        rm -rf "$k8sconfig_path_dir"/*
        log_info "Configuration files have been cleaned up"
    else
        log_warning "Configuration directory does not exist, create directory: $k8sconfig_path_dir"
        mkdir -p "$k8sconfig_path_dir"
    fi
}

# 停止操作
stop_operation() {
    log_info "========== Start stopping operation =========="
    
    # 1. 清理现有集群
    cleanup_existing_clusters
    
    # 2. 清理配置文件
    cleanup_config_files
    
    log_info "========== Stopping operation completed =========="
}

# 创建集群
create_cluster() {
    local cluster_name=$1
    local config_path=$2
    
    log_info "Create cluster: $cluster_name"
    
    # 使用 podman/docker 作为 provider 创建集群
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
    
    # 检查配置文件是否存在
    if [ ! -f "$config_path" ]; then
        log_error "Configuration file does not exist: $config_path"
        return 1
    fi
    
    # 获取集群信息
    if kubectl --kubeconfig="$config_path" cluster-info &>/dev/null; then
        log_info "Cluster $cluster_name is running normally"
        
        # 获取节点信息
        nodes=$(kubectl --kubeconfig="$config_path" get nodes -o wide 2>/dev/null)
        if [ $? -eq 0 ]; then
            echo "Node information:"
            echo "$nodes"
        fi
        
        # 检查所有 pod 是否就绪
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

# 启动操作
start_operation() {
    log_info "========== Start Kind cluster deployment =========="
    
    # 1. 清理现有集群
    cleanup_existing_clusters
    
    # 2. 清理配置文件
    cleanup_config_files
    
    # 3. 显示初始 inotify 状态
    show_inotify_status
    
    # 4. 计算批次数量
    total_batches=$(( (cluster_count + batch_size - 1) / batch_size ))
    
    log_info "Will create $cluster_count clusters, divided into $total_batches batches, each batch has $batch_size clusters"
    
    success_count=0
    failed_count=0
    
    # 5. 分批创建集群
    for batch in $(seq 0 $((total_batches - 1))); do
        batch_start=$((batch * batch_size + 1))
        batch_end=$((batch_start + batch_size - 1))
        
        # 确保不超过总数
        if [ $batch_end -gt $cluster_count ]; then
            batch_end=$cluster_count
        fi
        
        log_batch "========== Start batch $((batch + 1))/$total_batches (cluster $batch_start-$batch_end) =========="
        
        # 创建这一批的集群
        for i in $(seq $batch_start $batch_end); do
            clustername="${cluster_prefix}${i}"
            configpath="$k8sconfig_path_dir/$clustername-config.yaml"
            
            echo ""
            log_info "========== Processing cluster $i/$cluster_count =========="
            
            # 创建集群
            if create_cluster "$clustername" "$configpath"; then
                # 验证集群
                sleep 5  # 等待集群稳定
                if verify_cluster "$clustername" "$configpath"; then
                    ((success_count++))
                else
                    ((failed_count++))
                    log_error "Cluster $clustername verification failed"
                fi
            else
                ((failed_count++))
            fi
            
            # 每个集群之间短暂等待
            if [ $i -lt $batch_end ]; then
                log_info "Wait 5 seconds before creating the next cluster..."
                sleep 5
            fi
        done
        
        # 批次完成后的处理
        log_batch "Batch $((batch + 1))/$total_batches completed"
        show_inotify_status
        
        # 如果不是最后一批，等待较长时间让资源释放
        if [ $batch -lt $((total_batches - 1)) ]; then
            log_batch "Wait $batch_delay seconds for system resources to be released..."
            for i in $(seq $batch_delay -1 1); do
                echo -ne "\r${BLUE}[BATCH]${NC} Waiting: $i seconds  "
                sleep 1
            done
            echo ""
            
            # 可选：在批次之间显示当前集群状态
            log_info "Current active clusters:"
            kind get clusters
        fi
    done
    
    # 6. 总结
    echo ""
    log_info "========== Deployment completed =========="
    log_info "Successfully created and verified clusters: $success_count"
    if [ $failed_count -gt 0 ]; then
        log_error "Failed clusters: $failed_count"
    fi
    
    # 列出所有集群
    log_info "All Kind clusters:"
    kind get clusters
    
    # 列出所有配置文件
    log_info "Generated configuration files:"
    ls -la "$k8sconfig_path_dir"/*.yaml 2>/dev/null || log_warning "No configuration files found"
    
    # 最终 inotify 状态
    show_inotify_status
}

# 主函数
main() {
    local operation=${1:-start}  # 默认操作是 start
    
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

# 检查依赖
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

# 脚本入口
check_dependencies
main "$@"