#!/bin/bash

set -e

# Prepare list of files to copy to container
echo "Preparing project files..."

image_name=${1:-"lockon0927/toolathlon-task-image:1016beta"}
runmode=${2:-"normal"}

IMAGE_NAME="$image_name"

# Get project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Generate unique container name
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
SAFE_TASK_NAME="check-installation"
CONTAINER_NAME="toolathlon-${SAFE_TASK_NAME}-${TIMESTAMP}"

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

# Add mounts
START_CONTAINER_ARGS+=(
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

# Step 3: Check installation in container
echo ""
echo "Step 3: Checking installation in container..."

# When running commands in the container, these env variables are already present due to -e at startup.

CONTAINER_CMD="uv run -m global_preparation.check_installation"

echo "Executing command in container: $CONTAINER_CMD"
echo ""

# Actually run the task inside the container
echo "Checking installation..."
$CONTAINER_RUNTIME exec -it "$CONTAINER_NAME" bash -c "$CONTAINER_CMD"
EXEC_EXIT_CODE=$?

echo ""
if [ $EXEC_EXIT_CODE -eq 0 ]; then
    echo "✓ Installation checked successfully, exit code: $EXEC_EXIT_CODE"
else
    echo "✗ Installation check failed, exit code: $EXEC_EXIT_CODE"
fi

EXIT_CODE=$EXEC_EXIT_CODE

exit $EXIT_CODE