#!/usr/bin/env python3
"""
Import JSON test data to BigQuery for WooCommerce new customer welcome task
"""

import json
from pathlib import Path
from datetime import datetime
import sys
import os

# Add paths for imports
current_dir = Path(__file__).parent
task_dir = current_dir.parent
sys.path.insert(0, str(task_dir))
sys.path.insert(0, str(current_dir))

from customer_database_bigquery import CustomerDatabase

def import_json_data_to_bigquery():
    """Import test data from JSON files to BigQuery"""
    print("🔄 IMPORTING JSON TEST DATA TO BIGQUERY")
    print("=" * 60)
    
    # Read the new customers JSON data
    json_file = current_dir / "new_customers.json"
    if not json_file.exists():
        print(f"❌ JSON文件不存在: {json_file}")
        return False
        
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            customers_data = json.load(f)
            
        print(f"📖 成功读取 {len(customers_data)} 个客户记录")
        
        # Initialize BigQuery database
        db = CustomerDatabase()
        print("✅ BigQuery连接初始化成功")
        
        # Import each customer
        imported_count = 0
        for customer in customers_data:
            # Transform the data to match our BigQuery schema
            customer_record = {
                'woocommerce_id': customer['id'],
                'email': customer['email'],
                'first_name': customer.get('first_name', ''),
                'last_name': customer.get('last_name', ''),
                'phone': '',  # Not in JSON data
                'date_created': customer.get('date_created'),
                'first_order_date': customer.get('first_order_date', customer.get('date_created')),
                'welcome_email_sent': False,
                'welcome_email_date': None,
                'sync_date': datetime.now().isoformat(),
                'metadata': {
                    'source': 'json_import',
                    'import_date': datetime.now().isoformat()
                }
            }
            
            if db.add_customer(customer_record):
                imported_count += 1
                print(f"   ✅ 导入客户: {customer['email']} (ID: {customer['id']})")
            else:
                print(f"   ❌ 导入失败: {customer['email']}")
        
        print(f"\n🎉 成功导入 {imported_count}/{len(customers_data)} 个客户到BigQuery")
        
        # Verify import by getting statistics
        stats = db.get_statistics()
        print(f"\n📊 BigQuery数据库统计:")
        print(f"   - 总客户数: {stats['total_customers']}")
        print(f"   - 新客户(7天): {stats['new_customers_7_days']}")
        print(f"   - 已发送欢迎邮件: {stats['welcome_emails_sent']}")
        print(f"   - 待发送邮件: {stats['pending_welcome_emails']}")
        
        return imported_count > 0
        
    except Exception as e:
        print(f"❌ 导入过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_data_import():
    """Verify that data was imported correctly"""
    print("\n🔍 VERIFYING DATA IMPORT")
    print("-" * 30)
    
    try:
        db = CustomerDatabase()
        
        # Test customer lookup
        test_emails = [
            "new.customer1@example.com",
            "new.customer2@example.com", 
            "new.customer3@example.com",
            "new.customer4@example.com"
        ]
        
        found_count = 0
        for email in test_emails:
            customer = db.get_customer_by_email(email)
            if customer:
                found_count += 1
                print(f"   ✅ 找到客户: {email}")
            else:
                print(f"   ❌ 未找到客户: {email}")
        
        print(f"\n📊 验证结果: {found_count}/{len(test_emails)} 个测试客户已导入")
        
        return found_count == len(test_emails)
        
    except Exception as e:
        print(f"❌ 验证过程中出错: {e}")
        return False

if __name__ == "__main__":
    print("🚀 开始导入WooCommerce测试数据到BigQuery")
    print("=" * 70)
    
    success = import_json_data_to_bigquery()
    
    if success:
        verify_success = verify_data_import()
        if verify_success:
            print("\n🎉 数据导入和验证完全成功！")
            print("现在BigQuery中包含了测试客户数据，evaluation应该能够正常工作。")
            sys.exit(0)
        else:
            print("\n⚠️  数据导入成功，但验证失败")
            sys.exit(1)
    else:
        print("\n❌ 数据导入失败")
        sys.exit(1)