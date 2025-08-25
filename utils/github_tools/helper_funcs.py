from github import Github, GithubException
import traceback

def get_user_name(token):
    """
    获取 GitHub 用户名。

    :param token: GitHub 访问令牌
    :return: 用户名
    """
    g = Github(token)
    user = g.get_user()
    return user.login

def read_file_content(token, repo_name, file_path, branch="master"):
    """
    读取指定仓库中的文件内容。

    :param token: GitHub 访问令牌
    :param repo_name: 仓库名称，格式为 "用户名/仓库名"
    :param file_path: 要读取的文件路径
    :param branch: 分支名称，默认为 "master"
    :return: 文件内容
    """
    g = Github(token)
    repo = g.get_repo(repo_name)
    
    try:
        file_content = repo.get_contents(file_path, ref=branch)
        return file_content.decoded_content.decode('utf-8')
    except GithubException as e:
        if e.status == 404:
            print(f"文件 {file_path} 不存在")
            return None
        else:
            print(f"错误: {traceback.format_exc()}")
            return None
    except UnicodeDecodeError:
        print(f"文件 {file_path} 是二进制文件，无法直接解码为 UTF-8")
        # 如果需要二进制内容
        return file_content.decoded_content
    
def roll_back_commit(token, repo_name, commit_sha, branch="master"):
    """
    回滚指定仓库的分支到指定的 commit。

    :param token: GitHub 访问令牌
    :param repo_name: 仓库名称，格式为 "用户名/仓库名"
    :param branch_name: 分支名称
    :param commit_sha: 要回滚到的 commit 的 SHA
    """
    g = Github(token)
    repo = g.get_repo(repo_name)

    # 获取分支的引用
    ref = repo.get_git_ref(f"heads/{branch}")

    # 更新分支引用到指定 commit
    ref.edit(sha=commit_sha, force=True)  # force=True 模拟 git reset --hard
    print(f"分支 {branch} 已回退到 commit: {commit_sha}")

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
    g = Github(token)
    repo = g.get_repo(repo_name)

    # 创建文件
    repo.create_file(file_path, commit_message, content, branch=branch)
    print(f"文件 {file_path} 已创建到分支 {branch}。")

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
    g = Github(token)
    repo = g.get_repo(repo_name)

    # 获取文件内容和 SHA
    file_content = repo.get_contents(file_path, ref=branch)
    
    # 更新文件
    repo.update_file(file_path, commit_message, content, file_content.sha, branch=branch)
    print(f"文件 {file_path} 已更新到分支 {branch}。")

def delete_folder_contents(token, repo_name, folder_path, branch="master"):
    """
    删除指定仓库中指定文件夹下的所有文件。

    :param token: GitHub 访问令牌
    :param repo_name: 仓库名称，格式为 "用户名/仓库名"
    :param folder_path: 要删除的文件夹路径
    :param branch: 分支名称，默认为 "master"
    """
    g = Github(token)
    repo = g.get_repo(repo_name)

    try:
        contents = repo.get_contents(folder_path, ref=branch)
        while contents:
            file_content = contents.pop(0)
            if file_content.type == "dir":
                # 递归添加子文件夹内容
                contents.extend(repo.get_contents(file_content.path, ref=branch))
            else:
                # 删除文件
                repo.delete_file(file_content.path, f"Delete {file_content.path}", file_content.sha, branch=branch)
                print(f"已删除: {file_content.path}")
        print(f"文件夹 {folder_path} 下的所有文件已删除")
    except GithubException as e:
        if e.status == 404:
            print(f"文件夹 {folder_path} 不存在")
        else:
            print(f"错误: {traceback.format_exc()}")

def get_latest_commit_sha(token, repo_name, branch="master"):
    """
    获取指定分支的最新 commit SHA。

    :param token: GitHub 访问令牌
    :param repo_name: 仓库名称，格式为 "用户名/仓库名"
    :param branch: 分支名称，默认为 "master"
    :return: 最新 commit 的 SHA
    """
    g = Github(token)
    repo = g.get_repo(repo_name)
    branch_ref = repo.get_branch(branch)
    return branch_ref.commit.sha

def get_modified_files_between_commits(token, repo_name, old_sha, new_sha):
    """
    获取两个 commit 之间修改的文件列表。

    :param token: GitHub 访问令牌
    :param repo_name: 仓库名称，格式为 "用户名/仓库名"
    :param old_sha: 旧的 commit SHA
    :param new_sha: 新的 commit SHA
    :return: 修改的文件列表
    """
    g = Github(token)
    repo = g.get_repo(repo_name)

    try:
        comparison = repo.compare(old_sha, new_sha)
        return comparison.files
    except GithubException as e:
        if e.status == 404:
            print("一个或多个 commit 不存在")
        elif e.status == 403:
            print("权限不足或 API 速率限制")
        else:
            print(f"错误: {traceback.format_exc()}")
        return None
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
    g = Github(token)
    try:
        g.get_repo(repo_name)
        return True
    except GithubException as e:
        if e.status == 404:
            return False
        else:
            print(f"错误: {traceback.format_exc()}")
            return False
        
def fork_repo(token, source_repo_name, new_repo_name=""):
    """
    Fork一个仓库到当前认证用户的账户下，并可选择性地进行重命名。

    :param token: GitHub 个人访问令牌 (Personal Access Token)。
    :param source_repo_name: 源仓库的全名，格式为 "owner/repo"。
    :param new_repo_name: Fork后为仓库设置的新名称（可选）。如果留空，将使用原始仓库名。
    :return: 返回最终创建的 PyGithub 仓库对象 (Repository object)。
    """
    try:
        g = Github(token)

        source_repo = g.get_repo(source_repo_name)
        forked_repo = source_repo.create_fork()
        
        if new_repo_name:
            forked_repo.edit(name=new_repo_name)

        print(f"✅ 成功将仓库 {source_repo_name} Fork 为 {forked_repo.full_name}")
        return forked_repo

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
    g = Github(token)
    user = g.get_user()
    
    # 创建仓库
    repo = user.create_repo(
        name=repo_name,
        description=description,
        private=private,
        auto_init=True
    )
    
    print(f"已创建仓库: {repo.full_name}")
    
    return repo