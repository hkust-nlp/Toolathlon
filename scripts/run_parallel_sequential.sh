# 定义模型提供商列表，使用 | 分隔格式："modelname|provider"
MODEL_PROVIDER_LIST=(
    # "grok-code-fast-1|openrouter"
    # "qwen-3-coder|qwen_official"
    # "deepseek-v3.1|deepseek_official"
    # "gemini-2.5-pro|openrouter"
    # "glm-4.5|openrouter"
    # "kimi-k2-0905|kimi_official"
    # "grok-4|openrouter"
    # "claude-4-sonnet-0514|openrouter"
    # "grok-4-fast|openrouter"
    # "gemini-2.5-flash|openrouter"
    # "gpt-5-mini|openrouter"
    # "o3|openrouter"
    # "o4-mini|openrouter"
    # "gpt-oss-120b|openrouter"
    # "gpt-5|openrouter"
    # "qwen-3-max|openrouter"
    # "claude-4.1-opus-0805|openrouter"
    # "gpt-5-high|openrouter"
    # "gpt-5-medium|openrouter"
    # "gpt-5-low|openrouter"
)

TASK_LIST_FILE="./filtered_tasks.txt"

poste_configure_dovecot=${1:-true}

for attempt in {1..3}; do
    for model_provider in "${MODEL_PROVIDER_LIST[@]}"; do
        # Parse model name and provider
        MODEL_SHORT_NAME="${model_provider%%|*}"  # Extract left part up to first |
        PROVIDER="${model_provider##*|}"         # Extract right part after last |
        
        echo "Running $MODEL_SHORT_NAME with $PROVIDER, attempt $attempt ......"

        bash global_preparation/deploy_containers.sh $poste_configure_dovecot
        bash scripts/run_parallel.sh "$MODEL_SHORT_NAME" "./dumps_finalexp/${MODEL_SHORT_NAME}_${attempt}" "$PROVIDER" "$TASK_LIST_FILE"
    done
done