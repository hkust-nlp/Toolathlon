#!/usr/bin/env python3
"""
WooCommerce清理状态验证工具
验证商店是否已完全清理干净
"""

import sys
import os
from typing import Dict, List

# 添加路径
current_dir = os.path.dirname(os.path.abspath(__file__))
task_dir = os.path.dirname(current_dir)
sys.path.insert(0, task_dir)
sys.path.insert(0, current_dir)

from woocommerce_client import WooCommerceClient

def verify_clean_state(wc_client: WooCommerceClient) -> Dict:
    """
    验证WooCommerce商店是否处于清洁状态
    
    Args:
        wc_client: WooCommerce客户端
        
    Returns:
        验证结果字典
    """
    print("🔍 验证WooCommerce商店清理状态...")
    
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
    
    # 1. 检查商品
    print("   检查商品...")
    products = wc_client.get_all_products()
    product_count = len(products)
    verification_result["summary"]["products_count"] = product_count
    
    if product_count > 0:
        verification_result["is_clean"] = False
        verification_result["issues"].append(f"仍有 {product_count} 个商品未清理")
        print(f"   ❌ 发现 {product_count} 个商品")
        
        # 显示前5个商品作为示例
        for i, product in enumerate(products[:5]):
            print(f"      - {product.get('name', 'Unknown')} (ID: {product.get('id')})")
        
        if product_count > 5:
            print(f"      ... 还有 {product_count - 5} 个商品")
    else:
        print("   ✅ 商品清理完成")
    
    # 2. 检查订单
    print("   检查订单...")
    orders = wc_client.get_all_orders()
    order_count = len(orders)
    verification_result["summary"]["orders_count"] = order_count
    
    if order_count > 0:
        verification_result["is_clean"] = False
        verification_result["issues"].append(f"仍有 {order_count} 个订单未清理")
        print(f"   ❌ 发现 {order_count} 个订单")
    else:
        print("   ✅ 订单清理完成")
    
    # 3. 检查测试客户
    print("   检查测试客户...")
    try:
        success, customers = wc_client.list_customers(per_page=100)
        if success:
            test_customers = [c for c in customers if c.get('email', '').startswith('test_recall_')]
            test_customer_count = len(test_customers)
            verification_result["summary"]["test_customers_count"] = test_customer_count
            
            if test_customer_count > 0:
                verification_result["is_clean"] = False
                verification_result["issues"].append(f"仍有 {test_customer_count} 个测试客户未清理")
                print(f"   ❌ 发现 {test_customer_count} 个测试客户")
                for customer in test_customers:
                    print(f"      - {customer.get('email')}")
            else:
                print("   ✅ 测试客户清理完成")
    except Exception as e:
        print(f"   ⚠️ 检查客户时出错: {e}")
    
    # 4. 检查自定义分类
    print("   检查自定义分类...")
    try:
        success, categories = wc_client.get_product_categories()
        if success:
            # 过滤掉默认分类
            custom_categories = [
                cat for cat in categories 
                if cat.get('id') != 15 and cat.get('slug') != 'uncategorized'
            ]
            custom_cat_count = len(custom_categories)
            verification_result["summary"]["custom_categories_count"] = custom_cat_count
            
            if custom_cat_count > 0:
                verification_result["is_clean"] = False
                verification_result["issues"].append(f"仍有 {custom_cat_count} 个自定义分类未清理")
                print(f"   ❌ 发现 {custom_cat_count} 个自定义分类")
                for cat in custom_categories[:3]:  # 显示前3个
                    print(f"      - {cat.get('name')} (ID: {cat.get('id')})")
            else:
                print("   ✅ 自定义分类清理完成")
    except Exception as e:
        print(f"   ⚠️ 检查分类时出错: {e}")
    
    # 输出验证结果
    print("\n📊 验证结果:")
    if verification_result["is_clean"]:
        print("✅ 商店已完全清理干净，可以开始初始化")
    else:
        print("❌ 商店清理不完整，发现以下问题:")
        for issue in verification_result["issues"]:
            print(f"   - {issue}")
    
    return verification_result

def main():
    """主函数 - 独立验证清理状态"""
    try:
        from token_key_session import all_token_key_session
        
        site_url = all_token_key_session.woocommerce_site_url
        consumer_key = all_token_key_session.woocommerce_api_key
        consumer_secret = all_token_key_session.woocommerce_api_secret
        
    except ImportError:
        print("❌ 未找到 token_key_session 配置文件")
        return False
    
    print("🔍 WooCommerce清理状态验证工具")
    print("=" * 50)
    
    wc_client = WooCommerceClient(site_url, consumer_key, consumer_secret)
    result = verify_clean_state(wc_client)
    
    return result["is_clean"]

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)