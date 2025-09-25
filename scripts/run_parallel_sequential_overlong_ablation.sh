# 定义模型提供商列表，使用 | 分隔格式："modelname|provider"
MODEL_PROVIDER_LIST=(
    "grok-4-fast|openrouter"
    "grok-code-fast-1|openrouter"
    # "qwen-3-coder|qwen_official"
    # "deepseek-v3.1|deepseek_official"
    # "gemini-2.5-pro|openrouter"
    # "glm-4.5|openrouter"
    # "kimi-k2-0905|kimi_official"
    # "grok-4|openrouter"
    # "claude-4-sonnet-0514|openrouter"
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

DATESTR="09210140"

for overlong_threshold in 5000 15000 40000; 
do
    echo "Running overlong_threshold $overlong_threshold ......"
    export BENCH_MAX_SINGLE_TURN_RETURN_CHARS=$overlong_threshold
    for model_provider in "${MODEL_PROVIDER_LIST[@]}"; do
        # 解析模型名和提供商
        MODEL_SHORT_NAME="${model_provider%%|*}"  # 从左边提取到第一个 | 之前的内容
        PROVIDER="${model_provider##*|}"         # 从右边提取最后一个 | 之后的内容
        
        echo "Running $MODEL_SHORT_NAME with $PROVIDER, overlong_threshold $overlong_threshold ......"

        # uv run python -c "import os; print(int(os.getenv('BENCH_MAX_SINGLE_TURN_RETURN_CHARS', 100000)))"

        bash global_preparation/deploy_containers.sh
        kind delete clusters --all
        bash scripts/run_parallel_jh.sh "$MODEL_SHORT_NAME" "./dumps_finalexp_overlong_ablation/${MODEL_SHORT_NAME}_${DATESTR}_OVERLONG${overlong_threshold}" "$PROVIDER" "$DATESTR"
    done
done