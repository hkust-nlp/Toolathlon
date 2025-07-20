from argparse import ArgumentParser
import os

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True)
    args = parser.parse_args()

    # 需要处理的文件列表
    to_process_files = ["Market_Data.xlsx"]
    
    print(f"开始处理文件，工作目录: {args.agent_workspace}")
    
    for filename in to_process_files:
        source_path = os.path.join(args.agent_workspace, filename)
        print(f"处理文件: {filename}")
        print(f"源文件路径: {source_path}")
        print(f"源文件是否存在: {os.path.exists(source_path)}")

        if os.path.exists(source_path):
            print(f"{filename} 已存在于正确位置，无需处理")
        else:
            print(f"警告：源文件未找到 '{source_path}'，已跳过。")

    print("\n所有文件处理完毕。") 