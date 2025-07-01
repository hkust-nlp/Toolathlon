# 和scripts/debug_manual.sh基本一致，区别在于这里用到的scripts/model_wise下的配置文件会输出到 recorded_trajectories_v2, 随后会被上传

uv run demo.py \
--eval_config scripts/model_wise/eval_gpt-4.1-mini.json \
--task_dir jl/set-conf-cr-ddl \
--debug
# --multi_turn_mode