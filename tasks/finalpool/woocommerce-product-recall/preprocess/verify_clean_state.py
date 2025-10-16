#!/usr/bin/env python3
"""
WooCommerce Clean State Verification Tool
Verify whether the store has been fully cleaned
"""

import sys
import os
from typing import Dict, List

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
task_dir = os.path.dirname(current_dir)
sys.path.insert(0, task_dir)
sys.path.insert(0, current_dir)

from woocommerce_client import WooCommerceClient

def verify_clean_state(wc_client: WooCommerceClient) -> Dict:
    """
    Verify whether the WooCommerce store is in a clean state
    
    Args:
        wc_client: WooCommerce client instance
        
    Returns:
        A dictionary containing the verification result
    """
    print("🔍 Verifying WooCommerce store clean state...")
    
    verification_result = {
        "is_clean": True,
        "issues": [],
        "summary": {
            "products_count": 0,
            "orders_count": 0,
            "test_customers_count": 0,
            "custom_categories_count": 0
        }
    }
    
    # 1. Check products
    print("   Checking products...")
    products = wc_client.get_all_products()
    product_count = len(products)
    verification_result["summary"]["products_count"] = product_count
    
    if product_count > 0:
        verification_result["is_clean"] = False
        verification_result["issues"].append(f"{product_count} products have not been cleaned")
        print(f"   ❌ Found {product_count} products")
        
        # Show first 5 products as examples
        for i, product in enumerate(products[:5]):
            print(f"      - {product.get('name', 'Unknown')} (ID: {product.get('id')})")
        
        if product_count > 5:
            print(f"      ... {product_count - 5} more products")
    else:
        print("   ✅ All products cleaned")
    
    # 2. Check orders
    print("   Checking orders...")
    orders = wc_client.get_all_orders()
    order_count = len(orders)
    verification_result["summary"]["orders_count"] = order_count
    
    if order_count > 0:
        verification_result["is_clean"] = False
        verification_result["issues"].append(f"{order_count} orders have not been cleaned")
        print(f"   ❌ Found {order_count} orders")
    else:
        print("   ✅ All orders cleaned")
    
    # 3. Check test customers
    print("   Checking test customers...")
    try:
        success, customers = wc_client.list_customers(per_page=100)
        if success:
            test_customers = [c for c in customers if c.get('email', '').startswith('test_recall_')]
            test_customer_count = len(test_customers)
            verification_result["summary"]["test_customers_count"] = test_customer_count
            
            if test_customer_count > 0:
                verification_result["is_clean"] = False
                verification_result["issues"].append(f"{test_customer_count} test customers have not been cleaned")
                print(f"   ❌ Found {test_customer_count} test customers")
                for customer in test_customers:
                    print(f"      - {customer.get('email')}")
            else:
                print("   ✅ All test customers cleaned")
    except Exception as e:
        print(f"   ⚠️ Error checking customers: {e}")
    
    # 4. Check custom categories
    print("   Checking custom categories...")
    try:
        success, categories = wc_client.get_product_categories()
        if success:
            # Filter out the default category
            custom_categories = [
                cat for cat in categories 
                if cat.get('id') != 15 and cat.get('slug') != 'uncategorized'
            ]
            custom_cat_count = len(custom_categories)
            verification_result["summary"]["custom_categories_count"] = custom_cat_count
            
            if custom_cat_count > 0:
                verification_result["is_clean"] = False
                verification_result["issues"].append(f"{custom_cat_count} custom categories have not been cleaned")
                print(f"   ❌ Found {custom_cat_count} custom categories")
                for cat in custom_categories[:3]:  # Show first 3
                    print(f"      - {cat.get('name')} (ID: {cat.get('id')})")
            else:
                print("   ✅ All custom categories cleaned")
    except Exception as e:
        print(f"   ⚠️ Error checking categories: {e}")
    
    # Print verification result
    print("\n📊 Verification Result:")
    if verification_result["is_clean"]:
        print("✅ Store is fully clean and ready for initialization")
    else:
        print("❌ Store is not completely clean, issues found:")
        for issue in verification_result["issues"]:
            print(f"   - {issue}")
    
    return verification_result

def main():
    """Main function - verify clean state independently"""
    try:
        from token_key_session import all_token_key_session
        
        site_url = all_token_key_session.woocommerce_site_url
        consumer_key = all_token_key_session.woocommerce_api_key
        consumer_secret = all_token_key_session.woocommerce_api_secret
        
    except ImportError:
        print("❌ Could not find token_key_session configuration file")
        return False
    
    print("🔍 WooCommerce Clean State Verification Tool")
    print("=" * 50)
    
    wc_client = WooCommerceClient(site_url, consumer_key, consumer_secret)
    result = verify_clean_state(wc_client)
    
    return result["is_clean"]

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)