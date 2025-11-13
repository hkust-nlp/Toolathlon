"""
High-level repository operations combining API and Git functionality.
"""
import base64
import requests
from .api import github_headers, GITHUB_API, DEFAULT_TIMEOUT, github_retry


@github_retry
def update_file_content(token: str, repo_full_name: str, file_path: str,
                       replacements: dict, commit_message: str = "Update file content") -> None:
    """
    Update a file in repository by replacing placeholders.

    Args:
        token: GitHub token
        repo_full_name: Repository full name (owner/repo)
        file_path: Path to file in repo (e.g., "README.md")
        replacements: Dict mapping placeholder -> replacement value
        commit_message: Commit message for the update
    """
    headers = github_headers(token)

    # Get repository info to find default branch
    repo_url = f"{GITHUB_API}/repos/{repo_full_name}"
    r_repo = requests.get(repo_url, headers=headers, timeout=DEFAULT_TIMEOUT)
    if r_repo.status_code != 200:
        raise RuntimeError(f"Failed to fetch repo info {repo_full_name}: {r_repo.status_code} {r_repo.text}")
    default_branch = (r_repo.json() or {}).get("default_branch", "main")

    # Get current file content
    get_url = f"{GITHUB_API}/repos/{repo_full_name}/contents/{file_path}"
    r_get = requests.get(get_url, headers=headers, params={"ref": default_branch}, timeout=DEFAULT_TIMEOUT)
    if r_get.status_code != 200:
        print(f"{file_path} not found or cannot be fetched for {repo_full_name}: {r_get.status_code} {r_get.text}")
        return

    file_info = r_get.json()
    file_sha = file_info.get("sha")
    file_content_b64 = file_info.get("content", "")

    try:
        current_text = base64.b64decode(file_content_b64).decode("utf-8", errors="replace")
    except Exception:
        # Fallback in case of unexpected encoding/newlines
        current_text = base64.b64decode(file_content_b64.encode("utf-8")).decode("utf-8", errors="replace")

    # Apply all replacements
    updated_text = current_text
    for placeholder, replacement in replacements.items():
        updated_text = updated_text.replace(placeholder, replacement)

    if updated_text == current_text:
        print(f"No changes needed for {file_path} in {repo_full_name}")
        return

    new_content_b64 = base64.b64encode(updated_text.encode("utf-8")).decode("utf-8")

    # Update the file
    put_url = f"{GITHUB_API}/repos/{repo_full_name}/contents/{file_path}"
    payload = {
        "message": commit_message,
        "content": new_content_b64,
        "sha": file_sha,
        "branch": default_branch,
    }
    r_put = requests.put(put_url, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT)
    if r_put.status_code not in (200, 201):
        raise RuntimeError(f"Failed to update {file_path}: {r_put.status_code} {r_put.text}")
    print(f"Updated {file_path} for {repo_full_name} on branch {default_branch}")