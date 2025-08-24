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

def delete_investigation_file_if_exists(bucket_name="mcp-fraud-investigation-archive", file_name="T8492XJ3.json", project_id="mcp-bench0606"):
    """删除Google Cloud Storage存储桶中的调查文件（如果存在）"""
    print(f"🧹 Checking for existing investigation file: gs://{bucket_name}/{file_name}")
    
    try:
        # 检查文件是否存在
        check_result = subprocess.run(['gcloud', 'storage', 'ls', f'gs://{bucket_name}/{file_name}'], 
                                    capture_output=True, text=True)
        
        if check_result.returncode == 0:
            print(f"📄 Found existing investigation file: {file_name}")
            print(f"🗑️  Deleting file: {file_name} to allow fresh task execution...")
            
            # 删除文件
            delete_result = subprocess.run(['gcloud', 'storage', 'rm', f'gs://{bucket_name}/{file_name}'], 
                                         capture_output=True, text=True)
            
            if delete_result.returncode == 0:
                print(f"✅ Successfully deleted investigation file: {file_name}")
                return True
            else:
                print(f"❌ Failed to delete investigation file: {file_name}")
                print(f"Error: {delete_result.stderr}")
                return False
        else:
            print(f"✅ Investigation file {file_name} does not exist - no cleanup needed")
            return True
            
    except FileNotFoundError:
        print("❌ Error: gcloud command not found. Please install Google Cloud SDK.")
        return False
    except Exception as e:
        print(f"❌ Error checking/deleting investigation file: {e}")
        return False

def ensure_bucket_exists(bucket_name="mcp-fraud-investigation-archive", project_id="mcp-bench0606"):
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

def check_log_bucket_exists(bucket_name="Trading_Logging", project_id="mcp-bench0606"):
    """检查Google Cloud Logging bucket是否存在"""
    print(f"🔍 Checking if log bucket exists: {bucket_name}")
    
    try:
        # 检查log bucket是否存在 - 使用正确的格式获取bucket名称
        check_result = subprocess.run(['gcloud', 'logging', 'buckets', 'list', 
                                     '--project', project_id, '--format=value(name.basename())'], 
                                    capture_output=True, text=True)
        
        if check_result.returncode == 0:
            # 检查输出中是否包含我们的bucket名称
            buckets = check_result.stdout.strip().split('\n')
            for bucket in buckets:
                if bucket.strip() == bucket_name:
                    print(f"✅ Log bucket {bucket_name} already exists")
                    return True
            
            print(f"📝 Log bucket {bucket_name} does not exist")
            return False
        else:
            print(f"❌ Failed to list log buckets")
            print(f"Error: {check_result.stderr}")
            return False
            
    except FileNotFoundError:
        print("❌ Error: gcloud command not found. Please install Google Cloud SDK.")
        return False
    except Exception as e:
        print(f"❌ Error checking log bucket: {e}")
        return False

def create_log_bucket(bucket_name="Trading_Logging", project_id="mcp-bench0606", location="global"):
    """创建Google Cloud Logging bucket"""
    print(f"📝 Creating log bucket: {bucket_name}")
    
    try:
        # 创建log bucket
        create_result = subprocess.run(['gcloud', 'logging', 'buckets', 'create', bucket_name,
                                      '--project', project_id, '--location', location,
                                      '--retention-days=30'], 
                                     capture_output=True, text=True)
        
        if create_result.returncode == 0:
            print(f"✅ Successfully created log bucket: {bucket_name}")
            return True
        else:
            # 检查是否是因为bucket已存在而失败
            if "ALREADY_EXISTS" in create_result.stderr:
                print(f"✅ Log bucket {bucket_name} already exists (detected during creation)")
                return True
            else:
                print(f"❌ Failed to create log bucket: {bucket_name}")
                print(f"Error: {create_result.stderr}")
                return False
            
    except FileNotFoundError:
        print("❌ Error: gcloud command not found. Please install Google Cloud SDK.")
        return False
    except Exception as e:
        print(f"❌ Error creating log bucket: {e}")
        return False

def clear_log_bucket_logs(bucket_name="Trading_Logging", project_id="mcp-bench0606"):
    """清空log bucket中的日志"""
    print(f"🧹 Clearing logs from log bucket: {bucket_name}")
    
    try:
        # 首先列出bucket中的日志
        list_result = subprocess.run(['gcloud', 'logging', 'logs', 'list', 
                                    '--project', project_id, '--format=value(name)'], 
                                   capture_output=True, text=True)
        
        if list_result.returncode != 0:
            print(f"❌ Failed to list logs in project")
            print(f"Error: {list_result.stderr}")
            return False
        
        # 删除与Trading相关的日志
        logs_to_delete = []
        if list_result.stdout.strip():
            all_logs = list_result.stdout.strip().split('\n')
            logs_to_delete = [log for log in all_logs if 'trading' in log.lower() or 'transaction' in log.lower()]
        
        if logs_to_delete:
            print(f"🗑️  Found {len(logs_to_delete)} trading-related logs to clear")
            
            for log_name in logs_to_delete:
                delete_result = subprocess.run(['gcloud', 'logging', 'logs', 'delete', log_name,
                                              '--project', project_id, '--quiet'], 
                                             capture_output=True, text=True)
                
                if delete_result.returncode == 0:
                    print(f"✅ Cleared log: {log_name}")
                else:
                    print(f"⚠️  Failed to clear log: {log_name}")
        else:
            print(f"✅ No trading-related logs found to clear")
        
        return True
        
    except FileNotFoundError:
        print("❌ Error: gcloud command not found. Please install Google Cloud SDK.")
        return False
    except Exception as e:
        print(f"❌ Error clearing log bucket logs: {e}")
        return False

def manage_trading_log_bucket(project_id="mcp-bench0606", bucket_name="Trading_Logging"):
    """管理Trading_Logging log bucket的完整流程"""
    print(f"📊 Managing Trading_Logging log bucket...")
    
    results = {
        "bucket_exists": False,
        "bucket_created": False,
        "logs_cleared": False
    }
    
    # 检查bucket是否存在
    bucket_exists = check_log_bucket_exists(bucket_name, project_id)
    results["bucket_exists"] = bucket_exists
    
    if bucket_exists:
        # 如果存在，清空日志
        logs_cleared = clear_log_bucket_logs(bucket_name, project_id)
        results["logs_cleared"] = logs_cleared
        print(f"✅ Log bucket {bucket_name} is ready (logs cleared)")
    else:
        # 如果不存在，创建新的bucket
        bucket_created = create_log_bucket(bucket_name, project_id)
        results["bucket_created"] = bucket_created
        if bucket_created:
            print(f"✅ Log bucket {bucket_name} is ready (newly created)")
        else:
            print(f"❌ Failed to prepare log bucket {bucket_name}")
    
    return results

def check_bq_dataset_exists(dataset_name="transactions_analytics", project_id="mcp-bench0606"):
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

def delete_bq_dataset(dataset_name="transactions_analytics", project_id="mcp-bench0606"):
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

def create_bq_dataset(dataset_name="transactions_analytics", project_id="mcp-bench0606", location="US"):
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

def upload_csv_to_bq_table(csv_file_path, table_name, dataset_name="transactions_analytics", project_id="mcp-bench0606"):
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

def manage_transactions_analytics_dataset(project_id="mcp-bench0606", dataset_name="transactions_analytics", csv_directory="transactions_analytics"):
    """管理transactions_analytics BigQuery数据集的完整流程"""
    print(f"📊 Managing BigQuery dataset: {dataset_name}")
    
    results = {
        "dataset_existed": False,
        "dataset_deleted": False,
        "dataset_created": False,
        "tables_uploaded": [],
        "upload_failures": []
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
    
    # 获取当前脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_dir_path = os.path.join(script_dir, csv_directory)
    
    if not os.path.exists(csv_dir_path):
        print(f"❌ CSV directory not found: {csv_dir_path}")
        return results
    
    # 上传所有CSV文件到BigQuery表
    csv_files = [f for f in os.listdir(csv_dir_path) if f.endswith('.csv')]
    print(f"📁 Found {len(csv_files)} CSV files to upload")
    
    for csv_file in csv_files:
        csv_file_path = os.path.join(csv_dir_path, csv_file)
        table_name = os.path.splitext(csv_file)[0]  # 移除.csv后缀作为表名
        
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
    """清理preprocess环境，为Live Transactions任务做准备"""
    print("🚀 Starting Live Transactions Preprocess Cleanup...")
    
    # 检查Google Cloud认证
    if not check_gcloud_authentication():
        print("⚠️  Warning: Google Cloud CLI not authenticated. Some cleanup may fail.")
        print("   Please run: gcloud auth login")
    
    cleanup_results = {}
    
    # 确保存储桶存在
    bucket_ready = ensure_bucket_exists("mcp-fraud-investigation-archive", project_id)
    cleanup_results["bucket_ready"] = bucket_ready
    
    # 删除目标交易的调查文件（如果存在）
    file_cleanup = delete_investigation_file_if_exists("mcp-fraud-investigation-archive", f"{target_transaction_id}.json", project_id)
    cleanup_results["file_cleanup"] = file_cleanup
    
    # 管理Trading_Logging log bucket
    log_bucket_results = manage_trading_log_bucket(project_id)
    cleanup_results["log_bucket_results"] = log_bucket_results

    # 管理transactions_analytics BigQuery数据集
    bq_dataset_results = manage_transactions_analytics_dataset(project_id)
    cleanup_results["bq_dataset_results"] = bq_dataset_results
    
    # 保存清理结果到workspace
    results_file = os.path.join(workspace_dir, "preprocess_cleanup_results.json")
    with open(results_file, 'w') as f:
        json.dump({
            "cleanup_timestamp": subprocess.run(['date', '+%Y-%m-%d %H:%M:%S'], 
                                              capture_output=True, text=True).stdout.strip(),
            "target_transaction_id": target_transaction_id,
            "bucket_ready": bucket_ready,
            "file_cleanup_success": file_cleanup,
            "log_bucket_results": log_bucket_results,
            "bq_dataset_results": bq_dataset_results,
            "cleaned_files": [f"{target_transaction_id}.json"] if file_cleanup else [],
            "bucket_name": "mcp-fraud-investigation-archive",
            "status": "completed"
        }, f, indent=2)
    
    print(f"📋 Cleanup results saved to: {results_file}")
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
    
    print("=== Live Transactions Fraud Investigation Preprocess ===")
    print(f"Agent workspace: {args.agent_workspace}")
    print(f"Target transaction ID: {args.transaction_id}")
    print(f"Project ID: {args.project_id}")
    
    # 确保workspace目录存在
    os.makedirs(args.agent_workspace, exist_ok=True)
    
    # 默认执行清理，除非明确指定不清理
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
    
    # 创建最终结果文件
    results_file = os.path.join(args.agent_workspace, "preprocess_results.json")
    final_results = {
        "timestamp": subprocess.run(['date', '+%Y-%m-%d %H:%M:%S'], 
                                  capture_output=True, text=True).stdout.strip(),
        "target_transaction_id": args.transaction_id,
        "cleanup_performed": should_cleanup,
        "bucket_name": "mcp-fraud-investigation-archive",
        "log_bucket_name": "Trading_Logging",
        "bq_dataset_name": "transactions_analytics",
        "expected_output_file": f"{args.transaction_id}.json",
        "status": "ready_for_investigation",
        "task_description": "Investigate suspicious transaction and upload to archive bucket"
    }
    
    # 如果执行了清理，添加详细结果
    if should_cleanup and 'cleanup_results' in locals():
        final_results["cleanup_details"] = cleanup_results
        
    with open(results_file, 'w') as f:
        json.dump(final_results, f, indent=2)
    
    print(f"\n🎯 Environment prepared for fraud investigation!")
    print(f"🔍 Ready to investigate transaction: {args.transaction_id}")
    print(f"📤 Target upload location: gs://mcp-fraud-investigation-archive/{args.transaction_id}.json")
    print(f"📊 Trading_Logging log bucket is ready for transaction logging")
    print(f"💾 BigQuery transactions_analytics dataset is ready with fresh data")
    print("🚨 Ready for task execution - environment has been prepared and cleaned up")
