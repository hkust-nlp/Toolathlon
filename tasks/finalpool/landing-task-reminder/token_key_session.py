from addict import Dict
import os

emails_config_file = os.path.join(os.path.dirname(__file__), "emails_config.json")

# Task-specific token overrides for debug task
all_token_key_session = Dict(
    # Override snowflake work directory for debug task
    snowflake_op_allowed_databases = "LANDING_TASK_REMINDER",
    emails_config_file = emails_config_file,
)