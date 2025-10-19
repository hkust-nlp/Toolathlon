from addict import Dict
import os
import json

allowed_bucket_name_path = os.path.join(os.path.dirname(__file__), "groundtruth_workspace", "bucket_name.txt")
allowed_log_bucket_name_path = os.path.join(os.path.dirname(__file__), "groundtruth_workspace", "log_bucket_name.txt")

with open(allowed_bucket_name_path, "r") as f:
    allowed_bucket_name = f.read().strip()
with open(allowed_log_bucket_name_path, "r") as f:
    allowed_log_bucket_name = f.read().strip()

all_token_key_session = Dict(
    google_cloud_allowed_buckets = allowed_bucket_name,
    google_cloud_allowed_bigquery_datasets = "transactions_analytics",
    google_cloud_allowed_log_buckets = allowed_log_bucket_name,
    google_cloud_allowed_instances = "null",
)