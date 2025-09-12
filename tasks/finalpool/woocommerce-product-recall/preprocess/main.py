#!/usr/bin/env python3
"""
预处理脚本 - 设置产品召回任务初始环境
"""

import os
import sys
import shutil
import json
from argparse import ArgumentParser
from pathlib import Path

# 添加项目路径
current_dir = Path(__file__).parent
task_dir = current_dir.parent
sys.path.insert(0, str(task_dir))

def setup_recall_test_data():
    """设置产品召回测试数据"""
    print("🛒 设置产品召回测试数据...")
    
    try:
        from .setup_recall_data import main as setup_recall_main
        from .verify_clean_state import verify_clean_state
        from token_key_session import all_token_key_session
        from .woocommerce_client import WooCommerceClient
        
        # 初始化WooCommerce客户端进行验证
        wc_client = WooCommerceClient(
            all_token_key_session.woocommerce_site_url,
            all_token_key_session.woocommerce_api_key,
            all_token_key_session.woocommerce_api_secret
        )
        
        # 验证清理状态
        print("🔍 验证WooCommerce清理状态...")
        verification = verify_clean_state(wc_client)
        
        if not verification["is_clean"]:
            print("⚠️ WooCommerce尚未完全清理，建议先运行清理操作")
            print("发现的问题:")
            for issue in verification["issues"]:
                print(f"  - {issue}")
        
        # 运行召回数据设置
        success = setup_recall_main()
        
        if success:
            print("✅ 产品召回测试数据设置完成")
            
            # 设置完成后再次验证
            print("\n🔍 验证设置结果...")
            # final_verification = verify_clean_state(wc_client)
            
            # 检查是否有预期的测试数据
            products = wc_client.get_all_products()
            orders = wc_client.get_all_orders()
            
            print(f"📊 设置完成摘要:")
            print(f"   - 创建了 {len(products)} 个商品")
            print(f"   - 创建了 {len(orders)} 个订单")
            
            recalled_products = [p for p in products if "召回" in p.get('description', '')]
            print(f"   - 其中 {len(recalled_products)} 个是召回商品")
            
        else:
            print("⚠️ 产品召回测试数据设置部分完成")
        return success
        
    except Exception as e:
        print(f"❌ 产品召回测试数据设置失败: {e}")
        print("ℹ️ 请确保已正确配置 token_key_session.py 文件")
        return False

if __name__ == "__main__":
    parser = ArgumentParser(description="预处理脚本 - 设置产品召回任务的初始环境")
    parser.add_argument("--agent_workspace", required=False, help="Agent工作空间路径")
    parser.add_argument("--setup_data", default=True, help="同时设置WooCommerce测试数据")
    parser.add_argument("--launch_time", required=False, help="Launch time")

    args = parser.parse_args()
    
    print("=" * 60)
    print("🎯 产品召回任务 - 预处理")
    print("=" * 60)
        
    # 设置产品召回测试数据
    success = True
    if args.setup_data:
        success = setup_recall_test_data()
    
    if success:
        print("\n🎉 预处理完成！agent工作空间已准备就绪")
        exit(0)
    else:
        print("\n⚠️ 预处理部分完成，请检查错误信息")
        exit(1)