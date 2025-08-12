from utils.data_processing.process_ops import copy_multiple_times
from argparse import ArgumentParser
import os
import tarfile
import glob

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True)
    parser.add_argument("--launch_time", nargs='*', required=False, help="Launch time (can contain spaces)")
    args = parser.parse_args()

    # 找到--agent_workspace 下的 files.tar.gz
    workspace_path = args.agent_workspace
    tar_pattern = os.path.join(workspace_path, "files.tar.gz")
    
    # 查找 files.tar.gz 文件
    tar_files = glob.glob(tar_pattern)
    
    if not tar_files:
        print(f"未在 {workspace_path} 中找到 files.tar.gz 文件")
        exit(1)
    
    tar_file_path = tar_files[0]
    print(f"找到压缩文件: {tar_file_path}")
    
    # 解压缩
    try:
        with tarfile.open(tar_file_path, 'r:gz') as tar:
            print(f"正在解压缩到: {workspace_path}")
            tar.extractall(path=workspace_path)
            print("解压缩完成")
    except Exception as e:
        print(f"解压缩失败: {e}")
        exit(1)
    
    # 然后删除 files.tar.gz
    try:
        os.remove(tar_file_path)
        print(f"已删除原始压缩文件: {tar_file_path}")
    except Exception as e:
        print(f"删除压缩文件失败: {e}")
        exit(1)
    
    print("处理完成")

    
