#!/bin/bash

# 设置变量
k8sconfig_path_dir=deployment/k8s/configs
cluster_prefix="cluster"
cluster_count=2
batch_size=1  # 每批创建3个集群
batch_delay=1  # 批次之间等待30秒

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
    echo "用法: $0 [start|stop]"
    echo ""
    echo "参数:"
    echo "  start  - 创建并启动 Kind 集群 (默认行为)"
    echo "  stop   - 停止并清理所有 Kind 集群和配置文件"
    echo ""
    echo "示例:"
    echo "  $0 start    # 创建集群"
    echo "  $0 stop     # 清理集群"
    echo "  $0          # 默认执行 start 操作"
}

# 清理函数
cleanup_existing_clusters() {
    log_info "开始清理现有集群..."
    
    # 获取所有 kind 集群
    existing_clusters=$(kind get clusters 2>/dev/null)
    
    if [ -n "$existing_clusters" ]; then
        log_info "发现以下集群："
        echo "$existing_clusters"
        
        # 删除每个集群
        while IFS= read -r cluster; do
            log_info "删除集群: $cluster"
            kind delete cluster --name "$cluster"
        done <<< "$existing_clusters"
        
        log_info "所有集群已删除"
    else
        log_info "没有发现现有集群"
    fi
}

# 清理配置文件
cleanup_config_files() {
    log_info "清理配置文件目录: $k8sconfig_path_dir"
    
    if [ -d "$k8sconfig_path_dir" ]; then
        rm -rf "$k8sconfig_path_dir"/*
        log_info "配置文件已清理"
    else
        log_warning "配置目录不存在，创建目录: $k8sconfig_path_dir"
        mkdir -p "$k8sconfig_path_dir"
    fi
}

# 停止操作
stop_operation() {
    log_info "========== 开始停止操作 =========="
    
    # 1. 清理现有集群
    cleanup_existing_clusters
    
    # 2. 清理配置文件
    cleanup_config_files
    
    log_info "========== 停止操作完成 =========="
}

# 创建集群
create_cluster() {
    local cluster_name=$1
    local config_path=$2
    
    log_info "创建集群: $cluster_name"
    
    # 使用 podman 作为 provider 创建集群
    if KIND_EXPERIMENTAL_PROVIDER=podman kind create cluster --name "$cluster_name" --kubeconfig "$config_path"; then
        log_info "集群 $cluster_name 创建成功"
        return 0
    else
        log_error "集群 $cluster_name 创建失败"
        return 1
    fi
}

# 验证集群
verify_cluster() {
    local cluster_name=$1
    local config_path=$2
    
    log_info "验证集群: $cluster_name"
    
    # 检查配置文件是否存在
    if [ ! -f "$config_path" ]; then
        log_error "配置文件不存在: $config_path"
        return 1
    fi
    
    # 获取集群信息
    if kubectl --kubeconfig="$config_path" cluster-info &>/dev/null; then
        log_info "集群 $cluster_name 运行正常"
        
        # 获取节点信息
        nodes=$(kubectl --kubeconfig="$config_path" get nodes -o wide 2>/dev/null)
        if [ $? -eq 0 ]; then
            echo "节点信息:"
            echo "$nodes"
        fi
        
        # 检查所有 pod 是否就绪
        kubectl --kubeconfig="$config_path" wait --for=condition=Ready pods --all -n kube-system --timeout=60s &>/dev/null
        if [ $? -eq 0 ]; then
            log_info "所有系统 Pod 已就绪"
        else
            log_warning "部分系统 Pod 未就绪"
        fi
        
        return 0
    else
        log_error "无法连接到集群 $cluster_name"
        return 1
    fi
}

# 显示 inotify 状态
show_inotify_status() {
    local current_instances=$(ls /proc/*/fd/* 2>/dev/null | xargs -I {} readlink {} 2>/dev/null | grep -c inotify || echo "0")
    local max_instances=$(cat /proc/sys/fs/inotify/max_user_instances 2>/dev/null || echo "unknown")
    log_info "Inotify 实例使用情况: $current_instances / $max_instances"
}

# 启动操作
start_operation() {
    log_info "========== 开始 Kind 集群部署 =========="
    
    # 1. 清理现有集群
    cleanup_existing_clusters
    
    # 2. 清理配置文件
    cleanup_config_files
    
    # 3. 显示初始 inotify 状态
    show_inotify_status
    
    # 4. 计算批次数量
    total_batches=$(( (cluster_count + batch_size - 1) / batch_size ))
    
    log_info "将创建 $cluster_count 个集群，分为 $total_batches 批，每批 $batch_size 个"
    
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
        
        log_batch "========== 开始第 $((batch + 1))/$total_batches 批 (集群 $batch_start-$batch_end) =========="
        
        # 创建这一批的集群
        for i in $(seq $batch_start $batch_end); do
            clustername="${cluster_prefix}${i}"
            configpath="$k8sconfig_path_dir/$clustername-config.yaml"
            
            echo ""
            log_info "========== 处理集群 $i/$cluster_count =========="
            
            # 创建集群
            if create_cluster "$clustername" "$configpath"; then
                # 验证集群
                sleep 5  # 等待集群稳定
                if verify_cluster "$clustername" "$configpath"; then
                    ((success_count++))
                else
                    ((failed_count++))
                    log_error "集群 $clustername 验证失败"
                fi
            else
                ((failed_count++))
            fi
            
            # 每个集群之间短暂等待
            if [ $i -lt $batch_end ]; then
                log_info "等待 5 秒后创建下一个集群..."
                sleep 5
            fi
        done
        
        # 批次完成后的处理
        log_batch "第 $((batch + 1))/$total_batches 批完成"
        show_inotify_status
        
        # 如果不是最后一批，等待较长时间让资源释放
        if [ $batch -lt $((total_batches - 1)) ]; then
            log_batch "等待 $batch_delay 秒让系统资源释放..."
            for i in $(seq $batch_delay -1 1); do
                echo -ne "\r${BLUE}[BATCH]${NC} 等待中: $i 秒  "
                sleep 1
            done
            echo ""
            
            # 可选：在批次之间显示当前集群状态
            log_info "当前活跃的集群:"
            kind get clusters
        fi
    done
    
    # 6. 总结
    echo ""
    log_info "========== 部署完成 =========="
    log_info "成功创建并验证的集群: $success_count"
    log_error "失败的集群: $failed_count"
    
    # 列出所有集群
    log_info "当前所有 Kind 集群:"
    kind get clusters
    
    # 列出所有配置文件
    log_info "生成的配置文件:"
    ls -la "$k8sconfig_path_dir"/*.yaml 2>/dev/null || log_warning "没有找到配置文件"
    
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
            log_error "无效的操作: $operation"
            show_usage
            exit 1
            ;;
    esac
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
        log_error "缺少必要的命令: ${missing[*]}"
        log_info "请先安装这些工具"
        exit 1
    fi
}

# 脚本入口
check_dependencies
main "$@"