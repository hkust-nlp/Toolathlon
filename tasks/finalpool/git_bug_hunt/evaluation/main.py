import sys
from argparse import ArgumentParser
from pathlib import Path

# 添加当前目录到Python路径
sys.path.append(str(Path(__file__).parent))
from check_email_content import EmailContentChecker 

if __name__=="__main__":
    parser = ArgumentParser()
    print("args started")
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--groundtruth_workspace", required=False)
    parser.add_argument("--res_log_file", required=False)
    parser.add_argument("--launch_time", required=False)

    args = parser.parse_args()

    # 获取文件路径
    task_dir = Path(__file__).parent.parent
    receiver_config_file = task_dir / "files" / "receiver_config.json"
    template_file = task_dir / "initial_workspace" / "template.txt"
    groundtruth_file = task_dir / "groundtruth_workspace" / "expected_author_info.json"
    
    print(f"配置文件路径: {receiver_config_file}")
    print(f"模板文件路径: {template_file}")
    print(f"真值文件路径: {groundtruth_file}")
    
    # 实例化检查器
    checker = EmailContentChecker(
        str(receiver_config_file), 
        str(template_file),
        str(groundtruth_file)
    )
    success = checker.run() 
    
    if success:
        print("\n检查成功")
    else:
        print("\n检查失败")
        exit(1)
    
    