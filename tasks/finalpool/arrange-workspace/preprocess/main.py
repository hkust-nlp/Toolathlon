from argparse import ArgumentParser
import os
import shutil
import tarfile

def main():
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True, help="agent工作空间路径，必须明确指定")
    parser.add_argument("--launch_time", required=False, help="Launch time (can contain spaces)")
    args = parser.parse_args()
    
    # 确保agent workspace存在
    os.makedirs(args.agent_workspace, exist_ok=True)
    dst_tar_path = os.path.join(args.agent_workspace, "initial_workspace.tar.gz")

    # 解压缩
    try:
        with tarfile.open(dst_tar_path, 'r:gz') as tar:
            print(f"正在解压缩到: {args.agent_workspace}")
            # Use the filter parameter to avoid deprecation warning in Python 3.14+
            tar.extractall(path=args.agent_workspace, filter='data')
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
    
    print("预处理完成 - 工作空间文件已准备就绪")

if __name__ == "__main__":
    main()
