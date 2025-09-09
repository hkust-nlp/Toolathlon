#!/bin/bash

# Script for running a single task in a containerized environment
# Usage: ./run_single_containerized.sh <task_dir> <log_path>

set -e

task_dir_arg=$1 # domain/taskname
tag=${2:-"testrun"}
modelname=${3:-"testmodel"}
provider=${4:-"testprovider"}
maxstep=${5:-"testmaxstep"}
eval_config=${6:-"scripts/foraml_run_v0.json"}
dump_path=${7:-"./dumps"}

taskdomain=${task_dir_arg%/*}
taskname=${task_dir_arg#*/}

# Updated log paths to use dump_path
container_log_path="${dump_path}/${taskdomain}/${taskname}/container.log"
run_log_path="${dump_path}/${taskdomain}/${taskname}/run.log"
output_folder="${dump_path}/${taskdomain}/${taskname}"


if [ -z "$task_dir_arg" ] || [ -z "$tag" ] || [ -z "$modelname" ]; then
    echo "Usage: $0 <task_dir> <tag> <modelname>"
    echo "Example: $0 debug/debug-task testrun testmodel"
    exit 1
fi

# Get project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "Project root: $PROJECT_ROOT"
echo "Task directory: $task_dir_arg"
echo "Tag: $tag"
echo "Modelname: $modelname"
echo "Container log: $container_log_path"
echo "Run log: $run_log_path"
echo "Output folder: $output_folder"
echo "Dump path: $dump_path"

# Read container runtime configuration
CONTAINER_RUNTIME=$(uv run python -c "
import sys
sys.path.append('$PROJECT_ROOT/configs')
try:
    from global_configs import global_configs
    runtime = global_configs.get('podman_or_docker', 'podman')
    print(runtime)
except Exception as e:
    print('podman')
" 2>/dev/null)

echo "Using container runtime: $CONTAINER_RUNTIME"

# Image name
IMAGE_NAME="lockon0927/mcpbench-task-image-v2:latest"

# Generate unique container name
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
SAFE_TASK_NAME=$(echo "$task_dir_arg" | sed 's|/|-|g')
CONTAINER_NAME="mcpbench-${SAFE_TASK_NAME}-${TIMESTAMP}"

echo "Container name: $CONTAINER_NAME"


# Cleanup function
cleanup() {
    echo ""
    echo "Performing cleanup..."
    # Stop and clean up container
    if $CONTAINER_RUNTIME ps -aq --filter "name=$CONTAINER_NAME" 2>/dev/null | grep -q .; then
        echo "  Stopping and removing container: $CONTAINER_NAME"
        $CONTAINER_RUNTIME stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
        $CONTAINER_RUNTIME rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
        echo "  ✓ Container stopped and removed"
    fi
    echo "Cleanup completed"
}
trap cleanup EXIT

# Verify task directory exists
TASK_SOURCE="$PROJECT_ROOT/tasks/$task_dir_arg"
if [ ! -d "$TASK_SOURCE" ]; then
    echo "Error: Task directory does not exist: $TASK_SOURCE"
    exit 1
fi

# Prepare list of files to copy to container
echo "Preparing project files..."

# List of files and directories to copy
FILES_TO_COPY=(
    "configs"
    # "deployment/k8s"
    "scripts"
    "deployment/canvas/logs"
    "global_preparation/check_installation.py"
    "local_binary/github-mcp-server"
    "utils"
    "demo.py"
)

# Verify all required files/directories exist
echo "  Verifying file existence..."
for item in "${FILES_TO_COPY[@]}"; do
    if [ ! -e "$PROJECT_ROOT/$item" ]; then
        echo "  Warning: $item does not exist, skipping"
    else
        echo "  ✓ $item exists"
    fi
done

# Verify task directory existence
echo "  ✓ Task directory: tasks/$task_dir_arg"

# Ensure log directories exist
CONTAINER_LOG_DIR=$(dirname "$container_log_path")
RUN_LOG_DIR=$(dirname "$run_log_path")
mkdir -p "$CONTAINER_LOG_DIR"
mkdir -p "$RUN_LOG_DIR"
CONTAINER_LOG_PATH_ABS=$(readlink -f "$container_log_path")
RUN_LOG_FILE_NAME=$(basename "$run_log_path")

# Ensure output folder exists
mkdir -p "$output_folder"

echo "Preparing to start container..."

# Step 1: Start container and keep it running
echo "Step 1: Starting container and keeping it running..."

# Container startup parameters (don't execute commands, just start and keep running)
START_CONTAINER_ARGS=(
    "$CONTAINER_RUNTIME" "run"
    "-d"  # 后台运行
    "--name" "$CONTAINER_NAME"
    # Use host network to allow container access to Kind cluster on host
    "--network" "host"
)

# Add socket mount based on container runtime
if [ "$CONTAINER_RUNTIME" = "podman" ]; then
    echo "Configuring Podman environment..."
    # Podman socket mount, allowing kind in container to create clusters on host
    PODMAN_SOCKET_FOUND=false
    
    # 1. Check system-level podman socket
    if [ -S "/run/podman/podman.sock" ]; then
        START_CONTAINER_ARGS+=(
            "-v" "/run/podman/podman.sock:/run/podman/podman.sock"
        )
        echo "Using system-level podman socket: /run/podman/podman.sock"
        PODMAN_SOCKET_FOUND=true
    # 2. Check user-level podman socket
    elif [ -S "/run/user/$(id -u)/podman/podman.sock" ]; then
        START_CONTAINER_ARGS+=(
            "-v" "/run/user/$(id -u)/podman/podman.sock:/run/podman/podman.sock"
        )
        echo "Using user-level podman socket: /run/user/$(id -u)/podman/podman.sock"
        PODMAN_SOCKET_FOUND=true
    fi
    
    if [ "$PODMAN_SOCKET_FOUND" = false ]; then
        echo "Warning: Podman socket not found, Kind may not work"
        echo "Tip: Please manually run 'systemctl --user start podman.socket' or 'sudo systemctl start podman.socket'"
    fi
    # # Set environment variable for Kind to use Podman
    START_CONTAINER_ARGS+=(
        "-e" "KIND_EXPERIMENTAL_PROVIDER=podman"
    )
elif [ "$CONTAINER_RUNTIME" = "docker" ]; then
    echo "Configuring Docker environment..."
    # Docker socket mount
    START_CONTAINER_ARGS+=(
        "-v" "/var/run/docker.sock:/var/run/docker.sock"
    )
fi

# Add mounts
START_CONTAINER_ARGS+=(    
    # Mount results directory (read-write)
    
    # Mount the specific task output folder to /workspace/dumps
    "-v" "$PROJECT_ROOT/$output_folder:/workspace/dumps"
    
    # Mount log directory
    "-v" "$RUN_LOG_DIR:/workspace/logs"

    # Mount deployment/k8s directory
    "-v" "$PROJECT_ROOT/deployment/k8s:/workspace/deployment/k8s"
    
    # Working directory
    "-w" "/workspace"
    
    # Image
    "$IMAGE_NAME"
    
    # Command to keep container running
    "sleep" "infinity"
)

echo "Container start command: ${START_CONTAINER_ARGS[*]}"
echo ""

# exit 0

# Start container
echo "Starting container..."
CONTAINER_ID=$("${START_CONTAINER_ARGS[@]}")
START_EXIT_CODE=$?

if [ $START_EXIT_CODE -eq 0 ]; then
    echo "✓ Container started successfully"
    echo "  Container ID: $CONTAINER_ID"
    echo "  Container name: $CONTAINER_NAME"
else
    echo "✗ Container startup failed, exit code: $START_EXIT_CODE"
    exit $START_EXIT_CODE
fi

# Step 2: Wait for container to be ready
echo ""
echo "Step 2: Waiting for container to be ready..."

# Check container status
MAX_WAIT=30
WAIT_COUNT=0
CONTAINER_READY=false

while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    # Check if container is still running
    if $CONTAINER_RUNTIME ps -q --filter "name=$CONTAINER_NAME" | grep -q .; then
        # Try to execute simple command in container to verify ready state
        if $CONTAINER_RUNTIME exec "$CONTAINER_NAME" echo "container ready" >/dev/null 2>&1; then
            CONTAINER_READY=true
            break
        fi
    else
        echo "✗ Container unexpectedly stopped"
        exit 1
    fi
    
    echo "  Waiting for container to be ready... (${WAIT_COUNT}/${MAX_WAIT})"
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
done

if [ "$CONTAINER_READY" = true ]; then
    echo "✓ Container is ready"
else
    echo "✗ Container not ready within ${MAX_WAIT} seconds, timeout exit"
    exit 1
fi

# Step 2.5: Copy project files to container's /workspace
echo ""
echo "Step 2.5: Copying project files to container..."

# First create necessary directory structure in container
echo "  Creating directory structure..."
$CONTAINER_RUNTIME exec "$CONTAINER_NAME" mkdir -p "/workspace/deployment"
$CONTAINER_RUNTIME exec "$CONTAINER_NAME" mkdir -p "/workspace/deployment/canvas"
$CONTAINER_RUNTIME exec "$CONTAINER_NAME" mkdir -p "/workspace/global_preparation"
$CONTAINER_RUNTIME exec "$CONTAINER_NAME" mkdir -p "/workspace/tasks"

# Copy basic files and directories to container
for item in "${FILES_TO_COPY[@]}"; do
    if [ -e "$PROJECT_ROOT/$item" ]; then
        echo "  Copying $item to container..."
        if [ -d "$PROJECT_ROOT/$item" ]; then
            # If it's a directory, ensure target parent directory exists
            parent_dir=$(dirname "$item")
            if [ "$parent_dir" != "." ]; then
                $CONTAINER_RUNTIME exec "$CONTAINER_NAME" mkdir -p "/workspace/$parent_dir"
            fi
        fi
        $CONTAINER_RUNTIME cp "$PROJECT_ROOT/$item" "$CONTAINER_NAME:/workspace/$item"
    fi
done

# Copy task directory
echo "  Copying task directory tasks/$task_dir_arg to container..."
# Ensure target directory structure exists
TARGET_PARENT_DIR=$(dirname "$task_dir_arg")
if [ "$TARGET_PARENT_DIR" != "." ]; then
    $CONTAINER_RUNTIME exec "$CONTAINER_NAME" mkdir -p "/workspace/tasks/$TARGET_PARENT_DIR"
fi
# Copy specific task directory, maintaining complete directory structure
$CONTAINER_RUNTIME cp "$TASK_SOURCE" "$CONTAINER_NAME:/workspace/tasks/$TARGET_PARENT_DIR/"

echo "✓ File copying completed" 

# Run the above command again
echo ""
echo "Step 2.6: Executing necessary configurations..."
echo " Executing necessary configurations"
$CONTAINER_RUNTIME exec "$CONTAINER_NAME" bash -c "mkdir -p ~/.gmail-mcp && mkdir -p ~/.calendar-mcp && cp ./configs/gcp-oauth.keys.json ~/.calendar-mcp/ && cp ./configs/gcp-oauth.keys.json ~/.gmail-mcp/ && cp ./configs/google_credentials.json  ~/.calendar-mcp/credentials.json && cp ./configs/google_credentials.json  ~/.gmail-mcp/credentials.json"


# Add after step 2.7
echo ""
echo "Step 2.7: Verifying Kind environment..."

# Check kind command
if $CONTAINER_RUNTIME exec "$CONTAINER_NAME" which kind >/dev/null 2>&1; then
    echo "✓ Kind is installed"
    $CONTAINER_RUNTIME exec "$CONTAINER_NAME" kind version
else
    echo "✗ Kind not installed, installing..."
    $CONTAINER_RUNTIME exec "$CONTAINER_NAME" bash -c "
        curl -Lo /tmp/kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64 &&
        chmod +x /tmp/kind &&
        mv /tmp/kind /usr/local/bin/kind
    "
fi


# Test Kind functionality
echo "Testing Kind connection..."
if $CONTAINER_RUNTIME exec "$CONTAINER_NAME" $CONTAINER_RUNTIME version >/dev/null 2>&1; then
    echo "✓ $CONTAINER_RUNTIME API accessible"
else
    echo "✗ Cannot access $CONTAINER_RUNTIME API"
    exit 1
fi


# Step 3: Execute task command in container
echo ""
echo "Step 3: Executing task command in container..."

# Command to execute in container
CONTAINER_CMD="uv run demo.py --eval_config $eval_config --task_dir $task_dir_arg --max_steps_under_single_turn_mode $maxstep --model_short_name $modelname --provider $provider --debug > /workspace/logs/$RUN_LOG_FILE_NAME 2>&1"

echo "Executing command: $CONTAINER_CMD"
echo ""

# exit 0

# Execute command in container (let run_parallel.py handle container log)
echo "Executing task..."
$CONTAINER_RUNTIME exec "$CONTAINER_NAME" bash -c "$CONTAINER_CMD"
EXEC_EXIT_CODE=$?

echo ""
if [ $EXEC_EXIT_CODE -eq 0 ]; then
    echo "✓ Task executed successfully, exit code: $EXEC_EXIT_CODE"
else
    echo "✗ Task execution failed, exit code: $EXEC_EXIT_CODE"
fi

EXIT_CODE=$EXEC_EXIT_CODE

# Copy run log from container to host
echo "Copying run log from container..."
$CONTAINER_RUNTIME cp "$CONTAINER_NAME:/workspace/logs/$RUN_LOG_FILE_NAME" "$run_log_path" 2>/dev/null || echo "Warning: Could not copy run log from container"

# Display log summary
if [ -f "$container_log_path" ]; then
    echo ""
    echo "=== Container execution log (last 20 lines) ==="
    tail -20 "$container_log_path"
    echo ""
    echo "=== Container log path: $container_log_path ==="
fi

if [ -f "$run_log_path" ]; then
    echo ""
    echo "=== Task run log (last 20 lines) ==="
    tail -20 "$run_log_path"
    echo ""
    echo "=== Run log path: $run_log_path ==="
fi

# Check if kubeconfig was generated
echo ""
echo "=== Checking generated Kubeconfig files in container ==="
$CONTAINER_RUNTIME exec "$CONTAINER_NAME" bash -c "ls -la /workspace/deployment/k8s/configs/*.yaml 2>/dev/null || echo 'None'"

exit $EXIT_CODE