#!/usr/bin/env python3
"""
Preprocessing Script - Set up initial environment for update product cover task
"""

import os
import sys
import json
import time
from argparse import ArgumentParser
from pathlib import Path
from datetime import datetime

# Add project path
current_dir = Path(__file__).parent
task_dir = current_dir.parent
sys.path.insert(0, str(task_dir))

def setup_test_products():
    """Set up test products and data"""
    print("🛒 Initializing test products and sales data...")
    
    try:
        # Ensure modules in the same directory can be found
        import sys
        import os
        current_script_dir = os.path.dirname(os.path.abspath(__file__))
        if current_script_dir not in sys.path:
            sys.path.insert(0, current_script_dir)
        
        from setup_test_products import TestProductSetup
        from token_key_session import all_token_key_session
        
        # Get WooCommerce information from configuration
        site_url = all_token_key_session.woocommerce_site_url
        consumer_key = all_token_key_session.woocommerce_api_key
        consumer_secret = all_token_key_session.woocommerce_api_secret
        wp_username = all_token_key_session.woocommerce_admin_username
        wp_password = all_token_key_session.woocommerce_admin_password
        
        print(f"🔧 Connect to WooCommerce store: {site_url}")
        setup = TestProductSetup(site_url, consumer_key, consumer_secret, wp_username, wp_password)
        
        # Step 1: Clean existing data
        print("\n📋 Step 1: Clean existing data in the store")
        clear_result = setup.clear_all_products()
        if not clear_result.get('success'):
            print("⚠️ Clean not fully successful, but continue to the next step...")
        
        time.sleep(3)
        
        # Step 2: Set product attributes
        print("\n📋 Step 2: Set product attributes")
        attr_result = setup.setup_product_attributes()
        if not attr_result.get('success'):
            print("❌ Attribute setting failed!")
            return False
        
        time.sleep(2)
        
        # Step 3: Create test products
        print("\n📋 Step 3: Create test products and data")
        product_result = setup.create_test_products()
        
        if product_result.get('success'):
            print("✅ Test data setup completed!")
            
            # Save expected results
            expected_results = setup.get_expected_results()
            results_path = task_dir / "groundtruth_workspace" / "expected_results.json"
            
            # Ensure directory exists
            results_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(results_path, 'w', encoding='utf-8') as f:
                json.dump(expected_results, f, indent=2, ensure_ascii=False)
            print(f"📄 Expected results saved to: {results_path}")
            
            return True
        else:
            print("❌ Test product creation failed!")
            return False
            
    except Exception as e:
        print(f"❌ Test product setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def clear_store_only():
    """Only clear store data"""
    print("🧹 Clean WooCommerce store data...")
    
    try:
        # Ensure modules in the same directory can be found
        import sys
        import os
        current_script_dir = os.path.dirname(os.path.abspath(__file__))
        if current_script_dir not in sys.path:
            sys.path.insert(0, current_script_dir)
        
        from setup_test_products import TestProductSetup
        from token_key_session import all_token_key_session
        
        # Get WooCommerce information from configuration
        site_url = all_token_key_session.woocommerce_site_url
        consumer_key = all_token_key_session.woocommerce_api_key
        consumer_secret = all_token_key_session.woocommerce_api_secret
        wp_username = all_token_key_session.woocommerce_admin_username
        wp_password = all_token_key_session.woocommerce_admin_password
        
        print(f"🔧 Connect to WooCommerce store: {site_url}")
        setup = TestProductSetup(site_url, consumer_key, consumer_secret, wp_username, wp_password)
        
        clear_result = setup.clear_all_products()
        
        if clear_result.get('success'):
            print("✅ Store clear completed")
            return True
        else:
            print("⚠️ Store clear partially completed")
            return False
            
    except Exception as e:
        print(f"❌ Store clear failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    parser = ArgumentParser(description="Preprocessing script - set up initial environment for update product cover task")
    parser.add_argument("--agent_workspace", required=False, help="Agent workspace path")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    
    args = parser.parse_args()

    print("=" * 60)
    print("🎯 Update product cover task - preprocessing")
    print("=" * 60)

    # Full setup mode
    print("\n📋 Step 2: Set up test products and data")
    success = setup_test_products()

    print("\n" + "=" * 60)
    print("📊 Preprocessing result summary")
    print("=" * 60)
    print(f"✅ Test data setup: {'success' if success else 'failed'}")

    if success:
        print("\n🎉 Preprocessing completed! Update product cover system is ready")
        print("📝 Next, you can run the update product cover program to test")
        print("\n📊 The test data includes:")
        print("   - Variable products (rainbow sneakers)")
        print("   - Multiple color variations")
        print("   - Simulated last week's sales data")
        print("   - Expected update product cover results")
        exit(0)
    else:
        print("\n⚠️ Preprocessing partially completed, please check the error information")
        exit(1)
