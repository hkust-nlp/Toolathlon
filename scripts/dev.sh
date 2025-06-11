# this is a dev to run multiple tasks, we not skip this
uv run main.py \
--task_dir tasks/dev \
--eval_config scripts/eval_config.json \
--max_concurrent 10 \
--output eval_results/run1/dev/results.json