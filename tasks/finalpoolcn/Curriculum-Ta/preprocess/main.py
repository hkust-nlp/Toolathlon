import os
import shutil

def preprocess(initial_workspace: str, agent_workspace: str):
    """
    预处理函数，将初始工作区的文件复制到agent工作区
    为课程作业文件管理任务设置初始环境
    """
    
    # 确保agent工作区存在
    os.makedirs(agent_workspace, exist_ok=True)
    
    # 如果initial_workspace中有文件，则复制到agent_workspace
    if os.path.exists(initial_workspace):
        for item in os.listdir(initial_workspace):
            if item.startswith('.'):  # 跳过隐藏文件
                continue
                
            src_path = os.path.join(initial_workspace, item)
            dst_path = os.path.join(agent_workspace, item)
            
            if os.path.isfile(src_path):
                shutil.copy2(src_path, dst_path)
                print(f"复制文件: {item}")
            elif os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
                print(f"复制目录: {item}")
    
    print(f"预处理完成: {agent_workspace}")
    print("注意：请确保工作区中包含:")
    print("1. 各种操作系统相关的作业文件")
    print("2. 学院和学号的对应表文件")
    print("3. 文件命名应包含课程和作业序号信息")

if __name__ == "__main__":
    # 用于测试
    import sys
    if len(sys.argv) >= 3:
        preprocess(sys.argv[1], sys.argv[2])
    else:
        print("用法: python main.py <initial_workspace> <agent_workspace>") 