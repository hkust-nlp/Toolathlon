#!/usr/bin/env python3
"""
Simple BigQuery data import using direct INSERT statements
"""

import json
from pathlib import Path
from datetime import datetime
import sys
from google.cloud import bigquery
from google.oauth2 import service_account

def import_with_direct_insert():
    """Import data using direct SQL INSERT statements"""
    print("🔄 IMPORTING WITH DIRECT INSERT")
    print("=" * 50)
    
    # Read JSON data
    current_dir = Path(__file__).parent
    json_file = current_dir / "new_customers.json"
    
    with open(json_file, 'r', encoding='utf-8') as f:
        customers_data = json.load(f)
    
    # Initialize BigQuery client
    credentials_path = "configs/gcp-service_account.keys.json"
    credentials = service_account.Credentials.from_service_account_file(credentials_path)
    client = bigquery.Client(credentials=credentials, project="mcp-bench0606")
    
    # Clear existing data first
    print("🧹 清除现有数据...")
    clear_query = "DELETE FROM `mcp-bench0606.woocommerce_crm.customers` WHERE 1=1"
    client.query(clear_query).result()
    
    # Insert each customer using simple INSERT
    imported_count = 0
    for customer in customers_data:
        insert_query = f"""
        INSERT INTO `mcp-bench0606.woocommerce_crm.customers` 
        (woocommerce_id, email, first_name, last_name, phone, 
         date_created, first_order_date, welcome_email_sent, 
         welcome_email_date, sync_date, metadata)
        VALUES (
            {customer['id']},
            '{customer['email']}',
            '{customer.get('first_name', '')}',
            '{customer.get('last_name', '')}',
            '',
            PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%S', '{customer.get('date_created')}'),
            PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%S', '{customer.get('first_order_date', customer.get('date_created'))}'),
            false,
            NULL,
            CURRENT_TIMESTAMP(),
            '{{"source": "json_import", "import_date": "{datetime.now().isoformat()}"}}'
        )
        """
        
        try:
            client.query(insert_query).result()
            imported_count += 1
            print(f"   ✅ 插入客户: {customer['email']} (ID: {customer['id']})")
        except Exception as e:
            print(f"   ❌ 插入失败: {customer['email']} - {e}")
    
    print(f"\n🎉 成功导入 {imported_count}/{len(customers_data)} 个客户")
    
    # Verify import
    verify_query = """
    SELECT COUNT(*) as total_customers,
           COUNT(CASE WHEN DATE(first_order_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) THEN 1 END) as recent_customers
    FROM `mcp-bench0606.woocommerce_crm.customers`
    """
    
    results = list(client.query(verify_query).result())
    if results:
        result = results[0]
        print(f"\n📊 验证结果:")
        print(f"   - 总客户数: {result.total_customers}")
        print(f"   - 最近客户数: {result.recent_customers}")
        
        return result.total_customers > 0
    
    return False

if __name__ == "__main__":
    success = import_with_direct_insert()
    sys.exit(0 if success else 1)