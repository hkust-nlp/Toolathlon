#!/usr/bin/env python3
"""
Google Sheets预处理脚本
用于创建动态文件夹并清理已存在的投资分析相关Google Sheet文件
"""
import os
import sys
from argparse import ArgumentParser

# 任务配置
FOLDER_NAME = "InvestmentAnalysisWorkspace"

from utils.app_specific.googlesheet.drive_helper import (
    get_google_service, find_folder_by_name, create_folder, 
    clear_folder
)


def main():
    """主函数 - 模仿googlesheet-example的实现"""
    parser = ArgumentParser(description="Investment Decision Analysis preprocess")
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False)
    args = parser.parse_args()

    print("Investment Decision Analysis预处理工具")
    print("用途：创建动态文件夹并清理已存在的投资分析相关Google Sheets文件")
    print(f"动态文件夹名称: {FOLDER_NAME}")
    print("=" * 60)

    try:
        # 设置文件路径
        task_root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.makedirs(os.path.join(task_root_path, "files"), exist_ok=True)
        folder_id_file = os.path.join(task_root_path, "files", "folder_id.txt")

        # 删除旧的folder_id文件
        if os.path.exists(folder_id_file):
            os.remove(folder_id_file)
            print("已删除旧的folder_id文件")

        # 获取Google服务
        drive_service, sheets_service = get_google_service()
        print("Google服务认证成功")

        # 查找或创建文件夹
        folder_id = find_folder_by_name(drive_service, FOLDER_NAME)
        if not folder_id:
            folder_id = create_folder(drive_service, FOLDER_NAME)
            print(f"创建了新文件夹: {FOLDER_NAME} (ID: {folder_id})")
        else:
            print(f"找到现有文件夹: {FOLDER_NAME} (ID: {folder_id})")

        # 清理文件夹内容
        clear_folder(drive_service, folder_id)
        print("已清理文件夹内容")

        # 保存folder_id到文件
        with open(folder_id_file, "w") as f:
            f.write(folder_id)

        print(f"Folder ID已保存: {folder_id}")
        print("=" * 60)
        print("预处理完成：环境已准备好，可以开始任务")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f" 预处理过程中发生错误: {e}")
        print("=" * 60)
        print(" 预处理失败：无法准备环境")
        print("=" * 60)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)