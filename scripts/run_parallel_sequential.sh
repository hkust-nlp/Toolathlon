#!/bin/bash

models=("glm-4.5" "kimi-k2-instruct" "Kimi-K2-0905" "gpt5-mini")

for model in "${models[@]}"; do
    bash scripts/run_parallel_jh.sh $model "./dumps_0915_all_${model}"
done
