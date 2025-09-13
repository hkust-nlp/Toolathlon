from addict import Dict
import os

# Task-specific token overrides for debug task
all_token_key_session = Dict(
    # Override snowflake work directory for debug task
    snowflake_op_allowed_databases = "TRAVEL_EXPENSE_REIMBURSEMENT",
    emails_config_file = os.path.join(os.path.dirname(__file__),"email_config.json"),
)