# basically, this is a version simple version of `scripts/debug_manual.sh`
# however, this will load an actual eval_config, in our case is `scripts/model_wise/eval_claude-4-sonnet.json`
# also, you should assign a developed task config, with fully supported all components
# include everything

# we tun off the `--manual` to let gpt-4.1-0414 play as the user

# for --debug, you can either use it or not, depending on if you want to see the full trajectory
uv run demo.py \
--eval_config scripts/model_wise/eval_gpt-4.1-nano.json \
--task_config tasks/dev/filesystem_001.json \
--debug