from argparse import ArgumentParser
import os
import shutil
import json
import tarfile
import glob

def main():
    parser = ArgumentParser()
    parser.add_argument("--initial_workspace", required=True, help="初始工作空间路径，必须明确指定")
    parser.add_argument("--agent_workspace", required=True, help="agent工作空间路径，必须明确指定")
    args = parser.parse_args()
    
    # 确保agent workspace存在
    os.makedirs(args.agent_workspace, exist_ok=True)
    
    # 复制压缩文件到agent workspace
    tar_file_path = os.path.join(args.initial_workspace, "../files.tar.gz")
    if not os.path.exists(tar_file_path):
        print(f"错误: 压缩文件不存在: {tar_file_path}")
        return
    
    dst_tar_path = os.path.join(args.agent_workspace, "files.tar.gz")
    shutil.copy2(tar_file_path, dst_tar_path)
    print(f"复制压缩文件: files.tar.gz")
    
    # 解压缩
    try:
        with tarfile.open(dst_tar_path, 'r:gz') as tar:
            print(f"正在解压缩到: {args.agent_workspace}")
            tar.extractall(path=args.agent_workspace)
            print("解压缩完成")
    except Exception as e:
        print(f"解压缩失败: {e}")
        return
    
    # 删除压缩文件
    try:
        os.remove(dst_tar_path)
        print(f"已删除原始压缩文件: {dst_tar_path}")
    except Exception as e:
        print(f"删除压缩文件失败: {e}")
    
    # 创建desensitized_documents目录（用于保存脱敏文件）
    desen_docs_dir = os.path.join(args.agent_workspace, "desensitized_documents")
    os.makedirs(desen_docs_dir, exist_ok=True)
    print(f"创建desensitized_documents目录: {desen_docs_dir}")
    
    print("预处理完成")

if __name__ == "__main__":
    main() 