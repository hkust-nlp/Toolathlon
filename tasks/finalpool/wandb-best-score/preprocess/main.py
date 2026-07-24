"""Preflight: this task has no provisioning step, but requires a valid
wandb API key and the third-party public project mluo/deepscaler-1.5b with
the run the evaluation hardcodes. Verify at prepare time so a revoked key
or vanished upstream run fails prepare instead of wasting an agent run."""

from argparse import ArgumentParser

from configs.token_key_session import all_token_key_session
from utils.general.preflight import check_wandb_project, run_preflight

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    parser.parse_args()

    run_preflight([
        (
            "wandb project mluo/deepscaler-1.5b with run deepscaler-1.5b-24k",
            lambda: check_wandb_project(
                all_token_key_session.wandb_api_key,
                "mluo/deepscaler-1.5b",
                expected_run_names=["deepscaler-1.5b-24k"],
            ),
        ),
    ])
