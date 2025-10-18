# Some Configurations
TASK_IMAGE=lockon0927/toolathlon-task-image:1016beta # this is the image we use for parallel evaluation
# TASK_IMAGE="lockon0927/mcpbench-task-image-v2:jl0921alpha" # try an legacy one
TASK_LIST_FILE="" # you can specify a file with each line representing a task, by doing so you can evaluate on an arbitrary subset of tasks
DUMP_PATH="./dumps_finalexp" # you must have this ./ prefix
poste_configure_dovecot=true # or `false` if your Linux distribution does not need to configure Dovecot to allow plaintext auth
WROKERS=10


# Define the model provider list, using | to separate the model name and the provider
# See `utils/api_model/model_provider.py` for the available models and providers
MODEL_PROVIDER_LIST=(
    "gpt-5|openrouter"
)

# Main Loop
for attempt in {2..2}; do
    for model_provider in "${MODEL_PROVIDER_LIST[@]}"; do
        # Parse model name and provider
        MODEL_SHORT_NAME="${model_provider%%|*}"  # Extract left part up to first |
        PROVIDER="${model_provider##*|}"         # Extract right part after last |
        
        echo "Running $MODEL_SHORT_NAME with $PROVIDER, attempt $attempt ......"

        bash global_preparation/deploy_containers.sh $poste_configure_dovecot
        bash scripts/run_parallel.sh "$MODEL_SHORT_NAME" "$DUMP_PATH/${MODEL_SHORT_NAME}_${attempt}" "$PROVIDER" "$TASK_LIST_FILE" "$WROKERS" "$TASK_IMAGE"
    done
done

MODEL_PROVIDER_LIST=(
    # "grok-4-fast|openrouter"
    # "grok-code-fast-1|openrouter"
    # "claude-4.5-haiku-1001|openrouter"
    # "qwen-3-coder-0722|qwen_official"
    # "qwen-3-coder-0923|qwen_official"
    "kimi-k2-0905|kimi_official"
    "deepseek-v3.2-exp|deepseek_official"
    "qwen-3-coder|qwen_official"
    "glm-4.6|openrouter"
    # "qwen-3-max|qwen_official"
    # "gemini-2.5-pro|openrouter"
    # "grok-4|openrouter"
    # "claude-4.5-sonnet-0929|openrouter"
    # "gemini-2.5-flash|openrouter"
    # "gpt-5-mini|openrouter"
    # "o3|openrouter"
    # "o4-mini|openrouter"
    # "gpt-oss-120b|openrouter"
    "gpt-5|openrouter"
    # "claude-4.1-opus-0805|openrouter"
    # "gpt-5-high|openrouter"
    # "gpt-5-medium|openrouter"
    # "gpt-5-low|openrouter"
)

# Main Loop
for attempt in {3..3}; do
    for model_provider in "${MODEL_PROVIDER_LIST[@]}"; do
        # Parse model name and provider
        MODEL_SHORT_NAME="${model_provider%%|*}"  # Extract left part up to first |
        PROVIDER="${model_provider##*|}"         # Extract right part after last |
        
        echo "Running $MODEL_SHORT_NAME with $PROVIDER, attempt $attempt ......"

        bash global_preparation/deploy_containers.sh $poste_configure_dovecot
        bash scripts/run_parallel.sh "$MODEL_SHORT_NAME" "$DUMP_PATH/${MODEL_SHORT_NAME}_${attempt}" "$PROVIDER" "$TASK_LIST_FILE" "$WROKERS" "$TASK_IMAGE"
    done
done

MODEL_PROVIDER_LIST=(
    # "grok-4-fast|openrouter"
    # "grok-code-fast-1|openrouter"
    "claude-4.5-haiku-1001|openrouter"
    # "qwen-3-coder-0722|qwen_official"
    # "qwen-3-coder-0923|qwen_official"
    # "kimi-k2-0905|kimi_official"
    # "deepseek-v3.2-exp|deepseek_official"
    # "qwen-3-coder|qwen_official"
    # "glm-4.6|openrouter"
    # "qwen-3-max|qwen_official"
    # "gemini-2.5-pro|openrouter"
    # "grok-4|openrouter"
    "claude-4.5-sonnet-0929|openrouter"
    # "gemini-2.5-flash|openrouter"
    "gpt-5-mini|openrouter"
    "o3|openrouter"
    "o4-mini|openrouter"
    # "gpt-oss-120b|openrouter"
    # "gpt-5|openrouter"
    # "claude-4.1-opus-0805|openrouter"
    # "gpt-5-high|openrouter"
    # "gpt-5-medium|openrouter"
    # "gpt-5-low|openrouter"
)

# Main Loop
for attempt in {1..3}; do
    for model_provider in "${MODEL_PROVIDER_LIST[@]}"; do
        # Parse model name and provider
        MODEL_SHORT_NAME="${model_provider%%|*}"  # Extract left part up to first |
        PROVIDER="${model_provider##*|}"         # Extract right part after last |
        
        echo "Running $MODEL_SHORT_NAME with $PROVIDER, attempt $attempt ......"

        bash global_preparation/deploy_containers.sh $poste_configure_dovecot
        bash scripts/run_parallel.sh "$MODEL_SHORT_NAME" "$DUMP_PATH/${MODEL_SHORT_NAME}_${attempt}" "$PROVIDER" "$TASK_LIST_FILE" "$WROKERS" "$TASK_IMAGE"
    done
done