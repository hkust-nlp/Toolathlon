#!/usr/bin/env python3
"""
预处理脚本 - 设置库存同步任务的初始环境
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
    
    # 定义需要复制的文件和目录
    initial_workspace = task_dir / "initial_workspace"
    items_to_copy = [
        #"inventory_sync.py",
        "warehouse",  # 数据库目录
        #"config.json"
    ]
    
    copied_count = 0
    for item_name in items_to_copy:
        source_path = initial_workspace / item_name
        dest_path = Path(agent_workspace) / item_name
        
        if source_path.exists():
            try:
                if source_path.is_dir():
                    # 复制目录
                    if dest_path.exists():
                        shutil.rmtree(dest_path)
                    shutil.copytree(source_path, dest_path)
                    print(f"✅ 复制目录: {item_name}")
                else:
                    # 复制文件
                    shutil.copy2(source_path, dest_path)
                    print(f"✅ 复制文件: {item_name}")
                copied_count += 1
            except Exception as e:
                print(f"❌ 复制失败 {item_name}: {e}")
        else:
            print(f"⚠️ 源文件/目录不存在: {item_name}")
    
    print(f"📊 初始环境设置完成: 成功复制 {copied_count} 个项目")
    return copied_count > 0

def setup_woocommerce_store():
    """设置WooCommerce商店和产品数据"""
    print("🛒 初始化WooCommerce商店...")
    
    try:
        # 确保能找到同目录下的模块
        import sys
        import os
        current_script_dir = os.path.dirname(os.path.abspath(__file__))
        if current_script_dir not in sys.path:
            sys.path.insert(0, current_script_dir)
        
        from woocommerce_initializer import main as wc_initializer_main
        print("🔧 开始WooCommerce商店初始化...")
        
        # 执行WooCommerce初始化
        result = wc_initializer_main()
        
        if result and result.get("success", False):
            print("✅ WooCommerce商店初始化完成")
            return True
        else:
            print("⚠️ WooCommerce商店初始化部分完成或失败")
            print(result)
            if result and "errors" in result:
                for error in result["errors"]:
                    print(f"   ❌ {error}")
            return False
            
    except Exception as e:
        print(f"❌ WooCommerce商店初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def setup_warehouse_databases():
    """设置仓库数据库"""
    print("🏢 初始化仓库数据库...")
    
    try:
        # 确保能找到同目录下的模块
        import sys
        import os
        current_script_dir = os.path.dirname(os.path.abspath(__file__))
        if current_script_dir not in sys.path:
            sys.path.insert(0, current_script_dir)
        
        from database_setup import create_all_warehouse_databases, clear_all_databases
        
        print("🗑️ 清理现有数据库...")
        clear_all_databases()
        
        print("🔧 开始创建仓库数据库...")
        created_databases = create_all_warehouse_databases()
        
        if created_databases and len(created_databases) > 0:
            print("✅ 仓库数据库初始化完成")
            print(f"   📊 创建了 {len(created_databases)} 个城市的数据库")
            return True
        else:
            print("❌ 仓库数据库初始化失败")
            return False
            
    except Exception as e:
        print(f"❌ 仓库数据库初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_woocommerce_config():
    """创建WooCommerce配置文件"""
    print("📝 创建WooCommerce配置文件...")
    
    try:
        # 确保能找到token_key_session模块
        from token_key_session import all_token_key_session
        import json
        from datetime import datetime
        
        config_data = {
            "site_url": all_token_key_session.woocommerce_site_url,
            "consumer_key": all_token_key_session.woocommerce_api_key,
            "consumer_secret": all_token_key_session.woocommerce_api_secret,
            "initialization_date": datetime.now().isoformat(),
            "product_mapping": {},
            "categories": {},
            "products": {}
        }
        
        config_file = all_token_key_session.woocommerce_config_file
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 配置文件已创建: {config_file}")
        return True
        
    except Exception as e:
        print(f"❌ 创建配置文件失败: {e}")
        return False

if __name__ == "__main__":
    parser = ArgumentParser(description="预处理脚本 - 设置库存同步任务的初始环境")
    parser.add_argument("--agent_workspace", required=True, help="Agent工作空间路径")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    

    args = parser.parse_args()
    
    print("=" * 60)
    print("🎯 库存同步任务 - 预处理")
    print("=" * 60)
    
    success_setup_store = setup_woocommerce_store()
    success_setup_warehouse = setup_warehouse_databases()
    success_copy_file = copy_initial_files_to_workspace(args.agent_workspace)

    if success_setup_store and success_setup_warehouse and success_copy_file:
        print("\n🎉 预处理完成！库存同步系统已准备就绪")
        print("📝 下一步可以运行库存同步程序进行测试")
        exit(0)
    else:
        print("\n⚠️ 预处理部分完成，请检查错误信息")
        exit(1)
