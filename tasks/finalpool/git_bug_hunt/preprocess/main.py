import asyncio
import sys
import os
import shutil
import subprocess
from argparse import ArgumentParser
from pathlib import Path
from utils.general.helper import run_command, get_module_path

from utils.app_specific.poste.local_email_manager import LocalEmailManager


def setup_git_repository():
    """初始化Git仓库"""
    print("\n🔧 初始化Git仓库...")
    
    # 获取initial_workspace路径
    initial_workspace = Path(__file__).parent / ".." / "initial_workspace"
    luffy_path = initial_workspace / "LUFFY"
    git_path = luffy_path / ".git"
    git_backup_path = luffy_path / ".git_backup"
    
    repo_url = "https://github.com/motigrez/LUFFY.git"
    
    # 检查LUFFY目录是否存在
    if not luffy_path.exists():
        print("📁 LUFFY目录不存在，开始克隆...")
        try:
            result = subprocess.run([
                "git", "clone", repo_url, str(luffy_path)
            ], capture_output=True, text=True, cwd=str(initial_workspace))
            
            if result.returncode == 0:
                print("✅ 成功克隆LUFFY仓库")
            else:
                print(f"❌ 克隆失败: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ 克隆过程出错: {e}")
            return False
    else:
        print("📁 LUFFY目录已存在，检查Git状态...")
        
        # 检查.git文件夹
        if git_path.exists():
            print("✅ .git文件夹存在，仓库状态正常")
        else:
            print("⚠️ .git文件夹不存在，检查备份...")
            
            # 检查.git_backup文件夹
            if git_backup_path.exists():
                print("📋 发现.git_backup文件夹，恢复为.git...")
                try:
                    git_backup_path.rename(git_path)
                    print("✅ 成功恢复.git文件夹")
                except Exception as e:
                    print(f"❌ 恢复.git失败: {e}")
                    return False
            else:
                print("🔄 没有备份，删除现有目录并重新克隆...")
                try:
                    # 删除现有目录
                    if luffy_path.exists():
                        shutil.rmtree(luffy_path)
                        print("🗑️ 已删除现有LUFFY目录")
                    
                    # 重新克隆
                    result = subprocess.run([
                        "git", "clone", repo_url, str(luffy_path)
                    ], capture_output=True, text=True, cwd=str(initial_workspace))
                    
                    if result.returncode == 0:
                        print("✅ 成功重新克隆LUFFY仓库")
                    else:
                        print(f"❌ 重新克隆失败: {result.stderr}")
                        return False
                except Exception as e:
                    print(f"❌ 重新克隆过程出错: {e}")
                    return False
    
    print("✅ Git仓库初始化完成！")
    return True


if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()
    

    print("Preprocessing...")
    
    # 1. 初始化Git仓库
    if not setup_git_repository():
        print("❌ Git仓库初始化失败，终止预处理")
        sys.exit(1)

    # 2. 清理接收方邮箱
    print("\n📧 清理接收方邮箱...")
    receiver_config_file = Path(__file__).parent / ".." / "files" / "receiver_config.json"
    
    receiver_email_manager = LocalEmailManager(str(receiver_config_file), verbose=True)
    receiver_email_manager.clear_all_emails()

    print("✅ 已完成接收方邮箱清理！")