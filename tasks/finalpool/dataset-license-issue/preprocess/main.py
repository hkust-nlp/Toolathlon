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
    github_create_user_repo, github_get_latest_commit
)
from utils.app_specific.github.git_ops import git_mirror_clone, git_mirror_push
from utils.app_specific.github.repo_ops import update_file_content
from utils.app_specific.huggingface.datasets import (
    hf_get_namespace, hf_create_dataset, hf_delete_dataset, hf_upload_file
)

GITHUB_REPO_NAME = "Annoy-DataSync"
SOURCE_REPO_NAME = f"Toolathlon-Archive/{GITHUB_REPO_NAME}"
HF_DATASET_REASONING_SUFFIX = "Annoy-PyEdu-Rs" 
HF_DATASET_RAW_SUFFIX = "Annoy-PyEdu-Rs-Raw"

def hf_prepare_datasets(files_folder: Path, hf_token: str, namespace: str, github_namespace: str) -> dict:
    ds_reasoning = f"{namespace}/{HF_DATASET_REASONING_SUFFIX}"
    ds_raw = f"{namespace}/{HF_DATASET_RAW_SUFFIX}"

    # Delete if exists
    hf_delete_dataset(ds_reasoning, hf_token)
    hf_delete_dataset(ds_raw, hf_token)

    # Create repos
    hf_create_dataset(ds_reasoning, hf_token)
    hf_create_dataset(ds_raw, hf_token)

    # Process and upload README files
    for suffix, folder in [("reasoning", "hf-reasoning"), ("raw", "hf-raw")]:
        readme_path = files_folder / folder / "README.md"
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read().replace("{hf_namespace}", namespace).replace("{github_namespace}", github_namespace)
        
        tmp_path = files_folder / folder / "README.md.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        repo_id = ds_reasoning if suffix == "reasoning" else ds_raw
        hf_upload_file(str(tmp_path), repo_id, "README.md", hf_token)

    return {
        "reasoning": f"https://huggingface.co/datasets/{ds_reasoning}",
        "raw": f"https://huggingface.co/datasets/{ds_raw}",
    }

def update_readme(github_repo_full: str, github_owner: str, hf_namespace: str):
    token = all_token_key_session.github_token
    replacements = {"{github_namespace}": github_owner, "{hf_namespace}": hf_namespace}
    update_file_content(token, github_repo_full, "README.md", replacements, 
                       "chore: update README placeholders for namespaces")

async def main():
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--token_path", required=False, default="configs/token_key_session.py")
    parser.add_argument("--launch_time", required=False)
    args = parser.parse_args()

    files_folder = Path(os.path.dirname(__file__)) / ".." / "files"
    github_token = all_token_key_session.github_token
    hf_token = all_token_key_session.huggingface_token

    # Resolve dynamic namespaces/logins
    github_owner = github_get_login(github_token)
    github_repo_full = f"{github_owner}/{GITHUB_REPO_NAME}"

    # 1) Prepare HF datasets
    hf_namespace = hf_get_namespace(hf_token)
    hf_urls = hf_prepare_datasets(files_folder, hf_token, hf_namespace, github_owner)

    # 2) Fork the repo
    await fork_repo(SOURCE_REPO_NAME, str(github_repo_full), fork_default_branch_only=True, readonly=False)

    # 2.5) Update README.md
    update_readme(github_repo_full, github_owner, hf_namespace)

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

    # 3) Create issue on the new independent repo
    issue_title = "License info. needed"
    issue_body = "Thanks for sharing this project! Could you provide license info. for Annoy-PyEdu-Rs-Raw and Annoy-PyEdu-Rs? thanks!"
    issue = github_create_issue(github_token, github_repo_full, issue_title, issue_body)

    # wait for a while to ensure the repo being stable
    time.sleep(10)

    # Get latest commit hash
    latest_commit_hash = github_get_latest_commit(github_token, github_repo_full)

    state_info = {
        "github_repo": github_repo_full,
        "issue_number": issue.get("number"),
        "issue_url": issue.get("html_url"),
        "hf_datasets": hf_urls,
        "latest_commit_hash": latest_commit_hash,
    }

    # Save to groundtruth_workspace
    groundtruth_workspace = Path(os.path.dirname(__file__)) / ".." / "groundtruth_workspace"
    groundtruth_workspace.mkdir(exist_ok=True)
    with open(groundtruth_workspace / "task_state.json", "w", encoding="utf-8") as f:
        json.dump(state_info, f, ensure_ascii=False, indent=2)

    # Save hf token to agent_workspace/.hf_token
    with open(os.path.join(args.agent_workspace, ".hf_token"), "w", encoding="utf-8") as f:
        f.write(hf_token)

if __name__ == "__main__":
    asyncio.run(main())