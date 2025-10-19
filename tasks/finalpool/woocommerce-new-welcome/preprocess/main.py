#!/usr/bin/env python3
"""
WooCommerce New Welcome Task - Preprocess Setup
Set up the initial working environment: clear mailbox, set up WooCommerce order data, prepare BigQuery environment
"""
import os
import sys
import json
from argparse import ArgumentParser
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List

from utils.app_specific.poste.email_import_utils import clear_all_email_folders

# Add parent directory to import token configuration
current_dir = os.path.dirname(os.path.abspath(__file__))
task_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(task_dir)))
sys.path.insert(0, task_dir)  # For token_key_session
from token_key_session import all_token_key_session as local_token_key_session

def clear_mailbox():
    clear_all_email_folders(local_token_key_session.emails_config_file)

def setup_woocommerce_orders() -> Dict:
    """
    Set up WooCommerce order data: clear all current orders and add new first purchase orders.

    Returns:
        Result dictionary
    """
    print("🛍️ Setting up WooCommerce orders...")

    try:
        # Import token/session config
        from token_key_session import all_token_key_session

        # Lazy import WooCommerce modules
        try:
            from utils.app_specific.woocommerce import (
                OrderManager,
                create_new_welcome_orders
            )
        except ImportError as e:
            print(f"❌ Cannot import WooCommerce modules: {e}")
            return {
                "success": False,
                "error": f"Cannot import WooCommerce modules: {e}",
                "timestamp": datetime.now().isoformat()
            }

        # Initialize order manager
        order_manager = OrderManager(
            all_token_key_session.woocommerce_site_url,
            all_token_key_session.woocommerce_api_key,
            all_token_key_session.woocommerce_api_secret
        )

        # Step 1: Clear all current orders
        print("🗑️ Clearing all current orders...")
        clear_result = order_manager.clear_all_orders(confirm=True)

        if not clear_result['success']:
            error_msg = clear_result.get('error', 'Unknown error')
            print(f"❌ Failed to clear orders: {error_msg}")
            return {
                "success": False,
                "error": f"Failed to clear orders: {error_msg}",
                "deleted_count": clear_result.get('deleted_count', 0)
            }

        deleted_count = clear_result.get('deleted_count', 0)
        print(f"✅ Successfully deleted {deleted_count} existing orders")

        # Step 2: Generate new order data
        print("📦 Generating new order data...")
        all_orders, first_time_orders = create_new_welcome_orders()

        # Step 3: Upload new orders to WooCommerce
        print("📤 Uploading new orders to WooCommerce...")
        upload_result = order_manager.upload_orders(
            all_orders,
            virtual_product_id=1,
            batch_delay=0.8
        )

        if not upload_result['success']:
            error_msg = upload_result.get('error', 'Unknown error')
            print(f"❌ Failed to upload orders: {error_msg}")
            return {
                "success": False,
                "error": f"Failed to upload orders: {error_msg}",
                "deleted_count": deleted_count,
                "generated_orders": len(all_orders)
            }

        successful_orders = upload_result.get('successful_orders', 0)
        failed_orders = upload_result.get('failed_orders', 0)

        print(f"📊 WooCommerce order setup result:")
        print(f"   Deleted old orders: {deleted_count}")
        print(f"   Generated new orders: {len(all_orders)}")
        print(f"   Successfully uploaded: {successful_orders}")
        print(f"   Failed uploads: {failed_orders}")
        print(f"   First-time customers: {len(first_time_orders)}")

        # Save generated orders to file for evaluation
        current_dir = Path(__file__).parent
        orders_file = current_dir / "generated_orders.json"
        with open(orders_file, 'w', encoding='utf-8') as f:
            json.dump({
                "all_orders": all_orders,
                "first_time_orders": first_time_orders
            }, f, ensure_ascii=False, indent=2)

        print(f"📄 Order data saved to: {orders_file}")

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
        error_msg = f"Error occurred during WooCommerce order setup: {e}"
        print(f"❌ {error_msg}")
        return {
            "success": False,
            "error": error_msg
        }


def main():
    """Main preprocessing function"""

    parser = ArgumentParser(description="Preprocess script - Set up the initial environment for the WooCommerce new welcome task")
    parser.add_argument("--agent_workspace", required=False, help="Agent workspace path")
    parser.add_argument("--credentials_file", default="configs/gcp-service_account.keys.json", help="BigQuery credential file path")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    print("=" * 80)
    print("WooCommerce New Welcome Task - Preprocessing")
    print("=" * 80)

    results = []

    try:
        # Step 1: Clear mailbox
        print("\n" + "="*60)
        print("Step 1: Clear Mailbox")
        print("="*60)

        clear_mailbox()
        results.append(("Mailbox Cleanup", True, {}))

        # Step 2: Setup WooCommerce orders
        print("\n" + "="*60)
        print("Step 2: Setup WooCommerce Orders")
        print("="*60)

        woocommerce_result = setup_woocommerce_orders()
        results.append(("WooCommerce Setup", woocommerce_result["success"], woocommerce_result))

        if woocommerce_result["success"]:
            print("✅ WooCommerce order setup succeeded")
        else:
            print("❌ WooCommerce order setup failed")

        # Step 3: Setup BigQuery environment
        print("\n" + "="*60)
        print("Step 3: Setup BigQuery Environment")
        print("="*60)

        # Set BigQuery path and data
        credentials_path = Path(args.credentials_file)
        if not credentials_path.is_absolute():
            credentials_path = Path.cwd() / credentials_path

        if credentials_path.exists():
            # Read customer data
            current_dir = Path(__file__).parent
            json_path = current_dir / "customers_data.json"
            if json_path.exists():
                json_data = read_json_data(str(json_path))

                project_id = get_project_id_from_key(str(credentials_path))
                if project_id:
                    try:
                        client, dataset_id = setup_bigquery_resources(str(credentials_path), project_id, json_data)
                        results.append(("BigQuery Setup", True, {"dataset_id": dataset_id}))
                        print("✅ BigQuery environment setup succeeded")
                    except Exception as e:
                        results.append(("BigQuery Setup", False, {"error": str(e)}))
                        print(f"❌ BigQuery setup failed: {e}")
                else:
                    results.append(("BigQuery Setup", False, {"error": "Could not get project ID"}))
                    print("❌ Could not get project ID from credentials file")
            else:
                results.append(("BigQuery Setup", False, {"error": "Customer data file does not exist"}))
                print("❌ Customer data file does not exist")
        else:
            results.append(("BigQuery Setup", False, {"error": "Credential file does not exist"}))
            print("❌ BigQuery credential file does not exist")

        # Print summary
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
            print("\n🎉 All preprocessing steps completed! Task environment is ready.")
            return True
        else:
            print("\n⚠️  Preprocessing partially completed, please check failed steps.")
            return False

    except Exception as e:
        print(f"❌ Preprocessing failed: {e}")
        return False


# The following BigQuery-related functions remain unchanged

import logging
from google.cloud import bigquery
from google.oauth2 import service_account
from google.api_core.exceptions import Conflict, GoogleAPICallError, NotFound

# Enable verbose logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def read_json_data(json_path: str):
    """Read customer data from JSON file"""
    print(f"📖 Reading JSON data file: {json_path}")
    
    if not Path(json_path).exists():
        print(f"❌ JSON data file does not exist: {json_path}")
        return []
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            customers = json.load(f)
        
        # Ensure data format is correct
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
        
        print(f"✅ Successfully read {len(processed_customers)} customer records")
        return processed_customers
        
    except (json.JSONDecodeError, IOError) as e:
        print(f"❌ Error reading JSON data file: {e}")
        return []

def wait_for_table_availability(client: bigquery.Client, table_id: str, max_wait_time: int = 30):
    """
    Wait for BigQuery table to become fully available after creation
    """
    import time

    print(f"⏳ Waiting for table {table_id} to be fully available...")
    start_time = time.time()

    while time.time() - start_time < max_wait_time:
        try:
            # Try to get the table - this verifies it's fully available
            table = client.get_table(table_id)
            # Also try a simple query to make sure it's really ready
            query = f"SELECT COUNT(*) as row_count FROM `{table_id}` LIMIT 1"
            query_job = client.query(query)
            list(query_job.result())
            print(f"✅ Table {table_id} is fully available")
            return table
        except Exception as e:
            print(f"   Table not available yet: {e}")
            time.sleep(2)

    print(f"⚠️  Timed out waiting for table availability ({max_wait_time}s)")
    return None

def wait_for_dataset_deletion(client: bigquery.Client, dataset_id: str, max_wait_time: int = 30):
    """
    Wait for BigQuery dataset deletion to complete
    """
    import time

    print(f"⏳ Waiting for dataset {dataset_id} to be fully deleted...")
    start_time = time.time()

    while time.time() - start_time < max_wait_time:
        try:
            # Try to get the dataset - if it still exists, deletion isn't complete
            client.get_dataset(dataset_id)
            print(f"   Dataset still exists, waiting...")
            time.sleep(2)
        except NotFound:
            # Dataset is truly gone
            print(f"✅ Dataset {dataset_id} has been fully deleted")
            return True
        except Exception as e:
            print(f"⚠️  Error checking dataset status: {e}")
            time.sleep(2)

    print(f"⚠️  Timed out waiting for dataset to be deleted ({max_wait_time}s), continuing...")
    return False

def setup_or_clear_dataset(client: bigquery.Client, project_id: str):
    """
    Setup or clear existing woocommerce_crm dataset
    - If dataset exists: clear all table contents but keep the dataset and tables
    - If dataset doesn't exist: create it (tables will be created later)
    """
    dataset_id = f"{project_id}.woocommerce_crm"
    print(f"🧹 Checking and setting up dataset: {dataset_id}")

    try:
        # Try to get dataset info to see if it exists
        try:
            dataset = client.get_dataset(dataset_id)
            print(f"ℹ️  Found existing dataset: {dataset_id}")

            # List all tables in the dataset
            tables = list(client.list_tables(dataset_id))
            if tables:
                print(f"ℹ️  Dataset contains {len(tables)} tables:")
                for table in tables:
                    print(f"   - {table.table_id}")

                # Clear contents of all tables instead of deleting them
                for table in tables:
                    table_id = f"{dataset_id}.{table.table_id}"
                    print(f"🗑️  Clearing content of table {table.table_id}...")

                    # Use DELETE query to clear table contents
                    delete_query = f"DELETE FROM `{table_id}` WHERE true"
                    query_job = client.query(delete_query)
                    query_job.result()  # Wait for completion

                    print(f"✅ Cleared table {table.table_id}")
            else:
                print(f"ℹ️  Dataset is empty, nothing to clean")

        except NotFound:
            print(f"ℹ️  Dataset {dataset_id} does not exist, will create new dataset")
            # Create the dataset since it doesn't exist
            dataset = bigquery.Dataset(dataset_id)
            dataset.location = "US"
            dataset.description = "WooCommerce CRM dataset for customer management and welcome emails"
            client.create_dataset(dataset, timeout=30)
            print(f"✅ Dataset '{dataset.dataset_id}' created successfully")

    except Exception as e:
        print(f"❌ Error setting up dataset: {e}")
        logger.exception("Dataset setup failed")
        raise

def cleanup_existing_dataset(client: bigquery.Client, project_id: str):
    """
    Clean up existing woocommerce_crm dataset if it exists
    """
    dataset_id = f"{project_id}.woocommerce_crm"
    print(f"🧹 Checking and cleaning up existing dataset: {dataset_id}")
    
    try:
        # First try to get dataset info to see if it exists
        try:
            dataset = client.get_dataset(dataset_id)
            print(f"ℹ️  Found existing dataset: {dataset_id}")
            
            # List all tables in the dataset
            tables = list(client.list_tables(dataset_id))
            if tables:
                print(f"ℹ️  Dataset contains {len(tables)} tables:")
                for table in tables:
                    print(f"   - {table.table_id}")
        except NotFound:
            print(f"ℹ️  Dataset {dataset_id} does not exist, nothing to clean")
            return
        
        # Delete dataset with all contents
        print(f"🗑️  Deleting dataset and all its content...")
        client.delete_dataset(
            dataset_id, 
            delete_contents=True, 
            not_found_ok=True
        )
        print(f"✅ Successfully cleaned up dataset '{dataset_id}' and all its content")
        
        # Wait for deletion to propagate - BigQuery deletion is asynchronous
        wait_for_dataset_deletion(client, dataset_id)
        
    except NotFound:
        print(f"ℹ️  Dataset {dataset_id} does not exist, nothing to clean")
    except Exception as e:
        print(f"❌ Error cleaning up dataset: {e}")
        logger.exception("Dataset cleanup failed")
        raise

def setup_bigquery_resources(credentials_path: str, project_id: str, json_data: list):
    """
    Setup BigQuery dataset and tables for WooCommerce CRM, then populate with JSON data
    """
    print("=" * 60)
    print("🛍️ Starting to set up BigQuery WooCommerce CRM resources")
    print("=" * 60)
    
    try:
        print(f"🔗 Connecting to project '{project_id}' with credentials '{credentials_path}'...")
        
        # Use the newer authentication method
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        client = bigquery.Client(credentials=credentials, project=project_id)
        
        print("✅ Connection successful!")
        
        # Test connection by listing datasets
        print("🔍 Testing connection - listing available datasets...")
        try:
            datasets = list(client.list_datasets())
            print(f"ℹ️  There are {len(datasets)} datasets in this project")
            for dataset in datasets:
                print(f"   - {dataset.dataset_id}")
        except Exception as e:
            print(f"⚠️  Error listing datasets: {e}")

        # Setup or clear existing dataset (don't delete it)
        setup_or_clear_dataset(client, project_id)

        # Create dataset if needed (handled in setup_or_clear_dataset)
        dataset_id = f"{project_id}.woocommerce_crm"

        # Create customers table (or skip if exists)
        table_id_customers = f"{dataset_id}.customers"
        print(f"🗂️  Checking and creating table: {table_id_customers}")
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
            print(f"✅ Table '{table_id_customers}' created successfully.")
        except Conflict:
            print(f"ℹ️  Table '{table_id_customers}' already exists, skipping creation.")
        except Exception as e:
            print(f"❌ Failed to create table '{table_id_customers}': {e}")
            raise

        # Get table reference for data insertion
        print(f"📋 Getting table reference...")
        table_ref = client.get_table(table_id_customers)
        print(f"✅ Got table reference: {table_ref.table_id}")

        # Insert JSON data into BigQuery
        if json_data:
            print(f"💾 Inserting {len(json_data)} customer records into BigQuery...")
            try:
                # Use the table reference we already verified is available
                print(f"✅ Using verified table reference: {table_ref.table_id}")

                # **ALTERNATIVE APPROACH: Use load_table_from_json instead of insert_rows_json**
                # This bypasses potential caching issues with streaming inserts
                print("🔄 Trying batch load instead of streaming insert...")

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

                print(f"   Started batch load job: {load_job.job_id}")
                load_job.result()  # Wait for the job to complete

                print(f"🎉 Successfully batch loaded {len(bigquery_rows)} customer records into customers table")
                
                # Verify data insertion
                print("🔍 Verifying data insertion...")
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
                    print(f"✅ Verification succeeded: {result.total_rows} rows, {result.unique_customers} unique customers, {result.emails_sent} welcome emails sent")
                else:
                    print("⚠️  Verification query returned no results")
                    
            except Exception as e:
                print(f"❌ Error inserting data: {e}")
                logger.exception("Data insertion failed")
                raise Exception(f"Data insertion failed: {e}")
        else:
            print("⚠️  No JSON data to insert")

        return client, dataset_id

    except GoogleAPICallError as e:
        print(f"❌ Google Cloud API call failed: {e}")
        logger.exception("Google Cloud API call failed")
        raise
    except Exception as e:
        print(f"❌ Error during setup: {e}")
        logger.exception("Setup process failed")
        raise

def get_project_id_from_key(credentials_path: str) -> str | None:
    """Read project ID from service account key file"""
    try:
        with open(credentials_path, 'r') as f:
            data = json.load(f)
            return data.get("project_id")
    except (FileNotFoundError, json.JSONDecodeError):
        return None

if __name__ == "__main__":
    main()