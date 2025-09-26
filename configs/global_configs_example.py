# 请将该文件填写上实际内容后，复制一份，去掉_example的后缀
# _ds后缀代表这是用于deepseek model的
from addict import Dict
global_configs = Dict(
    aihubmix_key= "xxx", # 填写aihubmix的key
    openrouter_key="xxx", # 填写openrouter的key
    qwen_official_key="xxx", # 填写qwen_official的key
    kimi_official_key="xxx", # 填写kimi_official的key
    deepseek_official_key="xxx", # 填写deepseek_official的key
    podman_or_docker="podman", # or `docker`
)