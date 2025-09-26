import os
import json
import shutil
import asyncio
from argparse import ArgumentParser
from pathlib import Path
import time

from utils.general.helper import fork_repo
from configs.token_key_session import all_token_key_session
from utils.app_specific.github.api import (
    github_get_login, github_create_issue, github_delete_repo, 
    github_create_user_repo, github_get_latest_commit, github_get_repo
)
from utils.app_specific.github.git_ops import git_mirror_clone, git_mirror_push
from utils.app_specific.github.repo_ops import update_file_content
from utils.app_specific.huggingface.datasets import (
    hf_get_namespace, hf_create_dataset, hf_delete_dataset, hf_upload_file
)

GITHUB_REPO_NAME = "LUFFY"
SOURCE_REPO_NAME = f"Toolathlon-Archive/{GITHUB_REPO_NAME}"

async def main():
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--token_path", required=False, default="configs/token_key_session.py")
    parser.add_argument("--launch_time", required=False)
    args = parser.parse_args()

    github_token = all_token_key_session.github_token

    # # Resolve dynamic namespaces/logins
    github_owner = github_get_login(github_token)
    github_repo_full = f"{github_owner}/{GITHUB_REPO_NAME}"

    # 2) Fork the repo
    await fork_repo(SOURCE_REPO_NAME, str(github_repo_full), fork_default_branch_only=False, readonly=False)
    
    # check if the forked repo is ready, query for 5 times, each 10 secs interval
    for i in range(5):
        if github_get_repo(github_token, github_owner, GITHUB_REPO_NAME):
            break
        time.sleep(10*(i+1))

    # 2.6) Mirror clone forked repo locally
    tmpdir = Path(os.path.dirname(__file__)) / ".." / "tmp"
    tmpdir.mkdir(exist_ok=True)
    local_mirror_dir = tmpdir / f"{GITHUB_REPO_NAME}.git"
    await git_mirror_clone(github_token, github_repo_full, str(local_mirror_dir))

    # 2.7) Delete the forked repo to free the name
    github_delete_repo(github_token, github_owner, GITHUB_REPO_NAME)
    time.sleep(2)

    # 2.8) Create a new independent repo with the same name
    github_create_user_repo(github_token, GITHUB_REPO_NAME, private=False)

    # 2.9) Push mirror to the new repo
    await git_mirror_push(github_token, str(local_mirror_dir), github_repo_full)

    # Cleanup
    shutil.rmtree(tmpdir)

    with open(os.path.join(args.agent_workspace, ".github_token"), "w", encoding="utf-8") as f:
        f.write(github_token)

if __name__ == "__main__":
    asyncio.run(main())