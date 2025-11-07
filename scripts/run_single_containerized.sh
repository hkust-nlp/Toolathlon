#!/bin/bash

# Script for running a single task in a containerized environment
# Usage: ./run_single_containerized.sh <task_dir> <runmode> <dump_path> <modelname> [provider] [maxstep] [eval_config] [image_name]

#### If you want to use the unified model provider, 
# but do not want to explicitly export these environment variables in your shell, 
# you can also uncomment these lines and set the values here
# ↓↓↓↓ uncomment these lines ↓↓↓↓
# TOOLATHLON_OPENAI_BASE_URL="your-custom-base-url"
# TOOLATHLON_OPENAI_API_KEY="your-custom-api-key"
# export TOOLATHLON_OPENAI_BASE_URL
# export TOOLATHLON_OPENAI_API_KEY

set -e

task_dir_arg=$1 # domain/taskname
runmode=${2:-"normal"}
dump_path=${3:-"./dumps_quick_start"}
modelname=${4:-"anthropic/claude-sonnet-4.5"}
provider=${5:-"unified"}
maxstep=${6:-"100"}
eval_config=${7:-"scripts/foraml_run_v0.json"}
image_name=${8:-"lockon0927/toolathlon-task-image:1016beta"}

taskdomain=${task_dir_arg%/*}
taskname=${task_dir_arg#*/}

# Set up log paths using dump_path
container_log_path="${dump_path}/${taskdomain}/${taskname}/container.log"
run_log_path="${dump_path}/${taskdomain}/${taskname}/run.log"
output_folder="${dump_path}/${taskdomain}/${taskname}"

if [ -z "$task_dir_arg" ] || [ -z "$runmode" ] || [ -z "$modelname" ]; then
    echo "Usage: $0 <task_dir> <runmode> <modelname>"
    echo "Example: $0 debug/debug-task testrun testmodel"
    exit 1
fi

# Get project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "Project root: $PROJECT_ROOT"
echo "Task directory: $task_dir_arg"
echo "Runmode: $runmode"
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

# Use the image name from parameter
IMAGE_NAME="$image_name"
echo "Using container image: $IMAGE_NAME"

# Generate unique container name
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
SAFE_TASK_NAME=$(echo "$task_dir_arg" | sed 's|/|-|g')
CONTAINER_NAME="toolathlon-${SAFE_TASK_NAME}-${TIMESTAMP}"

echo "Container name: $CONTAINER_NAME"

# --- BEGIN: Detect and propagate TOOLATHLON_OPENAI env vars from host to container ---
EXTRA_ENV_ARGS=()
if [ ! -z "${TOOLATHLON_OPENAI_BASE_URL+x}" ]; then
    EXTRA_ENV_ARGS+=("-e" "TOOLATHLON_OPENAI_BASE_URL=${TOOLATHLON_OPENAI_BASE_URL}")
    echo "Detected host TOOLATHLON_OPENAI_BASE_URL, will pass into container"
fi

if [ ! -z "${TOOLATHLON_OPENAI_API_KEY+x}" ]; then
    EXTRA_ENV_ARGS+=("-e" "TOOLATHLON_OPENAI_API_KEY=${TOOLATHLON_OPENAI_API_KEY}")
    echo "Detected host TOOLATHLON_OPENAI_API_KEY, will pass into container"
fi
# --- END: Detect and propagate TOOLATHLON_OPENAI env vars ---

# Cleanup function
cleanup() {
    echo ""
    echo "Performing cleanup..."
    # Stop and remove container if exists
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
    "deployment/k8s"
    "scripts"
    "deployment/canvas/logs"
    "global_preparation/check_installation.py"
    "local_binary/github-mcp-server"
    "utils"
    "main.py"
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

# Confirm existence of task directory
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

# Container startup parameters (only start and keep alive, do not execute task yet)
START_CONTAINER_ARGS=(
    "$CONTAINER_RUNTIME" "run"
    "-d"  # Run in background
    "--name" "$CONTAINER_NAME"
    "--network" "host" # Use host network for Kind cluster access
)

# Add environment variables for TOOLATHLON_OPENAI from host
for envarg in "${EXTRA_ENV_ARGS[@]}"; do
    START_CONTAINER_ARGS+=("$envarg")
done

# Add socket mount based on container runtime
if [ "$CONTAINER_RUNTIME" = "podman" ]; then
    echo "Configuring Podman environment..."
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
    # Set env variable for Kind to use Podman
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

# if output_folder is not a absolute path, make it absolute
# if [ ! -d "$output_folder" ]; then
# fi

# make output_folder absolute
output_folder=$(realpath "$output_folder")
# make RUN_LOG_DIR absolute
RUN_LOG_DIR=$(realpath "$RUN_LOG_DIR")

# Add mounts
START_CONTAINER_ARGS+=(
    # Mount output folder as /workspace/dumps
    "-v" "$output_folder:/workspace/dumps"
    # Mount log directory
    "-v" "$RUN_LOG_DIR:/workspace/logs"
    # Set working directory
    "-w" "/workspace"
    # Set image
    "$IMAGE_NAME"
    # Keep the container alive for later exec
    "sleep" "3600"
)

echo "Container start command: ${START_CONTAINER_ARGS[*]}"
echo ""

# Start the container
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

MAX_WAIT=30
WAIT_COUNT=0
CONTAINER_READY=false

while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    # Check if container is still running
    if $CONTAINER_RUNTIME ps -q --filter "name=$CONTAINER_NAME" | grep -q .; then
        # Verify basic exec in container
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

# Create directory structure inside the container, if needed
echo "  Creating directory structure in container..."
$CONTAINER_RUNTIME exec "$CONTAINER_NAME" mkdir -p "/workspace/deployment"
$CONTAINER_RUNTIME exec "$CONTAINER_NAME" mkdir -p "/workspace/deployment/canvas"
$CONTAINER_RUNTIME exec "$CONTAINER_NAME" mkdir -p "/workspace/global_preparation"
$CONTAINER_RUNTIME exec "$CONTAINER_NAME" mkdir -p "/workspace/tasks"

# Copy basic files and directories to container
for item in "${FILES_TO_COPY[@]}"; do
    if [ -e "$PROJECT_ROOT/$item" ]; then
        echo "  Copying $item to container..."
        if [ -d "$PROJECT_ROOT/$item" ]; then
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
TARGET_PARENT_DIR=$(dirname "$task_dir_arg")
if [ "$TARGET_PARENT_DIR" != "." ]; then
    $CONTAINER_RUNTIME exec "$CONTAINER_NAME" mkdir -p "/workspace/tasks/$TARGET_PARENT_DIR"
fi
# Copy actual task directory
$CONTAINER_RUNTIME cp "$TASK_SOURCE" "$CONTAINER_NAME:/workspace/tasks/$TARGET_PARENT_DIR/"

echo "✓ File copying completed"

# Run the necessary configuration commands in the container
echo ""
echo "Step 2.6: Executing necessary configurations..."
echo " Executing necessary configurations"
copy_config_cmd='
  for dir in ~/.gmail-mcp ~/.calendar-mcp; do
    mkdir -p $dir
    cp ./configs/gcp-oauth.keys.json $dir/
    cp ./configs/google_credentials.json $dir/credentials.json
  done
'
if [ "$runmode" = "quickstart" ]; then
    $CONTAINER_RUNTIME exec "$CONTAINER_NAME" bash -c "$copy_config_cmd" || echo "Warning: Failed to copy config files, but continuing due to quickstart mode"
else
    $CONTAINER_RUNTIME exec "$CONTAINER_NAME" bash -c "$copy_config_cmd"
fi

# Copy MCP auth directory if it exists
if [ -d "$HOME/.mcp-auth" ]; then
    echo " Copying MCP authentication data to container..."
    $CONTAINER_RUNTIME exec "$CONTAINER_NAME" mkdir -p /root/.mcp-auth
    $CONTAINER_RUNTIME cp "$HOME/.mcp-auth/." "$CONTAINER_NAME:/root/.mcp-auth/"
    echo "✓ MCP auth data copied"
else
    echo " Warning: $HOME/.mcp-auth not found, skipping MCP auth copy"
fi

# Step 2.7: Verify Kind environment
echo ""
echo "Step 2.7: Verifying Kind environment..."

if $CONTAINER_RUNTIME exec "$CONTAINER_NAME" which kind >/dev/null 2>&1; then
    echo "✓ Kind is installed"
    $CONTAINER_RUNTIME exec "$CONTAINER_NAME" kind version
else
    echo "✗ Kind is not installed, installing..."
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

# When running commands in the container, these env variables are already present due to -e at startup.

CONTAINER_CMD="uv run main.py --eval_config $eval_config --task_dir $task_dir_arg --max_steps_under_single_turn_mode $maxstep --model_short_name $modelname --provider $provider --debug > /workspace/logs/$RUN_LOG_FILE_NAME 2>&1"
CONTAINER_CMD_DISPLAY_INPLACE="uv run main.py --eval_config $eval_config --task_dir $task_dir_arg --max_steps_under_single_turn_mode $maxstep --model_short_name $modelname --provider $provider --debug"

# if quickstart mode, use the display inplace command
if [ "$runmode" = "quickstart" ]; then
    CONTAINER_CMD="$CONTAINER_CMD_DISPLAY_INPLACE"
else
    CONTAINER_CMD="$CONTAINER_CMD"
fi


echo "Executing command in container: $CONTAINER_CMD"
echo ""

# Actually run the task inside the container
echo "Executing task, please wait for a while ..."
if [ "$runmode" = "quickstart" ]; then
    $CONTAINER_RUNTIME exec -t "$CONTAINER_NAME" bash -c "$CONTAINER_CMD"
else
    $CONTAINER_RUNTIME exec "$CONTAINER_NAME" bash -c "$CONTAINER_CMD"
fi
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

# Display last lines of container and run logs if present
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