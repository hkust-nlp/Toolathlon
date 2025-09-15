import asyncio
from argparse import ArgumentParser
from pathlib import Path
from utils.general.helper import run_command, get_module_path
import os
import json
import logging
from datetime import datetime, date, timedelta
from google.cloud import bigquery
from google.oauth2 import service_account
from google.api_core.exceptions import Conflict, GoogleAPICallError, NotFound

# Enable verbose logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def read_json_data(json_path: str):
    """从JSON文件读取客户数据"""
    print(f"📖 正在读取JSON数据文件: {json_path}")
    
    if not Path(json_path).exists():
        print(f"❌ JSON数据文件不存在: {json_path}")
        return []
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            customers = json.load(f)
        
        # 确保数据格式正确
        processed_customers = []
        for customer in customers:
            processed_customer = {
                'id': customer.get('id'),
                'woocommerce_id': customer.get('woocommerce_id'),
                'email': customer.get('email'),
                'first_name': customer.get('first_name'),
                'last_name': customer.get('last_name'),
                'phone': customer.get('phone', ''),
                'date_created': customer.get('date_created'),
                'first_order_date': customer.get('first_order_date'),
                'welcome_email_sent': customer.get('welcome_email_sent', False),
                'welcome_email_date': customer.get('welcome_email_date'),
                'sync_date': customer.get('sync_date'),
                'metadata': customer.get('metadata', '{}')
            }
            processed_customers.append(processed_customer)
        
        print(f"✅ 成功读取 {len(processed_customers)} 条客户记录")
        return processed_customers
        
    except (json.JSONDecodeError, IOError) as e:
        print(f"❌ 读取JSON数据文件时出错: {e}")
        return []

def cleanup_existing_dataset(client: bigquery.Client, project_id: str):
    """
    Clean up existing woocommerce_crm dataset if it exists
    """
    dataset_id = f"{project_id}.woocommerce_crm"
    print(f"🧹 检查并清理现有数据集: {dataset_id}")
    
    try:
        # First try to get dataset info to see if it exists
        try:
            dataset = client.get_dataset(dataset_id)
            print(f"ℹ️  找到现有数据集: {dataset_id}")
            
            # List all tables in the dataset
            tables = list(client.list_tables(dataset_id))
            if tables:
                print(f"ℹ️  数据集包含 {len(tables)} 个表:")
                for table in tables:
                    print(f"   - {table.table_id}")
        except NotFound:
            print(f"ℹ️  数据集 {dataset_id} 不存在，无需清理")
            return
        
        # Delete dataset with all contents
        print(f"🗑️  删除数据集及其所有内容...")
        client.delete_dataset(
            dataset_id, 
            delete_contents=True, 
            not_found_ok=True
        )
        print(f"✅ 已成功清理数据集 '{dataset_id}' 及其所有内容")
        
        # Wait a moment for deletion to propagate
        import time
        time.sleep(2)
        
    except NotFound:
        print(f"ℹ️  数据集 {dataset_id} 不存在，无需清理")
    except Exception as e:
        print(f"❌ 数据集清理过程出错: {e}")
        logger.exception("Dataset cleanup failed")
        raise

def setup_bigquery_resources(credentials_path: str, project_id: str, json_data: list):
    """
    Setup BigQuery dataset and tables for WooCommerce CRM, then populate with JSON data
    """
    print("=" * 60)
    print("🛍️ 开始设置 BigQuery WooCommerce CRM 资源")
    print("=" * 60)
    
    try:
        print(f"🔗 正在使用凭证 '{credentials_path}' 连接到项目 '{project_id}'...")
        
        # Use the newer authentication method
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        client = bigquery.Client(credentials=credentials, project=project_id)
        
        print("✅ 连接成功！")
        
        # Test connection by listing datasets
        print("🔍 测试连接 - 列出现有数据集...")
        try:
            datasets = list(client.list_datasets())
            print(f"ℹ️  项目中现有 {len(datasets)} 个数据集")
            for dataset in datasets:
                print(f"   - {dataset.dataset_id}")
        except Exception as e:
            print(f"⚠️  列出数据集时出错: {e}")

        # Clean up existing dataset first
        cleanup_existing_dataset(client, project_id)

        # Create dataset
        dataset_id = f"{project_id}.woocommerce_crm"
        print(f"📊 创建数据集: {dataset_id}")
        try:
            dataset = bigquery.Dataset(dataset_id)
            dataset.location = "US"
            dataset.description = "WooCommerce CRM dataset for customer management and welcome emails"
            client.create_dataset(dataset, timeout=30)
            print(f"✅ 数据集 '{dataset.dataset_id}' 已成功创建。")
        except Conflict:
            print(f"ℹ️  数据集 '{dataset_id}' 已存在，跳过创建。")
        except Exception as e:
            print(f"❌ 创建数据集失败: {e}")
            logger.exception("Dataset creation failed")
            raise

        # Create customers table
        table_id_customers = f"{dataset_id}.customers"
        print(f"🗂️  创建表: {table_id_customers}")
        schema_customers = [
            bigquery.SchemaField("id", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("woocommerce_id", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("email", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("first_name", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("last_name", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("phone", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("date_created", "TIMESTAMP", mode="NULLABLE"),
            bigquery.SchemaField("first_order_date", "TIMESTAMP", mode="NULLABLE"),
            bigquery.SchemaField("welcome_email_sent", "BOOLEAN", mode="NULLABLE"),
            bigquery.SchemaField("welcome_email_date", "TIMESTAMP", mode="NULLABLE"),
            bigquery.SchemaField("sync_date", "TIMESTAMP", mode="NULLABLE"),
            bigquery.SchemaField("metadata", "STRING", mode="NULLABLE"),
        ]
        table_customers = bigquery.Table(table_id_customers, schema=schema_customers)
        try:
            client.create_table(table_customers)
            print(f"✅ 表 '{table_id_customers}' 已成功创建。")
        except Conflict:
            print(f"ℹ️  表 '{table_id_customers}' 已存在，跳过创建。")
        except Exception as e:
            print(f"❌ 创建表 '{table_id_customers}' 失败: {e}")
            raise

        # Insert JSON data into BigQuery
        if json_data:
            print(f"💾 插入 {len(json_data)} 条客户数据到 BigQuery...")
            try:
                table_ref = client.get_table(table_id_customers)
                print(f"✅ 获取到表引用: {table_ref.table_id}")
                
                # Convert JSON data for BigQuery
                bigquery_rows = []
                for customer in json_data:
                    # Convert datetime strings to proper format
                    def convert_timestamp(timestamp_str):
                        if not timestamp_str:
                            return None
                        try:
                            # Try to parse various timestamp formats
                            if 'T' in timestamp_str:
                                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')).isoformat()
                            else:
                                return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S').isoformat()
                        except ValueError:
                            return None
                    
                    bigquery_row = {
                        "id": customer['id'],
                        "woocommerce_id": customer['woocommerce_id'],
                        "email": customer['email'],
                        "first_name": customer['first_name'],
                        "last_name": customer['last_name'],
                        "phone": customer['phone'],
                        "date_created": convert_timestamp(customer['date_created']),
                        "first_order_date": convert_timestamp(customer['first_order_date']),
                        "welcome_email_sent": customer['welcome_email_sent'],
                        "welcome_email_date": convert_timestamp(customer['welcome_email_date']),
                        "sync_date": convert_timestamp(customer['sync_date']),
                        "metadata": customer['metadata']
                    }
                    bigquery_rows.append(bigquery_row)
                
                # Insert data in batches
                batch_size = 100
                total_inserted = 0
                for i in range(0, len(bigquery_rows), batch_size):
                    batch = bigquery_rows[i:i + batch_size]
                    print(f"   插入批次 {i//batch_size + 1}: {len(batch)} 条记录...")
                    
                    errors = client.insert_rows_json(table_ref, batch)
                    if errors:
                        print(f"❌ 批次 {i//batch_size + 1} 插入错误: {errors}")
                        for error in errors:
                            logger.error(f"Insert error: {error}")
                        raise Exception(f"批次插入失败: {errors}")
                    else:
                        total_inserted += len(batch)
                        print(f"   ✅ 批次 {i//batch_size + 1} 成功插入 {len(batch)} 条记录")
                
                print(f"🎉 成功插入总计 {total_inserted} 条客户数据到 customers 表")
                
                # Verify data insertion
                print("🔍 验证数据插入...")
                query = f"""
                SELECT COUNT(*) as total_rows, 
                       COUNT(DISTINCT woocommerce_id) as unique_customers,
                       COUNT(CASE WHEN welcome_email_sent = true THEN 1 END) as emails_sent
                FROM `{table_id_customers}`
                """
                query_job = client.query(query)
                results = list(query_job.result())
                if results:
                    result = results[0]
                    print(f"✅ 验证成功: {result.total_rows} 行数据, {result.unique_customers} 个独特客户, {result.emails_sent} 封邮件已发送")
                else:
                    print("⚠️  验证查询未返回结果")
                    
            except Exception as e:
                print(f"❌ 插入数据时出现错误: {e}")
                logger.exception("Data insertion failed")
                raise Exception(f"插入数据失败: {e}")
        else:
            print("⚠️  没有JSON数据可插入")

        return client, dataset_id

    except GoogleAPICallError as e:
        print(f"❌ Google Cloud API 调用失败: {e}")
        logger.exception("Google Cloud API call failed")
        raise
    except Exception as e:
        print(f"❌ 设置过程中发生错误: {e}")
        logger.exception("Setup process failed")
        raise

def get_project_id_from_key(credentials_path: str) -> str | None:
    """从服务账号密钥文件中读取项目ID"""
    try:
        with open(credentials_path, 'r') as f:
            data = json.load(f)
            return data.get("project_id")
    except (FileNotFoundError, json.JSONDecodeError):
        return None

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--credentials_file", default="configs/gcp-service_account.keys.json")
    parser.add_argument("--launch_time", required=False, help="Launch time (can contain spaces)")
    args = parser.parse_args()

    print("🛍️ 开始设置 BigQuery WooCommerce CRM 资源...")
    print("=" * 60)
    
    # Get credentials file path
    credentials_path = Path(args.credentials_file)
    
    # Make sure the path is absolute
    if not credentials_path.is_absolute():
        credentials_path = Path.cwd() / credentials_path
    
    if not credentials_path.exists():
        print(f"❌ 错误：凭证文件不存在: {credentials_path}")
        print("请确保服务账号密钥文件存在于指定路径")
        exit(1)
    else:
        print(f"✅ 找到凭证文件: {credentials_path}")
    
    # Get JSON data file path
    json_path = Path(os.path.join(os.path.dirname(__file__), "customers_data.json"))
    if not json_path.is_absolute():
        json_path = Path.cwd() / json_path
        
    print(f"📖 JSON数据文件路径: {json_path}")
    
    # Read JSON data
    json_data = read_json_data(str(json_path))
    
    project_id = get_project_id_from_key(str(credentials_path))
    
    if project_id:
        print(f"🆔 从凭证文件中成功读取项目ID: {project_id}")
        try:
            client, dataset_id = setup_bigquery_resources(str(credentials_path), project_id, json_data)
            print("\n" + "=" * 60)
            print("🎉 所有 BigQuery 资源设置完毕！")
            print("📊 已将JSON数据迁移到BigQuery")
            print("🎯 任务：代理需要同步新客户数据并发送欢迎邮件")
            print("=" * 60)
        except Exception as e:
            print(f"\n❌ 设置失败: {e}")
            exit(1)
    else:
        print(f"❌ 无法从凭证文件中读取项目ID。")
        exit(1)