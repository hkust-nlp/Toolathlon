from google.cloud import bigquery
from google.cloud.exceptions import NotFound, Conflict
import sys


def manage_bigquery_dataset(
    project_id: str,
    dataset_id: str,
    location: str = "US",
    description: str = None,
    delete_if_exists: bool = True,
    credentials=None
):
    """
    Check if BigQuery dataset exists, optionally delete and recreate it
    
    Args:
        project_id: Google Cloud project ID
        dataset_id: BigQuery dataset ID
        location: Dataset location (default: "US")
        description: Optional dataset description
        delete_if_exists: If True, delete existing dataset before creating new one
        credentials: Google Cloud credentials
    
    Returns:
        bigquery.Dataset: The created dataset object
    """
    
    # Initialize BigQuery client
    try:
        client = bigquery.Client(project=project_id, credentials=credentials)
        print(f"Connected to project: {project_id}")
    except Exception as e:
        print(f"❌ Failed to initialize BigQuery client: {e}")
        print("Make sure you're authenticated: gcloud auth application-default login")
        sys.exit(1)
    
    # Get dataset reference
    dataset_ref = client.dataset(dataset_id)
    
    # Check if dataset exists
    try:
        existing_dataset = client.get_dataset(dataset_ref)
        print(f"✅ Dataset '{dataset_id}' exists")
        
        if delete_if_exists:
            print(f"🗑️  Deleting existing dataset '{dataset_id}' and all its tables...")
            try:
                # Delete dataset and all tables
                client.delete_dataset(dataset_ref, delete_contents=True, not_found_ok=True)
                print(f"✅ Dataset '{dataset_id}' deleted successfully")
            except Exception as e:
                print(f"❌ Failed to delete dataset: {e}")
                return None
        else:
            print(f"ℹ️  Dataset '{dataset_id}' already exists, skipping creation")
            return existing_dataset
            
    except NotFound:
        print(f"ℹ️  Dataset '{dataset_id}' does not exist")
    except Exception as e:
        print(f"❌ Error checking dataset: {e}")
        return None
    
    # Create new dataset
    print(f"🔨 Creating new dataset '{dataset_id}'...")
    try:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = location
        if description:
            dataset.description = description
            
        created_dataset = client.create_dataset(dataset, exists_ok=False)
        print(f"✅ Dataset '{dataset_id}' created successfully in {location}")
        return created_dataset
        
    except Conflict:
        print(f"ℹ️  Dataset '{dataset_id}' already exists (race condition)")
        return client.get_dataset(dataset_ref)
    except Exception as e:
        print(f"❌ Failed to create dataset: {e}")
        return None


def check_dataset_exists(project_id: str, dataset_id: str, credentials=None) -> bool:
    """
    Simple function to check if a dataset exists
    
    Returns:
        bool: True if dataset exists, False otherwise
    """
    try:
        client = bigquery.Client(project=project_id, credentials=credentials)
        dataset_ref = client.dataset(dataset_id)
        client.get_dataset(dataset_ref)
        return True
    except NotFound:
        return False
    except Exception as e:
        print(f"Error checking dataset: {e}")
        return False


def setup_all_transactions_dataset(project_id: str, credentials=None):
    """Specific setup for flagged-transactions task"""
    
    dataset = manage_bigquery_dataset(
        project_id=project_id,
        dataset_id="all_transactions",
        location="US",
        description="Flagged transactions dataset for anomaly detection analysis",
        delete_if_exists=True,
        credentials=credentials
    )
    
    if dataset:
        print(f"💳 Flagged transactions dataset ready: {dataset.dataset_id}")
        return dataset
    else:
        print("❌ Failed to setup flagged transactions dataset")
        return None


def clean_dataset(project_id, credentials=None):
    """Clean and setup the all_transactions dataset"""
    print("\n1. Checking if dataset exists...")
    exists = check_dataset_exists(project_id, "all_transactions", credentials)
    print(f"Dataset 'all_transactions' exists: {exists}")
    
    print("\n2. Setting up clean all_transactions dataset...")
    dataset = setup_all_transactions_dataset(project_id, credentials)
    
    if dataset:
        print("\n✅ Dataset management complete!")
        print(f"Ready to populate dataset '{dataset.dataset_id}' with transaction data.")
        return dataset
    else:
        print("\n❌ Dataset management failed!")
        return None