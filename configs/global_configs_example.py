# Please fill in the actual content of this file, and copy it, removing the _example suffix
from addict import Dict
global_configs = Dict(
    # these api keys are optional is you use the unified model provider
    aihubmix_key="xxx", 
    openrouter_key="xxx", 
    qwen_official_key="xxx", 
    kimi_official_key="xxx", 
    deepseek_official_key="xxx", 
    anthropic_official_key="xxx", 
    openai_official_key="xxx", 
    google_official_key="xxx", 
    xai_official_key="xxx", 
    
    # the following two are necessary
    podman_or_docker="docker", # or `podman` depending on which one you want to use
    notion_preprocess_with_playwright=False, # In genral you do not need to change this! It is whether you use mcp/playwright to preprocess the notion page, default as false.
)