# Some Configurations
TASK_IMAGE=lockon0927/toolathlon-task-image:1016beta # this is the image we use for parallel evaluation
DUMP_PATH="./dumps_finalexp" # you must have this ./ prefix or use absolute path
poste_configure_dovecot=true # or `false` if your Linux distribution does not need to configure Dovecot to allow plaintext auth
WROKERS=10

#### If you want to use the unified model provider, 
# but do not want to explicitly export these environment variables in your shell, 
# you can also uncomment these lines and set the values here
# ↓↓↓↓ uncomment these lines ↓↓↓↓
# TOOLATHLON_OPENAI_BASE_URL="your-custom-base-url"
# TOOLATHLON_OPENAI_API_KEY="your-custom-api-key"
# export TOOLATHLON_OPENAI_BASE_URL
# export TOOLATHLON_OPENAI_API_KEY

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
    # "claude-haiku-4-5|unified" # you can also use this unified model provider, as long as you correctly set the environment variables TOOLATHLON_OPENAI_BASE_URL and TOOLATHLON_OPENAI_API_KEY
)

# Main Loop, you can set the number of attempts to run the same model with the same provider
for attempt in {1..1}; do
    for model_provider in "${MODEL_PROVIDER_LIST[@]}"; do
        # Parse model name and provider
        MODEL_SHORT_NAME="${model_provider%%|*}"  # Extract left part up to first |
        PROVIDER="${model_provider##*|}"         # Extract right part after last |
        
        echo "Running $MODEL_SHORT_NAME with $PROVIDER, attempt $attempt ......"

        bash global_preparation/deploy_containers.sh $poste_configure_dovecot
        bash scripts/run_parallel.sh "$MODEL_SHORT_NAME" "$DUMP_PATH/${MODEL_SHORT_NAME}_${attempt}" "$PROVIDER" "$WROKERS" "$TASK_IMAGE"
    done
done