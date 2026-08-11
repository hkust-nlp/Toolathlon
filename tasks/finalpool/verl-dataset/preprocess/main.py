"""Preflight: this task has no provisioning step, but requires a valid
Hugging Face token (the remote huggingface MCP server authenticates with
it, and check_installation.py deliberately skips that server) and at least
one DeepScaleR dataset on the Hub, which the task premise assumes. Verify
at prepare time so a bad token or vanished dataset fails prepare instead of
wasting an agent run."""

from argparse import ArgumentParser

from configs.token_key_session import all_token_key_session
from utils.general.preflight import (
    check_hf_dataset_search,
    check_hf_token,
    run_preflight,
)

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    parser.parse_args()

    run_preflight([
        (
            "Hugging Face token",
            lambda: check_hf_token(all_token_key_session.huggingface_token),
        ),
        (
            "DeepScaleR datasets on the Hub",
            lambda: check_hf_dataset_search("DeepScaleR"),
        ),
    ])
