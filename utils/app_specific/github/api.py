"""
Core GitHub API operations for common tasks.
"""
import requests
from typing import Dict, Any
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    AsyncRetrying
)
from requests.exceptions import RequestException, Timeout, ConnectionError


GITHUB_API = "https://api.github.com"
DEFAULT_TIMEOUT = 500  # Default timeout for all HTTP requests in seconds

# Retry decorator for synchronous functions
# Retries up to 3 times with exponential backoff starting at 2 seconds, max wait 10 seconds
github_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    retry=retry_if_exception_type((RequestException, Timeout, ConnectionError)),
    reraise=True
)

# Async retry configuration for async functions
github_retry_async = AsyncRetrying(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    retry=retry_if_exception_type((RequestException, Timeout, ConnectionError)),
    reraise=True
)


def github_headers(token: str) -> Dict[str, str]:
    """Generate standard GitHub API headers."""
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }


@github_retry
def github_get_repo(token: str, owner: str, repo_name: str) -> Dict[str, Any]:
    """Get a repository."""
    url = f"{GITHUB_API}/repos/{owner}/{repo_name}"
    r = requests.get(url, headers=github_headers(token), timeout=DEFAULT_TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"Failed to fetch repo {owner}/{repo_name}: {r.status_code} {r.text}")
    return r.json()

@github_retry
def github_get_login(token: str) -> str:
    """Get the authenticated user's login name."""
    url = f"{GITHUB_API}/user"
    r = requests.get(url, headers=github_headers(token), timeout=DEFAULT_TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"Failed to fetch GitHub user: {r.status_code} {r.text}")
    return r.json().get("login")


@github_retry
def github_delete_repo(token: str, owner: str, repo_name: str,enable_not_found:bool=True) -> None:
    """Delete a GitHub repository."""
    url = f"{GITHUB_API}/repos/{owner}/{repo_name}"
    r = requests.delete(url, headers=github_headers(token), timeout=DEFAULT_TIMEOUT)
    if r.status_code not in (204,):
        if enable_not_found and r.status_code == 404:
            return
        raise RuntimeError(f"Failed to delete repo {owner}/{repo_name}: {r.status_code} {r.text}")


@github_retry
def github_create_user_repo(token: str, name: str, private: bool = False) -> Dict[str, Any]:
    """Create a new repository under the authenticated user's account."""
    url = f"{GITHUB_API}/user/repos"
    payload = {
        "name": name,
        "private": private,
        "has_issues": True,
        "auto_init": False,
    }
    r = requests.post(url, headers=github_headers(token), json=payload, timeout=DEFAULT_TIMEOUT)
    if r.status_code not in (201,):
        raise RuntimeError(f"Failed to create repo {name}: {r.status_code} {r.text}")
    return r.json()


@github_retry
def github_enable_issues(token: str, full_name: str) -> None:
    """Enable issues for a repository."""
    url = f"{GITHUB_API}/repos/{full_name}"
    payload = {"has_issues": True}
    r = requests.patch(url, headers=github_headers(token), json=payload, timeout=DEFAULT_TIMEOUT)
    if r.status_code not in (200,):
        raise RuntimeError(f"Failed to enable issues: {r.status_code} {r.text}")


@github_retry
def github_create_issue(token: str, full_name: str, title: str, body: str) -> Dict[str, Any]:
    """Create an issue in a repository."""
    # First ensure issues are enabled
    github_enable_issues(token, full_name)

    url = f"{GITHUB_API}/repos/{full_name}/issues"
    payload = {"title": title, "body": body}
    r = requests.post(url, headers=github_headers(token), json=payload, timeout=DEFAULT_TIMEOUT)
    if r.status_code not in (201,):
        raise RuntimeError(f"Failed to create issue: {r.status_code} {r.text}")
    return r.json()


@github_retry
def github_get_repo_info(token: str, full_name: str) -> Dict[str, Any]:
    """Get repository information."""
    url = f"{GITHUB_API}/repos/{full_name}"
    r = requests.get(url, headers=github_headers(token), timeout=DEFAULT_TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"Failed to fetch repo info {full_name}: {r.status_code} {r.text}")
    return r.json()


@github_retry
def github_get_latest_commit(token: str, full_name: str) -> str:
    """Get the latest commit SHA for a repository."""
    url = f"{GITHUB_API}/repos/{full_name}/commits"
    r = requests.get(url, headers=github_headers(token), params={"per_page": 1}, timeout=DEFAULT_TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"Failed to fetch commits: {r.status_code} {r.text}")
    commits = r.json()
    if not commits:
        raise RuntimeError(f"No commits found in {full_name}")
    return commits[0]["sha"]


@github_retry
def github_get_issue(token: str, full_name: str, issue_number: int) -> Dict[str, Any]:
    """Get issue information."""
    url = f"{GITHUB_API}/repos/{full_name}/issues/{issue_number}"
    r = requests.get(url, headers=github_headers(token), timeout=DEFAULT_TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"Failed to fetch issue: {r.status_code} {r.text}")
    return r.json()


@github_retry
def github_get_issue_comments(token: str, full_name: str, issue_number: int) -> list:
    """Get all comments for an issue."""
    url = f"{GITHUB_API}/repos/{full_name}/issues/{issue_number}/comments"
    r = requests.get(url, headers=github_headers(token), params={"per_page": 100}, timeout=DEFAULT_TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"Failed to fetch comments: {r.status_code} {r.text}")
    return r.json()