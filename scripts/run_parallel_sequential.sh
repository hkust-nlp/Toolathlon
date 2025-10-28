# Some Configurations
TASK_IMAGE=lockon0927/toolathlon-task-image:1022openhands # this is the image we use for parallel evaluation
TASK_LIST_FILE="" # you can specify a file with each line representing a task, by doing so you can evaluate on an arbitrary subset of tasks
DUMP_PATH="./dumps_finalexp_openhands" # you must have this ./ prefix
poste_configure_dovecot=true # or `false` if your Linux distribution does not need to configure Dovecot to allow plaintext auth
WROKERS=10

# Define the model provider list, using | to separate the model name and the provider
# See `utils/api_model/model_provider.py` for the available models and providers
MODEL_PROVIDER_LIST=(
    "grok-4-fast|openrouter"
    "grok-code-fast-1|openrouter"
    "claude-4.5-haiku-1001|openrouter"
    "kimi-k2-0905|kimi_official"
    "deepseek-v3.2-exp|deepseek_official"
    "qwen-3-coder|qwen_official"
    "glm-4.6|openrouter"
    "grok-4|openrouter"
    "claude-4.5-sonnet-0929|openrouter"
    "claude-4-sonnet-0514|openrouter"
    "gpt-5-mini|openrouter"
    "o3|openrouter"
    "o4-mini|openrouter"
    "gpt-5|openrouter"
    "gpt-5-high|openrouter"
    "gemini-2.5-flash|openrouter"
    "gemini-2.5-pro|openrouter"
)

# Main Loop, you can set the number of attempts to run the same model with the same provider
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