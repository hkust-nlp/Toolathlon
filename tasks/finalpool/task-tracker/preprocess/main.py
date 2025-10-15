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
from utils.general.helper import run_command, print_color, fork_repo

READONLY = False
FORKING_LIST = [
    # source repo, fork_default_branch_only
    ("Toolathlon-Archive/BenchTasksCollv3", False)
]
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


    real_forking_list = []
    for source_repo, fork_default_branch_only in FORKING_LIST:
        target_repo = source_repo.split("/")[1]
        real_forking_list.append((source_repo, target_repo, fork_default_branch_only, READONLY))

    tasks = [fork_repo(source_repo, target_repo, fork_default_branch_only, readonly) for source_repo, target_repo, fork_default_branch_only, readonly in real_forking_list]
    await asyncio.gather(*tasks)

    print_color("Forking all repos successfully!","green")

if __name__ == "__main__":
    asyncio.run(main())