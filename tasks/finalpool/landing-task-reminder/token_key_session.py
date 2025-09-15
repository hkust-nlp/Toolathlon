from addict import Dict

# Task-specific token overrides for debug task
all_token_key_session = Dict(
    # Override snowflake work directory for debug task
    snowflake_op_allowed_databases = "LANDING_TASK_REMINDER",
    emails_config_file = "tasks/fan/landing-task-reminder/email_config.json",
)