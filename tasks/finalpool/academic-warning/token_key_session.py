from addict import Dict
import os
import json

all_token_key_session = Dict(
    # default set to null to disable the agent from access anything
    # reset in task specific dir for the names your task needs
    google_cloud_allowed_buckets = "null",
    google_cloud_allowed_bigquery_datasets = "academic_warning",
    google_cloud_allowed_log_buckets = "exam_log",
    google_cloud_allowed_instances = "null",

)