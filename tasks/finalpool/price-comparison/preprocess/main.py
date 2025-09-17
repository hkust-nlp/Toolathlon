#!/usr/bin/env python3
"""
BigQuery Pricing Analysis Preprocessing Pipeline
This script sets up the BigQuery dataset for competitive pricing analysis
"""

import sys
import os
import json
from pathlib import Path
from google.cloud import bigquery
from google.oauth2.service_account import Credentials

# Add the root directory to the path to import utils
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

# Import local token key session for this task
sys.path.append(str(Path(__file__).parent.parent))
from token_key_session import all_token_key_session


def _get_bigquery_client() -> bigquery.Client:
    """
    Initialize BigQuery client using service account credentials
    """
    try:
        # First try to use service account file from global config  
        service_account_path = "configs/gcp-service_account.keys.json"
        
        if os.path.exists(service_account_path):
            print(f"Using service account from: {service_account_path}")
            credentials = Credentials.from_service_account_file(service_account_path)
            
            # Read project_id from service account file
            with open(service_account_path, 'r') as f:
                service_account_info = json.load(f)
                project_id = service_account_info.get('project_id')
            
            return bigquery.Client(credentials=credentials, project=project_id)
        
        # Last resort: try default credentials without specifying project
        print("Warning: No credentials file found, trying default credentials")
        return bigquery.Client()  # Let it determine project automatically
        
    except Exception as e:
        print(f"Error initializing BigQuery client: {e}")
        import traceback
        traceback.print_exc()
        raise e


def check_and_delete_dataset(client: bigquery.Client, dataset_name: str) -> bool:
    """
    Check if dataset exists and delete it if found
    
    Args:
        client: BigQuery client instance
        dataset_name: Name of the dataset to check and delete
        
    Returns:
        bool: True if dataset was deleted or didn't exist, False if error occurred
    """
    try:
        # First, try to get dataset info to see if it exists
        print(f"Checking if dataset '{dataset_name}' exists...")
        
        dataset_ref = client.dataset(dataset_name)
        try:
            client.get_dataset(dataset_ref)
            # If we get here, dataset exists
            print(f"Dataset '{dataset_name}' found. Attempting to delete...")
            
            # Delete the dataset and all its contents
            client.delete_dataset(dataset_ref, delete_contents=True, not_found_ok=True)
            print(f"Dataset '{dataset_name}' deleted successfully")
            return True
            
        except Exception as e:
            if "Not found" in str(e) or "does not exist" in str(e):
                print(f"Dataset '{dataset_name}' does not exist - no need to delete")
                return True
            else:
                print(f"Error checking dataset: {e}")
                return False
        
    except Exception as e:
        print(f"Error in check_and_delete_dataset: {e}")
        return False


def create_dataset(client: bigquery.Client, dataset_name: str) -> bool:
    """
    Create a new empty BigQuery dataset
    
    Args:
        client: BigQuery client instance
        dataset_name: Name of the dataset to create
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"Creating dataset '{dataset_name}'...")
        
        # Create dataset reference
        dataset_ref = client.dataset(dataset_name)
        
        # Create dataset object with configuration
        dataset = bigquery.Dataset(dataset_ref)
        dataset.description = "Dataset for competitive pricing analysis between our products and FutureGadget"
        dataset.location = "US"
        
        # Create the dataset
        dataset = client.create_dataset(dataset, timeout=30)  # Wait up to 30 seconds
        
        print(f"Dataset '{dataset_name}' created successfully")
        print(f"Dataset location: {dataset.location}")
        print(f"Dataset description: {dataset.description}")
        return True
        
    except Exception as e:
        print(f"Error creating dataset: {e}")
        return False


def verify_dataset_creation(client: bigquery.Client, dataset_name: str) -> bool:
    """
    Verify that the dataset was created successfully
    
    Args:
        client: BigQuery client instance
        dataset_name: Name of the dataset to verify
        
    Returns:
        bool: True if dataset exists, False otherwise
    """
    try:
        print(f"Verifying dataset '{dataset_name}' creation...")
        
        dataset_ref = client.dataset(dataset_name)
        dataset = client.get_dataset(dataset_ref)
        
        print(f"Dataset '{dataset_name}' verified successfully")
        print(f"Dataset ID: {dataset.dataset_id}")
        print(f"Dataset location: {dataset.location}")
        print(f"Dataset description: {dataset.description}")
        print(f"Dataset created: {dataset.created}")
        return True
        
    except Exception as e:
        print(f"Error verifying dataset: {e}")
        return False


def list_all_datasets(client: bigquery.Client) -> bool:
    """
    List all datasets to confirm our dataset exists
    
    Args:
        client: BigQuery client instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print("Listing all datasets...")
        
        datasets = list(client.list_datasets())
        
        if datasets:
            print("Available datasets:")
            for dataset in datasets:
                print(f"  - {dataset.dataset_id}")
        else:
            print("No datasets found in this project")
        
        return True
        
    except Exception as e:
        print(f"Error listing datasets: {e}")
        return False


def main():
    """
    Main preprocessing pipeline
    """
    dataset_name = "bigquery_pricing_analysis"
    
    print("=" * 60)
    print("BigQuery Pricing Analysis - Preprocessing Pipeline")
    print("=" * 60)
    
    # Initialize BigQuery client
    try:
        print("Initializing BigQuery client...")
        client = _get_bigquery_client()
        print(f"BigQuery client initialized for project: {client.project}")
        
        # Step 1: Check and delete existing dataset if it exists
        print("\n" + "=" * 40)
        print("Step 1: Check and delete existing dataset")
        print("=" * 40)
        
        if not check_and_delete_dataset(client, dataset_name):
            print("Warning: Could not check/delete existing dataset, continuing anyway")
        
        # Step 2: Create new empty dataset
        print("\n" + "=" * 40)
        print("Step 2: Create new empty dataset")
        print("=" * 40)
        
        success = create_dataset(client, dataset_name)
        if not success:
            print("Failed to create dataset")
            return False
        
        # Step 3: Verify dataset creation
        print("\n" + "=" * 40)
        print("Step 3: Verify dataset creation")
        print("=" * 40)
        
        if not verify_dataset_creation(client, dataset_name):
            print("Failed to verify dataset creation")
            return False
        
        # Step 4: List all datasets for confirmation
        print("\n" + "=" * 40)
        print("Step 4: List all datasets")
        print("=" * 40)
        
        list_all_datasets(client)
        
        print("\n" + "=" * 60)
        print("Preprocessing pipeline completed successfully!")
        print(f"Dataset '{dataset_name}' is ready for competitive pricing analysis")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"Error in preprocessing pipeline: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Run the main function
    success = main()
    sys.exit(0 if success else 1)