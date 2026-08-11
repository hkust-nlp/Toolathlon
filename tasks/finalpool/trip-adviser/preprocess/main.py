"""Preflight: this task has no provisioning step; it depends on a working
Google Maps API key (Places/Directions). Verify at prepare time so a dead
key fails prepare instead of wasting an agent run."""

from argparse import ArgumentParser

from configs.token_key_session import all_token_key_session
from utils.general.preflight import check_google_maps_key, run_preflight

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    parser.parse_args()

    run_preflight([
        (
            "Google Maps API key",
            lambda: check_google_maps_key(all_token_key_session.google_cloud_console_api_key),
        ),
    ])
