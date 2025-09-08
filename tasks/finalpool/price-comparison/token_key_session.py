from addict import Dict
import os
# this is the local token key session for local testing
# will override the token key session in the global ones in configs/token_key_session.py
all_token_key_session = Dict(
    canvas_api_token = "canvas_token_Lrobinson113", 
    google_cloud_allowed_buckets = "promo-assets-for-b,mcp-fraud-investigation-archive,iot_anomaly_reports",
    google_cloud_allowed_bigquery_datasets = "bigquery_pricing_analysis",
    google_cloud_allowed_log_buckets = "bigquery_pricing_analysis",
    google_cloud_allowed_instances = "null",

)