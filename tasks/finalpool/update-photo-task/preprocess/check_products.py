#!/usr/bin/env python3
"""
快速检查 WooCommerce 产品状态的脚本
用于调试评估脚本找不到产品的问题
"""

import sys
import os
from pathlib import Path

# 添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
task_dir = os.path.dirname(current_dir)
sys.path.append(task_dir)

from preprocess.woocommerce_client import WooCommerceClient, add_woocommerce_extensions

def check_products():
    """检查当前商店中的产品状态"""
    try:
        from token_key_session import all_token_key_session
        
        site_url = all_token_key_session.woocommerce_site_url
        consumer_key = all_token_key_session.woocommerce_api_key
        consumer_secret = all_token_key_session.woocommerce_api_secret
        
        print(f"🔍 检查商店产品状态: {site_url}")
        
        wc_client = add_woocommerce_extensions(
            WooCommerceClient(site_url, consumer_key, consumer_secret)
        )
        
        # 获取所有产品（不同状态）
        statuses = ['publish', 'draft', 'private', 'pending']
        
        total_products = 0
        
        for status in statuses:
            print(f"\n📊 检查状态为 '{status}' 的产品:")
            
            success, products = wc_client._make_request('GET', 'products', params={
                'status': status,
                'per_page': 100
            })
            
            if success and products:
                product_count = len(products)
                total_products += product_count
                print(f"   找到 {product_count} 个产品")
                
                for product in products:
                    product_id = product.get('id')
                    product_name = product.get('name', 'Unknown')
                    product_type = product.get('type', 'unknown')
                    date_created = product.get('date_created', 'unknown')
                    
                    print(f"   - ID: {product_id} | {product_name} | {product_type} | {date_created}")
                    
                    # 如果是可变商品，检查变体
                    if product_type == 'variable':
                        var_success, variations = wc_client._make_request('GET', f'products/{product_id}/variations')
                        if var_success and variations:
                            print(f"     └─ 有 {len(variations)} 个变体")
                        else:
                            print(f"     └─ 无变体或获取失败")
            else:
                print(f"   未找到产品或API调用失败")
        
        print(f"\n📈 总结:")
        print(f"   总产品数量: {total_products}")
        
        if total_products == 0:
            print("\n❌ 没有找到任何产品！")
            print("   可能的解决方案:")
            print("   1. 运行 python setup_test_products.py 创建测试产品")
            print("   2. 检查 WooCommerce API 连接")
            print("   3. 检查 API 密钥和权限")
        else:
            print(f"\n✅ 找到产品，评估脚本应该能够检测到它们")
            
            # 检查是否有 variable 产品
            success, all_products = wc_client._make_request('GET', 'products', params={'per_page': 100})
            if success and all_products:
                variable_products = [p for p in all_products if p.get('type') == 'variable']
                print(f"   其中 {len(variable_products)} 个是可变商品 (评估需要)")
        
        return total_products > 0
        
    except Exception as e:
        print(f"❌ 检查过程中出错: {e}")
        return False

if __name__ == "__main__":
    check_products() 