import requests
import base64
import traceback
import time
from .api import github_headers, GITHUB_API


def get_user_name(token):
    """
    获取 GitHub 用户名。

    :param token: GitHub 访问令牌
    :return: 用户名
    """
    url = f"{GITHUB_API}/user"
    r = requests.get(url, headers=github_headers(token))
    if r.status_code != 200:
        raise RuntimeError(f"Failed to fetch GitHub user: {r.status_code} {r.text}")
    return r.json().get("login")


def read_file_content(token, repo_name, file_path, branch="master"):
    """
    读取指定仓库中的文件内容。

    :param token: GitHub 访问令牌
    :param repo_name: 仓库名称，格式为 "用户名/仓库名"
    :param file_path: 要读取的文件路径
    :param branch: 分支名称，默认为 "master"
    :return: 文件内容
    """
    url = f"{GITHUB_API}/repos/{repo_name}/contents/{file_path}"
    params = {"ref": branch}
    r = requests.get(url, headers=github_headers(token), params=params)

    try:
        if r.status_code == 404:
            print(f"文件 {file_path} 不存在")
            return None
        elif r.status_code != 200:
            print(f"错误: HTTP {r.status_code} - {r.text}")
            return None

        file_info = r.json()
        content_b64 = file_info.get("content", "")

        try:
            return base64.b64decode(content_b64).decode('utf-8')
        except UnicodeDecodeError:
            print(f"文件 {file_path} 是二进制文件，无法直接解码为 UTF-8")
            # 如果需要二进制内容
            return base64.b64decode(content_b64)
    except Exception as e:
        print(f"错误: {traceback.format_exc()}")
        return None


def roll_back_commit(token, repo_name, commit_sha, branch="master"):
    """
    回滚指定仓库的分支到指定的 commit。

    :param token: GitHub 访问令牌
    :param repo_name: 仓库名称，格式为 "用户名/仓库名"
    :param branch_name: 分支名称
    :param commit_sha: 要回滚到的 commit 的 SHA
    """
    url = f"{GITHUB_API}/repos/{repo_name}/git/refs/heads/{branch}"
    payload = {
        "sha": commit_sha,
        "force": True
    }

    r = requests.patch(url, headers=github_headers(token), json=payload)
    if r.status_code == 200:
        print(f"分支 {branch} 已回退到 commit: {commit_sha}")
    else:
        raise RuntimeError(f"Failed to rollback branch {branch}: {r.status_code} {r.text}")


def create_file(token, repo_name, file_path, commit_message, content, branch="master"):
    """
    在指定仓库中创建一个新文件。

    :param token: GitHub 访问令牌
    :param repo_name: 仓库名称，格式为 "用户名/仓库名"
    :param file_path: 要创建的文件路径
    :param commit_message: 提交信息
    :param content: 文件内容
    :param branch: 分支名称，默认为 "master"
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

    r = requests.put(url, headers=github_headers(token), json=payload)
    if r.status_code in (200, 201):
        print(f"文件 {file_path} 已创建到分支 {branch}。")
    else:
        raise RuntimeError(f"Failed to create file {file_path}: {r.status_code} {r.text}")


def update_file(token, repo_name, file_path, commit_message, content, branch="master"):
    """
    更新指定仓库中的文件。

    :param token: GitHub 访问令牌
    :param repo_name: 仓库名称，格式为 "用户名/仓库名"
    :param file_path: 要更新的文件路径
    :param commit_message: 提交信息
    :param content: 文件的新内容
    :param branch: 分支名称，默认为 "master"
    """
    # First get the current file to get its SHA
    get_url = f"{GITHUB_API}/repos/{repo_name}/contents/{file_path}"
    params = {"ref": branch}
    r_get = requests.get(get_url, headers=github_headers(token), params=params)

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

    r = requests.put(put_url, headers=github_headers(token), json=payload)
    if r.status_code in (200, 201):
        print(f"文件 {file_path} 已更新到分支 {branch}。")
    else:
        raise RuntimeError(f"Failed to update file {file_path}: {r.status_code} {r.text}")


def delete_folder_contents(token, repo_name, folder_path, branch="master"):
    """
    删除指定仓库中指定文件夹下的所有文件。

    :param token: GitHub 访问令牌
    :param repo_name: 仓库名称，格式为 "用户名/仓库名"
    :param folder_path: 要删除的文件夹路径
    :param branch: 分支名称，默认为 "master"
    """
    def _delete_contents_recursive(path):
        url = f"{GITHUB_API}/repos/{repo_name}/contents/{path}"
        params = {"ref": branch}
        r = requests.get(url, headers=github_headers(token), params=params)

        if r.status_code == 404:
            print(f"文件夹 {path} 不存在")
            return
        elif r.status_code != 200:
            print(f"错误: {traceback.format_exc()}")
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
                delete_r = requests.delete(delete_url, headers=github_headers(token), json=delete_payload)
                if delete_r.status_code == 200:
                    print(f"已删除: {item['path']}")
                else:
                    print(f"删除失败: {item['path']} - {delete_r.status_code} {delete_r.text}")

    try:
        _delete_contents_recursive(folder_path)
        print(f"文件夹 {folder_path} 下的所有文件已删除")
    except Exception as e:
        print(f"错误: {traceback.format_exc()}")


def get_latest_commit_sha(token, repo_name, branch="master"):
    """
    获取指定分支的最新 commit SHA。

    :param token: GitHub 访问令牌
    :param repo_name: 仓库名称，格式为 "用户名/仓库名"
    :param branch: 分支名称，默认为 "master"
    :return: 最新 commit 的 SHA
    """
    url = f"{GITHUB_API}/repos/{repo_name}/branches/{branch}"
    r = requests.get(url, headers=github_headers(token))

    if r.status_code != 200:
        raise RuntimeError(f"Failed to get branch {branch}: {r.status_code} {r.text}")

    branch_info = r.json()
    return branch_info["commit"]["sha"]


def get_modified_files_between_commits(token, repo_name, old_sha, new_sha):
    """
    获取两个 commit 之间修改的文件列表。

    :param token: GitHub 访问令牌
    :param repo_name: 仓库名称，格式为 "用户名/仓库名"
    :param old_sha: 旧的 commit SHA
    :param new_sha: 新的 commit SHA
    :return: 修改的文件列表
    """
    url = f"{GITHUB_API}/repos/{repo_name}/compare/{old_sha}...{new_sha}"

    try:
        r = requests.get(url, headers=github_headers(token))
        if r.status_code == 404:
            print("一个或多个 commit 不存在")
            return None
        elif r.status_code == 403:
            print("权限不足或 API 速率限制")
            return None
        elif r.status_code != 200:
            print(f"错误: HTTP {r.status_code} - {r.text}")
            return None

        comparison = r.json()
        return comparison.get("files", [])
    except Exception as e:
        print(f"发生错误: {e}")
        return None


def check_repo_exists(token, repo_name):
    """
    检查指定的 GitHub 仓库是否存在。

    :param token: GitHub 访问令牌
    :param repo_name: 仓库名称，格式为 "用户名/仓库名"
    :return: 如果仓库存在则返回 True，否则返回 False
    """
    url = f"{GITHUB_API}/repos/{repo_name}"

    try:
        r = requests.get(url, headers=github_headers(token))
        if r.status_code == 200:
            return True
        elif r.status_code == 404:
            return False
        else:
            print(f"错误: {traceback.format_exc()}")
            return False
    except Exception as e:
        print(f"错误: {traceback.format_exc()}")
        return False


def fork_repo(token, source_repo_name, new_repo_name=""):
    """
    Fork一个仓库到当前认证用户的账户下，并可选择性地进行重命名。

    :param token: GitHub 个人访问令牌 (Personal Access Token)。
    :param source_repo_name: 源仓库的全名，格式为 "owner/repo"。
    :param new_repo_name: Fork后为仓库设置的新名称（可选）。如果留空，将使用原始仓库名。
    :return: 返回最终创建的仓库信息字典 (类似 PyGithub 仓库对象的属性)。
    """
    try:
        # Fork the repository
        fork_url = f"{GITHUB_API}/repos/{source_repo_name}/forks"
        fork_data = {}
        if new_repo_name:
            fork_data["name"] = new_repo_name

        r = requests.post(fork_url, headers=github_headers(token), json=fork_data)
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

            rename_r = requests.patch(rename_url, headers=github_headers(token), json=rename_data)
            if rename_r.status_code == 200:
                forked_repo_info = rename_r.json()

        print(f"✅ 成功将仓库 {source_repo_name} Fork 为 {forked_repo_info['full_name']}")

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
        print(f"❌ Fork操作失败: {e}")
        return None


def create_repo(token, repo_name, description="", private=False):
    """
    为论文创建一个GitHub仓库，并初始化基本的项目结构。

    :param token: GitHub 访问令牌
    :param repo_name: 仓库名称
    :param description: 仓库描述
    :param private: 是否私有仓库，默认为 False
    :return: 创建的仓库对象
    """
    url = f"{GITHUB_API}/user/repos"
    payload = {
        "name": repo_name,
        "description": description,
        "private": private,
        "auto_init": True,
        "has_issues": True
    }

    r = requests.post(url, headers=github_headers(token), json=payload)
    if r.status_code != 201:
        raise RuntimeError(f"Failed to create repo {repo_name}: {r.status_code} {r.text}")

    repo_data = r.json()
    print(f"已创建仓库: {repo_data['full_name']}")

    # Return an object that mimics PyGithub Repository object attributes
    class RepoObj:
        def __init__(self, repo_data):
            self.full_name = repo_data.get("full_name")
            self.name = repo_data.get("name")
            self.id = repo_data.get("id")
            self.clone_url = repo_data.get("clone_url")
            self.html_url = repo_data.get("html_url")

    return RepoObj(repo_data)