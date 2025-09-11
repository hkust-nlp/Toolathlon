from addict import Dict
import os

file_path = os.path.abspath(__file__)
emails_config_file = os.path.join(os.path.dirname(file_path), "email_config.json")

# Task-specific token overrides for debug task
all_token_key_session = Dict(
    # Override snowflake work directory for debug task
    snowflake_op_allowed_databases = "PURCHASE_INVOICE",
    emails_config_file = emails_config_file,
)