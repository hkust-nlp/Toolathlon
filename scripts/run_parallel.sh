#!/bin/bash

#### If you want to use the unified model provider, 
# but do not want to explicitly export these environment variables in your shell, 
# you can also uncomment these lines and set the values here
# ↓↓↓↓ uncomment these lines ↓↓↓↓
# TOOLATHLON_OPENAI_BASE_URL="your-custom-base-url"
# TOOLATHLON_OPENAI_API_KEY="your-custom-api-key"
# export TOOLATHLON_OPENAI_BASE_URL
# export TOOLATHLON_OPENAI_API_KEY

# Configuration Variables - Modify as needed
TASKS_FOLDER="finalpool"
TAG="full"

# Parse input arguments for model_name, provider and dump_path
MODEL_NAME="${1:-gpt-5-mini}"
DUMP_PATH="${2:-./parallel_debug_gpt5}"
MODEL_PROVIDER="${3:-openrouter}"

# legacy arguments, not used in toolathlon
USER_MODEL_NAME="gpt-5" # this is of no use as toolathlon now does not involve user model   
USER_MODEL_PROVIDER="aihubmix" # this is of no use as toolathlon now does not involve user model   
MAX_TURNS="50" # this is of no use as toolathlon now does not have multiple user-agent interactive turns

# task-execution related arguments
MAX_STEPS="100" # this is the maximum number of steps an agent can take in a single turn, you can set it to a larger value if you want to evaluate on a longer trajectory
WORKERS=${5:-10} # number of workers to use in parallel evaluation
TIMEOUT="2400" # the timeout for each task execution, including pre-processing, agentloop and post-processing

# model sampling related arguments
TEMPERATURE="0.6"
TOP_P="1"
MAX_TOKENS="8192"
USER_TEMPERATURE="1.0" # not used in toolathlon
USER_TOP_P="1.0" # not used in toolathlon
USER_MAX_TOKENS="1024" # not used in toolathlon
IMAGE_NAME=${6:-"lockon0927/toolathlon-task-image:1016beta"}  # Docker image to use

mkdir -p $DUMP_PATH

# You can provide a txt file with each line representing a task, by doing so you can evaluate on an arbitrary subset of tasks
# if leave an empty string, it will evaluate on all tasks
TASK_LIST=${4:-""}

# Generate temporary config file with random suffix to avoid conflicts
RANDOM_SUFFIX=$(date +%s)_$$_$(shuf -i 1000-9999 -n 1)
mkdir -p scripts/temp_configs
TEMP_CONFIG="scripts/temp_configs/temp_parallel_config_${RANDOM_SUFFIX}.json"
cat > "$TEMP_CONFIG" <<EOF
{
    "global_task_config":{
        "max_turns": $MAX_TURNS,
        "max_steps_under_single_turn_mode": $MAX_STEPS,
        "dump_path": "/workspace/dumps",
        "direct_to_dumps": true
    },
    "mcp":{
        "server_config_path": "configs/mcp_servers"
    },
    "agent":{
        "model":{
            "short_name": "$MODEL_NAME",
            "provider": "$MODEL_PROVIDER"
        },
        "generation":{
            "temperature": $TEMPERATURE,
            "top_p": $TOP_P,
            "max_tokens": $MAX_TOKENS
        },
        "tool":{
            "tool_choice": "auto",
            "parallel_tool_calls": true,
            "max_inner_turns": 2000
        }
    },
    "user":{
        "model":{
            "short_name": "$USER_MODEL_NAME",
            "provider": "$USER_MODEL_PROVIDER"
        },
        "generation":{
            "temperature": $USER_TEMPERATURE,
            "top_p": $USER_TOP_P,
            "max_tokens": $USER_MAX_TOKENS
        }
    }
}
EOF

# Build command arguments
ARGS="--tasks_folder $TASKS_FOLDER --tag $TAG --model_short_name $MODEL_NAME --provider $MODEL_PROVIDER --maxstep $MAX_STEPS --workers $WORKERS --timeout $TIMEOUT --dump_path $DUMP_PATH --eval_config $TEMP_CONFIG --image_name $IMAGE_NAME"

# Add optional task list if specified
if [ ! -z "$TASK_LIST" ]; then
    ARGS="$ARGS --task_list $TASK_LIST"
fi

echo "🚀 Starting parallel evaluation..."
echo "📁 Tasks folder: $TASKS_FOLDER"
echo "🏷️  Tag: $TAG"
echo "🤖 Agent model: $MODEL_NAME ($MODEL_PROVIDER)"
echo "👤 User model: $USER_MODEL_NAME ($USER_MODEL_PROVIDER)"
echo "🌡️  Temperature: $TEMPERATURE"
echo "📁 Dump path: $DUMP_PATH"
echo "🐳 Docker image: $IMAGE_NAME"
echo "⚙️  Config file: $TEMP_CONFIG"
if [ ! -z "$TASK_LIST" ]; then
    echo "📋 Task list filter: $TASK_LIST"
fi

# Execute evaluation with custom config
PYTHONUNBUFFERED=1 uv run run_parallel.py $ARGS 2>&1 | tee "$DUMP_PATH/stdout.log"

EVAL_EXIT_CODE=$?

# Post-processing: Aggregate logs and create comprehensive statistics
echo ""
echo "📋 Post-processing: Aggregating logs and creating comprehensive statistics..."

# 1. Concatenate all container logs
echo "📝 Aggregating container logs..."
find "$DUMP_PATH" -name "container.log" -type f -exec cat {} \; > "$DUMP_PATH/container_all.log" 2>/dev/null
echo "✅ Container logs saved to: $DUMP_PATH/container_all.log"

# 2. Concatenate all run logs  
echo "📝 Aggregating run logs..."
find "$DUMP_PATH" -name "run.log" -type f -exec cat {} \; > "$DUMP_PATH/run_all.log" 2>/dev/null
echo "✅ Run logs saved to: $DUMP_PATH/run_all.log"

# 3. Create eval_res_all.jsonl by aggregating all eval_res.json files
echo "📝 Creating eval_res_all.jsonl..."
find "$DUMP_PATH" -name "eval_res.json" -type f -exec sh -c 'jq -c . "$1"' _ {} \; > "$DUMP_PATH/eval_res_all.jsonl" 2>/dev/null
echo "✅ Evaluation results saved to: $DUMP_PATH/eval_res_all.jsonl"

# 4. Create traj_log_all.jsonl by aggregating all traj_log.json files
echo "📝 Creating traj_log_all.jsonl..."
find "$DUMP_PATH" -name "traj_log.json" -type f -exec sh -c 'cat "$1" && echo' _ {} \; > "$DUMP_PATH/traj_log_all.jsonl" 2>/dev/null
echo "✅ Trajectory logs saved to: $DUMP_PATH/traj_log_all.jsonl"

# 5. Generate enhanced statistics using separate script
echo "📊 Generating enhanced statistics..."
uv run scripts/generate_parallel_stats.py --dump_path "$DUMP_PATH" --tasks_folder "$TASKS_FOLDER" --temp_config "$TEMP_CONFIG" --task_list_file "${TASK_LIST:-all_tasks}"

echo ""
echo "📊 Parallel evaluation completed with exit code: $EVAL_EXIT_CODE"
echo "📁 All results saved to: $DUMP_PATH"
echo "📋 Key files:"
echo "  - eval_stats.json: Comprehensive statistics"
echo "  - eval_res_all.jsonl: All evaluation results"  
echo "  - container_all.log: All container logs"
echo "  - run_all.log: All task run logs"

exit $EVAL_EXIT_CODE