#!/usr/bin/env python3
"""
预处理脚本 - 设置初始工作环境
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

def copy_initial_files_to_workspace(agent_workspace: str):
    """
    将初始文件复制到agent工作空间
    
    Args:
        agent_workspace: Agent工作空间路径
    """
    print(f"🚀 设置初始工作环境到: {agent_workspace}")
    
    # 确保工作空间目录存在
    os.makedirs(agent_workspace, exist_ok=True)
    
    # 定义需要复制的文件
    initial_workspace = task_dir / "initial_workspace"
    files_to_copy = [
        "store_products.json",
        "subscriber.json", 
        "blog_template.md"
    ]
    
    copied_count = 0
    for filename in files_to_copy:
        source_path = initial_workspace / filename
        dest_path = Path(agent_workspace) / filename
        
        if source_path.exists():
            try:
                shutil.copy2(source_path, dest_path)
                print(f"✅ 复制文件: {filename}")
                copied_count += 1
            except Exception as e:
                print(f"❌ 复制文件失败 {filename}: {e}")
        else:
            print(f"⚠️ 源文件不存在: {filename}")
    
    print(f"📊 初始环境设置完成: 成功复制 {copied_count} 个文件")
    return copied_count > 0

def setup_woocommerce_test_data():
    """设置WooCommerce测试数据"""
    print("🛒 设置WooCommerce测试商品数据...")
    
    try:
        # 确保能找到同目录下的模块
        import sys
        import os
        current_script_dir = os.path.dirname(os.path.abspath(__file__))
        if current_script_dir not in sys.path:
            sys.path.insert(0, current_script_dir)
        
        from setup_test_products import main as setup_test_main
        success = setup_test_main()
        if success:
            print("✅ WooCommerce测试数据设置完成")
        else:
            print("⚠️ WooCommerce测试数据设置部分完成")
        return success
    except Exception as e:
        print(f"❌ WooCommerce测试数据设置失败: {e}")
        return False

if __name__ == "__main__":
    parser = ArgumentParser(description="预处理脚本 - 设置低销量产品筛选任务的初始环境")
    parser.add_argument("--agent_workspace", required=True, help="Agent工作空间路径")
    parser.add_argument("--setup_wc", action="store_true", help="同时设置WooCommerce测试数据")
    parser.add_argument("--launch_time", required=False, help="Launch time")

    args = parser.parse_args()
    
    print("=" * 60)
    print("🎯 低销量产品筛选任务 - 预处理")
    print("=" * 60)
    
    # 复制初始文件到工作空间
    success1 = True
    # 可选：设置WooCommerce测试数据
    success2 = True
    #if args.setup_wc:
    success2 = setup_woocommerce_test_data()
    
    if success1 and success2:
        print("\n🎉 预处理完成！agent工作空间已准备就绪")
        exit(0)
    else:
        print("\n⚠️ 预处理部分完成，请检查错误信息")
        exit(1)