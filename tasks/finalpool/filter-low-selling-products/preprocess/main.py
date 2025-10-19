#!/usr/bin/env python3
"""
Preprocessing Script - Set up initial working environment
"""

import os
import sys
import shutil
from argparse import ArgumentParser
from pathlib import Path

# Add project path
current_dir = Path(__file__).parent
task_dir = current_dir.parent
sys.path.insert(0, str(task_dir))

def setup_woocommerce_test_data():
    """Set up WooCommerce test data"""
    print("🛒 Setting up WooCommerce test product data...")
    
    try:
        # Ensure the module in the same directory can be found
        import sys
        import os
        current_script_dir = os.path.dirname(os.path.abspath(__file__))
        if current_script_dir not in sys.path:
            sys.path.insert(0, current_script_dir)
        
        from setup_test_products import main as setup_test_main
        success = setup_test_main()
        if success:
            print("✅ WooCommerce test data setup completed")
        else:
            print("⚠️ WooCommerce test data setup partially completed")
        return success
    except Exception as e:
        print(f"❌ WooCommerce test data setup failed: {e}")
        return False

if __name__ == "__main__":
    parser = ArgumentParser(description="Preprocessing Script - Initialize workspace for low-selling product filter task")
    parser.add_argument("--agent_workspace", required=True, help="Agent workspace path")
    parser.add_argument("--launch_time", required=False, help="Launch time")

    args = parser.parse_args()
    
    print("=" * 60)
    print("🎯 Low-selling Product Filter Task - Preprocessing")
    print("=" * 60)
    
    success2 = setup_woocommerce_test_data()
    
    if success2:
        print("\n🎉 Preprocessing completed! Agent workspace is ready.")
        exit(0)
    else:
        print("\n⚠️ Preprocessing partially completed, please check the error messages.")
        exit(1)