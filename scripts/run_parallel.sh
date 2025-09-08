###

# 这个脚本用于运行parallel.py
# 需要传入的参数：
# --tasks_folder 任务所在的tasks下的第一级目录
# --tag 任务标签，可以不填，不填的时候会自动生成一个shortuuid
# --model_short_name 模型简写名
# --provider 用哪家供应商，见utils/api_model/model_provider.py
# --maxstep 最大agentloop步数
# --worker 并发度
# --timeout 每个任务，包括预处理，agentloop和测试的最长运行时间

# 部分任务存在冲突，无法同时执行，可以在一级目录下配置task_conflict.json来解决，见tasks/testparallel/task_conflict.json

uv run run_parallel.py \
--tasks_folder testparallel \
--tag firsttry \
--model_short_name gpt-5-mini \
--provider aihubmix \
--maxstep 200 \
--worker 4 \
--timeout 1800