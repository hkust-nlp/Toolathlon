import os
import json
import shutil
import asyncio
import time
from argparse import ArgumentParser
from pathlib import Path

from utils.general.helper import run_command, print_color
from configs.token_key_session import all_token_key_session
from utils.app_specific.github.api import (
    github_get_login, github_delete_repo,
    github_create_user_repo, github_get_repo
)
from utils.app_specific.github.git_ops import git_mirror_clone, git_mirror_push

READONLY = False
FORKING_LIST = [
    # (source repo, fork_default_branch_only)
    ("Toolathlon-Archive/BenchTasksCollv3", False)
]
NEEDED_SUBPAGE_NAME = "Task Tracker"

async def prepare_one_repo(source_repo, target_repo_name):
    """
    Prepare a repository by creating an independent copy (not a fork).
    Directly mirror clone from source and create as independent repo.
    """
    github_token = all_token_key_session.github_token
    github_user = github_get_login(github_token)
    target_repo_full = f"{github_user}/{target_repo_name}"

    print_color(f"Preparing {source_repo} → {target_repo_full}...", "cyan")

    # Check if target repo exists, delete it if so
    try:
        if github_get_repo(github_token, github_user, target_repo_name):
            print_color(f"Target repo {target_repo_full} exists, deleting it...", "yellow")
            github_delete_repo(github_token, github_user, target_repo_name)
            time.sleep(2)
    except RuntimeError as e:
        # 404 means repo doesn't exist, which is fine
        if "404" not in str(e):
            raise

    # Mirror clone source repo directly
    task_root_path = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    tmpdir = task_root_path / "tmp" / target_repo_name
    tmpdir.mkdir(parents=True, exist_ok=True)
    local_mirror_dir = tmpdir / f"{target_repo_name}.git"

    print_color(f"Mirror cloning {source_repo}...", "cyan")
    await git_mirror_clone(github_token, source_repo, str(local_mirror_dir))

    # Create new independent repo
    print_color(f"Creating new independent repo {target_repo_full}...", "cyan")
    github_create_user_repo(github_token, target_repo_name, private=False)

    # Push mirror to new repo
    print_color(f"Pushing mirror to {target_repo_full}...", "cyan")
    await git_mirror_push(github_token, str(local_mirror_dir), target_repo_full)

    # Cleanup
    shutil.rmtree(tmpdir)
    print_color(f"✓ Completed {target_repo_full}", "green")

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
    await run_command(command, debug=True, show_output=True, check=True)

    # Verify duplicated page id file exists
    if not duplicated_page_id_file.exists():
        raise FileNotFoundError(f"Duplicated page id file {duplicated_page_id_file} not found")

    with open(duplicated_page_id_file, "r") as f:
        duplicated_page_id = f.read().strip()
    print_color(f"Notion page duplicated with ID: {duplicated_page_id}", "green")

    # Prepare GitHub repositories
    for source_repo, fork_default_branch_only in FORKING_LIST:
        target_repo = source_repo.split("/")[1]
        await prepare_one_repo(source_repo, target_repo)

    print_color("All repos prepared successfully as independent repositories!", "green")

if __name__ == "__main__":
    asyncio.run(main())