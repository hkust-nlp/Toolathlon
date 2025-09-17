from addict import Dict
import os
import json

all_token_key_session = Dict(
    google_cloud_allowed_buckets = "mcp-fraud-investigation-archive",
    google_cloud_allowed_bigquery_datasets = "transactions_analytics",
    google_cloud_allowed_log_buckets = "Trading_Logging",
    google_cloud_allowed_instances = "null",
)