from addict import Dict
import os
# I am gradually modifying the tokens to the pseudo account in this project
all_token_key_session = Dict(
    # added, use mcp0606 account!
    leetcode_session = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhY2NvdW50X3ZlcmlmaWVkX2VtYWlsIjpudWxsLCJfYXV0aF91c2VyX2lkIjoiMTc5NDI4NjMiLCJfYXV0aF91c2VyX2JhY2tlbmQiOiJhbGxhdXRoLmFjY291bnQuYXV0aF9iYWNrZW5kcy5BdXRoZW50aWNhdGlvbkJhY2tlbmQiLCJfYXV0aF91c2VyX2hhc2giOiI0ZmIzZjdiMmI5YjRhM2FhMGFmZTgxMmQzNjFiOTIyMzk1MTM2M2MzYjJjZGZjZTNhYzllMGQ0YjgzNWI2MGQ1Iiwic2Vzc2lvbl91dWlkIjoiNjhmODg3ZGQiLCJpZCI6MTc5NDI4NjMsImVtYWlsIjoibWNwdGVzdDA2MDZAZ21haWwuY29tIiwidXNlcm5hbWUiOiJ6eE51aGlEeXJoIiwidXNlcl9zbHVnIjoienhOdWhpRHlyaCIsImF2YXRhciI6Imh0dHBzOi8vYXNzZXRzLmxlZXRjb2RlLmNvbS91c2Vycy9kZWZhdWx0X2F2YXRhci5qcGciLCJyZWZyZXNoZWRfYXQiOjE3NDk0MzY4MDEsImlwIjoiMTkyLjIxMC4yMDYuMjMxIiwiaWRlbnRpdHkiOiIwZmU2ZmViNTQyODlmNGM2NzAyN2VjMDZjYzIxMzFmOCIsImRldmljZV93aXRoX2lwIjpbImI0OTQ1MGIwYTMwMzVjMDM4ZTBmYTc3MDY4NzQ4NjBhIiwiMTkyLjIxMC4yMDYuMjMxIl19.ifUux-wVKksegSMEvjY2TvLXxIOyshAEO9CE7rV790g",
    github_token = "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",
    
    google_cloud_console_api_key = "AIzaSyD8Q5ZPqCDZIgjOwBc9QtbdFLfGkijBmMU",
    
    google_search_engine_id = "d08f1d4bbe2294372",
    
    huggingface_token = "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",
    
    linkedin_email = "mcptest0606@gmail.com",
    linkedin_password = "MCPtest0606!!",

    # use local deployed ones, or set up your own token to control
    canvas_api_token = "PLEASE_RESET_IN_TASK_SPECIFIC_DIR",
    canvas_domain = "localhost:20001",

    wandb_api_key = "b3abe195bd69c07bdc47469d3956ac8d0c008714",
    
    tessdata_prefix = os.environ["TESSDATA_PREFIX"],
    amap_key="f789815a157fe45439c674c4a10e615b",
    
    google_sheets_folder_id = "1Zy_Hczc1kY6HoaMXW52lJbl9w8ffn31R",
    google_oauth2_credentials_path = "configs/credentials.json",
    google_oauth2_token_path = "configs/credentials.json", # I just put them all together in the same file

    notion_integration_key="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",

    woocommerce_api_key = "PLEASE_RESET_IN_TASK_SPECIFIC_DIR",
    woocommerce_api_secret = "PLEASE_RESET_IN_TASK_SPECIFIC_DIR",
    woocommerce_site_url = "PLEASE_RESET_IN_TASK_SPECIFIC_DIR",

    kubeconfig_path = "PLEASE_RESET_IN_TASK_SPECIFIC_DIR",

    gcp_project_id = "mcp-bench0606",
    gcp_service_account_path = "configs/mcp-bench0606-2b68b5487343.json",

    # default set to null to disable the agent from access anything
    # reset in task specific dir for the names your task needs
    google_cloud_allowed_buckets = "null",
    google_cloud_allowed_bigquery_datasets = "null",
    google_cloud_allowed_log_buckets = "null",
    google_cloud_allowed_instances = "null",

    # poste emails
    emails_config_file = "PLEASE_RESET_IN_TASK_SPECIFIC_DIR",

    # snowflake

    snowflake_account = "VBJIVCN-OI09931",
    snowflake_warehouse = "COMPUTE_WH",
    snowflake_role = "ACCOUNTADMIN",
    snowflake_user = "MCPTEST0606",
    snowflake_password = "MCPtest0606!!!",
    snowflake_database = "SNOWFLAKE",
    snowflake_schema = "PUBLIC",
    snowflake_op_allowed_databases = "PLEASE_RESET_IN_TASK_SPECIFIC_DIR",
)