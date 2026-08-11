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


def _raise_on_git_failure(operation: str, token: str, stderr: str, returncode: int) -> None:
    if returncode != 0:
        # git's stderr echoes the remote URL, which embeds the token
        sanitized = stderr.replace(token, "***") if token else stderr
        raise RuntimeError(f"{operation} exited with code {returncode}: {sanitized}")


@git_retry_async
async def git_mirror_clone(token: str, full_name: str, local_dir: str) -> None:
    """Clone a repository as a mirror."""
    src_url = git_auth_url(token, full_name)
    if os.path.exists(local_dir):
        shutil.rmtree(local_dir)
    cmd = f"git clone --mirror {src_url} {local_dir}"
    _, stderr, returncode = await run_command(cmd, debug=False, show_output=False)
    _raise_on_git_failure(f"git clone --mirror of {full_name}", token, stderr, returncode)


@git_retry_async
async def git_mirror_push(token: str, local_dir: str, dst_full_name: str) -> None:
    """Push all branches and tags to a destination repository.

    Deliberately not ``push --mirror``: a mirror clone carries GitHub's
    read-only PR refs (refs/pull/*), which GitHub rejects on push ("deny
    updating a hidden ref"), failing the whole push whenever the source
    repo has pull requests.
    """
    dst_url = git_auth_url(token, dst_full_name)
    cmd = (
        f"git -C {local_dir} push --force {dst_url} "
        f"'refs/heads/*:refs/heads/*' 'refs/tags/*:refs/tags/*'"
    )
    _, stderr, returncode = await run_command(cmd, debug=False, show_output=False)
    _raise_on_git_failure(f"git push to {dst_full_name}", token, stderr, returncode)