"""
Git operations for GitHub repositories.
"""
import os
import shutil
import asyncio
from utils.general.helper import run_command


def git_auth_url(token: str, full_name: str) -> str:
    """Generate authenticated Git URL."""
    return f"https://x-access-token:{token}@github.com/{full_name}.git"


async def git_mirror_clone(token: str, full_name: str, local_dir: str) -> None:
    """Clone a repository as a mirror."""
    src_url = git_auth_url(token, full_name)
    if os.path.exists(local_dir):
        shutil.rmtree(local_dir)
    cmd = f"git clone --mirror {src_url} {local_dir}"
    await run_command(cmd, debug=False, show_output=False)


async def git_mirror_push(token: str, local_dir: str, dst_full_name: str) -> None:
    """Push a mirror to a destination repository."""
    dst_url = git_auth_url(token, dst_full_name)
    cmd = f"git -C {local_dir} push --mirror {dst_url}"
    await run_command(cmd, debug=False, show_output=False)