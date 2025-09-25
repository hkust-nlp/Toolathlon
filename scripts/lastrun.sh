# # 定义模型提供商列表，使用 | 分隔格式："modelname|provider"
# MODEL_PROVIDER_LIST=(
#     "gpt-5|openrouter"
# )

# DATESTR="09210140"

# for distractor in 4; 
# do
#     echo "Running $distractor distractors ......"
#     for model_provider in "${MODEL_PROVIDER_LIST[@]}"; do
#         # 解析模型名和提供商
#         MODEL_SHORT_NAME="${model_provider%%|*}"  # 从左边提取到第一个 | 之前的内容
#         PROVIDER="${model_provider##*|}"         # 从右边提取最后一个 | 之后的内容
        
#         echo "Running $MODEL_SHORT_NAME with $PROVIDER, $distractor distractors ......"

#         bash global_preparation/deploy_containers.sh
#         kind delete clusters --all
#         bash scripts/run_parallel_jh_ablation.sh "$MODEL_SHORT_NAME" "./dumps_ablation/${MODEL_SHORT_NAME}_${DATESTR}" "$PROVIDER" "$DATESTR" "$distractor"
#     done
# done

# # 定义模型提供商列表，使用 | 分隔格式："modelname|provider"
# MODEL_PROVIDER_LIST=(
#     "gpt-5-high|openrouter"
# )

# DATESTR="09210140"

# for attempt in {2..3}; do
#     echo "Running attempt $attempt ......"
#     for model_provider in "${MODEL_PROVIDER_LIST[@]}"; do
#         # 解析模型名和提供商
#         MODEL_SHORT_NAME="${model_provider%%|*}"  # 从左边提取到第一个 | 之前的内容
#         PROVIDER="${model_provider##*|}"         # 从右边提取最后一个 | 之后的内容
        
#         echo "Running $MODEL_SHORT_NAME with $PROVIDER, attempt $attempt ......"

#         bash global_preparation/deploy_containers.sh
#         kind delete clusters --all
#         bash scripts/run_parallel_jh.sh "$MODEL_SHORT_NAME" "./dumps_finalexp/${MODEL_SHORT_NAME}_${DATESTR}_${attempt}" "$PROVIDER" "$DATESTR"
#     done
# done

# 定义模型提供商列表，使用 | 分隔格式："modelname|provider"
# MODEL_PROVIDER_LIST=(
#     "qwen-3-max|openrouter"
# )

# DATESTR="09210140"


# WORKERS="4"

# for attempt in {1..1}; do
#     echo "Running attempt $attempt ......"
#     for model_provider in "${MODEL_PROVIDER_LIST[@]}"; do
#         # 解析模型名和提供商
#         MODEL_SHORT_NAME="${model_provider%%|*}"  # 从左边提取到第一个 | 之前的内容
#         PROVIDER="${model_provider##*|}"         # 从右边提取最后一个 | 之后的内容
        
#         echo "Running $MODEL_SHORT_NAME with $PROVIDER, attempt $attempt ......"

#         # bash global_preparation/deploy_containers.sh
#         # kind delete clusters --all
#         bash scripts/run_parallel_jh.sh "$MODEL_SHORT_NAME" "./dumps_finalexp/${MODEL_SHORT_NAME}_${DATESTR}_${attempt}" "$PROVIDER" "$DATESTR" "$WORKERS"
#     done
# done


# WORKERS="4"

# for attempt in {2..3}; do
#     echo "Running attempt $attempt ......"
#     for model_provider in "${MODEL_PROVIDER_LIST[@]}"; do
#         # 解析模型名和提供商
#         MODEL_SHORT_NAME="${model_provider%%|*}"  # 从左边提取到第一个 | 之前的内容
#         PROVIDER="${model_provider##*|}"         # 从右边提取最后一个 | 之后的内容
        
#         echo "Running $MODEL_SHORT_NAME with $PROVIDER, attempt $attempt ......"

#         bash global_preparation/deploy_containers.sh
#         kind delete clusters --all
#         bash scripts/run_parallel_jh.sh "$MODEL_SHORT_NAME" "./dumps_finalexp/${MODEL_SHORT_NAME}_${DATESTR}_${attempt}" "$PROVIDER" "$DATESTR" "$WORKERS"
#     done
# done


# 定义模型提供商列表，使用 | 分隔格式："modelname|provider"
MODEL_PROVIDER_LIST=(
    "gemini-2.5-pro|openrouter"
)

DATESTR="09210140"

for attempt in {1..1}; do
    echo "Running attempt $attempt ......"
    for model_provider in "${MODEL_PROVIDER_LIST[@]}"; do
        # 解析模型名和提供商
        MODEL_SHORT_NAME="${model_provider%%|*}"  # 从左边提取到第一个 | 之前的内容
        PROVIDER="${model_provider##*|}"         # 从右边提取最后一个 | 之后的内容
        
        echo "Running $MODEL_SHORT_NAME with $PROVIDER, attempt $attempt ......"

        bash global_preparation/deploy_containers.sh
        kind delete clusters --all
        bash scripts/run_parallel_jh.sh "$MODEL_SHORT_NAME" "./dumps_finalexp_gemini25pro_only/${MODEL_SHORT_NAME}_${DATESTR}_${attempt}" "$PROVIDER" "$DATESTR"
    done
done