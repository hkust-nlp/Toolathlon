"""
Google Sheets预处理脚本
用于检测并删除已存在的inter-ucl-final2325 Google Sheet文件
"""
import sys
import os
import asyncio
from argparse import ArgumentParser

# 动态添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
sys.path.append(project_root)

from utils.app_specific.googlesheet.drive_helper import (
    get_google_service, find_folder_by_name, create_folder, 
    clear_folder, copy_sheet_to_folder
)

# 源Google Sheet URL (需要复制的模板)
SOURCE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fKZ2b4R5kFgxGFis9UuJV2ANxth0Kdu_ifK8krlui4o/edit?usp=sharing"

# 目标文件夹名称
FOLDER_NAME = "inter-ucl-final2325"

async def main():
    parser = ArgumentParser(description="Inter Final Performance Analysis preprocess")
    parser.add_argument("--agent_workspace", required=True)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    print("=" * 60)
    print("开始Google Sheets预处理 - Inter Final Performance Analysis")
    print("=" * 60)

    # 获取任务根目录路径
    task_root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 创建files目录
    files_dir = os.path.join(task_root_path, "files")
    os.makedirs(files_dir, exist_ok=True)
    
    # 文件夹ID保存文件路径
    folder_id_file = os.path.join(files_dir, "folder_id.txt")

    # 如果已存在folder_id.txt文件，删除它
    if os.path.exists(folder_id_file):
        os.remove(folder_id_file)
        print(f"✓ 已清理旧的文件夹ID文件")

    try:
        # 获取Google服务
        print("正在认证Google服务...")
        drive_service, sheets_service = get_google_service()
        print("✓ Google服务认证成功")

        # 查找或创建目标文件夹
        print(f"正在查找文件夹: {FOLDER_NAME}")
        folder_id = find_folder_by_name(drive_service, FOLDER_NAME)
        
        if not folder_id:
            print(f"未找到文件夹，正在创建: {FOLDER_NAME}")
            folder_id = create_folder(drive_service, FOLDER_NAME)
            print(f"✓ 成功创建文件夹: {FOLDER_NAME} (ID: {folder_id})")
        else:
            print(f"✓ 找到现有文件夹: {FOLDER_NAME} (ID: {folder_id})")

        # 清理文件夹中的所有文件
        print("正在清理文件夹中的现有文件...")
        clear_folder(drive_service, folder_id)
        print("✓ 文件夹已清理")

        # 复制源Google Sheet到目标文件夹
        print(f"正在复制源Google Sheet到文件夹...")
        print(f"源Sheet URL: {SOURCE_SHEET_URL}")
        copied_sheet_id = copy_sheet_to_folder(drive_service, SOURCE_SHEET_URL, folder_id)
        print(f"✓ 成功复制Google Sheet (新ID: {copied_sheet_id})")

        # 保存文件夹ID到文件
        with open(folder_id_file, "w") as f:
            f.write(folder_id)
        print(f"✓ 文件夹ID已保存到: {folder_id_file}")

        print("\n" + "=" * 60)
        print("✓ 预处理完成：环境已准备就绪")
        print(f"✓ 工作文件夹ID: {folder_id}")
        print(f"✓ 模板已复制，可以开始任务")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 预处理过程中发生错误: {e}")
        print("=" * 60)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())