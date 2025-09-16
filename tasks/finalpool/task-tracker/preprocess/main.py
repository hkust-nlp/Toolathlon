import os
import json
import shutil
import asyncio
import time
from argparse import ArgumentParser
from pathlib import Path

from utils.general.helper import fork_repo, run_command, print_color
from configs.token_key_session import all_token_key_session
from utils.app_specific.github.api import (
    github_get_login, github_delete_repo,
    github_create_user_repo, github_get_latest_commit
)
from utils.app_specific.github.git_ops import git_mirror_clone, git_mirror_push

GITHUB_REPO_NAME = "BenchTasksCollv2"
SOURCE_REPO_NAME = f"lockon-n/{GITHUB_REPO_NAME}"
NEEDED_SUBPAGE_NAME = "Task Tracker"

async def main():
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--token_path", required=False, default="configs/token_key_session.py")
    parser.add_argument("--launch_time", required=False)
    args = parser.parse_args()

    # Setup task directories
    task_root_path = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    files_dir = task_root_path / "files"
    files_dir.mkdir(exist_ok=True)

    # === NOTION PAGE DUPLICATION ===
    print_color("Starting Notion page duplication process...", "cyan")
    duplicated_page_id_file = files_dir / "duplicated_page_id.txt"

    # Delete the old duplicated page id file
    if duplicated_page_id_file.exists():
        duplicated_page_id_file.unlink()

    command = f"uv run -m utils.app_specific.notion.notion_remove_and_duplicate "
    command += f"--duplicated_page_id_file {duplicated_page_id_file} "
    command += f"--needed_subpage_name \"{NEEDED_SUBPAGE_NAME}\" "
    await run_command(command, debug=True, show_output=True)

    # Verify duplicated page id file exists
    if not duplicated_page_id_file.exists():
        raise FileNotFoundError(f"Duplicated page id file {duplicated_page_id_file} not found")

    with open(duplicated_page_id_file, "r") as f:
        duplicated_page_id = f.read().strip()
    print_color(f"Notion page duplicated with ID: {duplicated_page_id}", "green")

    # === GITHUB REPO SETUP ===
    print_color("Starting GitHub repository setup process...", "cyan")
    github_token = all_token_key_session.github_token

    # Resolve dynamic namespaces/logins
    github_owner = github_get_login(github_token)
    github_repo_full = f"{github_owner}/{GITHUB_REPO_NAME}"

    # 1) Fork the repo with all branches
    await fork_repo(SOURCE_REPO_NAME, str(github_repo_full), fork_default_branch_only=False, readonly=False)

    # 2) Mirror clone forked repo locally
    tmpdir = task_root_path / "tmp"
    tmpdir.mkdir(exist_ok=True)
    local_mirror_dir = tmpdir / f"{GITHUB_REPO_NAME}.git"
    await git_mirror_clone(github_token, github_repo_full, str(local_mirror_dir))

    # 3) Delete the forked repo to free the name
    github_delete_repo(github_token, github_owner, GITHUB_REPO_NAME)
    time.sleep(2)

    # 4) Create a new independent repo with the same name
    github_create_user_repo(github_token, GITHUB_REPO_NAME, private=False)

    # 5) Push mirror to the new repo with all branches
    await git_mirror_push(github_token, str(local_mirror_dir), github_repo_full)

    # Verify all branches were pushed correctly
    print_color(f"Verifying all branches were pushed to {github_repo_full}...", "cyan")

    # Wait a moment for GitHub to process
    time.sleep(3)

    # Cleanup
    shutil.rmtree(tmpdir)

    # Get latest commit hash
    latest_commit_hash = github_get_latest_commit(github_token, github_repo_full)
    print_color(f"GitHub repository setup completed: {github_repo_full}", "green")

    # === SAVE STATE INFO ===
    state_info = {
        "github_repo": github_repo_full,
        "source_repo": SOURCE_REPO_NAME,
        "latest_commit_hash": latest_commit_hash,
        "notion_page_id": duplicated_page_id,
        "notion_subpage_name": NEEDED_SUBPAGE_NAME,
        "preprocessing_completed": True
    }

    # Save to groundtruth_workspace
    groundtruth_workspace = task_root_path / "groundtruth_workspace"
    groundtruth_workspace.mkdir(exist_ok=True)
    with open(groundtruth_workspace / "task_state.json", "w", encoding="utf-8") as f:
        json.dump(state_info, f, ensure_ascii=False, indent=2)

    print_color(f"Successfully created independent repo: {github_repo_full}", "green")
    print_color(f"Successfully duplicated Notion page: {NEEDED_SUBPAGE_NAME} (ID: {duplicated_page_id})", "green")
    print_color(f"Task state saved to: {groundtruth_workspace / 'task_state.json'}", "green")

if __name__ == "__main__":
    asyncio.run(main())