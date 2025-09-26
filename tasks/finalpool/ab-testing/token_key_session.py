from addict import Dict
import os
import json

all_token_key_session = Dict(
    # default set to null to disable the agent from access anything
    # reset in task specific dir for the names your task needs
    google_cloud_allowed_buckets = "promo-assets-for-b",
    google_cloud_allowed_bigquery_datasets = "ab_testing",
    google_cloud_allowed_log_buckets = "abtesting_logging",
    google_cloud_allowed_instances = "null",
)