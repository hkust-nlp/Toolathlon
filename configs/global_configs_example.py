# Please fill in the actual content of this file, and copy it, removing the _example suffix
from addict import Dict
global_configs = Dict(
    aihubmix_key="xxx", # Fill in the aihubmix key
    openrouter_key="xxx", # Fill in the openrouter key
    qwen_official_key="xxx", # Fill in the qwen_official key
    kimi_official_key="xxx", # Fill in the kimi_official key
    deepseek_official_key="xxx", # Fill in the deepseek_official key
    anthropic_official_key="xxx", # Fill in the anthropic_official key
    openai_official_key="xxx", # Fill in the openai_official key
    google_official_key="xxx", # Fill in the google_official key
    xai_official_key="xxx", # Fill in the xai_official key
    podman_or_docker="docker", # or `podman` depending on which one you want to use
    notion_preprocess_with_playwright=False, # In genral you do not need to change this! It is whether you use mcp/playwright to preprocess the notion page, default as false.
)