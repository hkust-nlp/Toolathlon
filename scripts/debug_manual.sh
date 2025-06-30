# this is the debug script when you are developing new tasksAdd commentMore actions

# the task config you need to configature is `tasks/manual/manual_001.json`
# and you can tune the model you want to test in `scripts/debug_eval_config.json`

# please do not change the generation paramerters, the key arguments to adjust is `provider` and `short_name`
# see `utils/api_model/model_provider.py` to check what models you can use

# you can use --manual to switch off the llm-simulated user
# othewise, the user is simulated by gpt-4.1-0414 according to the user system prompt

# the --debug argument will print all information so that you can see the complete interaction history

# after the interaction, you will see the interaction hostory in "./dumps/run1" as recorded in `scripts/debug_eval_config.json`

# I have set the `dumps` in /gitignore, so this is completely your local env, and will not interfere with the recorded_trajectories
uv run demo.py \
--eval_config scripts/debug_eval_config.json \
--task_dir jl/set-icml-cr-ddl \
--debug
# --manual \
# --single_turn_mode
