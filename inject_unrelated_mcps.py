from utils.general.helper import read_json
import os
import json

def write_json(dt,fn):
    with open(fn,'w') as f:
        json.dump(dt,f,indent=4)

xxx = "how2shuffle.json"
how2shuffle = read_json(xxx)


for num in [2,4,8]:
    target_finalpool_dir = f"tasks/finalpool_add_unrelated_mcps_{num}"
    for task_name in how2shuffle:
        # print(task_name)
        target_task_config_file = os.path.join(target_finalpool_dir, task_name, "task_config.json")
        # print(target_task_config_file)
        new_task_config = how2shuffle[task_name][f"add_{num}"]
        # print(new_task_config)
        # raise ValueError
        write_json(new_task_config, target_task_config_file)

print("all done!")