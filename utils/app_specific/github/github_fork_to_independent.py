import os
import shutil
import asyncio
import time
from argparse import ArgumentParser

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from requests.exceptions import RequestException, Timeout, ConnectionError

from utils.general.helper import run_command, print_color
from configs.token_key_session import all_token_key_session
from utils.app_specific.github.api import DEFAULT_TIMEOUT

GITHUB_API = "https://api.github.com"

# Retry decorator for synchronous network operations
github_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    retry=retry_if_exception_type((RequestException, Timeout, ConnectionError)),
    reraise=True
)

# Async retry decorator for git operations
git_retry_async = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True
)


def _github_headers(token: str):
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


@github_retry
def github_get_login(token: str) -> str:
    url = f"{GITHUB_API}/user"
    r = requests.get(url, headers=_github_headers(token), timeout=DEFAULT_TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"Failed to fetch GitHub user: {r.status_code} {r.text}")
    return r.json().get("login")


@github_retry
def github_delete_repo(token: str, owner: str, repo_name: str) -> None:
    url = f"{GITHUB_API}/repos/{owner}/{repo_name}"
    r = requests.delete(url, headers=_github_headers(token), timeout=DEFAULT_TIMEOUT)
    if r.status_code not in (204,):
        raise RuntimeError(f"Failed to delete repo {owner}/{repo_name}: {r.status_code} {r.text}")
    print_color(f"Deleted repo {owner}/{repo_name}", "green")


@github_retry
def wait_until_repo_gone(token: str, owner: str, repo_name: str, timeout_sec: int = 30, interval_sec: float = 1.0) -> None:
    url = f"{GITHUB_API}/repos/{owner}/{repo_name}"
    start = time.time()
    while True:
        r = requests.get(url, headers=_github_headers(token), timeout=DEFAULT_TIMEOUT)
        if r.status_code == 404:
            return
        if time.time() - start > timeout_sec:
            raise TimeoutError(f"Timed out waiting for {owner}/{repo_name} to be deleted")
        time.sleep(interval_sec)


@github_retry
def github_create_user_repo(token: str, name: str, private: bool = False) -> dict:
    url = f"{GITHUB_API}/user/repos"
    payload = {
        "name": name,
        "private": private,
        "has_issues": True,
        "auto_init": False,
    }
    r = requests.post(url, headers=_github_headers(token), json=payload, timeout=DEFAULT_TIMEOUT)
    if r.status_code not in (201,):
        raise RuntimeError(f"Failed to create repo {name}: {r.status_code} {r.text}")
    print_color(f"Created new repo {name}", "green")
    return r.json()


def _git_auth_url(token: str, full_name: str) -> str:
    return f"https://x-access-token:{token}@github.com/{full_name}.git"


@git_retry_async
async def git_mirror_clone(token: str, full_name: str, local_dir: str) -> None:
    src_url = _git_auth_url(token, full_name)
    if os.path.exists(local_dir):
        shutil.rmtree(local_dir)
    cmd = f"git clone --mirror {src_url} {local_dir}"

    await run_command(cmd, debug=False, show_output=False)
    print_color(f"Mirrored {full_name} -> {local_dir}", "cyan")


@git_retry_async
async def git_mirror_push(token: str, local_dir: str, dst_full_name: str) -> None:
    dst_url = _git_auth_url(token, dst_full_name)
    cmd = f"git -C {local_dir} push --mirror {dst_url}"
    await run_command(cmd, debug=False, show_output=False)
    print_color(f"Pushed mirror to {dst_full_name}", "cyan")


async def main():
    parser = ArgumentParser()
    parser.add_argument("--repo_name", required=True, help="The forked repository name under your account")
    parser.add_argument("--tmp_dir", required=True, help="Temporary directory to hold the mirror clone")
    parser.add_argument("--private", action="store_true", help="Create the new repo as private")
    args = parser.parse_args()

    token = all_token_key_session.github_token
    repo_name = args.repo_name
    tmp_dir = args.tmp_dir
    private_flag = bool(args.private)

    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir, exist_ok=True)

    owner = github_get_login(token)
    if not owner:
        raise RuntimeError("Failed to resolve GitHub login")

    full_name = f"{owner}/{repo_name}"
    local_mirror_dir = os.path.join(tmp_dir, f"{repo_name}.git")

    # 1) Mirror clone fork
    await git_mirror_clone(token, full_name, local_mirror_dir)

    # 2) Delete forked repo
    github_delete_repo(token, owner, repo_name)
    wait_until_repo_gone(token, owner, repo_name)

    # 3) Create new independent repo with the same name
    github_create_user_repo(token, repo_name, private=private_flag)

    # 4) Push mirror to new repo
    await git_mirror_push(token, local_mirror_dir, full_name)

    # 5) Cleanup local mirror
    try:
        shutil.rmtree(local_mirror_dir)
    except Exception:
        pass

    # 6) Done
    print_color(f"Converted fork to independent repo: {full_name}", "green")


if __name__ == "__main__":
    asyncio.run(main())


