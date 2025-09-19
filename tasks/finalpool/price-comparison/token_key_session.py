from addict import Dict
import os
# this is the local token key session for local testing
# will override the token key session in the global ones in configs/token_key_session.py
all_token_key_session = Dict(
    google_cloud_allowed_buckets = "null",
    google_cloud_allowed_bigquery_datasets = "bigquery_pricing_analysis",
    google_cloud_allowed_log_buckets = "null",
    google_cloud_allowed_instances = "null",

)