import requests
import base64
import traceback
import time
from .api import github_headers, GITHUB_API, DEFAULT_TIMEOUT, github_retry


@github_retry
def get_user_name(token):
    """
    Get GitHub user name.

    :param token: GitHub access token
    :return: User name
    """
    url = f"{GITHUB_API}/user"
    r = requests.get(url, headers=github_headers(token), timeout=DEFAULT_TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"Failed to fetch GitHub user: {r.status_code} {r.text}")
    return r.json().get("login")


@github_retry
def read_file_content(token, repo_name, file_path, branch="master"):
    """
    Read the content of a file in a specified repository.

    :param token: GitHub access token
    :param repo_name: Repository name, format as "username/repo_name"
    :param file_path: Path to the file to read
    :param branch: Branch name, default is "master"
    :return: File content
    """
    url = f"{GITHUB_API}/repos/{repo_name}/contents/{file_path}"
    params = {"ref": branch}
    r = requests.get(url, headers=github_headers(token), params=params, timeout=DEFAULT_TIMEOUT)

    try:
        if r.status_code == 404:
            print(f"File {file_path} does not exist")
            return None
        elif r.status_code != 200:
            print(f"Error: HTTP {r.status_code} - {r.text}")
            return None

        file_info = r.json()
        content_b64 = file_info.get("content", "")

        try:
            return base64.b64decode(content_b64).decode('utf-8')
        except UnicodeDecodeError:
            print(f"File {file_path} is a binary file, cannot be decoded directly to UTF-8")
            # If binary content is needed
            return base64.b64decode(content_b64)
    except Exception as e:
        print(f"Error: {traceback.format_exc()}")
        return None


@github_retry
def roll_back_commit(token, repo_name, commit_sha, branch="master"):
    """
    Roll back a branch in a specified repository to a specified commit.

    :param token: GitHub access token
    :param repo_name: Repository name, format as "username/repo_name"
    :param branch_name: Branch name
    :param commit_sha: SHA of the commit to roll back to
    """
    url = f"{GITHUB_API}/repos/{repo_name}/git/refs/heads/{branch}"
    payload = {
        "sha": commit_sha,
        "force": True
    }

    r = requests.patch(url, headers=github_headers(token), json=payload, timeout=DEFAULT_TIMEOUT)
    if r.status_code == 200:
        print(f"Branch {branch} has been rolled back to commit: {commit_sha}")
    else:
        raise RuntimeError(f"Failed to rollback branch {branch}: {r.status_code} {r.text}")


@github_retry
def create_file(token, repo_name, file_path, commit_message, content, branch="master"):
    """
    Create a new file in a specified repository.

    :param token: GitHub access token
    :param repo_name: Repository name, format as "username/repo_name"
    :param file_path: Path to the file to create
    :param commit_message: Commit message
    :param content: File content
    :param branch: Branch name, default is "master"
    """
    url = f"{GITHUB_API}/repos/{repo_name}/contents/{file_path}"

    # Convert content to base64 if it's a string
    if isinstance(content, str):
        content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    else:
        content_b64 = base64.b64encode(content).decode('utf-8')

    payload = {
        "message": commit_message,
        "content": content_b64,
        "branch": branch
    }

    r = requests.put(url, headers=github_headers(token), json=payload, timeout=DEFAULT_TIMEOUT)
    if r.status_code in (200, 201):
        print(f"File {file_path} has been created on branch {branch}.")
    else:
        raise RuntimeError(f"Failed to create file {file_path}: {r.status_code} {r.text}")


@github_retry
def update_file(token, repo_name, file_path, commit_message, content, branch="master"):
    """
    Update a file in a specified repository.

    :param token: GitHub access token
    :param repo_name: Repository name, format as "username/repo_name"
    :param file_path: Path to the file to update
    :param commit_message: Commit message
    :param content: New content of the file
    :param branch: Branch name, default is "master"
    """
    # First get the current file to get its SHA
    get_url = f"{GITHUB_API}/repos/{repo_name}/contents/{file_path}"
    params = {"ref": branch}
    r_get = requests.get(get_url, headers=github_headers(token), params=params, timeout=DEFAULT_TIMEOUT)

    if r_get.status_code != 200:
        raise RuntimeError(f"Failed to get file {file_path}: {r_get.status_code} {r_get.text}")

    file_info = r_get.json()
    file_sha = file_info.get("sha")

    # Convert content to base64 if it's a string
    if isinstance(content, str):
        content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    else:
        content_b64 = base64.b64encode(content).decode('utf-8')

    put_url = f"{GITHUB_API}/repos/{repo_name}/contents/{file_path}"
    payload = {
        "message": commit_message,
        "content": content_b64,
        "sha": file_sha,
        "branch": branch
    }

    r = requests.put(put_url, headers=github_headers(token), json=payload, timeout=DEFAULT_TIMEOUT)
    if r.status_code in (200, 201):
        print(f"File {file_path} has been updated on branch {branch}.")
    else:
        raise RuntimeError(f"Failed to update file {file_path}: {r.status_code} {r.text}")


@github_retry
def delete_folder_contents(token, repo_name, folder_path, branch="master"):
    """
    Delete all files in a specified folder in a specified repository.

    :param token: GitHub access token
    :param repo_name: Repository name, format as "username/repo_name"
    :param folder_path: Path to the folder to delete
    :param branch: Branch name, default is "master"
    """
    def _delete_contents_recursive(path):
        url = f"{GITHUB_API}/repos/{repo_name}/contents/{path}"
        params = {"ref": branch}
        r = requests.get(url, headers=github_headers(token), params=params, timeout=DEFAULT_TIMEOUT)

        if r.status_code == 404:
            print(f"Folder {path} does not exist")
            return
        elif r.status_code != 200:
            print(f"Error: {traceback.format_exc()}")
            return

        contents = r.json()
        if not isinstance(contents, list):
            contents = [contents]

        for item in contents:
            if item["type"] == "dir":
                # Recursively delete directory contents
                _delete_contents_recursive(item["path"])
            else:
                # Delete file
                delete_url = f"{GITHUB_API}/repos/{repo_name}/contents/{item['path']}"
                delete_payload = {
                    "message": f"Delete {item['path']}",
                    "sha": item["sha"],
                    "branch": branch
                }
                delete_r = requests.delete(delete_url, headers=github_headers(token), json=delete_payload, timeout=DEFAULT_TIMEOUT)
                if delete_r.status_code == 200:
                    print(f"Deleted: {item['path']}")
                else:
                    print(f"Failed to delete: {item['path']} - {delete_r.status_code} {delete_r.text}")

    try:
        _delete_contents_recursive(folder_path)
        print(f"All files in folder {folder_path} have been deleted")
    except Exception as e:
        print(f"Error: {traceback.format_exc()}")


@github_retry
def get_latest_commit_sha(token, repo_name, branch="master"):
    """
    Get the latest commit SHA of a specified branch.

    :param token: GitHub access token
    :param repo_name: Repository name, format as "username/repo_name"
    :param branch: Branch name, default is "master"
    :return: SHA of the latest commit
    """
    url = f"{GITHUB_API}/repos/{repo_name}/branches/{branch}"
    r = requests.get(url, headers=github_headers(token), timeout=DEFAULT_TIMEOUT)

    if r.status_code != 200:
        raise RuntimeError(f"Failed to get branch {branch}: {r.status_code} {r.text}")

    branch_info = r.json()
    return branch_info["commit"]["sha"]


@github_retry
def get_modified_files_between_commits(token, repo_name, old_sha, new_sha):
    """
    Get the list of files modified between two commits.

    :param token: GitHub access token
    :param repo_name: Repository name, format as "username/repo_name"
    :param old_sha: SHA of the old commit
    :param new_sha: SHA of the new commit
    :return: List of modified files
    """
    url = f"{GITHUB_API}/repos/{repo_name}/compare/{old_sha}...{new_sha}"

    try:
        r = requests.get(url, headers=github_headers(token), timeout=DEFAULT_TIMEOUT)
        if r.status_code == 404:
            print("One or more commits do not exist")
            return None
        elif r.status_code == 403:
            print("Permission denied or API rate limit exceeded")
            return None
        elif r.status_code != 200:
            print(f"Error: HTTP {r.status_code} - {r.text}")
            return None

        comparison = r.json()
        return comparison.get("files", [])
    except Exception as e:
        print(f"Error: {e}")
        return None


@github_retry
def check_repo_exists(token, repo_name):
    """
    Check if a specified GitHub repository exists.

    :param token: GitHub access token
    :param repo_name: Repository name, format as "username/repo_name"
    :return: True if repository exists, False otherwise
    """
    url = f"{GITHUB_API}/repos/{repo_name}"

    try:
        r = requests.get(url, headers=github_headers(token), timeout=DEFAULT_TIMEOUT)
        if r.status_code == 200:
            return True
        elif r.status_code == 404:
            return False
        else:
            print(f"Error: {traceback.format_exc()}")
            return False
    except Exception as e:
        print(f"Error: {traceback.format_exc()}")
        return False


@github_retry
def fork_repo(token, source_repo_name, new_repo_name=""):
    """
    Fork a repository to the current authenticated user's account, and optionally rename it.

    :param token: GitHub personal access token (Personal Access Token).
    :param source_repo_name: Full name of the source repository, format as "owner/repo".
    :param new_repo_name: New name for the repository after forking (optional). If left empty, the original repository name will be used.
    :return: Dictionary of the final created repository information (similar to PyGithub repository object attributes).
    """
    try:
        # Fork the repository
        fork_url = f"{GITHUB_API}/repos/{source_repo_name}/forks"
        fork_data = {}
        if new_repo_name:
            fork_data["name"] = new_repo_name

        r = requests.post(fork_url, headers=github_headers(token), json=fork_data, timeout=DEFAULT_TIMEOUT)
        if r.status_code != 202:
            raise RuntimeError(f"Failed to fork repository: {r.status_code} {r.text}")

        forked_repo_info = r.json()

        # If we need to rename, update the repository
        if new_repo_name and new_repo_name != forked_repo_info.get("name"):
            # Wait a bit for the fork to be ready
            time.sleep(2)

            user_login = get_user_name(token)
            rename_url = f"{GITHUB_API}/repos/{user_login}/{forked_repo_info['name']}"
            rename_data = {"name": new_repo_name}

            rename_r = requests.patch(rename_url, headers=github_headers(token), json=rename_data, timeout=DEFAULT_TIMEOUT)
            if rename_r.status_code == 200:
                forked_repo_info = rename_r.json()

        print(f"✅ Successfully forked repository {source_repo_name} to {forked_repo_info['full_name']}")

        # Return an object that mimics PyGithub Repository object attributes
        class RepoObj:
            def __init__(self, repo_data):
                self.full_name = repo_data.get("full_name")
                self.name = repo_data.get("name")
                self.id = repo_data.get("id")
                self.clone_url = repo_data.get("clone_url")
                self.html_url = repo_data.get("html_url")

        return RepoObj(forked_repo_info)

    except Exception as e:
        print(f"❌ Fork operation failed: {e}")
        return None


@github_retry
def create_repo(token, repo_name, description="", private=False):
    """
    Create a GitHub repository for a paper, and initialize the basic project structure.

    :param token: GitHub access token
    :param repo_name: Repository name
    :param description: Repository description
    :param private: Whether to create a private repository, default is False
    :return: Created repository object
    """
    url = f"{GITHUB_API}/user/repos"
    payload = {
        "name": repo_name,
        "description": description,
        "private": private,
        "auto_init": True,
        "has_issues": True
    }

    r = requests.post(url, headers=github_headers(token), json=payload, timeout=DEFAULT_TIMEOUT)
    if r.status_code != 201:
        raise RuntimeError(f"Failed to create repo {repo_name}: {r.status_code} {r.text}")

    repo_data = r.json()
    print(f"Repository {repo_data['full_name']} has been created")

    # Return an object that mimics PyGithub Repository object attributes
    class RepoObj:
        def __init__(self, repo_data):
            self.full_name = repo_data.get("full_name")
            self.name = repo_data.get("name")
            self.id = repo_data.get("id")
            self.clone_url = repo_data.get("clone_url")
            self.html_url = repo_data.get("html_url")

    return RepoObj(repo_data)