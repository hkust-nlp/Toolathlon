from pathlib import Path
import argparse
from utils.github_tools.helper_funcs import get_user_name, roll_back_commit, get_latest_commit_sha, check_repo_exists
import json

def create_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser()
    
    parser.add_argument(
        '--github_token',
        help='GitHub Personal Access Token',
        default=""
    )
    
    return parser

def get_config():
    task_id = "email-paper-homepage"
    config_path = "configs/github_repos.json"
    with open(config_path, 'r') as f:
        data = json.load(f)
    for task in data:
        if task.get("task_id") == task_id:
            return task
    raise ValueError(f"Task ID {task_id} not found in config.")

def get_branch(repo_name):
    if "My-Homepage" not in repo_name:
        return "main"
    return "master"

def main(args):
    task_config = get_config()
    user_name = get_user_name(args.github_token)
    for repo in task_config.get("upstream_repos"):
        repo_name = repo.split('/')[-1]
        local_repo = f"{user_name}/{repo_name}"
        if not check_repo_exists(args.github_token, local_repo):
            # Local repo should be created during initialization process
            raise ValueError(f"Local repository {local_repo} does not exist. You should check the initialization process.")
        print(f"Processing repository: {local_repo}")
        commit_sha = get_latest_commit_sha(args.github_token, repo, get_branch(repo_name))
        roll_back_commit(args.github_token, local_repo, commit_sha, branch=get_branch(repo_name))
        print(f"Repository {local_repo} initialized successfully.")
    

if __name__ == "__main__":
    # 创建命令行参数解析器
    parser = create_parser()
    args = parser.parse_args()
    main(args)