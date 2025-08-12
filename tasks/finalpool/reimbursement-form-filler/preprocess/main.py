import os
import shutil
import tarfile
from pathlib import Path
from argparse import ArgumentParser

def setup_workspace(agent_workspace: str):
    """设置工作空间，解压bills.tar.gz文件中的PDF文件"""
    workspace_dir = Path(agent_workspace)
    bills_dir = workspace_dir / "bills"
    
    # 创建bills目录
    os.makedirs(bills_dir, exist_ok=True)
    
    # 获取压缩文件路径 - 从initial_workspace中的bills.tar.gz
    current_dir = Path(__file__).parent.parent
    archive_path = current_dir / "initial_workspace" / "bills" / "bills.tar.gz"
    
    # 检查压缩文件是否存在
    if not archive_path.exists():
        print(f"压缩文件不存在: {archive_path}")
        return
    
    # 解压缩PDF文件到工作空间
    try:
        with tarfile.open(archive_path, 'r:gz') as tar:
            # 获取所有PDF文件
            pdf_members = [member for member in tar.getmembers() if member.name.endswith('.pdf')]
            
            if not pdf_members:
                print(f"压缩文件中没有找到PDF文件: {archive_path}")
                return
            
            # 解压PDF文件到bills目录
            for member in pdf_members:
                # 解压到bills目录
                tar.extract(member, bills_dir)
                # 移动文件到bills目录根部（避免创建子目录）
                extracted_path = bills_dir / member.name
                if extracted_path.exists():
                    print(f"解压文件: {member.name}")
                else:
                    print(f"解压失败: {member.name}")
            
            print(f"已解压 {len(pdf_members)} 个PDF文件到工作空间")
            
    except Exception as e:
        print(f"解压缩过程中出错: {e}")
        return
    
    # 复制其他必要文件到工作空间
    initial_workspace = current_dir / "initial_workspace"
    files_to_copy = ["Bill_Format.xlsx", "requirement.txt"]
    
    for filename in files_to_copy:
        source_file = initial_workspace / filename
        dest_file = workspace_dir / filename
        
        if source_file.exists():
            shutil.copy2(source_file, dest_file)
            print(f"复制文件: {filename}")
        else:
            print(f"源文件不存在: {filename}")

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True, help="Agent workspace directory")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()
    
    setup_workspace(args.agent_workspace)
    print("已完成工作空间初始化！") 