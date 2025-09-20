# 列表: ("")

# bash global_preparation/deploy_containers.sh
# kind delete clusters --all
# bash scripts/run_parallel_jh.sh qwen-3-coder "./dumps/qwen-3-coder_09182034" qwen_official


# bash global_preparation/deploy_containers.sh
# kind delete clusters --all
# bash scripts/run_parallel_jh.sh Kimi-K2-0905 "./dumps/kimi-k2-0905_09182034" kimi_official


# bash global_preparation/deploy_containers.sh
# kind delete clusters --all
# bash scripts/run_parallel_jh.sh deepseek-v3.1 "./dumps/deepseek-v3.1_09182034" deepseek_official


# bash global_preparation/deploy_containers.sh
# kind delete clusters --all
# bash scripts/run_parallel_jh.sh glm-4.5 "./dumps/glm-4.5_09182034" openrouter

# bash global_preparation/deploy_containers.sh
# kind delete clusters --all
# bash scripts/run_parallel_jh.sh gpt-5 "./dumps/gpt-5_09182034" openrouter

# bash global_preparation/deploy_containers.sh
# kind delete clusters --all
# bash scripts/run_parallel_jh.sh grok-code-fast-1 "./dumps/grok-code-fast-1_09182034" openrouter

bash global_preparation/deploy_containers.sh
kind delete clusters --all
bash scripts/run_parallel_jh.sh gpt-5-mini "./dumps/gpt-5-mini-1_09182034" openrouter

bash global_preparation/deploy_containers.sh
kind delete clusters --all
bash scripts/run_parallel_jh.sh grok-4 "./dumps/grok-4_09182034" openrouter