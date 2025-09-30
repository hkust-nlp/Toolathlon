import glob
from pprint import pprint
from .utils import prepare_all_stat_for_one_traj
import json
from tqdm import tqdm

parent_dir = "dumps_finalexp"
full_stat_jsonl = []

for model_name in [
    "gpt-5",
    "grok-4",
    "claude-4-sonnet-0514",
    "deepseek-v3.1",
    "gemini-2.5-pro",
    "grok-code-fast-1",
    "kimi-k2-0905",
    "glm-4.5",
    "qwen-3-coder",
    "grok-4-fast",
    "gemini-2.5-flash",
    "gpt-5-mini",
    "o3",
    "o4-mini",
    "gpt-oss-120b",
    "qwen-3-max"
]:
    # find all {parent_dir}/{model_name}*
    all_model_dirs = glob.glob(f"{parent_dir}/{model_name}_09211710_*")
    for model_dir in tqdm(all_model_dirs):
        attempt_num = int(model_dir.split("_")[-1])
        # if attempt_num!=1:
        #     continue
        info = {"model_name": model_name, "attempt_num": attempt_num}
        # find all {model_dir}/finalpool/*
        all_finalpool_dirs = glob.glob(f"{model_dir}/finalpool/*")
        for task_dir in tqdm(all_finalpool_dirs):
            task_name = task_dir.split("/")[-1]
            try:
                result = prepare_all_stat_for_one_traj(task_dir)
            except Exception as e:
                print(f"Error processing task {task_dir}: {e}")
                result = None 
            # pprint(result)
            # raise ValueError
            fullinfo = {**info, "task_name": task_name, "traj_stat":result}
            full_stat_jsonl.append(fullinfo)

with open("./analysis/data/full_stat_3_runs.jsonl", "w") as f:
    for fullinfo in full_stat_jsonl:
        f.write(json.dumps(fullinfo) + "\n")


            