#!/bin/bash

models=("gpt-5" "Kimi-K2-0905" "qwen-3-coder" "claude-4-sonnet-0514")

for model in "${models[@]}"; do
    bash scripts/run_parallel_jh.sh $model "./dumps_0916_all_${model}"
done
