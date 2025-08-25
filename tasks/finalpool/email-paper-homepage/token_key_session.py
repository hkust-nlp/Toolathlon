from addict import Dict
import os
from pathlib import Path
import json

def get_github_token():
    task_id = "email-paper-homepage"
    config_path = "configs/github_repos.json"
    with open(config_path, 'r') as f:
        data = json.load(f)
    for task in data:
        if task.get("task_id") == task_id:
            return task.get("github_token", "")

github_token = get_github_token()
if not github_token:
    raise ValueError("[Warning] Task-Level GitHub token is not set.")
else:
    all_token_key_session = Dict(
        github_token = github_token,
        emails_config_file = str(Path(__file__).parent / "email_config.json"),
    )