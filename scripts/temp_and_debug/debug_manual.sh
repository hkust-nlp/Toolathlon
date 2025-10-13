# Parameter description
# eval_config: Controls the model to use, output save path, sampling parameters, etc. During development, please modify scripts/temp_and_debug/debug_eval_config.json
# task_dir: Task directory, please use the path relative to `tasks`
# debug: Enable debug mode to print all information
# manual: Use real users, otherwise simulated users will be used
# multi_turn_mode: Enable multi-turn mode, otherwise use single-turn mode; in single-turn mode, the core task is used as the first round of user input, and there will be no more simulated users afterwards

# the following parameters are used to override the parameters in the eval_config
# model_short_name: Model name, see utils/api_model/model_provider.py
# provider: Provider, see utils/api_model/model_provider.py
# max_steps_under_single_turn_mode: Maximum number of steps under single-turn mode

uv run demo.py \
--eval_config scripts/temp_and_debug/debug_eval_config.json \
--task_dir  finalpool/mrbeast-analysis \
--debug \
--model_short_name deepseek-v3.2-exp \
--provider deepseek_official \
--max_steps_under_single_turn_mode 200 \
# --multi_turn_mode \
# --manual \
