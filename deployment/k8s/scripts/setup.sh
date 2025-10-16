#!/bin/bash

# Set variables
k8sconfig_path_dir=deployment/k8s/configs
cluster_prefix="cluster"
cluster_count=1
batch_size=3      # Number of clusters per batch
batch_delay=5     # Wait time (seconds) between batches

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

podman_or_docker=$(uv run python -c "import sys; sys.path.append('configs'); from global_configs import global_configs; print(global_configs.podman_or_docker)")

# Log with color
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

# Show usage instructions
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

# Clean up existing clusters
cleanup_existing_clusters() {
    log_info "Start cleaning up existing clusters..."
    
    # Get all kind clusters
    existing_clusters=$(kind get clusters 2>/dev/null)
    
    if [ -n "$existing_clusters" ]; then
        log_info "Found the following clusters:"
        echo "$existing_clusters"
        
        # Delete each cluster
        while IFS= read -r cluster; do
            log_info "Deleting cluster: $cluster"
            kind delete cluster --name "$cluster"
        done <<< "$existing_clusters"
        
        log_info "All clusters have been deleted"
    else
        log_info "No existing clusters found"
    fi
}

# Clean up config files
cleanup_config_files() {
    log_info "Cleaning up kubeconfig directory: $k8sconfig_path_dir"
    
    if [ -d "$k8sconfig_path_dir" ]; then
        rm -rf "$k8sconfig_path_dir"/*
        log_info "Configuration files have been cleaned up"
    else
        log_warning "Configuration directory does not exist, creating: $k8sconfig_path_dir"
        mkdir -p "$k8sconfig_path_dir"
    fi
}

# Stop operation
stop_operation() {
    log_info "========== Start stopping operation =========="
    
    # 1. Clean up existing clusters
    cleanup_existing_clusters
    
    # 2. Clean up config files
    cleanup_config_files
    
    log_info "========== Stopping operation completed =========="
}

# Create a cluster
create_cluster() {
    local cluster_name=$1
    local config_path=$2
    
    log_info "Creating cluster: $cluster_name"
    
    # Use podman/docker as the provider when creating the cluster
    if KIND_EXPERIMENTAL_PROVIDER=$podman_or_docker kind create cluster --name "$cluster_name" --kubeconfig "$config_path"; then
        log_info "Cluster $cluster_name created successfully"
        return 0
    else
        log_error "Cluster $cluster_name creation failed"
        return 1
    fi
}

# Verify a cluster
verify_cluster() {
    local cluster_name=$1
    local config_path=$2
    
    log_info "Verifying cluster: $cluster_name"
    
    # Check if kubeconfig file exists
    if [ ! -f "$config_path" ]; then
        log_error "Configuration file does not exist: $config_path"
        return 1
    fi
    
    # Get cluster info
    if kubectl --kubeconfig="$config_path" cluster-info &>/dev/null; then
        log_info "Cluster $cluster_name is running normally"
        
        # Get node info
        nodes=$(kubectl --kubeconfig="$config_path" get nodes -o wide 2>/dev/null)
        if [ $? -eq 0 ]; then
            echo "Node information:"
            echo "$nodes"
        fi
        
        # Check if all pods are ready
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

# Start operation
start_operation() {
    log_info "========== Start Kind cluster deployment =========="
    
    # 1. Clean up existing clusters
    cleanup_existing_clusters
    
    # 2. Clean up config files
    cleanup_config_files
    
    # 3. Show initial inotify usage
    show_inotify_status
    
    # 4. Calculate total number of batches
    total_batches=$(( (cluster_count + batch_size - 1) / batch_size ))
    
    log_info "Will create $cluster_count cluster(s), divided into $total_batches batch(es), each batch has up to $batch_size clusters"
    
    success_count=0
    failed_count=0
    
    # 5. Create clusters by batch
    for batch in $(seq 0 $((total_batches - 1))); do
        batch_start=$((batch * batch_size + 1))
        batch_end=$((batch_start + batch_size - 1))
        
        # Ensure we do not go beyond the desired cluster count
        if [ $batch_end -gt $cluster_count ]; then
            batch_end=$cluster_count
        fi
        
        log_batch "========== Start batch $((batch + 1))/$total_batches (cluster $batch_start-$batch_end) =========="
        
        # Create this batch of clusters
        for i in $(seq $batch_start $batch_end); do
            clustername="${cluster_prefix}${i}"
            configpath="$k8sconfig_path_dir/$clustername-config.yaml"
            
            echo ""
            log_info "========== Processing cluster $i/$cluster_count =========="
            
            # Create cluster
            if create_cluster "$clustername" "$configpath"; then
                # Verify cluster
                sleep 5  # Wait for the cluster to stabilize
                if verify_cluster "$clustername" "$configpath"; then
                    ((success_count++))
                else
                    ((failed_count++))
                    log_error "Cluster $clustername verification failed"
                fi
            else
                ((failed_count++))
            fi
            
            # Wait for a while between creating clusters
            if [ $i -lt $batch_end ]; then
                log_info "Wait 5 seconds before creating the next cluster..."
                sleep 5
            fi
        done
        
        # After batch actions
        log_batch "Batch $((batch + 1))/$total_batches completed"
        show_inotify_status
        
        # If not the last batch, wait longer to free up system resources
        if [ $batch -lt $((total_batches - 1)) ]; then
            log_batch "Wait $batch_delay seconds for system resources to be released..."
            for i in $(seq $batch_delay -1 1); do
                echo -ne "\r${BLUE}[BATCH]${NC} Waiting: $i seconds  "
                sleep 1
            done
            echo ""
            
            # Optionally: show the current clusters between batches
            log_info "Current active clusters:"
            kind get clusters
        fi
    done
    
    # 6. Summary
    echo ""
    log_info "========== Deployment completed =========="
    log_info "Successfully created and verified clusters: $success_count"
    log_error "Failed clusters: $failed_count"
    
    # List all clusters
    log_info "All Kind clusters:"
    kind get clusters
    
    # List all config files
    log_info "Generated kubeconfig files:"
    ls -la "$k8sconfig_path_dir"/*.yaml 2>/dev/null || log_warning "No configuration files found"
    
    # Show final inotify usage
    show_inotify_status
}

# Main function
main() {
    local operation=${1:-start}  # Default operation is 'start'
    
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

# Script entry
check_dependencies
main "$@"