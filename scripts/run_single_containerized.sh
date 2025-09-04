#!/bin/bash

# 容器化运行单个任务的脚本
# 用法: ./run_single_containerized.sh <task_dir> <log_path>

set -e

task_dir_arg=$1
log_path=$2

if [ -z "$task_dir_arg" ] || [ -z "$log_path" ]; then
    echo "用法: $0 <task_dir> <log_path>"
    echo "示例: $0 debug/debug-task /tmp/test.log"
    exit 1
fi

# 获取项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "项目根目录: $PROJECT_ROOT"
echo "任务目录: $task_dir_arg"
echo "日志路径: $log_path"

# 读取容器运行时配置
CONTAINER_RUNTIME=$(python3 -c "
import sys
sys.path.append('$PROJECT_ROOT/configs')
try:
    from global_configs import global_configs
    runtime = global_configs.get('podman_or_docker', 'podman')
    print(runtime)
except Exception as e:
    print('podman')
" 2>/dev/null)

echo "使用容器运行时: $CONTAINER_RUNTIME"

# 镜像名称
IMAGE_NAME="lockon0927/mcpbench-basic-image:latest"

# 生成唯一容器名
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
SAFE_TASK_NAME=$(echo "$task_dir_arg" | sed 's|/|-|g')
CONTAINER_NAME="mcpbench-${SAFE_TASK_NAME}-${TIMESTAMP}"

echo "容器名称: $CONTAINER_NAME"



# 清理函数
cleanup() {
    echo ""
    echo "执行清理操作..."
    # 停止并清理容器
    if $CONTAINER_RUNTIME ps -aq --filter "name=$CONTAINER_NAME" 2>/dev/null | grep -q .; then
        echo "  停止并清除容器: $CONTAINER_NAME"
        $CONTAINER_RUNTIME stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
        $CONTAINER_RUNTIME rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
        echo "  ✓ 容器已停止并清除"
    fi
    echo "清理完成"
}
# trap cleanup EXIT

# 验证任务目录存在
TASK_SOURCE="$PROJECT_ROOT/tasks/$task_dir_arg"
if [ ! -d "$TASK_SOURCE" ]; then
    echo "错误: 任务目录不存在: $TASK_SOURCE"
    exit 1
fi

# 准备需要复制到容器的文件列表
echo "准备项目文件..."

# 需要复制的文件和目录列表
FILES_TO_COPY=(
    "configs"
    "deployment/k8s"
    "deployment/canvas/logs"
    "global_preparation/check_installation.py"
    "local_binary/github-mcp-server"
    "utils"
    "demo.py"
)

# 验证所有需要的文件/目录是否存在
echo "  验证文件存在性..."
for item in "${FILES_TO_COPY[@]}"; do
    if [ ! -e "$PROJECT_ROOT/$item" ]; then
        echo "  警告: $item 不存在，跳过"
    else
        echo "  ✓ $item 存在"
    fi
done

# 验证任务目录存在性
echo "  ✓ 任务目录: tasks/$task_dir_arg"

# 确保日志目录存在
LOG_DIR=$(dirname "$log_path")
mkdir -p "$LOG_DIR"
LOG_PATH_ABS=$(readlink -f "$log_path")
LOG_FILE_NAME=$(basename "$log_path")

echo "准备启动容器..."

# 第一步：启动容器并保持运行
echo "第一步：启动容器并保持运行..."

# 启动容器参数（不执行命令，只启动并保持运行）
START_CONTAINER_ARGS=(
    "$CONTAINER_RUNTIME" "run"
    "-d"  # 后台运行
    "--name" "$CONTAINER_NAME"
    # 使用host网络，让容器能访问宿主机上的Kind集群
    "--network" "host"
)

# 根据容器运行时添加socket挂载
if [ "$CONTAINER_RUNTIME" = "podman" ]; then
    echo "配置Podman环境..."
    # Podman socket挂载，让容器内的kind能在宿主机创建集群
    if [ -S "/run/podman/podman.sock" ]; then
        START_CONTAINER_ARGS+=(
            "-v" "/run/podman/podman.sock:/var/run/docker.sock"
        )
    elif [ -S "/run/user/$(id -u)/podman/podman.sock" ]; then
        # 用户级podman socket
        START_CONTAINER_ARGS+=(
            "-v" "/run/user/$(id -u)/podman/podman.sock:/var/run/docker.sock"
        )
    else
        echo "警告: 未找到Podman socket，Kind可能无法工作"
    fi
    # 设置环境变量让Kind使用Podman
    START_CONTAINER_ARGS+=(
        "-e" "KIND_EXPERIMENTAL_PROVIDER=podman"
    )
elif [ "$CONTAINER_RUNTIME" = "docker" ]; then
    echo "配置Docker环境..."
    # Docker socket挂载
    START_CONTAINER_ARGS+=(
        "-v" "/var/run/docker.sock:/var/run/docker.sock"
    )
fi

# 添加挂载
START_CONTAINER_ARGS+=(    
    # 挂载结果目录（读写）
    "-v" "$PROJECT_ROOT/dumps:/workspace/dumps"
    
    # 挂载日志目录
    "-v" "$LOG_DIR:/workspace/logs"
    
    # 工作目录
    "-w" "/workspace"
    
    # 镜像
    "$IMAGE_NAME"
    
    # 保持容器运行的命令
    "sleep" "infinity"
)

echo "启动容器命令: ${START_CONTAINER_ARGS[*]}"
echo ""

# exit 0

# 启动容器
echo "正在启动容器..."
CONTAINER_ID=$("${START_CONTAINER_ARGS[@]}")
START_EXIT_CODE=$?

if [ $START_EXIT_CODE -eq 0 ]; then
    echo "✓ 容器启动成功"
    echo "  容器ID: $CONTAINER_ID"
    echo "  容器名称: $CONTAINER_NAME"
else
    echo "✗ 容器启动失败，退出码: $START_EXIT_CODE"
    exit $START_EXIT_CODE
fi

# 第二步：等待容器就绪
echo ""
echo "第二步：等待容器就绪..."

# 检查容器状态
MAX_WAIT=30
WAIT_COUNT=0
CONTAINER_READY=false

while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    # 检查容器是否仍在运行
    if $CONTAINER_RUNTIME ps -q --filter "name=$CONTAINER_NAME" | grep -q .; then
        # 尝试在容器内执行简单命令来验证就绪状态
        if $CONTAINER_RUNTIME exec "$CONTAINER_NAME" echo "container ready" >/dev/null 2>&1; then
            CONTAINER_READY=true
            break
        fi
    else
        echo "✗ 容器意外停止"
        exit 1
    fi
    
    echo "  等待容器就绪... (${WAIT_COUNT}/${MAX_WAIT})"
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
done

if [ "$CONTAINER_READY" = true ]; then
    echo "✓ 容器已就绪"
else
    echo "✗ 容器在${MAX_WAIT}秒内未就绪，超时退出"
    exit 1
fi

# 第2.5步：复制项目文件到容器内的/workspace
echo ""
echo "第2.5步：复制项目文件到容器内..."

# 首先在容器内创建必要的目录结构
echo "  创建目录结构..."
$CONTAINER_RUNTIME exec "$CONTAINER_NAME" mkdir -p "/workspace/deployment/k8s"
$CONTAINER_RUNTIME exec "$CONTAINER_NAME" mkdir -p "/workspace/deployment/canvas"
$CONTAINER_RUNTIME exec "$CONTAINER_NAME" mkdir -p "/workspace/global_preparation"
$CONTAINER_RUNTIME exec "$CONTAINER_NAME" mkdir -p "/workspace/tasks"

# 复制基本文件和目录到容器
for item in "${FILES_TO_COPY[@]}"; do
    if [ -e "$PROJECT_ROOT/$item" ]; then
        echo "  复制 $item 到容器..."
        if [ -d "$PROJECT_ROOT/$item" ]; then
            # 如果是目录，确保目标父目录存在
            parent_dir=$(dirname "$item")
            if [ "$parent_dir" != "." ]; then
                $CONTAINER_RUNTIME exec "$CONTAINER_NAME" mkdir -p "/workspace/$parent_dir"
            fi
        fi
        $CONTAINER_RUNTIME cp "$PROJECT_ROOT/$item" "$CONTAINER_NAME:/workspace/$item"
    fi
done

# 复制任务目录
echo "  复制任务目录 tasks/$task_dir_arg 到容器..."
# 复制具体的任务目录
$CONTAINER_RUNTIME cp "$TASK_SOURCE" "$CONTAINER_NAME:/workspace/tasks/"

echo "✓ 文件复制完成" 

# 再运行一下上面的命令
$CONTAINER_RUNTIME exec "$CONTAINER_NAME" bash -c "mkdir -p ~/.gmail-mcp && mkdir -p ~/.calendar-mcp && cp ./configs/gcp-oauth.keys.json ~/.calendar-mcp/ && cp ./configs/gcp-oauth.keys.json ~/.gmail-mcp/ && cp ./configs/google_credentials.json  ~/.calendar-mcp/credentials.json && cp ./configs/google_credentials.json  ~/.gmail-mcp/credentials.json"


# 第三步：在容器内执行任务命令
echo ""
echo "第三步：在容器内执行任务命令..."

# 容器内执行的命令
CONTAINER_CMD="uv run demo.py --eval_config scripts/debug_eval_config.json --task_dir $task_dir_arg --debug > /workspace/logs/$LOG_FILE_NAME 2>&1"

echo "执行命令: $CONTAINER_CMD"
echo ""

exit 0

# 在容器内执行命令
echo "正在执行任务..."
$CONTAINER_RUNTIME exec "$CONTAINER_NAME" bash -c "$CONTAINER_CMD"
EXEC_EXIT_CODE=$?

echo ""
if [ $EXEC_EXIT_CODE -eq 0 ]; then
    echo "✓ 任务执行成功，退出码: $EXEC_EXIT_CODE"
else
    echo "✗ 任务执行失败，退出码: $EXEC_EXIT_CODE"
fi

EXIT_CODE=$EXEC_EXIT_CODE

# 显示日志摘要
if [ -f "$LOG_PATH_ABS" ]; then
    echo ""
    echo "=== 任务执行日志（最后20行）==="
    tail -20 "$LOG_PATH_ABS"
    echo ""
    echo "=== 完整日志路径: $LOG_PATH_ABS ==="
fi

# 检查是否有生成的kubeconfig
echo ""
echo "=== 检查容器内生成的Kubeconfig文件 ==="
$CONTAINER_RUNTIME exec "$CONTAINER_NAME" bash -c "ls -la /workspace/deployment/k8s/configs/*.yaml 2>/dev/null || echo '无'"

exit $EXIT_CODE