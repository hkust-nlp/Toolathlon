#!/bin/bash

# 脚本名称：pod.sh
# 功能：管理最近创建的 Podman 容器
# 使用方法：./pod.sh enter|delete|status|list

# this is an auxiliary to enter and the delete the latest container

set -e

# podman_or_docker from global_configs.py
podman_or_docker=$(uv run python -c "import sys; sys.path.append('configs'); from global_configs import global_configs; print(global_configs.podman_or_docker)")

# 颜色定义
RED=''
GREEN=''
YELLOW=''
BLUE=''
NC='' # No Color

# 打印带颜色的消息
print_info() {
    printf "${BLUE}[INFO]${NC} $1\n"
}

print_success() {
    printf "${GREEN}[SUCCESS]${NC} $1\n"
}

print_error() {
    printf "${RED}[ERROR]${NC} $1\n"
}

print_warning() {
    printf "${YELLOW}[WARNING]${NC} $1\n"
}

# 获取最近创建的容器
get_latest_container() {
    # 使用 podman ps -a 获取所有容器，按创建时间排序，取第一个
    local container_id=$($podman_or_docker ps -a --format "{{.ID}}" --latest)
    
    if [ -z "$container_id" ]; then
        print_error "没有找到任何容器"
        exit 1
    fi
    
    echo "$container_id"
}

# 获取容器详细信息
get_container_info() {
    local container_id=$1
    local name=$($podman_or_docker ps -a --filter "id=$container_id" --format "{{.Names}}")
    local status=$($podman_or_docker ps -a --filter "id=$container_id" --format "{{.Status}}")
    local image=$($podman_or_docker ps -a --filter "id=$container_id" --format "{{.Image}}")
    local created=$($podman_or_docker ps -a --filter "id=$container_id" --format "{{.Created}}")
    
    printf "${BLUE}容器信息：${NC}\n"
    printf "  ID:     ${YELLOW}$container_id${NC}\n"
    printf "  名称:   ${YELLOW}$name${NC}\n"
    printf "  镜像:   $image\n"
    printf "  状态:   $status\n"
    printf "  创建于: $created\n"
}

# 进入容器
enter_container() {
    local container_id=$(get_latest_container)
    
    print_info "准备进入最近创建的容器..."
    get_container_info "$container_id"
    echo
    
    # 检查容器是否在运行
    local is_running=$($podman_or_docker ps --filter "id=$container_id" --format "{{.ID}}")
    
    if [ -z "$is_running" ]; then
        print_warning "容器未运行，正在启动..."
        $podman_or_docker start "$container_id" > /dev/null
        sleep 1
    fi
    
    # 检查容器是否有 bash 或 sh
    local shell="/bin/bash"
    if ! $podman_or_docker exec "$container_id" which bash &>/dev/null; then
        shell="/bin/sh"
        print_info "使用 sh 而不是 bash"
    fi
    
    print_success "正在进入容器 $container_id..."
    printf "${YELLOW}提示: 使用 'exit' 或 Ctrl+D 退出容器${NC}\n"
    printf "\n"
    
    # 进入容器
    $podman_or_docker exec -it "$container_id" $shell
}

# 删除容器
delete_container() {
    local container_id=$(get_latest_container)
    
    print_info "准备删除最近创建的容器..."
    get_container_info "$container_id"
    printf "\n"
    
    # 确认删除
    read -p "$(printf ${YELLOW}确定要删除这个容器吗？[y/N]:${NC}) " -n 1 -r
    printf "\n"
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "取消删除操作"
        exit 0
    fi
    
    # 停止容器（如果正在运行）
    local is_running=$($podman_or_docker ps --filter "id=$container_id" --format "{{.ID}}")
    if [ ! -z "$is_running" ]; then
        print_info "正在停止容器..."
        $podman_or_docker stop "$container_id" > /dev/null
    fi
    
    # 删除容器
    print_info "正在删除容器..."
    $podman_or_docker rm "$container_id" > /dev/null
    
    print_success "容器 $container_id 已成功删除"
}

# 显示容器状态
show_status() {
    local container_id=$(get_latest_container)
    get_container_info "$container_id"
}

# 列出最近的容器
list_recent() {
    print_info "最近创建的5个容器："
    printf "\n"
    $podman_or_docker ps -a --format "table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Created}}" | head -n 6
}

# 显示帮助信息
show_help() {
    cat << EOF
${GREEN}Podman/Docker 容器快速管理工具${NC}

${YELLOW}使用方法:${NC}
    $0 <command>

${YELLOW}可用命令:${NC}
    ${BLUE}enter${NC}    - 进入最近创建的容器
    ${BLUE}delete${NC}   - 停止并删除最近创建的容器
    ${BLUE}status${NC}   - 显示最近创建的容器状态
    ${BLUE}list${NC}     - 列出最近创建的5个容器
    ${BLUE}help${NC}     - 显示此帮助信息

${YELLOW}示例:${NC}
    $0 enter     # 进入最近的容器
    $0 delete    # 删除最近的容器
    $0 status    # 查看最近容器的状态

${YELLOW}快捷别名设置:${NC}
    在 ~/.bashrc 或 ~/.zshrc 中添加：
    ${GREEN}alias pe='$0 enter'${NC}
    ${GREEN}alias pd='$0 delete'${NC}
    ${GREEN}alias ps='$0 status'${NC}

EOF
}

# 主函数
main() {
    # 检查是否安装了 podman
    if ! command -v podman &> /dev/null; then
        print_error "Podman/Docker 未安装，请先安装 Podman/Docker"
        exit 1
    fi
    
    # 检查参数
    if [ $# -eq 0 ]; then
        show_help
        exit 0
    fi
    
    # 根据参数执行相应操作
    case "$1" in
        enter|e)
            enter_container
            ;;
        delete|del|d|rm)
            delete_container
            ;;
        status|s)
            show_status
            ;;
        list|ls|l)
            list_recent
            ;;
        help|h|-h|--help)
            show_help
            ;;
        *)
            print_error "未知命令: $1"
            printf "\n"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"