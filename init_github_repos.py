import json
import argparse
from utils.app_specific.github.helper_funcs import check_repo_exists, fork_repo, get_user_name

CONFIG_PATH = "configs/github_repos.json"

def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    
    parser.add_argument(
        '--github_token',
        help='GitHub Personal Access Token',
        default=None
    )

    args = parser.parse_args()
    github_token = args.github_token
    if not github_token:
        from configs.token_key_session import all_token_key_session
        github_token = all_token_key_session.get("github_token", "")

    if not github_token:
        raise ValueError("GitHub token is required. Please provide it using --github_token argument.")

    config = load_config()

    user_name = get_user_name(github_token)
    # check existence
    for task in config:
        for repo in task.get("upstream_repos"):
            self_repo = f"{user_name}/{repo.split('/')[-1]}"
            if check_repo_exists(github_token, self_repo):
                raise ValueError(f"❌[Warning] Repository {self_repo} already exists. Please check with your account settings.")

    # fork repos
    for task in config:
        print("Task ID: ", task.get("task_id"))
        for repo in task.get("upstream_repos"):
            fork_repo(github_token, repo)
                


