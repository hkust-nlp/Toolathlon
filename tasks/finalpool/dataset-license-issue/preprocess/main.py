import os
import json
import shutil
import asyncio
import base64
from argparse import ArgumentParser
from pathlib import Path
import time

import requests

from utils.general.helper import fork_repo
from configs.token_key_session import all_token_key_session


GITHUB_API = "https://api.github.com"
GITHUB_REPO_NAME = "Annoy-DataSync"
SOURCE_REPO_NAME = f"lockon-n/{GITHUB_REPO_NAME}"
HF_DATASET_REASONING_SUFFIX = "Annoy-PyEdu-Rs" 
HF_DATASET_RAW_SUFFIX = "Annoy-PyEdu-Rs-Raw"

def _github_headers(token: str):
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

def github_get_login(token: str) -> str:
    url = f"{GITHUB_API}/user"
    r = requests.get(url, headers=_github_headers(token))
    if r.status_code != 200:
        raise RuntimeError(f"Failed to fetch GitHub user: {r.status_code} {r.text}")
    return r.json().get("login")

def github_create_issue(token: str, full_name: str, title: str, body: str) -> dict:
    url = f"{GITHUB_API}/repos/{full_name}"
    payload = {"has_issues": True}
    r = requests.patch(url, headers=_github_headers(token), json=payload)
    if r.status_code not in (200,):
        raise RuntimeError(f"Failed to enable issues: {r.status_code} {r.text}")

    print(f"Enabled issues for {full_name}")

    url = f"{GITHUB_API}/repos/{full_name}/issues"
    print(url)
    payload = {"title": title, "body": body}
    r = requests.post(url, headers=_github_headers(token), json=payload)
    if r.status_code not in (201,):
        raise RuntimeError(f"Failed to create issue: {r.status_code} {r.text}")
    print(f"Created issue {title} for {full_name}")
    return r.json()

def hf_prepare_datasets(files_folder: Path, hf_token: str, namespace: str, github_namespace: str) -> dict:
    from huggingface_hub import HfApi
    api = HfApi()

    ds_reasoning = f"{namespace}/{HF_DATASET_REASONING_SUFFIX}"
    ds_raw = f"{namespace}/{HF_DATASET_RAW_SUFFIX}"

    # Delete if exists
    for rid in [ds_reasoning, ds_raw]:
        try:
            api.delete_repo(repo_id=rid, repo_type="dataset", token=hf_token)
            print(f"Deleted repo {rid}")
        except Exception:
            print("Not found, skip deleting!")
            pass

    # Create repos
    api.create_repo(repo_id=ds_reasoning, repo_type="dataset", private=False, token=hf_token)
    api.create_repo(repo_id=ds_raw, repo_type="dataset", private=False, token=hf_token)

    # Upload README
    reasoning_readme = files_folder / "hf-reasoning" / "README.md"
    raw_readme = files_folder / "hf-raw" / "README.md"

    # 替换这两个文件里的{namespace}为namespace
    with open(reasoning_readme, "r", encoding="utf-8") as f:
        txt = f.read()
        reasoning_readme_txt = txt.replace("{hf_namespace}", namespace).replace("{github_namespace}", github_namespace)
        # 写入一个临时文件
        tmp_reasoning_readme = files_folder / "hf-reasoning" / "README.md.tmp"
        with open(tmp_reasoning_readme, "w", encoding="utf-8") as f:
            f.write(reasoning_readme_txt)

    with open(raw_readme, "r", encoding="utf-8") as f:
        txt = f.read()
        raw_readme_txt = txt.replace("{hf_namespace}", namespace).replace("{github_namespace}", github_namespace)
        # 写入一个临时文件
        tmp_raw_readme = files_folder / "hf-raw" / "README.md.tmp"
        with open(tmp_raw_readme, "w", encoding="utf-8") as f:
            f.write(raw_readme_txt)

    api.upload_file(
        path_or_fileobj=str(tmp_reasoning_readme),
        path_in_repo="README.md",
        repo_id=ds_reasoning,
        repo_type="dataset",
        token=hf_token,
    )
    api.upload_file(
        path_or_fileobj=str(tmp_raw_readme),
        path_in_repo="README.md",
        repo_id=ds_raw,
        repo_type="dataset",
        token=hf_token,
    )

    return {
        "reasoning": f"https://huggingface.co/datasets/{ds_reasoning}",
        "raw": f"https://huggingface.co/datasets/{ds_raw}",
    }

def update_readme(github_repo_full: str, github_owner: str, hf_namespace: str):
    token = all_token_key_session.github_token
    headers = _github_headers(token)

    # Resolve default branch
    repo_url = f"{GITHUB_API}/repos/{github_repo_full}"
    r_repo = requests.get(repo_url, headers=headers)
    if r_repo.status_code != 200:
        raise RuntimeError(f"Failed to fetch repo info {github_repo_full}: {r_repo.status_code} {r_repo.text}")
    default_branch = (r_repo.json() or {}).get("default_branch", "main")

    # Read current README.md at root via Contents API
    get_url = f"{GITHUB_API}/repos/{github_repo_full}/contents/README.md"
    r_get = requests.get(get_url, headers=headers, params={"ref": default_branch})
    if r_get.status_code != 200:
        print(f"README.md not found or cannot be fetched for {github_repo_full}: {r_get.status_code} {r_get.text}")
        return

    readme_info = r_get.json()
    readme_sha = readme_info.get("sha")
    readme_content_b64 = readme_info.get("content", "")

    try:
        current_text = base64.b64decode(readme_content_b64).decode("utf-8", errors="replace")
    except Exception:
        # Fallback in case of unexpected encoding/newlines
        current_text = base64.b64decode(readme_content_b64.encode("utf-8")).decode("utf-8", errors="replace")

    updated_text = (
        current_text.replace("{github_namespace}", github_owner).replace("{hf_namespace}", hf_namespace)
    )

    if updated_text == current_text:
        print(f"No README placeholders to update for {github_repo_full}")
        return

    new_content_b64 = base64.b64encode(updated_text.encode("utf-8")).decode("utf-8")

    put_url = f"{GITHUB_API}/repos/{github_repo_full}/contents/README.md"
    payload = {
        "message": "chore: update README placeholders for namespaces",
        "content": new_content_b64,
        "sha": readme_sha,
        "branch": default_branch,
    }
    r_put = requests.put(put_url, headers=headers, json=payload)
    if r_put.status_code not in (200, 201):
        raise RuntimeError(f"Failed to update README: {r_put.status_code} {r_put.text}")
    print(f"Updated README for {github_repo_full} on branch {default_branch}")

def github_delete_repo(token: str, owner: str, repo_name: str) -> None:
    url = f"{GITHUB_API}/repos/{owner}/{repo_name}"
    r = requests.delete(url, headers=_github_headers(token))
    if r.status_code not in (204,):
        raise RuntimeError(f"Failed to delete repo {owner}/{repo_name}: {r.status_code} {r.text}")
    print(f"Deleted repo {owner}/{repo_name}")

def github_create_user_repo(token: str, name: str, private: bool = False) -> dict:
    url = f"{GITHUB_API}/user/repos"
    payload = {
        "name": name,
        "private": private,
        "has_issues": True,
        "auto_init": False,
    }
    r = requests.post(url, headers=_github_headers(token), json=payload)
    if r.status_code not in (201,):
        raise RuntimeError(f"Failed to create repo {name}: {r.status_code} {r.text}")
    print(f"Created new repo {name}")
    return r.json()

def _git_auth_prefix(token: str) -> str:
    # Use x-access-token as username to avoid leaking real username in remote URL
    return f"https://x-access-token:{token}@github.com"

async def git_mirror_clone(token: str, full_name: str, workspace: str) -> str:
    """Clone a repository as a mirror into workspace and return local mirror path."""
    local_dir = os.path.join(workspace, f"{GITHUB_REPO_NAME}.git")
    if os.path.exists(local_dir):
        shutil.rmtree(local_dir)
    src_url = f"{_git_auth_prefix(token)}/{full_name}.git"
    cmd = f"git clone --mirror {src_url} {local_dir}"
    from utils.general.helper import run_command as _run
    await _run(cmd, debug=False, show_output=False)
    print(f"Mirrored {full_name} to {local_dir}")
    return local_dir

async def git_mirror_push(token: str, local_mirror_dir: str, dst_full_name: str) -> None:
    dst_url = f"{_git_auth_prefix(token)}/{dst_full_name}.git"
    cmd = f"git -C {local_mirror_dir} push --mirror {dst_url}"
    from utils.general.helper import run_command as _run
    await _run(cmd, debug=False, show_output=False)
    print(f"Pushed mirror to {dst_full_name}")

async def main():
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--token_path", required=False, default="configs/token_key_session.py")
    parser.add_argument("--launch_time", required=False)
    args = parser.parse_args()

    files_folder = os.path.join(os.path.dirname(__file__), "..","files")
    files_folder = Path(files_folder)

    github_token = all_token_key_session.github_token
    hf_token = all_token_key_session.huggingface_token

    # Resolve dynamic namespaces/logins
    github_owner = github_get_login(github_token)
    if not github_owner:
        raise RuntimeError("Failed to resolve GitHub login")
    github_repo_full = f"{github_owner}/{GITHUB_REPO_NAME}"

    # 1) Prepare HF datasets
    try:
        from huggingface_hub import whoami
        hf_info = whoami(token=hf_token)
        hf_namespace = hf_info.get("name") or hf_info.get("orgs")[0]["name"]
    except Exception:
        raise RuntimeError("Failed to determine HuggingFace namespace from token")
    hf_urls = hf_prepare_datasets(files_folder, hf_token, hf_namespace, github_owner)

    # 2) Fork the repo
    await fork_repo(SOURCE_REPO_NAME, str(github_repo_full), fork_default_branch_only=True, readonly=False)

    # 2.5) Update README.md {github_namespace} -> github_owner, {hf_namespace} -> hf_namespace
    update_readme(github_repo_full, github_owner, hf_namespace)

    # 2.6) Mirror clone forked repo locally
    tmpdir = os.path.join(os.path.dirname(__file__), "..","tmp")
    if not os.path.exists(tmpdir):
        os.makedirs(tmpdir)
    local_mirror_dir = await git_mirror_clone(github_token, github_repo_full, tmpdir)

    # 2.7) Delete the forked repo to free the name
    github_delete_repo(github_token, github_owner, GITHUB_REPO_NAME)

    # wait a bit for deletion to propagate
    time.sleep(2)

    # 2.8) Create a new independent repo with the same name
    github_create_user_repo(github_token, GITHUB_REPO_NAME, private=False)

    # 2.9) Push mirror to the new repo (same full name)
    await git_mirror_push(github_token, local_mirror_dir, github_repo_full)

    # 删掉tmpdir
    shutil.rmtree(tmpdir)

    # 3) Create issue on the new independent repo
    issue_title = "License info. needed"
    issue_body = "Thanks for sharing this project! Could you provide license info. for Annoy-PyEdu-Rs-Raw and Annoy-PyEdu-Rs? thanks!"
    issue = github_create_issue(github_token, github_repo_full, issue_title, issue_body)

    # Get latest commit hash
    commits_url = f"{GITHUB_API}/repos/{github_repo_full}/commits"
    r_commits = requests.get(commits_url, headers=_github_headers(github_token), params={"per_page": 1})
    if r_commits.status_code != 200:
        raise RuntimeError(f"Failed to fetch commits: {r_commits.status_code} {r_commits.text}")
    latest_commit_hash = r_commits.json()[0]["sha"]

    state_info = {
        "github_repo": github_repo_full,
        "issue_number": issue.get("number"),
        "issue_url": issue.get("html_url"),
        "hf_datasets": hf_urls,
        "latest_commit_hash": latest_commit_hash,
    }

    # save to groundtruth_workspace
    groundtruth_workspace = os.path.join(os.path.dirname(__file__), "..", "groundtruth_workspace")
    if not os.path.exists(groundtruth_workspace):
        os.makedirs(groundtruth_workspace)
    with open(os.path.join(groundtruth_workspace, "task_state.json"), "w", encoding="utf-8") as f:
        json.dump(state_info, f, ensure_ascii=False, indent=2)

    
    # save hftoken to agent_workspace/.hf_token
    with open(os.path.join(args.agent_workspace, ".hf_token"), "w", encoding="utf-8") as f:
        f.write(hf_token)

if __name__ == "__main__":
    asyncio.run(main())


