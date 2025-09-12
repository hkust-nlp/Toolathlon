from google.cloud import bigquery
import os
import glob
from pathlib import Path
import pandas as pd


def upload_csv_to_bigquery(
    project_id: str,
    dataset_id: str,
    table_name: str,
    csv_file_path: str,
    skip_header: bool = True,
    write_mode: str = "WRITE_TRUNCATE",
    credentials=None
):
    """
    Upload a single CSV file to BigQuery dataset
    
    Args:
        project_id: Google Cloud project ID
        dataset_id: BigQuery dataset ID
        table_name: Target table name
        csv_file_path: Path to the CSV file
        skip_header: Whether to skip first row (header)
        write_mode: WRITE_TRUNCATE, WRITE_APPEND, or WRITE_EMPTY
        credentials: Google Cloud credentials
    """

    # Initialize BigQuery client
    client = bigquery.Client(project=project_id, credentials=credentials)

    # Get dataset reference
    dataset_ref = client.dataset(dataset_id)

    print(f"\nUploading {csv_file_path} -> {dataset_id}.{table_name}")

    try:
        # Configure job
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1 if skip_header else 0,
            autodetect=True,  # Auto-detect schema
            write_disposition=write_mode
        )

        # Get table reference
        table_ref = dataset_ref.table(table_name)

        # Upload file
        with open(csv_file_path, "rb") as source_file:
            job = client.load_table_from_file(
                source_file,
                table_ref,
                job_config=job_config
            )

        # Wait for job to complete
        job.result()

        # Get table info
        table = client.get_table(table_ref)
        print(f"✅ Loaded {table.num_rows} rows into {dataset_id}.{table_name}")

        return True

    except Exception as e:
        print(f"❌ Error uploading {csv_file_path}: {e}")
        return False


def upload_csvs_to_bigquery(
    project_id: str,
    dataset_id: str,
    csv_folder: str,
    csv_pattern: str = "*.csv",
    skip_header: bool = True,
    write_mode: str = "WRITE_TRUNCATE",
    credentials=None
):
    """
    Upload multiple CSV files to BigQuery dataset
    
    Args:
        project_id: Google Cloud project ID
        dataset_id: BigQuery dataset ID
        csv_folder: Folder containing CSV files
        csv_pattern: Pattern to match CSV files (default: "*.csv")
        skip_header: Whether to skip first row (header)
        write_mode: WRITE_TRUNCATE, WRITE_APPEND, or WRITE_EMPTY
        credentials: Google Cloud credentials
    """

    # Initialize BigQuery client
    client = bigquery.Client(project=project_id, credentials=credentials)

    # Get dataset reference
    dataset_ref = client.dataset(dataset_id)

    # Create dataset if it doesn't exist
    try:
        dataset = client.get_dataset(dataset_ref)
        print(f"Dataset {dataset_id} already exists")
    except Exception:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "US"
        dataset = client.create_dataset(dataset)
        print(f"Created dataset {dataset_id}")

    # Find all CSV files
    csv_files = glob.glob(os.path.join(csv_folder, csv_pattern))

    if not csv_files:
        print(f"No CSV files found matching pattern {csv_pattern} in {csv_folder}")
        return

    print(f"Found {len(csv_files)} CSV files to upload")

    # Upload each CSV file
    success_count = 0
    for csv_file in csv_files:
        # Extract table name from filename (without extension)
        table_name = Path(csv_file).stem

        # Clean table name (BigQuery table names have restrictions)
        table_name = table_name.replace("-", "_").replace(" ", "_")

        success = upload_csv_to_bigquery(
            project_id=project_id,
            dataset_id=dataset_id,
            table_name=table_name,
            csv_file_path=csv_file,
            skip_header=skip_header,
            write_mode=write_mode,
            credentials=credentials
        )
        
        if success:
            success_count += 1

    print(f"\n✅ Upload complete: {success_count}/{len(csv_files)} files uploaded successfully")
    return success_count == len(csv_files)


def upload_transactions_data(project_id: str, credentials=None):
    """
    Specific function to upload flagged-transactions data
    """
    import os
    import sys

    # --- Add the parent directory ---
    current_file_path = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file_path)
    parent_dir = os.path.dirname(current_dir)
    base_path = parent_dir
    
    print("📊 Uploading flagged-transactions data to BigQuery...")
    
    # Upload all_transactions.csv as the main table
    all_transactions_path = os.path.join(base_path, "files", "all_transactions.csv")
    
    if not os.path.exists(all_transactions_path):
        print(f"❌ File not found: {all_transactions_path}")
        return False
    
    # Upload to table named "all_transactions_recordings" to match the task description
    success = upload_csv_to_bigquery(
        project_id=project_id,
        dataset_id="all_transactions",
        table_name="recordings",
        csv_file_path=all_transactions_path,
        credentials=credentials
    )
    
    if success:
        print("💳 Flagged transactions data uploaded successfully!")
        
        # Display some info about the uploaded data
        client = bigquery.Client(project=project_id, credentials=credentials)
        query = f"""
        SELECT 
            COUNT(*) as total_rows,
            COUNT(DISTINCT client_id) as unique_clients,
            MIN(PARSE_DATETIME('%Y-%m-%d %H:%M:%S.%f UTC', txn_time)) as earliest_transaction,
            MAX(PARSE_DATETIME('%Y-%m-%d %H:%M:%S.%f UTC', txn_time)) as latest_transaction,
            AVG(amount) as avg_amount
        FROM `{project_id}.all_transactions.recordings`
        """
        
        try:
            result = client.query(query).result()
            for row in result:
                print(f"📈 Data summary:")
                print(f"  - Total rows: {row.total_rows:,}")
                print(f"  - Unique clients: {row.unique_clients}")
                print(f"  - Date range: {row.earliest_transaction} to {row.latest_transaction}")
                print(f"  - Average amount: ${row.avg_amount:.2f}")
        except Exception as e:
            print(f"⚠️  Could not retrieve data summary: {e}")
    
    return success