#!/usr/bin/env python3
"""
预处理脚本 - 设置新品邮件任务的初始环境
"""

import os
import sys
import shutil
from argparse import ArgumentParser
from pathlib import Path

# 添加项目路径
current_dir = Path(__file__).parent
task_dir = current_dir.parent
sys.path.insert(0, str(task_dir))

# 添加邮件管理相关导入
from token_key_session import all_token_key_session
from utils.app_specific.poste.local_email_manager import LocalEmailManager


def clear_all_email_folders():
    """
    清理INBOX、Draft、Sent三个文件夹的邮件
    """
    # 获取邮件配置文件路径
    emails_config_file = all_token_key_session.emails_config_file
    print(f"使用邮件配置文件: {emails_config_file}")

    # 初始化邮件管理器
    email_manager = LocalEmailManager(emails_config_file, verbose=True)

    # 需要清理的文件夹（尝试清理这些文件夹，如果不存在会在清理时处理错误）
    folders_to_clear = ['INBOX', 'Drafts', 'Sent']

    print(f"将清理以下文件夹: {folders_to_clear}")

    for folder in folders_to_clear:
        try:
            print(f"清理 {folder} 文件夹...")
            email_manager.clear_all_emails(mailbox=folder)
            print(f"✅ {folder} 文件夹清理完成")
        except Exception as e:
            print(f"⚠️ 清理 {folder} 文件夹时出错: {e}")

    print("📧 所有邮箱文件夹清理完成")


def setup_woocommerce_test_data():
    """设置WooCommerce测试数据"""
    print("🛒 设置WooCommerce测试数据...")
    
    try:
        from .setup_new_product_data import main as setup_main
        success = setup_main()
        if success:
            print("✅ WooCommerce测试数据设置完成")
        else:
            print("⚠️ WooCommerce测试数据设置部分完成")
        return success
    except Exception as e:
        print(f"❌ WooCommerce测试数据设置失败: {e}")
        return False

if __name__ == "__main__":
    parser = ArgumentParser(description="预处理脚本 - 设置新品邮件任务的初始环境")
    parser.add_argument("--agent_workspace", required=False, help="Agent工作空间路径")
    parser.add_argument("--launch_time", required=False, help="Launch time")

    args = parser.parse_args()
    
    print("=" * 60)
    print("📧 新品预约与折扣提醒邮件任务 - 预处理")
    print("=" * 60)

    # 步骤0：清理邮箱
    print("=" * 60)
    print("第零步：清理邮箱文件夹")
    print("=" * 60)
    clear_all_email_folders()

    # 步骤1：设置WooCommerce测试数据
    print("\n" + "=" * 60)
    print("第一步：设置WooCommerce测试数据")
    print("=" * 60)
    success = setup_woocommerce_test_data()
    print(f"WooCommerce测试数据设置结果: {success}")
    
    if success:
        print("\n🎉 预处理完成！agent工作空间已准备就绪")
        exit(0)
    else:
        print("\n⚠️ 预处理部分完成，请检查错误信息")
        exit(1)