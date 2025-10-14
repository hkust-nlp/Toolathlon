from addict import Dict
import os
# this is the local token key session for local testing
# will override the token key session in the global ones in configs/token_key_session.py

allowed_bucket_name_path = os.path.join(os.path.dirname(__file__), "groundtruth_workspace", "bucket_name.txt")
with open(allowed_bucket_name_path, "r") as f:
    allowed_bucket_name = f.read().strip()

all_token_key_session = Dict(
    google_cloud_allowed_buckets = allowed_bucket_name,
    google_cloud_allowed_bigquery_datasets = "machine_operating",
    google_cloud_allowed_log_buckets = "null",
    google_cloud_allowed_instances = "null",

)