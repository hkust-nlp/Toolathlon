#!/usr/bin/env python3
"""
WooCommerce New Welcome Task - Preprocess Setup
设置初始工作环境：清空邮箱、设置WooCommerce订单数据、准备BigQuery环境
"""
import os
import sys
import json
import time
from argparse import ArgumentParser
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List

# Add parent directory to import token configuration
current_dir = os.path.dirname(os.path.abspath(__file__))
task_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(task_dir)))
sys.path.insert(0, task_dir)  # For token_key_session
sys.path.insert(0, project_root)  # For utils


def clear_mailbox() -> Dict:
    """
    清空邮箱 - 使用通用邮箱工具清理 INBOX, Sent, Drafts 文件夹

    Returns:
        清理结果字典
    """
    print("📧 开始清空邮箱...")

    try:
        # 导入配置
        from token_key_session import all_token_key_session

        # 读取邮件配置文件
        try:
            with open(all_token_key_session.emails_config_file, 'r', encoding='utf-8') as f:
                email_config = json.load(f)
        except Exception as e:
            print(f"❌ 无法读取邮件配置文件: {e}")
            return {
                "success": False,
                "error": f"无法读取邮件配置文件: {e}",
                "timestamp": datetime.now().isoformat()
            }

        # 延迟导入邮箱清理模块
        try:
            from utils.app_specific.poste.ops import setup_clean_mailbox_environment
        except ImportError as e:
            print(f"❌ 无法导入邮箱清理模块: {e}")
            return {
                "success": False,
                "error": f"无法导入邮箱清理模块: {e}",
                "timestamp": datetime.now().isoformat()
            }

        # 使用通用邮箱清理函数
        result = setup_clean_mailbox_environment(email_config)

        print(f"📊 邮箱清理结果:")
        if result["success"]:
            print(f"✅ 成功清理文件夹: {', '.join(result['cleared_folders'])}")
        else:
            print(f"⚠️ 部分文件夹清理失败:")
            for error in result.get("errors", []):
                print(f"   - {error}")

        return {
            "success": result["success"],
            "cleared_folders": result.get("cleared_folders", []),
            "failed_folders": result.get("failed_folders", []),
            "errors": result.get("errors", []),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        print(f"❌ 邮箱清理过程中出错: {e}")
        return error_result


def setup_woocommerce_orders() -> Dict:
    """
    设置WooCommerce订单数据：清空现有订单并添加新的首次购买订单

    Returns:
        设置结果字典
    """
    print("🛍️ 设置WooCommerce订单数据...")

    try:
        # 导入配置
        from token_key_session import all_token_key_session

        # 延迟导入WooCommerce模块
        try:
            from utils.app_specific.woocommerce import (
                OrderManager,
                create_new_welcome_orders
            )
        except ImportError as e:
            print(f"❌ 无法导入WooCommerce模块: {e}")
            return {
                "success": False,
                "error": f"无法导入WooCommerce模块: {e}",
                "timestamp": datetime.now().isoformat()
            }

        # 初始化订单管理器
        order_manager = OrderManager(
            all_token_key_session.woocommerce_site_url,
            all_token_key_session.woocommerce_api_key,
            all_token_key_session.woocommerce_api_secret
        )

        # 第一步：清空现有订单
        print("🗑️ 清空现有订单...")
        clear_result = order_manager.clear_all_orders(confirm=True)

        if not clear_result['success']:
            error_msg = clear_result.get('error', '未知错误')
            print(f"❌ 清空订单失败: {error_msg}")
            return {
                "success": False,
                "error": f"清空订单失败: {error_msg}",
                "deleted_count": clear_result.get('deleted_count', 0)
            }

        deleted_count = clear_result.get('deleted_count', 0)
        print(f"✅ 成功删除 {deleted_count} 个现有订单")

        # 第二步：生成新订单数据
        print("📦 生成新订单数据...")
        all_orders, first_time_orders = create_new_welcome_orders()

        # 第三步：上传新订单到WooCommerce
        print("📤 上传新订单到WooCommerce...")
        upload_result = order_manager.upload_orders(
            all_orders,
            virtual_product_id=1,
            batch_delay=0.8
        )

        if not upload_result['success']:
            error_msg = upload_result.get('error', '未知错误')
            print(f"❌ 上传订单失败: {error_msg}")
            return {
                "success": False,
                "error": f"上传订单失败: {error_msg}",
                "deleted_count": deleted_count,
                "generated_orders": len(all_orders)
            }

        successful_orders = upload_result.get('successful_orders', 0)
        failed_orders = upload_result.get('failed_orders', 0)

        print(f"📊 订单设置结果:")
        print(f"   删除旧订单: {deleted_count} 个")
        print(f"   生成新订单: {len(all_orders)} 个")
        print(f"   成功上传: {successful_orders} 个")
        print(f"   失败上传: {failed_orders} 个")
        print(f"   首次购买客户: {len(first_time_orders)} 个")

        # 保存订单数据到文件供评估使用
        current_dir = Path(__file__).parent
        orders_file = current_dir / "generated_orders.json"
        with open(orders_file, 'w', encoding='utf-8') as f:
            json.dump({
                "all_orders": all_orders,
                "first_time_orders": first_time_orders
            }, f, ensure_ascii=False, indent=2)

        print(f"📄 订单数据已保存到: {orders_file}")

        return {
            "success": failed_orders == 0,
            "deleted_count": deleted_count,
            "generated_orders": len(all_orders),
            "successful_uploads": successful_orders,
            "failed_uploads": failed_orders,
            "first_time_customers": len(first_time_orders),
            "orders_file": str(orders_file)
        }

    except Exception as e:
        error_msg = f"WooCommerce订单设置过程中出错: {e}"
        print(f"❌ {error_msg}")
        return {
            "success": False,
            "error": error_msg
        }


def main():
    """主预处理函数"""

    parser = ArgumentParser(description="Preprocess script - Set up the initial environment for the WooCommerce new welcome task")
    parser.add_argument("--agent_workspace", required=False, help="Agent工作空间路径")
    parser.add_argument("--credentials_file", default="configs/gcp-service_account.keys.json", help="BigQuery凭证文件路径")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    print("=" * 80)
    print("WooCommerce New Welcome Task - Preprocessing")
    print("=" * 80)

    results = []

    try:
        # 第一步：清空邮箱
        print("\n" + "="*60)
        print("Step 1: Clear Mailbox")
        print("="*60)

        mailbox_result = clear_mailbox()
        results.append(("Mailbox Cleanup", mailbox_result["success"], mailbox_result))

        if mailbox_result["success"]:
            print("✅ 邮箱清理成功")
        else:
            print("⚠️ 邮箱清理部分失败，但继续后续操作...")

        # 等待邮箱操作完成
        time.sleep(2)

        # 第二步：设置WooCommerce订单
        print("\n" + "="*60)
        print("Step 2: Setup WooCommerce Orders")
        print("="*60)

        woocommerce_result = setup_woocommerce_orders()
        results.append(("WooCommerce Setup", woocommerce_result["success"], woocommerce_result))

        if woocommerce_result["success"]:
            print("✅ WooCommerce订单设置成功")
        else:
            print("❌ WooCommerce订单设置失败")

        # 第三步：设置BigQuery环境
        print("\n" + "="*60)
        print("Step 3: Setup BigQuery Environment")
        print("="*60)

        # 设置BigQuery路径和数据
        credentials_path = Path(args.credentials_file)
        if not credentials_path.is_absolute():
            credentials_path = Path.cwd() / credentials_path

        if credentials_path.exists():
            # 读取客户数据
            current_dir = Path(__file__).parent
            json_path = current_dir / "customers_data.json"
            if json_path.exists():
                json_data = read_json_data(str(json_path))

                project_id = get_project_id_from_key(str(credentials_path))
                if project_id:
                    try:
                        client, dataset_id = setup_bigquery_resources(str(credentials_path), project_id, json_data)
                        results.append(("BigQuery Setup", True, {"dataset_id": dataset_id}))
                        print("✅ BigQuery环境设置成功")
                    except Exception as e:
                        results.append(("BigQuery Setup", False, {"error": str(e)}))
                        print(f"❌ BigQuery设置失败: {e}")
                else:
                    results.append(("BigQuery Setup", False, {"error": "无法获取项目ID"}))
                    print("❌ 无法从凭证文件获取项目ID")
            else:
                results.append(("BigQuery Setup", False, {"error": "客户数据文件不存在"}))
                print("❌ 客户数据文件不存在")
        else:
            results.append(("BigQuery Setup", False, {"error": "凭证文件不存在"}))
            print("❌ BigQuery凭证文件不存在")

        # 汇总结果
        print("\n" + "="*80)
        print("PREPROCESSING SUMMARY")
        print("="*80)

        success_count = sum(1 for _, success, _ in results if success)
        total_count = len(results)

        for step_name, success, details in results:
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{step_name}: {status}")
            if not success and "error" in details:
                print(f"  Error: {details['error']}")

        overall_success = success_count == total_count
        print(f"\nOverall: {success_count}/{total_count} steps completed successfully")

        if overall_success:
            print("\n🎉 所有预处理步骤完成！任务环境已就绪")
            return True
        else:
            print("\n⚠️ 预处理部分完成，请检查失败的步骤")
            return False

    except Exception as e:
        print(f"❌ 预处理失败: {e}")
        return False


# 以下是原有的BigQuery相关函数（保持不变）

import logging
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
    main()