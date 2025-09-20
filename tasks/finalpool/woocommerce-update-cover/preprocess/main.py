#!/usr/bin/env python3
"""
预处理脚本 - 设置更新商品主图任务的初始环境
"""

import os
import sys
import json
import time
from argparse import ArgumentParser
from pathlib import Path
from datetime import datetime

# 添加项目路径
current_dir = Path(__file__).parent
task_dir = current_dir.parent
sys.path.insert(0, str(task_dir))

def setup_test_products():
    """设置测试商品和数据"""
    print("🛒 初始化测试商品和销量数据...")
    
    try:
        # 确保能找到同目录下的模块
        import sys
        import os
        current_script_dir = os.path.dirname(os.path.abspath(__file__))
        if current_script_dir not in sys.path:
            sys.path.insert(0, current_script_dir)
        
        from setup_test_products import TestProductSetup
        from token_key_session import all_token_key_session
        
        # 从配置获取WooCommerce信息
        site_url = all_token_key_session.woocommerce_site_url
        consumer_key = all_token_key_session.woocommerce_api_key
        consumer_secret = all_token_key_session.woocommerce_api_secret
        wp_username = all_token_key_session.woocommerce_admin_username
        wp_password = all_token_key_session.woocommerce_admin_password
        
        print(f"🔧 连接到WooCommerce商店: {site_url}")
        setup = TestProductSetup(site_url, consumer_key, consumer_secret, wp_username, wp_password)
        
        # 步骤1: 清理现有数据
        print("\n📋 步骤1: 清理商店中的现有数据")
        clear_result = setup.clear_all_products()
        if not clear_result.get('success'):
            print("⚠️ 清理未完全成功，但继续下一步...")
        
        time.sleep(3)
        
        # 步骤2: 设置商品属性
        print("\n📋 步骤2: 设置商品属性")
        attr_result = setup.setup_product_attributes()
        if not attr_result.get('success'):
            print("❌ 属性设置失败！")
            return False
        
        time.sleep(2)
        
        # 步骤3: 创建测试商品
        print("\n📋 步骤3: 创建测试商品和销量数据")
        product_result = setup.create_test_products()
        
        if product_result.get('success'):
            print("✅ 测试数据设置完成！")
            
            # 保存预期结果
            expected_results = setup.get_expected_results()
            results_path = task_dir / "groundtruth_workspace" / "expected_results.json"
            
            # 确保目录存在
            results_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(results_path, 'w', encoding='utf-8') as f:
                json.dump(expected_results, f, indent=2, ensure_ascii=False)
            print(f"📄 预期结果已保存到: {results_path}")
            
            return True
        else:
            print("❌ 测试商品创建失败！")
            return False
            
    except Exception as e:
        print(f"❌ 测试商品设置失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def clear_store_only():
    """仅清理商店数据"""
    print("🧹 清理WooCommerce商店数据...")
    
    try:
        # 确保能找到同目录下的模块
        import sys
        import os
        current_script_dir = os.path.dirname(os.path.abspath(__file__))
        if current_script_dir not in sys.path:
            sys.path.insert(0, current_script_dir)
        
        from setup_test_products import TestProductSetup
        from token_key_session import all_token_key_session
        
        # 从配置获取WooCommerce信息
        site_url = all_token_key_session.woocommerce_site_url
        consumer_key = all_token_key_session.woocommerce_api_key
        consumer_secret = all_token_key_session.woocommerce_api_secret
        wp_username = all_token_key_session.woocommerce_admin_username
        wp_password = all_token_key_session.woocommerce_admin_password
        
        print(f"🔧 连接到WooCommerce商店: {site_url}")
        setup = TestProductSetup(site_url, consumer_key, consumer_secret, wp_username, wp_password)
        
        clear_result = setup.clear_all_products()
        
        if clear_result.get('success'):
            print("✅ 商店清理完成")
            return True
        else:
            print("⚠️ 商店清理部分完成")
            return False
            
    except Exception as e:
        print(f"❌ 商店清理失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    parser = ArgumentParser(description="预处理脚本 - 设置更新商品主图任务的初始环境")
    parser.add_argument("--agent_workspace", required=False, help="Agent工作空间路径")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    
    args = parser.parse_args()

    print("=" * 60)
    print("🎯 更新商品主图任务 - 预处理")
    print("=" * 60)

    # 完整设置模式
    print("\n📋 步骤2: 设置测试商品和数据")
    success = setup_test_products()

    print("\n" + "=" * 60)
    print("📊 预处理结果汇总")
    print("=" * 60)
    print(f"✅ 测试数据设置: {'成功' if success else '失败'}")

    if success:
        print("\n🎉 预处理完成！更新商品主图系统已准备就绪")
        print("📝 下一步可以运行主图更新程序进行测试")
        print("\n📊 创建的测试数据包括:")
        print("   - 可变商品（彩虹运动鞋）")
        print("   - 多个颜色规格的变体")
        print("   - 模拟的上周销量数据")
        print("   - 预期的主图更新结果")
        exit(0)
    else:
        print("\n⚠️ 预处理部分完成，请检查错误信息")
        exit(1)
