"""
Git operations for GitHub repositories.
"""
import os
import shutil
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from utils.general.helper import run_command

# Async retry decorator for git operations
# Retries on generic Exception since git commands may fail for various reasons
git_retry_async = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True
)


def git_auth_url(token: str, full_name: str) -> str:
    """Generate authenticated Git URL."""
    return f"https://x-access-token:{token}@github.com/{full_name}.git"


@git_retry_async
async def git_mirror_clone(token: str, full_name: str, local_dir: str) -> None:
    """Clone a repository as a mirror."""
    src_url = git_auth_url(token, full_name)
    if os.path.exists(local_dir):
        shutil.rmtree(local_dir)
    cmd = f"git clone --mirror {src_url} {local_dir}"
    await run_command(cmd, debug=False, show_output=False)


@git_retry_async
async def git_mirror_push(token: str, local_dir: str, dst_full_name: str) -> None:
    """Push a mirror to a destination repository."""
    dst_url = git_auth_url(token, dst_full_name)
    cmd = f"git -C {local_dir} push --mirror {dst_url}"
    await run_command(cmd, debug=False, show_output=False)