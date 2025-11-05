from argparse import ArgumentParser
import os
import json

from argparse import ArgumentParser
import os
import subprocess
import json
from google.cloud import storage
from google.cloud import bigquery
from google.cloud.exceptions import NotFound, Conflict
from google.oauth2 import service_account
import random
from google.cloud.logging_v2.types import CreateBucketRequest
from google.cloud.logging_v2.services import config_service_v2
from google.cloud.logging_v2.types import LogBucket

random.seed(42)

# Set path to credentials file
CREDENTIALS_PATH = "configs/gcp-service_account.keys.json"
if os.path.exists(CREDENTIALS_PATH):
    CREDENTIALS = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH)
else:
    CREDENTIALS = None

# Parse project_id from service account file
with open(CREDENTIALS_PATH, 'r') as f:
    service_account_info = json.load(f)
    PROJECT_ID = service_account_info.get('project_id')


import uuid

def delete_and_recreate_bucket(
    bucket_name="mcp-fraud-investigation-archive", project_id=PROJECT_ID, location="us-central1", max_retries=10
):
    """
    Find all buckets with prefix bucket_name, delete them, and recreate a new unique bucket (prefix bucket_name+uuid),
    and save the new bucket name to ../groundtruth_workspace/bucket_name.txt file.
    Retries up to max_retries times for robustness.
    """
    import time

    print(f"🔍 Finding and deleting buckets with prefix: {bucket_name}")

    for attempt in range(1, max_retries + 1):
        try:
            storage_client = storage.Client(project=project_id, credentials=CREDENTIALS)

            # Find all buckets with prefix matching
            found_buckets = []
            for bucket in storage_client.list_buckets():
                if bucket.name.startswith(bucket_name):
                    print(f"🗑️  Deleting bucket: {bucket.name}")
                    try:
                        # Need to delete all objects in the bucket first
                        blobs = list(bucket.list_blobs())
                        if blobs:
                            for blob in blobs:
                                blob.delete()
                        bucket.delete(force=True)
                        print(f"✅ Successfully deleted bucket {bucket.name}")
                    except Exception as del_e:
                        print(f"⚠️ Error deleting bucket {bucket.name}: {del_e}")
                    found_buckets.append(bucket.name)

            # Double check deletion
            still_exists = [b.name for b in storage_client.list_buckets() if b.name.startswith(bucket_name)]
            if still_exists:
                print(f"⚠️ Still found buckets after deletion attempt: {still_exists}. Retrying...")
                raise Exception("Buckets not fully deleted yet")

            # Generate new unique bucket name
            new_bucket_name = f"{bucket_name}-{uuid.uuid4().hex[:12]}"
            print(f"📦 Creating new bucket: {new_bucket_name}")

            # Try to create the new bucket, retry internally if Conflict
            create_succeeded = False
            for create_attempt in range(3):
                try:
                    bucket_obj = storage_client.bucket(new_bucket_name)
                    storage_client.create_bucket(bucket_obj, location=location)
                    print(f"✅ Successfully created bucket: {new_bucket_name}")
                    create_succeeded = True
                    break
                except Conflict:
                    print(f"⚠️ Bucket name {new_bucket_name} already taken/conflict, retrying with new name...")
                    new_bucket_name = f"{bucket_name}-{uuid.uuid4().hex[:12]}"
                except Exception as create_e:
                    print(f"❌ Failed to create bucket ({create_attempt+1}/3): {create_e}")
                    time.sleep(2)
            if not create_succeeded:
                raise Exception("Failed to create new bucket after retries")

            # Save bucket name to specified file
            save_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "../groundtruth_workspace/bucket_name.txt")
            )
            # Extra retry here in case of file IO issues
            for file_attempt in range(3):
                try:
                    with open(save_path, "w") as f:
                        f.write(new_bucket_name.strip() + "\n")
                    print(f"💾 Saved new bucket name to {save_path}")
                    break
                except Exception as file_e:
                    print(f"⚠️ Error saving bucket name file: {file_e}, retrying...")
                    time.sleep(1)
            else:
                raise Exception("Failed to write bucket name file after retries")

            return new_bucket_name

        except Exception as e:
            print(f"❌ Error handling buckets (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                print("⏳ Waiting a bit before next retry...")
                time.sleep(3)
            else:
                print("❌ All attempts failed. Giving up.")
                raise e


import uuid
import time

def manage_log_bucket(
        project_id,
        credentials=CREDENTIALS,
        bucket_name_prefix="abtesting_logging",
        location="global",
        max_retries=10
    ):
    print(f"🔍 Managing log buckets with prefix: {bucket_name_prefix}")
    config_client = config_service_v2.ConfigServiceV2Client(credentials=CREDENTIALS)
    parent = f"projects/{project_id}/locations/{location}"

    # Find existing log bucket
    matched_bucket = None
    matched_bucket_id = None
    buckets = list(config_client.list_buckets(parent=parent))
    for bucket in buckets:
        bucket_id = bucket.name.split('/')[-1]
        if bucket_id.startswith(bucket_name_prefix) and bucket.lifecycle_state.name == 'ACTIVE':
            matched_bucket = bucket
            matched_bucket_id = bucket_id
            break

    if matched_bucket is not None:
        print(f"✅ Found existing log bucket: {matched_bucket_id}")

        print("[IMPORTANT INFO] We now do not delete the logs in the log bucket, as google cloud sdk does not support delete log entries in custom log buckets.")

        save_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../groundtruth_workspace/log_bucket_name.txt")
        )
        with open(save_path, "w") as f:
            f.write(matched_bucket_id.strip() + "\n")
        print(f"💾 Saved log bucket name to {save_path}")

        return matched_bucket_id, True

    # Create new log bucket
    new_bucket_id = f"{bucket_name_prefix}-{uuid.uuid4().hex[:12]}"
    print(f"📝 Creating new log bucket: {new_bucket_id}")

    bucket_obj = LogBucket(retention_days=30)
    request = CreateBucketRequest(
        parent=parent,
        bucket_id=new_bucket_id,
        bucket=bucket_obj
    )
    config_client.create_bucket(request=request)
    print(f"✅ Successfully created log bucket: {new_bucket_id}")

    save_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../groundtruth_workspace/log_bucket_name.txt")
    )
    with open(save_path, "w") as f:
        f.write(new_bucket_id.strip() + "\n")
    print(f"💾 Saved new log bucket name to {save_path}")

    return new_bucket_id, True


def check_bq_dataset_exists(dataset_name="transactions_analytics", project_id="mcp-bench0606"):
    """Check if BigQuery dataset exists"""
    print(f"🔍 Checking if BigQuery dataset exists: {dataset_name}")

    bq_client = bigquery.Client(project=project_id, credentials=CREDENTIALS)
    dataset_id = f"{project_id}.{dataset_name}"

    try:
        bq_client.get_dataset(dataset_id)
        print(f"✅ BigQuery dataset {dataset_name} already exists")
        return True
    except Exception as e:
        from google.cloud.exceptions import NotFound
        if hasattr(e, "code") and e.code == 404:
            print(f"📊 BigQuery dataset {dataset_name} does not exist (404 Not Found)")
            return False
        if "Not found" in str(e) or isinstance(e, NotFound):
            print(f"📊 BigQuery dataset {dataset_name} does not exist (NotFound)")
            return False
        print(f"❌ Error checking BigQuery dataset: {e}")
        raise e

def delete_bq_dataset(dataset_name="transactions_analytics", project_id="mcp-bench0606"):
    """Delete BigQuery dataset"""
    print(f"🗑️  Deleting BigQuery dataset: {dataset_name}")

    bq_client = bigquery.Client(project=project_id, credentials=CREDENTIALS)
    dataset_id = f"{project_id}.{dataset_name}"

    bq_client.delete_dataset(dataset_id, delete_contents=True, not_found_ok=True)
    print(f"✅ Successfully deleted BigQuery dataset: {dataset_name}")
    return True

def create_bq_dataset(dataset_name="transactions_analytics", project_id="mcp-bench0606", location="US"):
    """Create BigQuery dataset"""
    print(f"📊 Creating BigQuery dataset: {dataset_name}")

    bq_client = bigquery.Client(project=project_id, credentials=CREDENTIALS)
    dataset_id = f"{project_id}.{dataset_name}"

    dataset = bigquery.Dataset(dataset_id)
    dataset.location = location
    bq_client.create_dataset(dataset, exists_ok=True)
    print(f"✅ Successfully created BigQuery dataset: {dataset_name}")
    return True

def upload_csv_to_bq_table(csv_file_path, table_name, dataset_name="transactions_analytics", project_id="mcp-bench0606"):
    """Upload CSV file to BigQuery table"""
    print(f"📤 Uploading {os.path.basename(csv_file_path)} to BigQuery table: {table_name}")

    bq_client = bigquery.Client(project=project_id, credentials=CREDENTIALS)
    table_id = f"{project_id}.{dataset_name}.{table_name}"

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        autodetect=True,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    with open(csv_file_path, "rb") as source_file:
        job = bq_client.load_table_from_file(source_file, table_id, job_config=job_config)

    job.result()
    print(f"✅ Successfully uploaded {os.path.basename(csv_file_path)} to table: {table_name}")
    return True

def manage_transactions_analytics_dataset(project_id="mcp-bench0606", dataset_name="transactions_analytics", csv_directory="transactions_analytics"):
    """Full process to manage the transactions_analytics BigQuery dataset."""
    print(f"📊 Managing BigQuery dataset: {dataset_name}")
    
    results = {
        "dataset_existed": False,
        "dataset_deleted": False,
        "dataset_created": False,
        "tables_uploaded": [],
        "upload_failures": []
    }
    
    # Check if the dataset exists
    dataset_exists = check_bq_dataset_exists(dataset_name, project_id)
    results["dataset_existed"] = dataset_exists
    
    if dataset_exists:
        # If it exists, delete the dataset
        dataset_deleted = delete_bq_dataset(dataset_name, project_id)
        results["dataset_deleted"] = dataset_deleted
        if not dataset_deleted:
            print(f"❌ Failed to delete existing dataset {dataset_name}")
            return results
    
    # Create a new dataset
    dataset_created = create_bq_dataset(dataset_name, project_id)
    results["dataset_created"] = dataset_created
    
    if not dataset_created:
        print(f"❌ Failed to create dataset {dataset_name}")
        return results
    
    # Get the directory path for CSV files
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_dir_path = os.path.join(script_dir, csv_directory)
    
    if not os.path.exists(csv_dir_path):
        print(f"❌ CSV directory not found: {csv_dir_path}")
        return results
    
    # Upload all CSV files to BigQuery tables
    csv_files = [f for f in os.listdir(csv_dir_path) if f.endswith('.csv')]
    print(f"📁 Found {len(csv_files)} CSV files to upload")
    
    for csv_file in csv_files:
        csv_file_path = os.path.join(csv_dir_path, csv_file)
        table_name = os.path.splitext(csv_file)[0]  # Remove .csv extension for table name
        
        upload_success = upload_csv_to_bq_table(csv_file_path, table_name, dataset_name, project_id)
        
        if upload_success:
            results["tables_uploaded"].append(table_name)
        else:
            results["upload_failures"].append(csv_file)
    
    print(f"✅ Dataset {dataset_name} management completed:")
    print(f"   - Tables uploaded: {len(results['tables_uploaded'])}")
    print(f"   - Upload failures: {len(results['upload_failures'])}")
    
    return results

def cleanup_preprocess_environment(workspace_dir, target_transaction_id="T8492XJ3", project_id="mcp-bench0606"):
    """Cleanup the preprocess environment and prepare for the Live Transactions task."""
    print("🚀 Starting Live Transactions Preprocess Cleanup...")
    
    cleanup_results = {}
    
    bucket_ready = delete_and_recreate_bucket("mcp-fraud-investigation-archive")
    cleanup_results["bucket_ready"] = bucket_ready
    
    # Clean up investigation file for the target transaction (if exists)
    # file_cleanup = delete_investigation_file_if_exists("mcp-fraud-investigation-archive", f"{target_transaction_id}.json", project_id)
    cleanup_results["file_cleanup"] = bucket_ready
    
    # Manage Trading_Logging log bucket
    log_bucket_results = manage_log_bucket(project_id, CREDENTIALS, "Trading_Logging")
    cleanup_results["log_bucket_results"] = log_bucket_results

    # Manage transactions_analytics BigQuery dataset
    bq_dataset_results = manage_transactions_analytics_dataset(project_id)
    cleanup_results["bq_dataset_results"] = bq_dataset_results
    
    return cleanup_results



if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True)
    parser.add_argument("--transaction_id", default="T8492XJ3",
                       help="Target suspicious transaction ID (default: T8492XJ3)")
    parser.add_argument("--cleanup_files", default=True, action="store_true",
                       help="Clean up existing investigation files to prevent task interference (default: enabled)")
    parser.add_argument("--no_cleanup", action="store_true",
                       help="Skip file cleanup (use when you want to preserve existing files)")
    parser.add_argument("--project_id", default="mcp-bench0606",
                       help="Google Cloud Project ID")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    
    args = parser.parse_args()
    args.project_id = PROJECT_ID # overwrite the project_id
    print("=== Live Transactions Fraud Investigation Preprocess ===")
    print(f"Agent workspace: {args.agent_workspace}")
    print(f"Target transaction ID: {args.transaction_id}")
    print(f"Project ID: {args.project_id}")
    
    # Ensure the workspace directory exists
    os.makedirs(args.agent_workspace, exist_ok=True)
    
    # By default, do cleanup unless explicitly skipped
    should_cleanup = args.cleanup_files and not args.no_cleanup
    
    if should_cleanup:
        print(f"\n🧹 Performing cleanup for transaction {args.transaction_id}...")
        cleanup_results = cleanup_preprocess_environment(args.agent_workspace, args.transaction_id, args.project_id)
        
        if cleanup_results.get("file_cleanup", False) or cleanup_results.get("bucket_ready", False) or cleanup_results.get("log_bucket_results", {}).get("bucket_exists", False) or cleanup_results.get("log_bucket_results", {}).get("bucket_created", False) or cleanup_results.get("bq_dataset_results", {}).get("dataset_existed", False) or cleanup_results.get("bq_dataset_results", {}).get("dataset_deleted", False) or cleanup_results.get("bq_dataset_results", {}).get("dataset_created", False) or cleanup_results.get("bq_dataset_results", {}).get("tables_uploaded"):
            print("✅ Preprocess cleanup completed successfully!")
        else:
            print("⚠️  Preprocess cleanup completed with warnings.")
    else:
        print("ℹ️  Cleanup skipped (--no_cleanup specified).")
    
    print(f"\n🎯 Environment prepared for fraud investigation!")
    print(f"🔍 Ready to investigate transaction: {args.transaction_id}")
    print(f"📤 Target upload location: gs://mcp-fraud-investigation-archive/{args.transaction_id}.json")
    print(f"📊 Trading_Logging log bucket is ready for transaction logging")
    print(f"💾 BigQuery transactions_analytics dataset is ready with fresh data")
    print("🚨 Ready for task execution - environment has been prepared and cleaned up")
