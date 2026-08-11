"""Preflight: this task has no provisioning step, but requires a working
YouTube Data API key (quota-limited) and the MrBeast channel the task
analyzes. Verify at prepare time so a revoked key or exhausted quota fails
prepare instead of wasting an agent run."""

from argparse import ArgumentParser

from configs.token_key_session import all_token_key_session
from utils.general.preflight import (
    check_youtube_api_key,
    check_youtube_channel,
    run_preflight,
)

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    parser.parse_args()

    api_key = all_token_key_session.google_cloud_console_api_key
    run_preflight([
        ("YouTube Data API key", lambda: check_youtube_api_key(api_key)),
        ("YouTube channel @MrBeast", lambda: check_youtube_channel(api_key, "@MrBeast")),
    ])
