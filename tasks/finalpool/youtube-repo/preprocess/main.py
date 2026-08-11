"""Preflight: this task has no provisioning step, but requires a working
YouTube Data API key, the specific third-party playlist the task reads, and
a valid GitHub token for repo lookups. Verify at prepare time so a revoked
key, exhausted quota, or removed playlist fails prepare instead of wasting
an agent run."""

from argparse import ArgumentParser

from configs.token_key_session import all_token_key_session
from utils.general.preflight import (
    check_github_token,
    check_youtube_api_key,
    check_youtube_playlist,
    run_preflight,
)

TASK_PLAYLIST_ID = "PLyzTA8cetPdHtlGw1X8Kt7Ea4bd27ApR7"

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    parser.parse_args()

    api_key = all_token_key_session.google_cloud_console_api_key
    run_preflight([
        ("YouTube Data API key", lambda: check_youtube_api_key(api_key)),
        (
            f"YouTube playlist {TASK_PLAYLIST_ID}",
            lambda: check_youtube_playlist(api_key, TASK_PLAYLIST_ID),
        ),
        (
            "GitHub token",
            lambda: check_github_token(all_token_key_session.github_token),
        ),
    ])
