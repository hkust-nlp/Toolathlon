# 和scripts/debug_manual.sh基本一致，区别在于这里用到的scripts/model_wise下的配置文件会输出到 recorded_trajectories_v2, 随后会被上传

task_dir=finalpool/canvas-art-quiz

uv run main.py \
--eval_config scripts/model_wise/eval_gpt-5.json \
--task_dir $task_dir \
--debug
# # --multi_turn_mode

# uv run main.py \
# --eval_config scripts/model_wise/eval_gpt-4.1-mini.json \
# --task_dir $task_dir \
# --debug
# # --multi_turn_mode

# uv run main.py \
# --eval_config scripts/model_wise/eval_claude-4-sonnet.json \
# --task_dir $task_dir \
# --debug \
# --cn_mode
# --multi_turn_mode

# uv run main.py \
# --eval_config scripts/model_wise/eval_gpt-4.1-mini.json \
# --task_dir $task_dir \
# --debug \
# --en_mode
# # --multi_turn_mode