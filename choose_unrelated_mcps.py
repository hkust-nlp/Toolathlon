all_mcps = ['filesystem', 'word', 'fetch', 'emails', 
'playwright_with_chunk', 'memory', 'excel', 'google-cloud', 
'notion', 'wandb', 'terminal', 'snowflake', 'pdf-tools', 
'huggingface', 'github', 'yahoo-finance', 'google_map', 'canvas', 
'k8s', 'google_sheet', 'woocommerce', 'pptx', 'youtube-transcript', 
'howtocook', 'arxiv-latex', 
'scholarly', 'arxiv_local', 'rail_12306', 'youtube', 'git']

from utils.general.helper import read_json
import os
import random
import json
import copy

# 遍历所有tasks/finalpool_with_unrelated_mcp/xx/task_config.json
# 记录下xx
# 随机选2，4，8个这个任务没有用到的mcp放进needed_mcp_servers作为干扰项
# 组成新的task_config.json


how2shuffle = {}

import glob
for task_folder in glob.glob("tasks/finalpool_with_unrelated_mcp/*"):
    if not os.path.isdir(task_folder):
        continue
    task_name = task_folder.split("/")[-1]
    task_config = os.path.join(task_folder, "task_config.json")
    dt = read_json(task_config)
    needed_mcp_servers = dt["needed_mcp_servers"]
    non_existed_mcps = [mcp for mcp in all_mcps if mcp not in needed_mcp_servers]
    for num in [2, 4, 8]:
        newdt = copy.deepcopy(dt)
        random.shuffle(non_existed_mcps)
        random_mcps = non_existed_mcps[:num]
        newdt["needed_mcp_servers"] = needed_mcp_servers + random_mcps
        if task_name not in how2shuffle:
            how2shuffle[task_name] = {}
        how2shuffle[task_name][f"add_{num}"] = newdt

with open("how2shuffle.json", "w") as f:
    json.dump(how2shuffle, f, indent=4)
