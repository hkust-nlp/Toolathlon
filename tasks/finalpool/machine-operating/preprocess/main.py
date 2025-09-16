from argparse import ArgumentParser
import os
import subprocess
import json
from google.cloud import storage
from google.cloud import bigquery
from google.cloud.exceptions import NotFound, Conflict
from google.oauth2 import service_account

# 设置认证文件路径
CREDENTIALS_PATH = "configs/gcp-service_account.keys.json"
if os.path.exists(CREDENTIALS_PATH):
    credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH)
else:
    credentials = None

def check_gcloud_authentication():
    """检查Google Cloud CLI是否已认证"""
    try:
        # 尝试创建客户端来验证认证
        storage_client = storage.Client(credentials=credentials)
        return True
    except Exception:
        return False

def delete_anomaly_reports_if_exist(bucket_name="iot_anomaly_reports", file_pattern="anomaly_report", project_id="mcp-bench0606"):
    """删除Google Cloud Storage存储桶中的异常报告文件（支持模式匹配）"""
    print(f"🧹 Checking for existing anomaly reports: gs://{bucket_name}/{file_pattern}*.csv")

    try:
        storage_client = storage.Client(project=project_id, credentials=credentials)

        try:
            bucket = storage_client.bucket(bucket_name)
            if not bucket.exists():
                print(f"✅ Bucket {bucket_name} does not exist - no cleanup needed")
                return True
        except NotFound:
            print(f"✅ Bucket {bucket_name} does not exist - no cleanup needed")
            return True

        # 列出所有匹配的文件
        files_to_delete = []
        blobs = bucket.list_blobs()

        for blob in blobs:
            # 检查是否匹配模式
            if blob.name.startswith(file_pattern) and blob.name.endswith('.csv'):
                files_to_delete.append(blob)

        if not files_to_delete:
            print(f"✅ No anomaly report files found matching pattern '{file_pattern}*.csv' - no cleanup needed")
            return True

        print(f"📄 Found {len(files_to_delete)} anomaly report file(s) to delete:")
        for blob in files_to_delete:
            print(f"   - {blob.name}")

        # 删除找到的文件
        deleted_count = 0
        failed_count = 0

        for blob in files_to_delete:
            try:
                print(f"🗑️  Deleting: {blob.name}")
                blob.delete()
                print(f"✅ Successfully deleted: {blob.name}")
                deleted_count += 1
            except Exception as e:
                print(f"❌ Failed to delete {blob.name}: {e}")
                failed_count += 1

        print(f"📊 Cleanup summary: {deleted_count} deleted, {failed_count} failed")
        return failed_count == 0

    except Exception as e:
        print(f"❌ Error checking/deleting anomaly reports: {e}")
        return False

def ensure_bucket_exists(bucket_name="iot_anomaly_reports", project_id="mcp-bench0606", location="us-central1"):
    """确保存储桶存在，如果不存在则创建"""
    print(f"🔍 Checking if bucket exists: {bucket_name}")

    try:
        storage_client = storage.Client(project=project_id, credentials=credentials)

        try:
            bucket = storage_client.bucket(bucket_name)
            if bucket.exists():
                print(f"✅ Bucket {bucket_name} already exists")

                # # 删除桶中的所有对象
                # print(f"🗑️  Deleting all objects in bucket {bucket_name}...")
                # blobs = bucket.list_blobs()
                # for blob in blobs:
                #     blob.delete()
                #     print(f"   Deleted: {blob.name}")

                # 删除桶本身
                print(f"🗑️  Deleting bucket {bucket_name}...")
                bucket.delete()
                print(f"✅ Successfully deleted bucket {bucket_name}")

                # # 重新创建桶
                # print(f"📦 Recreating bucket: {bucket_name}")
                # bucket = storage_client.create_bucket(bucket_name, location=location)
                # print(f"✅ Successfully recreated bucket: {bucket_name}")
                # return True
            else:
                # # Bucket不存在，创建它
                # print(f"📦 Creating bucket: {bucket_name}")
                # bucket = storage_client.create_bucket(bucket_name, location=location)
                # print(f"✅ Successfully created bucket: {bucket_name}")
                # return True
                pass

        except NotFound:
            # Bucket不存在，创建它
            print(f"📦 Creating bucket: {bucket_name}")
            bucket = storage_client.create_bucket(bucket_name, location=location)
            print(f"✅ Successfully created bucket: {bucket_name}")
            return True

        except Conflict:
            # Bucket已经存在（可能属于其他项目）
            print(f"⚠️  Bucket {bucket_name} already exists (possibly in another project)")
            return True

    except Exception as e:
        print(f"❌ Error checking/creating bucket: {e}")
        return False

def check_bq_dataset_exists(dataset_name="machine_operating", project_id="mcp-bench0606"):
    """检查BigQuery数据集是否存在"""
    print(f"🔍 Checking if BigQuery dataset exists: {dataset_name}")

    try:
        client = bigquery.Client(project=project_id, credentials=credentials)
        dataset_id = f"{project_id}.{dataset_name}"

        try:
            dataset = client.get_dataset(dataset_id)
            print(f"✅ BigQuery dataset {dataset_name} already exists")
            return True
        except NotFound:
            print(f"📊 BigQuery dataset {dataset_name} does not exist")
            return False

    except Exception as e:
        print(f"❌ Error checking BigQuery dataset: {e}")
        return False

def delete_bq_dataset(dataset_name="machine_operating", project_id="mcp-bench0606"):
    """删除BigQuery数据集"""
    print(f"🗑️  Deleting BigQuery dataset: {dataset_name}")

    try:
        client = bigquery.Client(project=project_id, credentials=credentials)
        dataset_id = f"{project_id}.{dataset_name}"

        # 删除数据集（包括所有表）
        client.delete_dataset(dataset_id, delete_contents=True, not_found_ok=True)
        print(f"✅ Successfully deleted BigQuery dataset: {dataset_name}")
        return True

    except Exception as e:
        print(f"❌ Error deleting BigQuery dataset: {e}")
        return False

def create_bq_dataset(dataset_name="machine_operating", project_id="mcp-bench0606", location="US"):
    """创建BigQuery数据集"""
    print(f"📊 Creating BigQuery dataset: {dataset_name}")

    try:
        client = bigquery.Client(project=project_id, credentials=credentials)
        dataset_id = f"{project_id}.{dataset_name}"

        # 创建数据集
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = location

        dataset = client.create_dataset(dataset, timeout=30)
        print(f"✅ Successfully created BigQuery dataset: {dataset_name}")
        return True

    except Conflict:
        print(f"⚠️  Dataset {dataset_name} already exists")
        return True
    except Exception as e:
        print(f"❌ Error creating BigQuery dataset: {e}")
        return False

def upload_csv_to_bq_table(csv_file_path, table_name, dataset_name="machine_operating", project_id="mcp-bench0606"):
    """上传CSV文件到BigQuery表"""
    print(f"📤 Uploading {os.path.basename(csv_file_path)} to BigQuery table: {table_name}")

    try:
        client = bigquery.Client(project=project_id, credentials=credentials)
        table_id = f"{project_id}.{dataset_name}.{table_name}"

        # 配置加载作业
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,  # 跳过CSV头部
            autodetect=True,  # 自动检测schema
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE  # 替换现有表
        )

        # 从nCSV文件加载数据
        with open(csv_file_path, "rb") as source_file:
            load_job = client.load_table_from_file(
                source_file, table_id, job_config=job_config
            )

        # 等待作业完成
        load_job.result()

        # 获取表信息
        table = client.get_table(table_id)
        print(f"✅ Successfully uploaded {os.path.basename(csv_file_path)} to table: {table_name}")
        print(f"   Loaded {table.num_rows} rows to {table_name}")
        return True

    except Exception as e:
        print(f"❌ Error uploading CSV to BigQuery table: {e}")
        return False

def manage_machine_operating_dataset(project_id="mcp-bench0606", dataset_name="machine_operating", csv_file_path=None):
    """管理machine_operating BigQuery数据集的完整流程"""
    print(f"📊 Managing BigQuery dataset: {dataset_name}")

    # 如果没有指定CSV文件路径，使用默认路径
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

        # 检查数据集是否存在
        try:
            dataset = client.get_dataset(dataset_id)
            print(f"✅ BigQuery dataset {dataset_name} already exists")
            results["dataset_existed"] = True

            # 列出并删除所有表
            tables = list(client.list_tables(dataset_id))
            if tables:
                print(f"📋 Dataset contains {len(tables)} object(s) (tables/views):")
                for table in tables:
                    # table对象包含表和视图
                    table_type = "view" if table.table_type == "VIEW" else "table"
                    print(f"   - {table.table_id} ({table_type})")

                # 删除所有表和视图
                for table in tables:
                    table_id = f"{dataset_id}.{table.table_id}"
                    table_type = "view" if table.table_type == "VIEW" else "table"
                    print(f"🗑️  Deleting {table_type} {table.table_id}...")

                    try:
                        client.delete_table(table_id, not_found_ok=True)  # delete_table也能删除视图
                        print(f"✅ Successfully deleted {table_type} {table.table_id}")
                    except Exception as e:
                        print(f"⚠️  Could not delete {table_type} {table.table_id}: {e}")

                results["dataset_cleared"] = True
            else:
                print(f"📊 Dataset is empty, no tables or views to delete")

        except NotFound:
            # 数据集不存在，创建新的
            print(f"📊 Dataset {dataset_name} does not exist, creating new dataset...")
            dataset = bigquery.Dataset(dataset_id)
            dataset.location = "US"
            dataset = client.create_dataset(dataset, timeout=30)
            print(f"✅ Successfully created BigQuery dataset: {dataset_name}")
            results["dataset_created"] = True

        # 检查CSV文件是否存在
        if not os.path.exists(csv_file_path):
            print(f"❌ CSV file not found: {csv_file_path}")
            results["upload_failure"] = f"CSV file not found: {csv_file_path}"
            return results

        # 上传CSV文件到BigQuery表
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

def cleanup_preprocess_environment(workspace_dir, anomaly_report_pattern="anomaly_report"):
    """清理preprocess环境，为Machine Operating任务做准备"""
    print("🚀 Starting Machine Operating Anomaly Detection Preprocess Cleanup...")
    
    # 检查Google Cloud认证
    if not check_gcloud_authentication():
        print("⚠️  Warning: Google Cloud CLI not authenticated. Some cleanup may fail.")
        print("   Please run: gcloud auth login")
    
    cleanup_results = {}
    
    # 确保存储桶存在
    bucket_ready = ensure_bucket_exists("iot_anomaly_reports")
    cleanup_results["bucket_ready"] = bucket_ready
    
    # 删除异常报告文件（支持模式匹配）
    file_cleanup = delete_anomaly_reports_if_exist("iot_anomaly_reports", anomaly_report_pattern)
    cleanup_results["file_cleanup"] = file_cleanup

    # 管理machine_operating BigQuery数据集
    bq_dataset_results = manage_machine_operating_dataset()
    cleanup_results["bq_dataset_results"] = bq_dataset_results

    return cleanup_results

def verify_required_files(workspace_dir):
    """验证任务所需的数据文件是否存在"""
    print("🔍 Verifying required data files...")
    
    required_files = [
        "live_sensor_data.csv",
        "machine_operating_parameters.xlsx"
    ]
    
    missing_files = []
    existing_files = []
    
    for file_name in required_files:
        file_path = os.path.join(workspace_dir, file_name)
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            existing_files.append({
                "name": file_name,
                "path": file_path,
                "size_kb": file_size / 1024
            })
            print(f"✅ Found: {file_name} ({file_size/1024:.1f}KB)")
        else:
            missing_files.append(file_name)
            print(f"❌ Missing: {file_name}")
    
    if missing_files:
        print(f"\n⚠️  Warning: {len(missing_files)} required files are missing:")
        for file_name in missing_files:
            print(f"   - {file_name}")
        print("\nPlease generate the required data files using the data generation scripts.")
        return False, existing_files, missing_files
    else:
        print(f"\n✅ All {len(required_files)} required files are present!")
        return True, existing_files, missing_files

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True,
                       help="Agent workspace directory")
    parser.add_argument("--anomaly_report_pattern", default="anomaly_report",
                       help="Target anomaly report file pattern (default: anomaly_report, matches anomaly_report*.csv)")
    parser.add_argument("--cleanup_files", default=True, action="store_true",
                       help="Clean up existing anomaly report files to prevent task interference (default: enabled)")
    parser.add_argument("--no_cleanup", action="store_true",
                       help="Skip file cleanup (use when you want to preserve existing files)")
    parser.add_argument("--project_id", default="mcp-bench0606",
                       help="Google Cloud Project ID")
    parser.add_argument("--verify_data", action="store_true",
                       help="Verify required data files exist in workspace")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    
    args = parser.parse_args()
    
    print("=== Machine Operating Anomaly Detection Preprocess ===")
    print(f"Agent workspace: {args.agent_workspace}")
    print(f"Target anomaly report pattern: {args.anomaly_report_pattern}*.csv")
    print(f"Project ID: {args.project_id}")
    print(f"Verify data files: {args.verify_data}")
    
    # 确保workspace目录存在
    os.makedirs(args.agent_workspace, exist_ok=True)
    
    # 验证数据文件（如果启用）
    data_verification_passed = True
    existing_data_files = []
    missing_data_files = []
    
    if args.verify_data:
        print(f"\n📋 Verifying data files in workspace...")
        data_verification_passed, existing_data_files, missing_data_files = verify_required_files(args.agent_workspace)
    
    # 默认执行清理，除非明确指定不清理
    should_cleanup = args.cleanup_files and not args.no_cleanup
    
    if should_cleanup:
        print(f"\n🧹 Performing cleanup for anomaly reports matching pattern '{args.anomaly_report_pattern}*.csv'...")
        cleanup_results = cleanup_preprocess_environment(args.agent_workspace, args.anomaly_report_pattern)
        
        if cleanup_results.get("file_cleanup", False) or cleanup_results.get("bucket_ready", False):
            print("✅ Preprocess cleanup completed successfully!")
        else:
            print("⚠️  Preprocess cleanup completed with warnings.")
    else:
        print("ℹ️  Cleanup skipped (--no_cleanup specified).")
        cleanup_results = {"bucket_ready": False, "file_cleanup": False}
    
    print(f"\n🎯 Environment prepared for anomaly detection!")
    print(f"🔍 Ready to analyze sensor data and detect anomalies")
    print(f"📤 Target upload location: gs://iot_anomaly_reports/{args.anomaly_report_pattern}*.csv")
    print(f"💾 BigQuery machine_operating dataset is ready with live_sensor table")
    
    if data_verification_passed:
        print("✅ All required data files are available - ready for task execution")
    else:
        print("⚠️  Some data files are missing - please generate them first")
    
    if should_cleanup:
        print("🚨 Ready for task execution - existing anomaly reports and BigQuery dataset have been cleaned up")
