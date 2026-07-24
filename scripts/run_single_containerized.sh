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
eval_config=${7:-"scripts/formal_run_v0.json"}
image_name=${8:-"lockon0927/toolathlon-task-image:1016beta"}
containerized_mode=${TOOLATHLON_CONTAINERIZED_MODE:-"phased"}
parent_captures_run_log=${TOOLATHLON_PARENT_CAPTURES_RUN_LOG:-"0"}

case "$containerized_mode" in
    phased)
        ;;
    legacy)
        echo "WARNING: TOOLATHLON_CONTAINERIZED_MODE=legacy disables grader/ground-truth isolation." >&2
        ;;
    *)
        echo "Error: unsupported TOOLATHLON_CONTAINERIZED_MODE: $containerized_mode" >&2
        echo "Supported values: phased, legacy" >&2
        exit 1
        ;;
esac

if [ -z "$task_dir_arg" ] || [ -z "$runmode" ] || [ -z "$modelname" ]; then
    echo "Usage: $0 <task_dir> <runmode> <modelname>"
    echo "Example: $0 debug/debug-task testrun testmodel"
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
output_folder="${dump_path}/${taskdomain}/${taskname}"

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
echo "Containerized execution mode: $containerized_mode"

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

# --- BEGIN: Detect and propagate TOOLATHLON_OPENAI env vars from host to container ---
EXTRA_ENV_ARGS=()
if [ ! -z "${TOOLATHLON_OPENAI_BASE_URL+x}" ]; then
    EXTRA_ENV_ARGS+=("-e" "TOOLATHLON_OPENAI_BASE_URL")
    echo "Detected host TOOLATHLON_OPENAI_BASE_URL, will pass into container"
fi

if [ ! -z "${TOOLATHLON_OPENAI_API_KEY+x}" ]; then
    EXTRA_ENV_ARGS+=("-e" "TOOLATHLON_OPENAI_API_KEY")
    echo "Detected host TOOLATHLON_OPENAI_API_KEY, will pass into container"
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
# --- END: Detect and propagate TOOLATHLON_OPENAI env vars ---

# Private host-side state used only by phased mode.  Initialize these before
# installing the trap so cleanup is safe on every early-exit path.
ARTIFACT_STASH_DIR=""
TRUSTED_STASH_DIR=""
CURRENT_CONTAINER_BUNDLE=""

# Cleanup function
cleanup() {
    cleanup_exit_code=$?
    trap - EXIT
    set +e
    echo ""
    echo "Performing cleanup..."

    if [ -n "$CURRENT_CONTAINER_BUNDLE" ]; then
        $CONTAINER_RUNTIME exec "$CONTAINER_NAME" rm -f -- "$CURRENT_CONTAINER_BUNDLE" >/dev/null 2>&1 || true
        CURRENT_CONTAINER_BUNDLE=""
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

    # Stop and remove container if exists
    if $CONTAINER_RUNTIME ps -aq --filter "name=$CONTAINER_NAME" 2>/dev/null | grep -q .; then
        echo "  Stopping and removing container: $CONTAINER_NAME"
        $CONTAINER_RUNTIME stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
        $CONTAINER_RUNTIME rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
        echo "  ✓ Container stopped and removed"
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

# Add mounts
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
# Copy actual task directory
# The image may already contain a same-named task. Remove it first so docker
# cp cannot merge stale evaluator files into the trusted source snapshot.
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

# Step 3: Execute task command(s) in container
echo ""
echo "Step 3: Executing task in $containerized_mode mode..."

# Build environment variables array for exec commands.
EXEC_ENV_ARGS=("--env" "DOCKER_API_VERSION=1.44")
if [ ! -z "$CONTAINER_MODEL_PARAMS_FILE" ]; then
    EXEC_ENV_ARGS+=("--env" "TOOLATHLON_MODEL_PARAMS_FILE=${CONTAINER_MODEL_PARAMS_FILE}")
    echo "Setting container env: TOOLATHLON_MODEL_PARAMS_FILE=${CONTAINER_MODEL_PARAMS_FILE}"
fi

# Normal runs append every phase to the same run.log. Quickstart keeps the
# existing interactive TTY behavior.
run_container_phase() {
    if [ "$runmode" = "quickstart" ]; then
        $CONTAINER_RUNTIME exec "${EXEC_ENV_ARGS[@]}" -t "$CONTAINER_NAME" "$@"
    elif [ "$parent_captures_run_log" = "1" ]; then
        # run_parallel.py already owns run.log and captures this stdout stream.
        $CONTAINER_RUNTIME exec "${EXEC_ENV_ARGS[@]}" "$CONTAINER_NAME" "$@"
    else
        $CONTAINER_RUNTIME exec "${EXEC_ENV_ARGS[@]}" "$CONTAINER_NAME" "$@" >> "$run_log_path" 2>&1
    fi
}

stage_trusted_bundle() {
    CURRENT_CONTAINER_BUNDLE=$(
        $CONTAINER_RUNTIME exec "$CONTAINER_NAME" \
            mktemp /run/toolathlon-task-bundle.XXXXXX.json
    )
    if [ -z "$CURRENT_CONTAINER_BUNDLE" ]; then
        echo "✗ Failed to allocate a private container bundle path" >&2
        return 1
    fi
    $CONTAINER_RUNTIME cp \
        "$TRUSTED_BUNDLE_FILE" \
        "$CONTAINER_NAME:$CURRENT_CONTAINER_BUNDLE"
    $CONTAINER_RUNTIME exec "$CONTAINER_NAME" chmod 600 "$CURRENT_CONTAINER_BUNDLE"
}

discard_container_bundle() {
    if [ -n "$CURRENT_CONTAINER_BUNDLE" ]; then
        $CONTAINER_RUNTIME exec "$CONTAINER_NAME" \
            rm -f -- "$CURRENT_CONTAINER_BUNDLE" >/dev/null 2>&1 || true
        CURRENT_CONTAINER_BUNDLE=""
    fi
}

if [ "$runmode" != "quickstart" ] && [ "$parent_captures_run_log" != "1" ]; then
    : > "$run_log_path"
fi

if [ "$containerized_mode" = "legacy" ]; then
    echo "Executing legacy one-shot task flow..."
    set +e
    run_container_phase \
        uv run main.py \
        --eval_config "$eval_config" \
        --task_dir "$task_dir_arg" \
        --max_steps_under_single_turn_mode "$maxstep" \
        --model_short_name "$modelname" \
        --provider "$provider" \
        --debug
    EXEC_EXIT_CODE=$?
    set -e
else
    # Keep trusted state under the host's /tmp, which this runner never mounts
    # into the task container.  Do not honor TMPDIR: callers may point it at
    # the bind-mounted task output directory.
    TRUSTED_STASH_DIR=$(mktemp -d "/tmp/toolathlon-containerized.XXXXXX")
    chmod 700 "$TRUSTED_STASH_DIR"
    TRUSTED_BUNDLE_FILE="$TRUSTED_STASH_DIR/task_bundle.json"
    PREPROCESS_CONTAINER_BUNDLE=$(
        $CONTAINER_RUNTIME exec "$CONTAINER_NAME" \
            mktemp /run/toolathlon-preprocess-bundle.XXXXXX.json
    )
    CURRENT_CONTAINER_BUNDLE="$PREPROCESS_CONTAINER_BUNDLE"

    echo "Step 3.1: Running preprocess..."
    set +e
    run_container_phase \
        uv run python -m scripts.decoupled.container_preprocess \
        --eval_config "$eval_config" \
        --task_dir "$task_dir_arg" \
        --max_steps_under_single_turn_mode "$maxstep" \
        --model_short_name "$modelname" \
        --provider "$provider" \
        --bundle_file "$PREPROCESS_CONTAINER_BUNDLE" \
        --debug
    PREPROCESS_EXIT_CODE=$?
    set -e
    if [ "$PREPROCESS_EXIT_CODE" -ne 0 ]; then
        echo "✗ Preprocess failed, exit code: $PREPROCESS_EXIT_CODE" >&2
        exit "$PREPROCESS_EXIT_CODE"
    fi

    # Move the trusted, resolved bundle off-container before the model runs.
    $CONTAINER_RUNTIME cp \
        "$CONTAINER_NAME:$PREPROCESS_CONTAINER_BUNDLE" \
        "$TRUSTED_BUNDLE_FILE"
    chmod 600 "$TRUSTED_BUNDLE_FILE"
    discard_container_bundle
    uv run python -c '
import json, posixpath, sys
with open(sys.argv[1], "r", encoding="utf-8") as bundle_file:
    bundle = json.load(bundle_file)
if bundle.get("schema_version") != 2 or not isinstance(bundle.get("resolved_task_config"), dict):
    raise SystemExit("preprocess produced an incomplete trusted task bundle")
container_paths = bundle.get("container_paths")
task_root = container_paths.get("task_root") if isinstance(container_paths, dict) else None
if not isinstance(task_root, str) or not posixpath.isabs(task_root):
    raise SystemExit("trusted bundle task root must be an absolute path")
if posixpath.normpath(task_root) != task_root:
    raise SystemExit("trusted bundle task root must be normalized")
try:
    inside_workspace = posixpath.commonpath(("/workspace", task_root)) == "/workspace"
except ValueError:
    inside_workspace = False
if not inside_workspace:
    raise SystemExit("trusted bundle task root must be under /workspace")
' "$TRUSTED_BUNDLE_FILE"
    CONTAINER_TASK_ROOT=$(uv run python -c '
import json, sys
with open(sys.argv[1], "r", encoding="utf-8") as bundle_file:
    print(json.load(bundle_file)["container_paths"]["task_root"])
' "$TRUSTED_BUNDLE_FILE")
    if [ -z "$CONTAINER_TASK_ROOT" ]; then
        echo "✗ Trusted bundle contains an empty task root" >&2
        exit 1
    fi

    echo "Step 3.2: Hiding evaluator and ground-truth artifacts..."
    mkdir -p "$TRUSTED_STASH_DIR/artifacts"
    chmod 700 "$TRUSTED_STASH_DIR/artifacts"
    if ! ARTIFACT_STASH_DIR=$(uv run python -m scripts.containerized.task_artifact_guard stash \
        --runtime "$CONTAINER_RUNTIME" \
        --container "$CONTAINER_NAME" \
        --task-path "$CONTAINER_TASK_PATH" \
        --stash-root "$TRUSTED_STASH_DIR/artifacts"); then
        echo "✗ Failed to hide evaluator artifacts; agent will not start" >&2
        exit 1
    fi

    echo "Step 3.3: Running prepared agent..."
    stage_trusted_bundle
    set +e
    run_container_phase \
        uv run python -m scripts.containerized.container_agent \
        --bundle_file "$CURRENT_CONTAINER_BUNDLE" \
        --debug
    AGENT_EXIT_CODE=$?
    set -e
    discard_container_bundle
    if [ "$AGENT_EXIT_CODE" -eq 0 ]; then
        echo "✓ Agent completed successfully"
    else
        echo "✗ Agent failed, exit code: $AGENT_EXIT_CODE; restoring and evaluating anyway" >&2
    fi

    # Keep the same live container: some tasks intentionally leave processes
    # (for example kubectl port-forward) running for their evaluator to inspect.
    echo "Step 3.4: Restoring trusted evaluator artifacts..."
    uv run python -m scripts.containerized.task_artifact_guard restore \
        --runtime "$CONTAINER_RUNTIME" \
        --container "$CONTAINER_NAME" \
        --task-path "$CONTAINER_TASK_PATH" \
        --stash-dir "$ARTIFACT_STASH_DIR"

    # Never let an agent-created cached result bypass the real evaluator.
    $CONTAINER_RUNTIME exec "$CONTAINER_NAME" \
        rm -rf -- "$CONTAINER_TASK_ROOT/eval_res.json"

    echo "Step 3.5: Running evaluation with trusted config..."
    stage_trusted_bundle
    set +e
    run_container_phase \
        uv run python -m scripts.decoupled.container_eval \
        --bundle_file "$CURRENT_CONTAINER_BUNDLE" \
        --require_resolved_task_config \
        --boolean_evaluation_status \
        --consume_bundle \
        --agent_exit_code "$AGENT_EXIT_CODE"
    EVAL_EXIT_CODE=$?
    set -e
    discard_container_bundle
    if [ "$EVAL_EXIT_CODE" -eq 0 ]; then
        echo "✓ Evaluation passed"
    else
        echo "✗ Evaluation failed, exit code: $EVAL_EXIT_CODE" >&2
    fi

    EXEC_EXIT_CODE=$EVAL_EXIT_CODE
    if [ "$EXEC_EXIT_CODE" -eq 0 ] && [ "$AGENT_EXIT_CODE" -ne 0 ]; then
        EXEC_EXIT_CODE=$AGENT_EXIT_CODE
    fi
fi

echo ""
if [ "$EXEC_EXIT_CODE" -eq 0 ]; then
    echo "✓ Task executed successfully, exit code: $EXEC_EXIT_CODE"
else
    echo "✗ Task execution failed, exit code: $EXEC_EXIT_CODE"
fi

EXIT_CODE=$EXEC_EXIT_CODE

# Avoid copying the bind-mounted run.log onto itself, which can truncate it on
# some runtimes. Quickstart is display-in-place and does not create a run.log.
if [ "$runmode" = "quickstart" ]; then
    echo "Quickstart output was displayed in place; no run log was generated"
elif [ "$parent_captures_run_log" = "1" ]; then
    echo "Run log is being captured by the parent runner: $run_log_path"
else
    echo "Run log written directly to: $run_log_path"
fi

# Display last lines of container and run logs if present
if [ -f "$container_log_path" ]; then
    echo ""
    echo "=== Container execution log (last 20 lines) ==="
    tail -20 "$container_log_path"
    echo ""
    echo "=== Container log path: $container_log_path ==="
fi

if [ "$runmode" != "quickstart" ] && \
   [ "$parent_captures_run_log" != "1" ] && \
   [ -f "$run_log_path" ]; then
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
