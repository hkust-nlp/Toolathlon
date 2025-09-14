# 参数说明
# eval_config 控制使用的模型，输出保存路径，采样参数等；开发阶段请在scripts/debug_eval_config.json里修改
# task_dir 任务路径，请使用相对于`tasks`的相对路径
# debug 开启debug模式，打印所有信息
# manual 使用真实用户，否则使用模拟用户
# multi_turn_mode 开启多轮模式，否则使用单轮模式；单轮模式下，核心任务直接作为第一轮用户输入，此后不再有模拟用户

uv run demo.py \
--eval_config scripts/model_wise/eval_claude-4-sonnet.json \
--task_dir finalpool/woocommerce-new-product \
--debug \
# --model_short_name claude-4-sonnet-0514 \
# --provider aihubmix \
# --max_steps_under_single_turn_mode 200 \
# --multi_turn_mode \
# --manual \
