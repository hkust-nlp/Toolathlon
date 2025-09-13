#!/usr/bin/env python3
"""
预处理脚本 - 设置库存预警任务的初始工作环境
"""

import os
import sys
import shutil
import json
import logging
from argparse import ArgumentParser
from pathlib import Path

# 添加项目路径
current_dir = Path(__file__).parent
task_dir = current_dir.parent
sys.path.insert(0, str(task_dir))

# 导入WooCommerce客户端和token配置
from woocommerce_client import WooCommerceClient
try:
    from token_key_session import all_token_key_session
except ImportError:
    print("⚠️ 无法导入token_key_session，请确保配置文件存在")
    all_token_key_session = None

def setup_logging():
    """设置日志"""
    logging.basicConfig(level=logging.INFO)
    return logging.getLogger(__name__)

def copy_initial_files_to_workspace(agent_workspace: str):
    """
    将初始文件复制到agent工作空间
    
    Args:
        agent_workspace: Agent工作空间路径
    """
    print(f"🚀 设置库存预警任务初始工作环境到: {agent_workspace}")
    
    # 确保工作空间目录存在
    os.makedirs(agent_workspace, exist_ok=True)
    
    # 定义需要复制的文件
    initial_workspace = task_dir / "initial_workspace"
    files_to_copy = [
        "woocommerce_products.json",
        "google_sheets_data.json", 
        "email_config.json",
        "monitoring_state.json"
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

def create_workspace_directories(agent_workspace: str):
    """创建必要的工作目录"""
    directories = ["logs", "reports"]
    for directory in directories:
        dir_path = Path(agent_workspace) / directory
        os.makedirs(dir_path, exist_ok=True)
        print(f"📁 创建目录: {directory}")

def setup_woocommerce_test_data():
    """设置WooCommerce测试数据"""
    logger = setup_logging()
    
    if not all_token_key_session:
        logger.error("❌ 无法获取WooCommerce配置信息")
        return False
    
    try:
        # 从token配置获取WooCommerce连接信息
        site_url = all_token_key_session.woocommerce_site_url
        api_key = all_token_key_session.woocommerce_api_key
        api_secret = all_token_key_session.woocommerce_api_secret
        
        print(f"🔗 连接到WooCommerce: {site_url}")
        
        # 创建WooCommerce客户端
        wc_client = WooCommerceClient(site_url, api_key, api_secret)
        
        # 测试连接
        if not wc_client.test_connection():
            logger.error("❌ WooCommerce连接测试失败")
            return False
        
        print("✅ WooCommerce连接测试成功")
        
        # 清理现有产品
        print("🧹 清理现有产品...")
        success, count = wc_client.clear_all_products()
        if success:
            print(f"✅ 清理完成，删除了 {count} 个现有产品")
        
        # 读取产品数据
        products_file = task_dir / "initial_workspace" / "woocommerce_products.json"
        if not products_file.exists():
            logger.error(f"❌ 产品数据文件不存在: {products_file}")
            return False
        
        with open(products_file, 'r', encoding='utf-8') as f:
            products_data = json.load(f)
        
        # 设置测试产品
        products_list = products_data.get('products', [])
        success, created_products = wc_client.setup_stock_alert_products(products_list)
        
        if success:
            print(f"✅ WooCommerce产品设置完成，创建了 {len(created_products)} 个测试产品")
            
            # 显示低库存产品信息
            low_stock_products = wc_client.get_low_stock_products()
            if low_stock_products:
                print(f"\n⚠️ 检测到 {len(low_stock_products)} 个低库存产品:")
                for product in low_stock_products:
                    print(f"   - {product['name']} (SKU: {product['sku']}) - 库存: {product['stock_quantity']}, 阈值: {product['stock_threshold']}")
            
            return True
        else:
            logger.error("❌ WooCommerce产品设置失败")
            return False
            
    except Exception as e:
        logger.error(f"设置WooCommerce测试数据时出错: {e}")
        return False

if __name__ == "__main__":
    parser = ArgumentParser(description="预处理脚本 - 设置库存预警任务的初始环境")
    parser.add_argument("--agent_workspace", required=True, help="Agent工作空间路径")
    parser.add_argument("--setup_wc", action="store_true", help="同时设置WooCommerce测试数据")
    parser.add_argument("--launch_time", required=False, help="Launch time")

    args = parser.parse_args()
    
    print("=" * 60)
    print("📦 库存预警监控系统 - 预处理")
    print("=" * 60)
    
    # 复制初始文件到工作空间
    success1 = copy_initial_files_to_workspace(args.agent_workspace)
    
    # 创建必要的目录结构
    create_workspace_directories(args.agent_workspace)
    
    # 设置WooCommerce测试数据
    success2 = True
    if args.setup_wc or True:  # 默认总是设置WooCommerce数据
        print("\n🛒 开始设置WooCommerce测试数据...")
        success2 = setup_woocommerce_test_data()
    
    if success1 and success2:
        print("\n🎉 预处理完成！库存预警系统工作空间已准备就绪")
        print("\n📋 工作空间包含以下文件:")
        print("  - woocommerce_products.json: WooCommerce商品数据")
        print("  - google_sheets_data.json: Google Sheets初始数据")
        print("  - email_config.json: 邮件发送配置")
        print("  - monitoring_state.json: 监控状态文件")
        print("\n🎯 任务目标:")
        print("  1. 检测低于安全阈值的库存产品")
        print("  2. 更新Google Sheets采购需求清单")
        print("  3. 发送邮件预警给采购经理")
        print("  4. 生成监控报告")
        print("\n🔧 WooCommerce配置:")
        if all_token_key_session:
            print(f"  - 站点URL: {all_token_key_session.woocommerce_site_url}")
            print(f"  - 已初始化测试产品")
        print("\n✨ 环境准备完成，可以开始库存预警任务！")
        exit(0)
    else:
        print("\n⚠️ 预处理部分完成，请检查错误信息")
        exit(1)