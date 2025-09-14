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

    success = setup_woocommerce_test_data()
    print(f"WooCommerce测试数据设置结果: {success}")
    
    if success:
        print("\n🎉 预处理完成！agent工作空间已准备就绪")
        exit(0)
    else:
        print("\n⚠️ 预处理部分完成，请检查错误信息")
        exit(1)