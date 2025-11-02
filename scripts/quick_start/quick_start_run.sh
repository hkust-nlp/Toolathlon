#### Parameter description
# eval_config: Controls the model to use, output save path, sampling parameters, etc. During development, please modify scripts/temp_and_debug/debug_eval_config.json
# task_dir: Task directory, please use the path relative to `tasks`
# debug: Enable debug mode to print all information
# manual: Use real users, otherwise simulated users will be used
# multi_turn_mode: Enable multi-turn mode, otherwise use single-turn mode; in single-turn mode, the core task is used as the first round of user input, and there will be no more simulated users afterwards

#### the following parameters are used to override the parameters in the eval_config
# model_short_name: Model name/ID from the API endpoint
# provider: default to unified when directly using TOOLATHLON_OPENAI_BASE_URL
# max_steps_under_single_turn_mode: Maximum number of steps under single-turn mode

#### you must use any of these 3 example tasks in this quick start run script, they don't require any additional configurations.
# 1. finalpool/find-alita-paper
# 2. finalpool/excel-market-research
# 3. finalpool/interview-report

task="finalpool/find-alita-paper"

#### after you have do the full praparation, you can switch to any task under `tasks/finalpool`, the format be like `finalpool/{taskname}`

# for the model_short_name here we use the claude sonnet 4.5 model ID from OpenRouter
uv run main.py \
--eval_config scripts/quick_start/quick_start_eval_config.json \
--task_dir $task \
--debug \
--model_short_name anthropic/claude-sonnet-4.5 \
--provider unified \
--max_steps_under_single_turn_mode 200 \
# --multi_turn_mode \
# --manual
