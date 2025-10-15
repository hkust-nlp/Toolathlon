from addict import Dict
import os
import json

allowed_log_bucket_name_path = os.path.join(os.path.dirname(__file__), "groundtruth_workspace", "log_bucket_name.txt")

with open(allowed_log_bucket_name_path, "r") as f:
    allowed_log_bucket_name = f.read().strip()

all_token_key_session = Dict(
    # default set to null to disable the agent from access anything
    # reset in task specific dir for the names your task needs
    google_cloud_allowed_buckets = "promo-assets-for-b*",
    google_cloud_allowed_bigquery_datasets = "ab_testing",
    google_cloud_allowed_log_buckets = allowed_log_bucket_name,
    google_cloud_allowed_instances = "null",
)