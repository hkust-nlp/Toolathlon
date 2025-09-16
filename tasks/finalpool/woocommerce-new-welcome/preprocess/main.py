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

def wait_for_table_availability(client: bigquery.Client, table_id: str, max_wait_time: int = 30):
    """
    Wait for BigQuery table to become fully available after creation
    """
    import time

    print(f"⏳ 等待表 {table_id} 完全可用...")
    start_time = time.time()

    while time.time() - start_time < max_wait_time:
        try:
            # Try to get the table - this verifies it's fully available
            table = client.get_table(table_id)
            # Also try a simple query to make sure it's really ready
            query = f"SELECT COUNT(*) as row_count FROM `{table_id}` LIMIT 1"
            query_job = client.query(query)
            list(query_job.result())
            print(f"✅ 表 {table_id} 已完全可用")
            return table
        except Exception as e:
            print(f"   表仍不可用: {e}")
            time.sleep(2)

    print(f"⚠️  等待表可用超时 ({max_wait_time}秒)")
    return None

def wait_for_dataset_deletion(client: bigquery.Client, dataset_id: str, max_wait_time: int = 30):
    """
    Wait for BigQuery dataset deletion to complete
    """
    import time

    print(f"⏳ 等待数据集 {dataset_id} 完全删除...")
    start_time = time.time()

    while time.time() - start_time < max_wait_time:
        try:
            # Try to get the dataset - if it still exists, deletion isn't complete
            client.get_dataset(dataset_id)
            print(f"   数据集仍然存在，继续等待...")
            time.sleep(2)
        except NotFound:
            # Dataset is truly gone
            print(f"✅ 数据集 {dataset_id} 已完全删除")
            return True
        except Exception as e:
            print(f"⚠️  检查数据集状态时出错: {e}")
            time.sleep(2)

    print(f"⚠️  等待超时 ({max_wait_time}秒)，继续执行...")
    return False

def setup_or_clear_dataset(client: bigquery.Client, project_id: str):
    """
    Setup or clear existing woocommerce_crm dataset
    - If dataset exists: clear all table contents but keep the dataset and tables
    - If dataset doesn't exist: create it (tables will be created later)
    """
    dataset_id = f"{project_id}.woocommerce_crm"
    print(f"🧹 检查并设置数据集: {dataset_id}")

    try:
        # Try to get dataset info to see if it exists
        try:
            dataset = client.get_dataset(dataset_id)
            print(f"ℹ️  找到现有数据集: {dataset_id}")

            # List all tables in the dataset
            tables = list(client.list_tables(dataset_id))
            if tables:
                print(f"ℹ️  数据集包含 {len(tables)} 个表:")
                for table in tables:
                    print(f"   - {table.table_id}")

                # Clear contents of all tables instead of deleting them
                for table in tables:
                    table_id = f"{dataset_id}.{table.table_id}"
                    print(f"🗑️  清空表 {table.table_id} 的内容...")

                    # Use DELETE query to clear table contents
                    delete_query = f"DELETE FROM `{table_id}` WHERE true"
                    query_job = client.query(delete_query)
                    query_job.result()  # Wait for completion

                    print(f"✅ 已清空表 {table.table_id}")
            else:
                print(f"ℹ️  数据集为空，无需清理")

        except NotFound:
            print(f"ℹ️  数据集 {dataset_id} 不存在，将创建新数据集")
            # Create the dataset since it doesn't exist
            dataset = bigquery.Dataset(dataset_id)
            dataset.location = "US"
            dataset.description = "WooCommerce CRM dataset for customer management and welcome emails"
            client.create_dataset(dataset, timeout=30)
            print(f"✅ 数据集 '{dataset.dataset_id}' 已成功创建")

    except Exception as e:
        print(f"❌ 数据集设置过程出错: {e}")
        logger.exception("Dataset setup failed")
        raise

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
        
        # Wait for deletion to propagate - BigQuery deletion is asynchronous
        wait_for_dataset_deletion(client, dataset_id)
        
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

        # Setup or clear existing dataset (don't delete it)
        setup_or_clear_dataset(client, project_id)

        # Create dataset if needed (handled in setup_or_clear_dataset)
        dataset_id = f"{project_id}.woocommerce_crm"

        # Create customers table (or skip if exists)
        table_id_customers = f"{dataset_id}.customers"
        print(f"🗂️  检查并创建表: {table_id_customers}")
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

        # Get table reference for data insertion
        print(f"📋 获取表引用...")
        table_ref = client.get_table(table_id_customers)
        print(f"✅ 获取到表引用: {table_ref.table_id}")

        # Insert JSON data into BigQuery
        if json_data:
            print(f"💾 插入 {len(json_data)} 条客户数据到 BigQuery...")
            try:
                # Use the table reference we already verified is available
                print(f"✅ 使用已验证的表引用: {table_ref.table_id}")

                # **ALTERNATIVE APPROACH: Use load_table_from_json instead of insert_rows_json**
                # This bypasses potential caching issues with streaming inserts
                print("🔄 尝试使用批量加载而非流式插入...")

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

                # Use load_table_from_json instead of insert_rows_json
                job_config = bigquery.LoadJobConfig(
                    write_disposition="WRITE_TRUNCATE",  # Overwrite existing data
                    source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
                )

                load_job = client.load_table_from_json(
                    bigquery_rows, table_ref, job_config=job_config
                )

                print(f"   开始批量加载作业: {load_job.job_id}")
                load_job.result()  # Wait for the job to complete

                print(f"🎉 成功批量加载 {len(bigquery_rows)} 条客户数据到 customers 表")
                
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