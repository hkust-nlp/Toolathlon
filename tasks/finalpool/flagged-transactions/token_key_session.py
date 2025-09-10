from addict import Dict
import os
# I am gradually modifying the tokens to the pseudo account in this project
all_token_key_session = Dict(
    # default set to null to disable the agent from access anything
    # reset in task specific dir for the names your task needs
    google_cloud_allowed_buckets = "promo-assets-for-b,mcp-fraud-investigation-archive,iot_anomaly_reports",
    google_cloud_allowed_bigquery_datasets = "all_transactions",
    google_cloud_allowed_log_buckets = "null",
    google_cloud_allowed_instances = "null",
    
    # GCP project & service account used by this task
    gcp_project_id = "mcp-bench0606",
    gcp_service_account_path = "configs/mcp-bench0606-2b68b5487343.json",
)
