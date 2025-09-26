# this is a dev to run multiple tasks, we now skip this in development stage
# In real evaluation setting, we now use the `task_dir` to specify the subset we want to evaluate a model, 
# the following command take the `dev` subset as an example.
uv run main.py \
--task_dir tasks/dev \
--eval_config scripts/eval_config.json \
--max_concurrent 10 \
--output eval_results/run1/dev/results.json