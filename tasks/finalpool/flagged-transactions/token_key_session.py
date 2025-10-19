from addict import Dict
import os
# I am gradually modifying the tokens to the pseudo account in this project
all_token_key_session = Dict(
    # default set to null to disable the agent from access anything
    # reset in task specific dir for the names your task needs
    google_cloud_allowed_buckets = "null",
    google_cloud_allowed_bigquery_datasets = "all_transactions",
    google_cloud_allowed_log_buckets = "null",
    google_cloud_allowed_instances = "null",
)
