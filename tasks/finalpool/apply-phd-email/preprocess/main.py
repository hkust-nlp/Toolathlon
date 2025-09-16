import sys
import os
import tarfile
from argparse import ArgumentParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # 添加任务目录到路径
from token_key_session import all_token_key_session
from utils.app_specific.poste.email_import_utils import setup_email_environment

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()
    
    # 首先处理文件解压缩（如果agent_workspace被指定）
    if args.agent_workspace:
        # 确保agent workspace存在
        os.makedirs(args.agent_workspace, exist_ok=True)
        dst_tar_path = os.path.join(args.agent_workspace, "files.tar.gz")
        
        # 解压缩文件
        try:
            with tarfile.open(dst_tar_path, 'r:gz') as tar:
                print(f"正在解压缩申请文件到: {args.agent_workspace}")
                # Use the filter parameter to avoid deprecation warning in Python 3.14+
                tar.extractall(path=args.agent_workspace, filter='data')
                print("解压缩完成")
        except Exception as e:
            print(f"解压缩失败: {e}")
            # 继续执行，因为可能文件已经存在或者不需要解压缩
        
        # 删除压缩文件
        try:
            os.remove(dst_tar_path)
            print(f"已删除原始压缩文件: {dst_tar_path}")
        except Exception as e:
            print(f"删除压缩文件失败: {e}")

    print("Preprocessing...")
    print("使用MCP邮件导入模式")

    # 获取任务邮件备份文件路径
    task_backup_file = Path(__file__).parent / ".." / "files" / "emails_backup.json"

    if not task_backup_file.exists():
        print("❌ 未找到任务邮件备份文件，请先运行转换脚本生成emails_backup.json")
        sys.exit(1)

    # 使用工具函数设置邮件环境
    success = setup_email_environment(
        local_token_key_session=all_token_key_session,
        task_backup_file=str(task_backup_file)
    )

    if not success:
        print("\n❌ 邮件环境设置失败！")
        sys.exit(1)