#!/bin/bash

# Script for running a single task in decoupled mode:
# preprocess + gateway in container, agent loop on host, eval in container.
# Usage:
#   ./run_single_decoupled.sh <task_dir> <runmode> <dump_path> <modelname> \
#     [provider] [maxstep] [eval_config] [image_name] [agent_framework] [gateway_port]
#
# Supported agent frameworks:
#   - toolathlon_default
#   - claude_agent_sdk
#
# Legacy compatibility:
#   This script also accepts the old positional layout:
#   [gateway_port] [host_loop_backend] [tool_call_mode]

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
eval_config=${7:-"scripts/formal_run_v0.json"}
image_name=${8:-"lockon0927/toolathlon-task-image:1016beta"}
arg9=${9:-""}
arg10=${10:-""}
arg11=${11:-""}
parent_captures_run_log=${TOOLATHLON_PARENT_CAPTURES_RUN_LOG:-"0"}

agent_framework="${TOOLATHLON_AGENT_FRAMEWORK:-toolathlon_default}"
gateway_port=""
host_loop_backend=""
tool_call_mode="parallel"

resolve_agent_framework() {
    case "$1" in
        toolathlon_default|default|openai|openai_agents)
            echo "toolathlon_default"
            ;;
        claude_agent_sdk|claude_sdk|claude)
            echo "claude_agent_sdk"
            ;;
        *)
            return 1
            ;;
    esac
}

resolve_host_loop_backend() {
    case "$1" in
        toolathlon_default)
            echo "openai"
            ;;
        claude_agent_sdk)
            echo "claude_sdk"
            ;;
        *)
            return 1
            ;;
    esac
}

if resolved_framework=$(resolve_agent_framework "$arg9"); then
    agent_framework="$resolved_framework"
    gateway_port="$arg10"
elif [ -z "$arg9" ]; then
    gateway_port="$arg10"
else
    # Legacy positional layout:
    #   [gateway_port] [host_loop_backend] [tool_call_mode]
    gateway_port="$arg9"
    host_loop_backend="${arg10:-openai}"
    tool_call_mode="${arg11:-parallel}"
    case "$host_loop_backend" in
        openai|openai_agents)
            agent_framework="toolathlon_default"
            host_loop_backend="openai"
            ;;
        claude|claude_sdk|claude_agent_sdk)
            agent_framework="claude_agent_sdk"
            host_loop_backend="claude_sdk"
            ;;
        *)
            echo "Unsupported legacy host_loop_backend: $host_loop_backend"
            echo "Supported values: openai, claude_sdk"
            exit 1
            ;;
    esac
fi

if [ -z "$host_loop_backend" ]; then
    host_loop_backend=$(resolve_host_loop_backend "$agent_framework") || {
        echo "Unsupported agent_framework: $agent_framework"
        echo "Supported values: toolathlon_default, claude_agent_sdk"
        exit 1
    }
fi

if [ -z "$task_dir_arg" ] || [ -z "$runmode" ] || [ -z "$modelname" ]; then
    echo "Usage: $0 <task_dir> <runmode> <dump_path> <modelname> [provider] [maxstep] [eval_config] [image_name] [agent_framework] [gateway_port]"
    echo "Example: $0 finalpool/find-alita-paper quickstart /tmp/dumps anthropic/claude-sonnet-4.5 unified 100 scripts/formal_run_v0.json lockon0927/toolathlon-task-image:1016beta toolathlon_default"
    exit 1
fi

taskdomain=${task_dir_arg%/*}
taskname=${task_dir_arg#*/}

if [[ ! "$task_dir_arg" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]] || \
   [ "$taskdomain" = "." ] || [ "$taskdomain" = ".." ] || \
   [ "$taskname" = "." ] || [ "$taskname" = ".." ]; then
    echo "Error: task_dir must be a safe domain/task_name path: $task_dir_arg" >&2
    exit 1
fi

CONTAINER_TASK_PATH="/workspace/tasks/$task_dir_arg"

# Set up log paths using dump_path
container_log_path="${dump_path}/${taskdomain}/${taskname}/container.log"
run_log_path="${dump_path}/${taskdomain}/${taskname}/run.log"
host_loop_log_path="${dump_path}/${taskdomain}/${taskname}/host_loop.log"
preprocess_log_path="${dump_path}/${taskdomain}/${taskname}/preprocess.log"
gateway_log_path="${dump_path}/${taskdomain}/${taskname}/gateway.log"
eval_log_path="${dump_path}/${taskdomain}/${taskname}/eval.log"
output_folder="${dump_path}/${taskdomain}/${taskname}"

# Get project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "Project root: $PROJECT_ROOT"
echo "Task directory: $task_dir_arg"
echo "Runmode: $runmode"
echo "Modelname: $modelname"
echo "Agent framework: $agent_framework"
echo "Host loop backend: $host_loop_backend"
echo "Tool call mode: $tool_call_mode"
echo "Container log: $container_log_path"
echo "Run log: $run_log_path"
echo "Output folder: $output_folder"
echo "Dump path: $dump_path"

if [ "$host_loop_backend" = "claude_sdk" ]; then
    echo "Claude tool call mode: parallel"
    echo "Claude permission mode: default"
    if [ -n "${TOOLATHLON_MAX_TURNS_PER_TASK:-}" ]; then
        echo "Task max turns override: ${TOOLATHLON_MAX_TURNS_PER_TASK}"
    fi
fi

if [ -z "$gateway_port" ]; then
    gateway_port=$(uv run python -c "import socket; s=socket.socket(); s.bind(('127.0.0.1', 0)); print(s.getsockname()[1]); s.close()")
fi
if [[ ! "$gateway_port" =~ ^[0-9]+$ ]] || \
   [ "$gateway_port" -lt 1 ] || [ "$gateway_port" -gt 65535 ]; then
    echo "Error: gateway_port must be an integer between 1 and 65535: $gateway_port" >&2
    exit 1
fi
echo "Gateway port: $gateway_port"

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

# Read instance_prefix from ports_config.yaml
INSTANCE_PREFIX=$(uv run python -c "
import sys
import yaml
from pathlib import Path
try:
    ports_config_path = Path('$PROJECT_ROOT/configs/ports_config.yaml')
    if ports_config_path.exists():
        with open(ports_config_path, 'r') as f:
            config = yaml.safe_load(f)
            prefix = config.get('instance_prefix', '')
            print(prefix if prefix else '')
    else:
        print('')
except Exception:
    print('')
" 2>/dev/null)

if [ -z "$INSTANCE_PREFIX" ]; then
    echo "Using default container prefix (no instance prefix)"
else
    echo "Using instance prefix: $INSTANCE_PREFIX"
fi

# Use the image name from parameter
IMAGE_NAME="$image_name"
echo "Using container image: $IMAGE_NAME"

# Generate unique container name with instance prefix
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
SAFE_TASK_NAME=$(echo "$task_dir_arg" | sed 's|/|-|g')
CONTAINER_NAME="${INSTANCE_PREFIX}toolathlon-${SAFE_TASK_NAME}-${TIMESTAMP}"

echo "Container name: $CONTAINER_NAME"

EXTRA_ENV_ARGS=()
USE_UNIFIED_MODEL_ENV=true
case "$host_loop_backend" in
    claude|claude_sdk|claude_agent_sdk)
        USE_UNIFIED_MODEL_ENV=false
        ;;
esac

if [ "$USE_UNIFIED_MODEL_ENV" = true ]; then
    if [ ! -z "${TOOLATHLON_OPENAI_BASE_URL+x}" ]; then
        EXTRA_ENV_ARGS+=("-e" "TOOLATHLON_OPENAI_BASE_URL")
        echo "Detected host TOOLATHLON_OPENAI_BASE_URL, will pass into container"
    fi

    if [ ! -z "${TOOLATHLON_OPENAI_API_KEY+x}" ]; then
        EXTRA_ENV_ARGS+=("-e" "TOOLATHLON_OPENAI_API_KEY")
        echo "Detected host TOOLATHLON_OPENAI_API_KEY, will pass into container"
    fi
else
    echo "Skipping TOOLATHLON_OPENAI_* passthrough for Claude SDK host loop"
fi

# Detect TOOLATHLON_MODEL_PARAMS_FILE - will copy file and set container path later
HOST_MODEL_PARAMS_FILE=""
CONTAINER_MODEL_PARAMS_FILE=""
if [ ! -z "${TOOLATHLON_MODEL_PARAMS_FILE+x}" ] && [ -f "${TOOLATHLON_MODEL_PARAMS_FILE}" ]; then
    HOST_MODEL_PARAMS_FILE="${TOOLATHLON_MODEL_PARAMS_FILE}"
    # Container path will be /workspace/model_params.json
    CONTAINER_MODEL_PARAMS_FILE="/workspace/model_params.json"
    echo "Detected host TOOLATHLON_MODEL_PARAMS_FILE: ${HOST_MODEL_PARAMS_FILE}"
    echo "Will copy to container as: ${CONTAINER_MODEL_PARAMS_FILE}"
fi

# Private host-side state for evaluator artifacts and the resolved task
# bundle.  None of these paths are bind-mounted into the task container.
ARTIFACT_STASH_DIR=""
TRUSTED_STASH_DIR=""
TRUSTED_BUNDLE_FILE=""
HOST_AGENT_BUNDLE_FILE=""
CURRENT_CONTAINER_BUNDLE=""

# Ownership-restoration state for the bind-mounted output tree.  DUMPS_OWNER
# is captured right before preprocess runs as container root, and
# DUMPS_RESTORE_PENDING stays 1 until the tree has been handed back, so
# cleanup() can finish a restoration the main flow never reached (preprocess
# failure, SIGINT/SIGTERM).  On the interrupted path cleanup() must quiesce
# the container before restoring: the exec'd preprocess can outlive its
# local client and keep writing (see the pending block in cleanup()).
DUMPS_OWNER=""
DUMPS_RESTORE_PENDING=0

restore_dumps_ownership() {
    $CONTAINER_RUNTIME exec "$CONTAINER_NAME" \
        chown -R -- "$DUMPS_OWNER" /workspace/dumps || return 1
    DUMPS_RESTORE_PENDING=0
}

# Cleanup function
cleanup() {
    cleanup_exit_code=$?
    trap - EXIT
    set +e
    echo ""
    echo "Performing cleanup..."

    # Finish any pending ownership restoration.  Killing the local exec
    # CLIENT (Ctrl-C, or run_parallel.py's process-group SIGTERM on task
    # timeout) does not kill the exec'd process inside the container: it
    # keeps writing root-owned files to the bind mount.  So quiesce first --
    # stopping the container tears down its PID namespace and every writer
    # in it -- then restart the now-inert container (its entrypoint is a
    # plain `sleep`, and reusing the same container keeps the user-namespace
    # mapping DUMPS_OWNER was captured under) and only then chown.
    #
    # The stop is cleanup's FIRST container operation -- ahead even of the
    # bundle removal below -- and uses -t 0: run_parallel.py escalates its
    # SIGTERM to SIGKILL after only 3 seconds, PID 1 (`sleep`) can never
    # honor a graceful stop anyway, and the daemon completes an accepted
    # stop even if this script is killed before it returns, whereas an exec
    # needs this client to survive the whole round-trip.  Nothing may spend
    # the kill window before the stop has been submitted.
    #
    # The stop's exit status gates the restoration: `start` returns 0 on an
    # already-running container, so it proves nothing about the writer --
    # only a successful stop does.  If the stop fails, skip the chown
    # entirely rather than hand the tree over under a live writer; the
    # teardown below retries the stop.  Worst case files are left with the
    # wrong owner, and the next successful run's full-tree hand-off chown
    # self-heals them.
    if [ "$DUMPS_RESTORE_PENDING" = "1" ]; then
        if $CONTAINER_RUNTIME stop -t 0 "$CONTAINER_NAME" >/dev/null 2>&1 \
            && $CONTAINER_RUNTIME start "$CONTAINER_NAME" >/dev/null 2>&1 \
            && restore_dumps_ownership >/dev/null 2>&1; then
            echo "  ✓ Restored output ownership: $output_folder"
        else
            echo "  Warning: could not restore output ownership: $output_folder" >&2
        fi
    fi

    # Remove the in-container bundle copy on early exits (the normal flow
    # discards it right after preprocess).  Best-effort and deliberately
    # AFTER the quiesce: if the container is not running anymore the exec
    # fails harmlessly and the unconditional `rm` below destroys the
    # container filesystem, bundle included.
    if [ -n "$CURRENT_CONTAINER_BUNDLE" ]; then
        $CONTAINER_RUNTIME exec "$CONTAINER_NAME" \
            rm -f -- "$CURRENT_CONTAINER_BUNDLE" >/dev/null 2>&1 || true
        CURRENT_CONTAINER_BUNDLE=""
    fi

    # Stop and remove container if exists.  -t 0 also here: nothing inside
    # can use a graceful stop (see above), so the default 10s grace is pure
    # added latency on every exit path.
    if $CONTAINER_RUNTIME ps -aq --filter "name=$CONTAINER_NAME" 2>/dev/null | grep -q .; then
        echo "  Stopping and removing container: $CONTAINER_NAME"
        $CONTAINER_RUNTIME stop -t 0 "$CONTAINER_NAME" >/dev/null 2>&1 || true
        $CONTAINER_RUNTIME rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
        echo "  ✓ Container stopped and removed"
    fi

    if [ -n "$ARTIFACT_STASH_DIR" ]; then
        uv run python -m scripts.containerized.task_artifact_guard cleanup \
            --stash-dir "$ARTIFACT_STASH_DIR" >/dev/null 2>&1 || \
            echo "  Warning: failed to clean artifact stash: $ARTIFACT_STASH_DIR" >&2
        ARTIFACT_STASH_DIR=""
    fi

    if [ -n "$TRUSTED_STASH_DIR" ] && [ -d "$TRUSTED_STASH_DIR" ]; then
        rm -rf -- "$TRUSTED_STASH_DIR"
        TRUSTED_STASH_DIR=""
    fi

    echo "Cleanup completed"
    exit "$cleanup_exit_code"
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
container_log_path="${output_folder}/container.log"
run_log_path="${output_folder}/run.log"
host_loop_log_path="${output_folder}/host_loop.log"
preprocess_log_path="${output_folder}/preprocess.log"
gateway_log_path="${output_folder}/gateway.log"
eval_log_path="${output_folder}/eval.log"

# Older decoupled runs placed the full task bundle in the bind-mounted output
# directory.  Remove that generated artifact before mounting the directory so
# this run cannot accidentally expose a stale evaluator configuration.
rm -rf -- "$output_folder/task_bundle.json"

# Bind-mount the host's configs/.mcp-auth so OAuth-refresh writes from
# mcp-remote inside the container persist back to host disk.  Notion's
# OAuth refresh_token rotates on every use; without this, the rotated
# token would die with the container and the next container would
# read a stale (now-invalidated) token and fail with "Grant not found".
# The mount path matches MCP_REMOTE_CONFIG_DIR in
# configs/mcp_servers/notion_official.yaml ("./configs/.mcp-auth", which
# resolves to /workspace/configs/.mcp-auth inside the container).
mkdir -p "$PROJECT_ROOT/configs/.mcp-auth"
START_CONTAINER_ARGS+=(
    "-v" "$PROJECT_ROOT/configs/.mcp-auth:/workspace/configs/.mcp-auth"
)

# Overlay the pinned Notion MCP's restrictive OpenAPI schema at runtime.
NOTION_OPENAPI_PATCH="$PROJECT_ROOT/configs/notion-mcp-patches/notion-openapi.json"
if [ -f "$NOTION_OPENAPI_PATCH" ]; then
    START_CONTAINER_ARGS+=(
        "-v" "$NOTION_OPENAPI_PATCH:/workspace/node_modules/@notionhq/notion-mcp-server/scripts/notion-openapi.json:ro"
    )
fi

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
    "sleep" "7200"
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

# Copy basic files and directories to container.
#
# For directories, use the ``src/.`` ("contents only") cp pattern with the
# destination pre-created.  Plain ``docker cp src dest`` would put src
# INSIDE dest when dest exists — and dest does exist whenever a bind
# mount above caused Docker to auto-create the destination's parent
# (e.g. /workspace/configs is auto-created here because we bind-mount
# /workspace/configs/.mcp-auth).  Without this pattern, configs/ contents
# would land at /workspace/configs/configs/* instead of /workspace/configs/*,
# breaking module imports like ``configs.global_configs``.
for item in "${FILES_TO_COPY[@]}"; do
    if [ -e "$PROJECT_ROOT/$item" ]; then
        echo "  Copying $item to container..."
        if [ -d "$PROJECT_ROOT/$item" ]; then
            $CONTAINER_RUNTIME exec "$CONTAINER_NAME" mkdir -p "/workspace/$item"
            if [ "$item" = "configs" ] && [ -d "$PROJECT_ROOT/configs/.mcp-auth" ]; then
                _stage=$(mktemp -d)
                (
                    cd "$PROJECT_ROOT/configs" && \
                    find . -mindepth 1 -maxdepth 1 ! -name '.mcp-auth' -exec cp -a {} "$_stage/" \;
                )
                $CONTAINER_RUNTIME cp "$_stage/." "$CONTAINER_NAME:/workspace/$item/"
                rm -rf "$_stage"
            else
                $CONTAINER_RUNTIME cp "$PROJECT_ROOT/$item/." "$CONTAINER_NAME:/workspace/$item/"
            fi
        else
            parent_dir=$(dirname "$item")
            if [ "$parent_dir" != "." ]; then
                $CONTAINER_RUNTIME exec "$CONTAINER_NAME" mkdir -p "/workspace/$parent_dir"
            fi
            $CONTAINER_RUNTIME cp "$PROJECT_ROOT/$item" "$CONTAINER_NAME:/workspace/$item"
        fi
    fi
done

# Copy task directory
echo "  Copying task directory tasks/$task_dir_arg to container..."
TARGET_PARENT_DIR=$(dirname "$task_dir_arg")
if [ "$TARGET_PARENT_DIR" != "." ]; then
    $CONTAINER_RUNTIME exec "$CONTAINER_NAME" mkdir -p "/workspace/tasks/$TARGET_PARENT_DIR"
fi
# The image may already contain a same-named task.  Remove it first so the
# trusted source cannot be merged with stale evaluator files from the image.
$CONTAINER_RUNTIME exec "$CONTAINER_NAME" rm -rf -- "$CONTAINER_TASK_PATH"
$CONTAINER_RUNTIME cp "$TASK_SOURCE" "$CONTAINER_NAME:/workspace/tasks/$TARGET_PARENT_DIR/"

echo "✓ File copying completed"

# Step 2.5.1: Copy model_params file to container if specified
if [ ! -z "$HOST_MODEL_PARAMS_FILE" ]; then
    echo ""
    echo "Step 2.5.1: Copying model_params file to container..."
    echo "  Copying ${HOST_MODEL_PARAMS_FILE} to ${CONTAINER_MODEL_PARAMS_FILE}..."
    $CONTAINER_RUNTIME cp "$HOST_MODEL_PARAMS_FILE" "$CONTAINER_NAME:${CONTAINER_MODEL_PARAMS_FILE}"
    echo "✓ Model params file copied"
fi

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

# Copy MCP auth directory if it exists (prefer ./configs/.mcp-auth over ~/.mcp-auth)
if [ -d "$PROJECT_ROOT/configs/.mcp-auth" ]; then
    echo " Using bind-mounted MCP authentication data from ./configs/.mcp-auth"
elif [ -d "$HOME/.mcp-auth" ]; then
    echo " ./configs/.mcp-auth not found, falling back to ~/.mcp-auth..."
    echo " Copying MCP authentication data from ~/.mcp-auth to container..."
    $CONTAINER_RUNTIME exec "$CONTAINER_NAME" mkdir -p /root/.mcp-auth
    $CONTAINER_RUNTIME cp "$HOME/.mcp-auth/." "$CONTAINER_NAME:/root/.mcp-auth/"
    echo "✓ MCP auth data copied from home directory"
else
    echo " Warning: MCP auth not found in ./configs/.mcp-auth or ~/.mcp-auth, skipping MCP auth copy"
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
if $CONTAINER_RUNTIME exec --env DOCKER_API_VERSION=1.44 "$CONTAINER_NAME" $CONTAINER_RUNTIME version >/dev/null 2>&1; then
    echo "✓ $CONTAINER_RUNTIME API accessible"
else
    echo "✗ Cannot access $CONTAINER_RUNTIME API"
    exit 1
fi

# Step 3: Container preprocess only
echo ""
echo "Step 3: Running preprocess in container..."

# Build environment variables array for exec command
EXEC_ENV_ARGS=("--env" "DOCKER_API_VERSION=1.44")

# Add TOOLATHLON_MODEL_PARAMS_FILE if it was copied
if [ ! -z "$CONTAINER_MODEL_PARAMS_FILE" ]; then
    EXEC_ENV_ARGS+=("--env" "TOOLATHLON_MODEL_PARAMS_FILE=${CONTAINER_MODEL_PARAMS_FILE}")
    echo "Setting container env: TOOLATHLON_MODEL_PARAMS_FILE=${CONTAINER_MODEL_PARAMS_FILE}"
fi

stage_trusted_bundle() {
    CURRENT_CONTAINER_BUNDLE=$(
        $CONTAINER_RUNTIME exec "$CONTAINER_NAME" \
            mktemp /run/toolathlon-decoupled-bundle.XXXXXX.json
    )
    if [ -z "$CURRENT_CONTAINER_BUNDLE" ]; then
        echo "✗ Failed to allocate a private container bundle path" >&2
        return 1
    fi
    $CONTAINER_RUNTIME cp \
        "$TRUSTED_BUNDLE_FILE" \
        "$CONTAINER_NAME:$CURRENT_CONTAINER_BUNDLE"
    $CONTAINER_RUNTIME exec "$CONTAINER_NAME" \
        chmod 600 "$CURRENT_CONTAINER_BUNDLE"
}

discard_container_bundle() {
    if [ -n "$CURRENT_CONTAINER_BUNDLE" ]; then
        $CONTAINER_RUNTIME exec "$CONTAINER_NAME" \
            rm -f -- "$CURRENT_CONTAINER_BUNDLE" >/dev/null 2>&1 || true
        CURRENT_CONTAINER_BUNDLE=""
    fi
}

TRUSTED_STASH_DIR=$(mktemp -d "/tmp/toolathlon-decoupled.XXXXXX")
chmod 700 "$TRUSTED_STASH_DIR"
TRUSTED_BUNDLE_FILE="$TRUSTED_STASH_DIR/task_bundle.json"
HOST_AGENT_BUNDLE_FILE="$TRUSTED_STASH_DIR/host_agent_bundle.json"
CURRENT_CONTAINER_BUNDLE=$(
    $CONTAINER_RUNTIME exec "$CONTAINER_NAME" \
        mktemp /run/toolathlon-preprocess-bundle.XXXXXX.json
)
if [ -z "$CURRENT_CONTAINER_BUNDLE" ]; then
    echo "✗ Failed to allocate the preprocess bundle path" >&2
    exit 1
fi

# Owner of the bind-mounted output tree as seen from inside the container's
# user namespace: the invoking host user on rootful Docker/Podman, container
# root under rootless Podman. Captured before preprocess (which runs as
# container root) so ownership can be restored afterwards.
if ! DUMPS_OWNER=$($CONTAINER_RUNTIME exec "$CONTAINER_NAME" \
    stat -c '%u:%g' /workspace/dumps); then
    echo "✗ Could not determine output ownership inside the container" >&2
    exit 1
fi
if [[ ! "$DUMPS_OWNER" =~ ^[0-9]+:[0-9]+$ ]]; then
    echo "✗ Invalid output ownership reported by container: $DUMPS_OWNER" >&2
    exit 1
fi
DUMPS_RESTORE_PENDING=1

PREPROCESS_ARGS=(
    uv run python -m scripts.decoupled.container_preprocess
    --eval_config "$eval_config"
    --task_dir "$task_dir_arg"
    --max_steps_under_single_turn_mode "$maxstep"
    --model_short_name "$modelname"
    --provider "$provider"
    --bundle_file "$CURRENT_CONTAINER_BUNDLE"
    --host_output_folder "$output_folder"
    --debug
)

set +e
if [ "$runmode" = "quickstart" ]; then
    $CONTAINER_RUNTIME exec "${EXEC_ENV_ARGS[@]}" -t \
        "$CONTAINER_NAME" "${PREPROCESS_ARGS[@]}"
else
    $CONTAINER_RUNTIME exec "${EXEC_ENV_ARGS[@]}" \
        "$CONTAINER_NAME" "${PREPROCESS_ARGS[@]}" \
        > "$preprocess_log_path" 2>&1
fi
PREPROCESS_EXIT_CODE=$?
set -e

# Preprocess runs as container root and may have created files in the
# bind-mounted output tree even when it failed.  Restore the tree to its
# pre-preprocess owner in the container's user namespace regardless of the
# preprocess result, so a failed run cannot strand root-owned files that
# break the next retry or cleanup with the same PermissionError.
if ! restore_dumps_ownership; then
    if [ $PREPROCESS_EXIT_CODE -eq 0 ]; then
        echo "✗ Failed to hand output ownership to the host agent" >&2
        exit 1
    fi
    # Keep the preprocess exit code authoritative; cleanup() retries the
    # restoration before the container is stopped.
    echo "Warning: could not restore output ownership after failed preprocess" >&2
fi

if [ $PREPROCESS_EXIT_CODE -ne 0 ]; then
    echo "✗ Preprocess failed, exit code: $PREPROCESS_EXIT_CODE"
    exit $PREPROCESS_EXIT_CODE
fi
echo "✓ Preprocess completed"

if ! $CONTAINER_RUNTIME cp \
    "$CONTAINER_NAME:$CURRENT_CONTAINER_BUNDLE" \
    "$TRUSTED_BUNDLE_FILE"; then
    echo "✗ Failed to preserve the preprocess bundle outside the container" >&2
    exit 1
fi
chmod 600 "$TRUSTED_BUNDLE_FILE"
discard_container_bundle

# Refuse to start an agent unless the phase bundle is complete and all paths
# are normalized beneath their expected roots.  The evaluator later replaces
# the agent-authored trajectory config with this resolved copy.
uv run python -c '
import json
import os
import posixpath
import sys

bundle_path, expected_task_dir, expected_host_root = sys.argv[1:]
with open(bundle_path, "r", encoding="utf-8") as bundle_file:
    bundle = json.load(bundle_file)

if bundle.get("schema_version") != 2:
    raise SystemExit("preprocess produced an unsupported task bundle")
if bundle.get("task_dir") != expected_task_dir:
    raise SystemExit("trusted bundle task_dir mismatch")
resolved = bundle.get("resolved_task_config")
if not isinstance(resolved, dict):
    raise SystemExit("trusted bundle is missing resolved_task_config")

container_paths = bundle.get("container_paths")
host_paths = bundle.get("host_paths")
if not isinstance(container_paths, dict) or not isinstance(host_paths, dict):
    raise SystemExit("trusted bundle is missing phase paths")

def require_normal_absolute(path, label, flavor):
    if not isinstance(path, str) or not flavor.isabs(path):
        raise SystemExit(f"{label} must be absolute")
    if flavor.normpath(path) != path:
        raise SystemExit(f"{label} must be normalized")
    return path

container_root = require_normal_absolute(
    container_paths.get("task_root"), "container task root", posixpath
)
try:
    inside_workspace = posixpath.commonpath(("/workspace", container_root)) == "/workspace"
except ValueError:
    inside_workspace = False
if not inside_workspace:
    raise SystemExit("container task root must be below /workspace")

for key in ("agent_workspace", "log_file"):
    value = require_normal_absolute(
        container_paths.get(key), f"container {key}", posixpath
    )
    if posixpath.commonpath((container_root, value)) != container_root:
        raise SystemExit(f"container {key} must be below the container task root")
    if resolved.get(key) != value:
        raise SystemExit(f"resolved config {key} does not match phase paths")
if resolved.get("task_root") != container_root:
    raise SystemExit("resolved config task_root does not match phase paths")

expected_host_root = os.path.abspath(expected_host_root)
host_root = require_normal_absolute(host_paths.get("task_root"), "host task root", os.path)
if host_root != expected_host_root:
    raise SystemExit("trusted bundle host output root mismatch")
for key in ("agent_workspace", "log_file"):
    value = require_normal_absolute(host_paths.get(key), f"host {key}", os.path)
    if os.path.commonpath((host_root, value)) != host_root:
        raise SystemExit(f"host {key} must be below the host task root")
' "$TRUSTED_BUNDLE_FILE" "$task_dir_arg" "$output_folder"

CONTAINER_EVAL_RESULT_PATH=$(uv run python -c '
import json, posixpath, sys
with open(sys.argv[1], "r", encoding="utf-8") as bundle_file:
    log_file = json.load(bundle_file)["container_paths"]["log_file"]
print(posixpath.join(posixpath.dirname(log_file), "eval_res.json"))
' "$TRUSTED_BUNDLE_FILE")

# The host loop gets a disposable copy; the master bundle remains unchanged
# for grading even if a host-loop implementation rewrites its input file.
cp "$TRUSTED_BUNDLE_FILE" "$HOST_AGENT_BUNDLE_FILE"
chmod 600 "$HOST_AGENT_BUNDLE_FILE"

echo "Step 3.1: Hiding evaluator and ground-truth artifacts..."
mkdir -p "$TRUSTED_STASH_DIR/artifacts"
chmod 700 "$TRUSTED_STASH_DIR/artifacts"
if ! ARTIFACT_STASH_DIR=$(uv run python -m scripts.containerized.task_artifact_guard stash \
    --runtime "$CONTAINER_RUNTIME" \
    --container "$CONTAINER_NAME" \
    --task-path "$CONTAINER_TASK_PATH" \
    --stash-root "$TRUSTED_STASH_DIR/artifacts"); then
    echo "✗ Failed to hide evaluator artifacts; gateway and agent will not start" >&2
    exit 1
fi

# Step 4: Start single-port gateway in container
echo ""
echo "Step 4: Starting container MCP gateway on port $gateway_port ..."
stage_trusted_bundle
GATEWAY_START_CMD="nohup uv run python -m scripts.decoupled.container_tool_gateway --bundle_file $CURRENT_CONTAINER_BUNDLE --host 0.0.0.0 --port $gateway_port --debug > /workspace/logs/gateway.log 2>&1 & echo \$!"
GATEWAY_PID=$($CONTAINER_RUNTIME exec "${EXEC_ENV_ARGS[@]}" "$CONTAINER_NAME" bash -c "$GATEWAY_START_CMD")
echo "Gateway PID in container: $GATEWAY_PID"

GATEWAY_READY=false
for i in $(seq 1 40); do
    if curl -fsS "http://127.0.0.1:${gateway_port}/health" >/dev/null 2>&1; then
        GATEWAY_READY=true
        break
    fi
    sleep 1
done

if [ "$GATEWAY_READY" != true ]; then
    echo "✗ Gateway did not become ready on port $gateway_port"
    exit 1
fi
echo "✓ Gateway is ready: http://127.0.0.1:${gateway_port}/sse"
discard_container_bundle

# Step 5: Host-side agent loop
echo ""
echo "Step 5: Running host-side agent loop..."
case "$host_loop_backend" in
    openai|openai_agents)
        HOST_LOOP_CMD=(
            uv run python -m scripts.decoupled.host_agent_loop
            --bundle_file "$HOST_AGENT_BUNDLE_FILE"
            --gateway_url "http://127.0.0.1:${gateway_port}/sse"
            --gateway_server_name "gw"
            --debug
        )
        ;;
    claude|claude_sdk|claude_agent_sdk)
        HOST_LOOP_CMD=(
            uv run python -m scripts.decoupled.host_agent_loop_claude_sdk
            --bundle_file "$HOST_AGENT_BUNDLE_FILE"
            --gateway_url "http://127.0.0.1:${gateway_port}/sse"
            --gateway_server_name "gw"
            --model "$modelname"
            --tool_call_mode "$tool_call_mode"
            --debug
        )
        ;;
    *)
        echo "✗ Unsupported host loop backend: $host_loop_backend"
        echo "Supported values: openai, openai_agents, claude, claude_sdk, claude_agent_sdk"
        exit 1
        ;;
esac

set +e
if [ "$runmode" = "quickstart" ]; then
    "${HOST_LOOP_CMD[@]}"
else
    "${HOST_LOOP_CMD[@]}" > "$host_loop_log_path" 2>&1
fi
HOST_LOOP_EXIT_CODE=$?
set -e
rm -f -- "$HOST_AGENT_BUNDLE_FILE"

if [ $HOST_LOOP_EXIT_CODE -eq 0 ]; then
    echo "✓ Host agent loop finished"
else
    echo "✗ Host agent loop failed, exit code: $HOST_LOOP_EXIT_CODE"
fi

# Always clean-replace agent-created name collisions before grading.  The
# same live container is retained because evaluator-visible task services may
# still be running in it.
echo ""
echo "Step 5.1: Restoring trusted evaluator artifacts..."
if ! uv run python -m scripts.containerized.task_artifact_guard restore \
    --runtime "$CONTAINER_RUNTIME" \
    --container "$CONTAINER_NAME" \
    --task-path "$CONTAINER_TASK_PATH" \
    --stash-dir "$ARTIFACT_STASH_DIR"; then
    echo "✗ Failed to restore trusted evaluator artifacts; refusing to grade" >&2
    exit 1
fi
uv run python -m scripts.containerized.task_artifact_guard cleanup \
    --stash-dir "$ARTIFACT_STASH_DIR"
ARTIFACT_STASH_DIR=""

# Never let a host agent's cached result bypass the real evaluator, including
# a directory or symlink collision at the expected result path.
$CONTAINER_RUNTIME exec "$CONTAINER_NAME" \
    rm -rf -- "$CONTAINER_EVAL_RESULT_PATH"

# Step 6: Container evaluation
echo ""
echo "Step 6: Running evaluation in container..."
stage_trusted_bundle
EVAL_ARGS=(
    uv run python -m scripts.decoupled.container_eval
    --bundle_file "$CURRENT_CONTAINER_BUNDLE"
    --require_resolved_task_config
    --consume_bundle
    --agent_exit_code "$HOST_LOOP_EXIT_CODE"
)

set +e
if [ "$runmode" = "quickstart" ]; then
    $CONTAINER_RUNTIME exec "${EXEC_ENV_ARGS[@]}" -t \
        "$CONTAINER_NAME" "${EVAL_ARGS[@]}"
else
    $CONTAINER_RUNTIME exec "${EXEC_ENV_ARGS[@]}" \
        "$CONTAINER_NAME" "${EVAL_ARGS[@]}" \
        > "$eval_log_path" 2>&1
fi
EVAL_EXIT_CODE=$?
set -e
discard_container_bundle

# Preserve the historical debugging artifact, but only after the model and
# evaluator have finished.  Clean-replace any agent-created collision with
# the untouched host-private master bundle.
PUBLISHED_BUNDLE_FILE="$output_folder/task_bundle.json"
rm -rf -- "$PUBLISHED_BUNDLE_FILE"
cp -- "$TRUSTED_BUNDLE_FILE" "$PUBLISHED_BUNDLE_FILE"
chmod 600 "$PUBLISHED_BUNDLE_FILE"

if [ $EVAL_EXIT_CODE -eq 0 ]; then
    echo "✓ Evaluation passed"
else
    echo "✗ Evaluation failed, exit code: $EVAL_EXIT_CODE"
fi

# Collect logs
echo ""
echo "Collecting logs..."
$CONTAINER_RUNTIME logs "$CONTAINER_NAME" > "$container_log_path" 2>&1 || true
# /workspace/logs is already the bind-mounted host output directory.  Copying
# these paths back with docker/podman cp would copy a file onto itself and can
# truncate it on some runtimes.

if [ "$runmode" != "quickstart" ] && [ "$parent_captures_run_log" != "1" ]; then
    echo "Decoupled run log placeholder" > "$run_log_path"
elif [ "$parent_captures_run_log" = "1" ]; then
    echo "Run log is being captured by the parent runner: $run_log_path"
fi

for log_file in "$container_log_path" "$preprocess_log_path" "$gateway_log_path" "$host_loop_log_path" "$eval_log_path"; do
    if [ -f "$log_file" ]; then
        echo ""
        echo "=== $(basename "$log_file") (last 20 lines) ==="
        tail -20 "$log_file"
    fi
done

EXIT_CODE=$EVAL_EXIT_CODE
if [ $EXIT_CODE -eq 0 ] && [ $HOST_LOOP_EXIT_CODE -ne 0 ]; then
    EXIT_CODE=$HOST_LOOP_EXIT_CODE
fi

echo ""
echo "Final exit code: $EXIT_CODE"
exit $EXIT_CODE
