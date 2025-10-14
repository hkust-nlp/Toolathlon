#!/usr/bin/env python3
"""
"""

import os
import sys
import shutil
from argparse import ArgumentParser
from pathlib import Path
import random
random.seed(42)

current_dir = Path(__file__).parent
task_dir = current_dir.parent
sys.path.insert(0, str(task_dir))

def copy_initial_files_to_workspace(agent_workspace: str):
    """
    Copy initial files to agent workspace
    
    Args:
        agent_workspace:
    """
    print(f"🚀 Setting initial workspace to: {agent_workspace}")
    
    # Ensure workspace directory exists
    os.makedirs(agent_workspace, exist_ok=True)
    
    # Define files and directories to copy
    initial_workspace = task_dir / "initial_workspace"
    items_to_copy = [
        #"inventory_sync.py",
        "warehouse",  # Database directory
        #"config.json"
    ]
    
    copied_count = 0
    for item_name in items_to_copy:
        source_path = initial_workspace / item_name
        dest_path = Path(agent_workspace) / item_name
        
        if source_path.exists():
            try:
                if source_path.is_dir():
                    # Copy directory
                    if dest_path.exists():
                        shutil.rmtree(dest_path)
                    shutil.copytree(source_path, dest_path)
                    print(f"✅ Copied directory: {item_name}")
                else:
                    # Copy file
                    shutil.copy2(source_path, dest_path)
                    print(f"✅ Copied file: {item_name}")
                copied_count += 1
            except Exception as e:
                print(f"❌ Copy failed {item_name}: {e}")
        else:
            print(f"⚠️ Source file/directory does not exist: {item_name}")
    
    print(f"📊 Initial environment setup completed: successfully copied {copied_count} items")
    return copied_count > 0

def setup_woocommerce_store():
    """Setup WooCommerce store and product data"""
    print("🛒 Initializing WooCommerce store...")
    
    try:
        # Ensure module is found in the same directory
        import sys
        import os
        current_script_dir = os.path.dirname(os.path.abspath(__file__))
        if current_script_dir not in sys.path:
            sys.path.insert(0, current_script_dir)
        
        from woocommerce_initializer import main as wc_initializer_main
        print("🔧 Starting WooCommerce store initialization...")
        
        # Execute WooCommerce initialization
        result = wc_initializer_main()
        
        if result and result.get("success", False):
            print("✅ WooCommerce store initialization completed")
            return True
        else:
            print("⚠️ WooCommerce store initialization partially completed or failed")
            print(result)
            if result and "errors" in result:
                for error in result["errors"]:
                    print(f"   ❌ {error}")
            return False
            
    except Exception as e:
        print(f"❌ WooCommerce store initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def setup_warehouse_databases():
    """Setup warehouse databases"""
    print("🏢 Initializing warehouse databases...")
    
    try:
        # Ensure module is found in the same directory
        import sys
        import os
        current_script_dir = os.path.dirname(os.path.abspath(__file__))
        if current_script_dir not in sys.path:
            sys.path.insert(0, current_script_dir)
        
        from database_setup import create_all_warehouse_databases, clear_all_databases
        
        print("🗑️ Clearing existing databases...")
        clear_all_databases()
        
        print("🔧 Starting to create warehouse databases...")
        created_databases = create_all_warehouse_databases()
        
        if created_databases and len(created_databases) > 0:
            print("✅ Warehouse database initialization completed")
            print(f"   📊 Created {len(created_databases)} databases for cities")
            return True
        else:
            print("❌ Warehouse database initialization failed")
            return False
            
    except Exception as e:
        print(f"❌ Warehouse database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_woocommerce_config():
    """Create WooCommerce configuration file"""
    print("📝 Creating WooCommerce configuration file...")
    
    try:
        # Ensure token_key_session module is found
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
        
        print(f"✅ Configuration file created: {config_file}")
        return True
        
    except Exception as e:
        print(f"❌ Creating configuration file failed: {e}")
        return False

if __name__ == "__main__":
    parser = ArgumentParser(description="Preprocess script - Setup inventory sync task initial environment")
    parser.add_argument("--agent_workspace", required=True, help="Agent workspace path")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    

    args = parser.parse_args()
    
    print("=" * 60)
    print("🎯 Inventory sync task - Preprocess")
    print("=" * 60)
    
    success_setup_store = setup_woocommerce_store()
    success_setup_warehouse = setup_warehouse_databases()
    success_copy_file = copy_initial_files_to_workspace(args.agent_workspace)

    if success_setup_store and success_setup_warehouse and success_copy_file:
        print("\n🎉 Preprocess completed! Inventory sync system is ready")
        print("📝 Next, you can run inventory sync program to test")
        exit(0)
    else:
        print("\n⚠️ Preprocess partially completed, please check error information")
        exit(1)
