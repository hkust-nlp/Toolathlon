from argparse import ArgumentParser
import os
import subprocess
import json

def check_gcloud_authentication():
    """检查Google Cloud CLI是否已认证"""
    try:
        result = subprocess.run(['gcloud', 'auth', 'list', '--filter=status:ACTIVE', '--format=value(account)'], 
                              capture_output=True, text=True, check=True)
        if '@' in result.stdout:
            return True
        return False
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def delete_anomaly_reports_if_exist(bucket_name="iot_anomaly_reports", file_pattern="anomaly_report", project_id="mcp-bench0606"):
    """删除Google Cloud Storage存储桶中的异常报告文件（支持模式匹配）"""
    print(f"🧹 Checking for existing anomaly reports: gs://{bucket_name}/{file_pattern}*.csv")
    
    try:
        # 列出所有匹配的文件
        list_result = subprocess.run(['gcloud', 'storage', 'ls', f'gs://{bucket_name}/'], 
                                   capture_output=True, text=True)
        
        if list_result.returncode != 0:
            print(f"✅ Bucket {bucket_name} is empty or does not exist - no cleanup needed")
            return True
        
        # 解析文件列表，查找匹配的异常报告文件
        files_to_delete = []
        for line in list_result.stdout.strip().split('\n'):
            if line.strip():
                # 提取文件名
                file_url = line.strip()
                if file_url.startswith(f'gs://{bucket_name}/'):
                    file_name = file_url.replace(f'gs://{bucket_name}/', '')
                    # 检查是否匹配模式
                    if file_name.startswith(file_pattern) and file_name.endswith('.csv'):
                        files_to_delete.append(file_name)
        
        if not files_to_delete:
            print(f"✅ No anomaly report files found matching pattern '{file_pattern}*.csv' - no cleanup needed")
            return True
        
        print(f"📄 Found {len(files_to_delete)} anomaly report file(s) to delete:")
        for file_name in files_to_delete:
            print(f"   - {file_name}")
        
        # 删除找到的文件
        deleted_count = 0
        failed_count = 0
        
        for file_name in files_to_delete:
            print(f"🗑️  Deleting: {file_name}")
            delete_result = subprocess.run(['gcloud', 'storage', 'rm', f'gs://{bucket_name}/{file_name}'], 
                                         capture_output=True, text=True)
            
            if delete_result.returncode == 0:
                print(f"✅ Successfully deleted: {file_name}")
                deleted_count += 1
            else:
                print(f"❌ Failed to delete: {file_name}")
                print(f"Error: {delete_result.stderr}")
                failed_count += 1
        
        print(f"📊 Cleanup summary: {deleted_count} deleted, {failed_count} failed")
        return failed_count == 0
            
    except FileNotFoundError:
        print("❌ Error: gcloud command not found. Please install Google Cloud SDK.")
        return False
    except Exception as e:
        print(f"❌ Error checking/deleting anomaly reports: {e}")
        return False

def ensure_bucket_exists(bucket_name="iot_anomaly_reports", project_id="mcp-bench0606"):
    """确保存储桶存在，如果不存在则创建"""
    print(f"🔍 Checking if bucket exists: {bucket_name}")
    
    try:
        # 检查存储桶是否存在
        check_result = subprocess.run(['gcloud', 'storage', 'ls', f'gs://{bucket_name}'], 
                                    capture_output=True, text=True)
        
        if check_result.returncode == 0:
            print(f"✅ Bucket {bucket_name} already exists")
            return True
        else:
            print(f"📦 Creating bucket: {bucket_name}")
            # 创建存储桶
            create_result = subprocess.run(['gcloud', 'storage', 'buckets', 'create', f'gs://{bucket_name}', 
                                          '--project', project_id, '--location=us-central1'], 
                                         capture_output=True, text=True)
            
            if create_result.returncode == 0:
                print(f"✅ Successfully created bucket: {bucket_name}")
                return True
            else:
                print(f"❌ Failed to create bucket: {bucket_name}")
                print(f"Error: {create_result.stderr}")
                return False
                
    except FileNotFoundError:
        print("❌ Error: gcloud command not found. Please install Google Cloud SDK.")
        return False
    except Exception as e:
        print(f"❌ Error checking/creating bucket: {e}")
        return False

def check_bq_dataset_exists(dataset_name="machine_operating", project_id="mcp-bench0606"):
    """检查BigQuery数据集是否存在"""
    print(f"🔍 Checking if BigQuery dataset exists: {dataset_name}")
    
    try:
        # 检查数据集是否存在 - 使用简单的列表命令然后解析
        check_result = subprocess.run(['bq', 'ls', '--project_id', project_id], 
                                    capture_output=True, text=True)
        
        if check_result.returncode == 0:
            # 解析输出，跳过表头，提取第一列（数据集名称）
            lines = check_result.stdout.strip().split('\n')
            if len(lines) > 2:  # 跳过表头
                for line in lines[2:]:  # 从第3行开始
                    if line.strip():
                        dataset = line.strip().split()[0]  # 获取第一列
                        if dataset == dataset_name:
                            print(f"✅ BigQuery dataset {dataset_name} already exists")
                            return True
            
            print(f"📊 BigQuery dataset {dataset_name} does not exist")
            return False
        else:
            print(f"❌ Failed to list BigQuery datasets")
            print(f"Error: {check_result.stderr}")
            return False
            
    except FileNotFoundError:
        print("❌ Error: bq command not found. Please install Google Cloud SDK.")
        return False
    except Exception as e:
        print(f"❌ Error checking BigQuery dataset: {e}")
        return False

def delete_bq_dataset(dataset_name="machine_operating", project_id="mcp-bench0606"):
    """删除BigQuery数据集"""
    print(f"🗑️  Deleting BigQuery dataset: {dataset_name}")
    
    try:
        # 删除数据集（包括所有表）
        delete_result = subprocess.run(['bq', 'rm', '-r', '-f', '--project_id', project_id, dataset_name], 
                                     capture_output=True, text=True)
        
        if delete_result.returncode == 0:
            print(f"✅ Successfully deleted BigQuery dataset: {dataset_name}")
            return True
        else:
            print(f"❌ Failed to delete BigQuery dataset: {dataset_name}")
            print(f"Error: {delete_result.stderr}")
            return False
            
    except FileNotFoundError:
        print("❌ Error: bq command not found. Please install Google Cloud SDK.")
        return False
    except Exception as e:
        print(f"❌ Error deleting BigQuery dataset: {e}")
        return False

def create_bq_dataset(dataset_name="machine_operating", project_id="mcp-bench0606", location="US"):
    """创建BigQuery数据集"""
    print(f"📊 Creating BigQuery dataset: {dataset_name}")
    
    try:
        # 创建数据集
        create_result = subprocess.run(['bq', 'mk', '--project_id', project_id, '--location', location, dataset_name], 
                                     capture_output=True, text=True)
        
        if create_result.returncode == 0:
            print(f"✅ Successfully created BigQuery dataset: {dataset_name}")
            return True
        else:
            print(f"❌ Failed to create BigQuery dataset: {dataset_name}")
            print(f"Error: {create_result.stderr}")
            return False
            
    except FileNotFoundError:
        print("❌ Error: bq command not found. Please install Google Cloud SDK.")
        return False
    except Exception as e:
        print(f"❌ Error creating BigQuery dataset: {e}")
        return False

def upload_csv_to_bq_table(csv_file_path, table_name, dataset_name="machine_operating", project_id="mcp-bench0606"):
    """上传CSV文件到BigQuery表"""
    print(f"📤 Uploading {os.path.basename(csv_file_path)} to BigQuery table: {table_name}")
    
    try:
        # 构建表的完整路径
        table_path = f"{project_id}:{dataset_name}.{table_name}"
        
        # 上传CSV文件到BigQuery表，自动检测schema
        upload_result = subprocess.run(['bq', 'load', '--autodetect', '--source_format=CSV', 
                                      '--replace', table_path, csv_file_path], 
                                     capture_output=True, text=True)
        
        if upload_result.returncode == 0:
            print(f"✅ Successfully uploaded {os.path.basename(csv_file_path)} to table: {table_name}")
            return True
        else:
            print(f"❌ Failed to upload {os.path.basename(csv_file_path)} to table: {table_name}")
            print(f"Error: {upload_result.stderr}")
            return False
            
    except FileNotFoundError:
        print("❌ Error: bq command not found. Please install Google Cloud SDK.")
        return False
    except Exception as e:
        print(f"❌ Error uploading CSV to BigQuery table: {e}")
        return False

def manage_machine_operating_dataset(project_id="mcp-bench0606", dataset_name="machine_operating", csv_file_path="/Users/zengweihao/mcp-bench/mcpbench_dev/tasks/finalpool/machine_operating/preprocess/machine_operating/live_sensor.csv"):
    """管理machine_operating BigQuery数据集的完整流程"""
    print(f"📊 Managing BigQuery dataset: {dataset_name}")
    
    results = {
        "dataset_existed": False,
        "dataset_deleted": False,
        "dataset_created": False,
        "table_uploaded": False,
        "upload_failure": None
    }
    
    # 检查数据集是否存在
    dataset_exists = check_bq_dataset_exists(dataset_name, project_id)
    results["dataset_existed"] = dataset_exists
    
    if dataset_exists:
        # 如果存在，删除数据集
        dataset_deleted = delete_bq_dataset(dataset_name, project_id)
        results["dataset_deleted"] = dataset_deleted
        if not dataset_deleted:
            print(f"❌ Failed to delete existing dataset {dataset_name}")
            return results
    
    # 创建新的数据集
    dataset_created = create_bq_dataset(dataset_name, project_id)
    results["dataset_created"] = dataset_created
    
    if not dataset_created:
        print(f"❌ Failed to create dataset {dataset_name}")
        return results
    
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
    
    # 保存清理结果到workspace
    results_file = os.path.join(workspace_dir, "preprocess_cleanup_results.json")
    with open(results_file, 'w') as f:
        json.dump({
            "cleanup_timestamp": subprocess.run(['date', '+%Y-%m-%d %H:%M:%S'], 
                                              capture_output=True, text=True).stdout.strip(),
            "target_anomaly_report_pattern": f"{anomaly_report_pattern}*.csv",
            "bucket_ready": bucket_ready,
            "file_cleanup_success": file_cleanup,
            "bq_dataset_results": bq_dataset_results,
            "cleanup_pattern": f"gs://iot_anomaly_reports/{anomaly_report_pattern}*.csv",
            "bucket_name": "iot_anomaly_reports",
            "bq_dataset_name": "machine_operating",
            "status": "completed"
        }, f, indent=2)
    
    print(f"📋 Cleanup results saved to: {results_file}")
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
    
    # 创建最终结果文件
    results_file = os.path.join(args.agent_workspace, "preprocess_results.json")
    final_results = {
        "timestamp": subprocess.run(['date', '+%Y-%m-%d %H:%M:%S'], 
                                  capture_output=True, text=True).stdout.strip(),
        "target_anomaly_report_pattern": f"{args.anomaly_report_pattern}*.csv",
        "cleanup_performed": should_cleanup,
        "data_verification_performed": args.verify_data,
        "data_verification_passed": data_verification_passed,
        "existing_data_files": existing_data_files,
        "missing_data_files": missing_data_files,
        "bucket_name": "iot_anomaly_reports",
        "bq_dataset_name": "machine_operating",
        "expected_output_pattern": f"{args.anomaly_report_pattern}*.csv",
        "status": "ready_for_anomaly_detection" if data_verification_passed else "data_files_missing",
        "task_description": "Analyze sensor data, detect anomalies, and upload report to IoT bucket"
    }
    
    # 如果执行了清理，添加详细结果
    if should_cleanup and 'cleanup_results' in locals():
        final_results["cleanup_details"] = cleanup_results
        
    with open(results_file, 'w') as f:
        json.dump(final_results, f, indent=2)
    
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
