#!/bin/bash

# models=("deepseek-v3.1" "claude-4-sonnet-0514")

# for model in "${models[@]}"; do
#     bash scripts/run_parallel_jh.sh $model "./dumps_0916_all_${model}"
# done

bash scripts/run_parallel_jh.sh grok-code-fast-1 "./dumps_0916_all_grok-code-fast-1" openrouter
bash scripts/run_parallel_jh.sh deepseek-v3.1 "./dumps_0916_all_deepseek-v3.1_aihubmix" aihubmix
