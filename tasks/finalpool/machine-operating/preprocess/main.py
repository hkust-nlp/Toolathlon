from argparse import ArgumentParser
import os
import subprocess
import json
from google.cloud import storage
from google.cloud import bigquery
from google.cloud.exceptions import NotFound, Conflict
from google.oauth2 import service_account
import random

random.seed(42)

# Set path to credentials file
CREDENTIALS_PATH = "configs/gcp-service_account.keys.json"
if os.path.exists(CREDENTIALS_PATH):
    credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH)
else:
    credentials = None

# Parse project_id from service account file
with open(CREDENTIALS_PATH, 'r') as f:
    service_account_info = json.load(f)
    PROJECT_ID = service_account_info.get('project_id')

def check_gcloud_authentication():
    """Check if Google Cloud CLI is authenticated"""
    try:
        storage_client = storage.Client(credentials=credentials)
        return True
    except Exception:
        return False

import uuid

def delete_and_recreate_bucket(
    bucket_name="iot_anomaly_reports", project_id=PROJECT_ID, location="us-central1", max_retries=10
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
            storage_client = storage.Client(project=project_id, credentials=credentials)

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






def upload_csv_to_bq_table(csv_file_path, table_name, dataset_name="machine_operating", project_id=PROJECT_ID):
    """Upload CSV file to BigQuery table"""
    print(f"📤 Uploading {os.path.basename(csv_file_path)} to BigQuery table: {table_name}")

    try:
        client = bigquery.Client(project=project_id, credentials=credentials)
        table_id = f"{project_id}.{dataset_name}.{table_name}"

        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,
            autodetect=True,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
        )

        with open(csv_file_path, "rb") as source_file:
            load_job = client.load_table_from_file(
                source_file, table_id, job_config=job_config
            )

        load_job.result()

        table = client.get_table(table_id)
        print(f"✅ Successfully uploaded {os.path.basename(csv_file_path)} to table: {table_name}")
        print(f"   Loaded {table.num_rows} rows to {table_name}")
        return True

    except Exception as e:
        print(f"❌ Error uploading CSV to BigQuery table: {e}")
        return False

def manage_machine_operating_dataset(project_id=PROJECT_ID, dataset_name="machine_operating", csv_file_path=None):
    """Manage the full life cycle of the machine_operating BigQuery dataset"""
    print(f"📊 Managing BigQuery dataset: {dataset_name}")

    # Use default CSV path if not provided
    if csv_file_path is None:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        csv_file_path = os.path.join(current_dir, "live_sensor_data.csv")

    results = {
        "dataset_existed": False,
        "dataset_cleared": False,
        "dataset_created": False,
        "table_uploaded": False,
        "upload_failure": None
    }

    try:
        client = bigquery.Client(project=project_id, credentials=credentials)
        dataset_id = f"{project_id}.{dataset_name}"

        # Check if the dataset exists
        try:
            dataset = client.get_dataset(dataset_id)
            print(f"✅ BigQuery dataset {dataset_name} already exists")
            results["dataset_existed"] = True

            # List and delete all tables and views
            tables = list(client.list_tables(dataset_id))
            if tables:
                print(f"📋 Dataset contains {len(tables)} object(s) (tables/views):")
                for table in tables:
                    table_type = "view" if table.table_type == "VIEW" else "table"
                    print(f"   - {table.table_id} ({table_type})")

                for table in tables:
                    table_id = f"{dataset_id}.{table.table_id}"
                    table_type = "view" if table.table_type == "VIEW" else "table"
                    print(f"🗑️  Deleting {table_type} {table.table_id}...")

                    try:
                        client.delete_table(table_id, not_found_ok=True)
                        print(f"✅ Successfully deleted {table_type} {table.table_id}")
                    except Exception as e:
                        print(f"⚠️  Could not delete {table_type} {table.table_id}: {e}")

                results["dataset_cleared"] = True
            else:
                print(f"📊 Dataset is empty, no tables or views to delete")

        except NotFound:
            # Dataset does not exist; create one
            print(f"📊 Dataset {dataset_name} does not exist, creating new dataset...")
            dataset = bigquery.Dataset(dataset_id)
            dataset.location = "US"
            dataset = client.create_dataset(dataset, timeout=30)
            print(f"✅ Successfully created BigQuery dataset: {dataset_name}")
            results["dataset_created"] = True

        # Check if CSV file exists
        if not os.path.exists(csv_file_path):
            print(f"❌ CSV file not found: {csv_file_path}")
            results["upload_failure"] = f"CSV file not found: {csv_file_path}"
            return results

        # Upload CSV file to BigQuery
        table_name = "live_sensor"
        upload_success = upload_csv_to_bq_table(csv_file_path, table_name, dataset_name, project_id)
        results["table_uploaded"] = upload_success

        if upload_success:
            print(f"✅ Dataset {dataset_name} management completed successfully!")
            print(f"   - Table uploaded: {table_name}")
        else:
            results["upload_failure"] = f"Failed to upload {os.path.basename(csv_file_path)}"
            print(f"❌ Failed to upload CSV file to table: {table_name}")

    except Exception as e:
        print(f"❌ Error managing dataset: {e}")
        results["upload_failure"] = str(e)

    return results

def cleanup_preprocess_environment():
    """Cleanup preprocess environment for Machine Operating task"""
    print("🚀 Starting Machine Operating Anomaly Detection Preprocess Cleanup...")
    
    # Check Google Cloud authentication
    if not check_gcloud_authentication():
        print("⚠️  Warning: Google Cloud CLI not authenticated. Some cleanup may fail.")
        print("   Please run: gcloud auth login")
    
    cleanup_results = {}
    
    # Ensure bucket is deleted
    bucket_ready = delete_and_recreate_bucket("iot_anomaly_reports")
    cleanup_results["bucket_ready"] = bucket_ready

    # Manage machine_operating BigQuery dataset
    bq_dataset_results = manage_machine_operating_dataset()
    cleanup_results["bq_dataset_results"] = bq_dataset_results

    return cleanup_results

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True,
                        help="Agent workspace directory")
    parser.add_argument("--project_id", default=PROJECT_ID,
                        help="Google Cloud Project ID")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    
    args = parser.parse_args()
    
    print("=== Machine Operating Anomaly Detection Preprocess ===")
    print(f"Agent workspace: {args.agent_workspace}")
    print(f"Project ID: {args.project_id}")
    
    # Ensure workspace directory exists
    os.makedirs(args.agent_workspace, exist_ok=True)
    
    # Data verification placeholder (if enabled)
    data_verification_passed = True
    
    # By default, perform cleanup unless explicitly specified otherwise
    cleanup_results = cleanup_preprocess_environment()

    print("✅ All required data files/Bigquery States are available - ready for task execution")
