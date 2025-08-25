import os
import shutil
import requests
import json

# do not need to do anything -- by weihao
def preprocess(initial_workspace: str, agent_workspace: str):
    """
    预处理函数，为NHL背靠背分析任务准备工作环境
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
    
    # 创建任务说明文件
    readme_content = """# NHL 2024-2025 背靠背比赛分析任务

## 任务目标
分析NHL 2024-2025赛季的赛程数据，统计每支球队的背靠背比赛情况。

## 核心定义
**背靠背比赛**：同一支球队在连续两天都有比赛（比赛日期相差恰好1天）

## 数据源
https://docs.google.com/spreadsheets/d/18Gpg5cauraSBIfrpn2VWbC7B2M999XpyPTVy3E29Pv8/edit?gid=1113684723#gid=1113684723

## 必须完成的输出

### 1. Google Sheets表格
- **表格名称**："背靠背比赛统计"
- **重要**：必须设置为公开可访问权限

### 2. 本地CSV文件
- **文件名**：nhl_b2b_analysis.csv
- **保存位置**：当前工作区目录
- **重要**：此文件是评估系统检查的关键文件，必须生成！
"""
    
    readme_path = os.path.join(agent_workspace, "README.md")
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print(f"创建任务说明文件: README.md")
    
    print(f"预处理完成: {agent_workspace}")

if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description='Preprocess NHL back-to-back analysis task')
    parser.add_argument("--agent_workspace", required=True, help="Path to agent workspace")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    
    args = parser.parse_args()
    # 使用固定的initial_workspace路径，因为系统只传递agent_workspace
    # initial_workspace = "tasks/gyy710/NHL-B2B-Analysis/initial_workspace"
    # preprocess(initial_workspace, args.agent_workspace)
