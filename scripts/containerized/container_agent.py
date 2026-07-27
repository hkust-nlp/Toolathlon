"""Run only the agent phase against an already prepared task workspace."""

import argparse
import asyncio
import json
import os
from typing import Any, Dict

from scripts.decoupled.container_preprocess import TASK_BUNDLE_SCHEMA_VERSION
from utils.data_structures.task_config import TaskConfig
from utils.general.helper import setup_proxy
from utils.roles.task_agent import TaskStatus
from utils.task_runner.runner import TaskRunner

# Keep the one-shot main.py runtime patches active in the phased entry point.
from utils.openai_agents_monkey_patch.custom_run_impl import *  # noqa: F401,F403,E402
from utils.openai_agents_monkey_patch.custom_mcp_util import *  # noqa: F401,F403,E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the agent in a workspace prepared by container_preprocess"
    )
    parser.add_argument("--bundle_file", default="/workspace/dumps/task_bundle.json")
    parser.add_argument("--with_proxy", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--allow_resume", action="store_true")
    parser.add_argument("--manual", action="store_true")
    return parser.parse_args()


def consume_task_bundle(bundle_file: str) -> Dict[str, Any]:
    """Read and remove a trusted phase bundle before any agent/tool execution."""
    bundle_path = os.path.abspath(bundle_file)
    bundle: Dict[str, Any]
    try:
        with open(bundle_path, "r", encoding="utf-8") as f:
            bundle = json.load(f)
    finally:
        # Bundle contents include evaluator paths and task-specific token material.
        # Refuse to launch the agent if the file cannot be made inaccessible.
        if os.path.exists(bundle_path):
            os.unlink(bundle_path)

    if not isinstance(bundle, dict):
        raise TypeError("task bundle must contain a JSON object")
    if bundle.get("schema_version") != TASK_BUNDLE_SCHEMA_VERSION:
        raise ValueError(
            "unsupported task bundle schema_version: "
            f"{bundle.get('schema_version')!r}; expected {TASK_BUNDLE_SCHEMA_VERSION}"
        )
    if not isinstance(bundle.get("resolved_task_config"), dict):
        raise ValueError("task bundle is missing resolved_task_config")
    if not isinstance(bundle.get("eval_config"), dict):
        raise ValueError("task bundle is missing eval_config")
    return bundle


async def run_agent_phase(
    bundle: Dict[str, Any],
    *,
    debug: bool = False,
    allow_resume: bool = False,
    manual: bool = False,
) -> TaskStatus:
    """Hydrate trusted phase state and run the common agent lifecycle only."""
    task_config = TaskConfig.from_resolved_dict(bundle["resolved_task_config"])
    mcp_config, agent_config, user_config = TaskRunner.load_configs(
        bundle["eval_config"]
    )

    return await TaskRunner.run_single_task(
        task_config=task_config,
        agent_config=agent_config,
        user_config=user_config,
        mcp_config=mcp_config,
        debug=debug,
        allow_resume=allow_resume,
        manual=manual,
        single_turn_mode=task_config.single_turn_mode,
        workspace_prepared=True,
    )


def main() -> None:
    args = parse_args()
    setup_proxy(args.with_proxy)

    # consume_task_bundle unlinks the file before TaskRunner can initialize MCP
    # servers, local tools, or the model-backed agent.
    bundle = consume_task_bundle(args.bundle_file)
    task_status = asyncio.run(
        run_agent_phase(
            bundle,
            debug=args.debug,
            allow_resume=args.allow_resume,
            manual=args.manual,
        )
    )

    print(f"Agent phase finished with status: {task_status.value}")
    raise SystemExit(0 if task_status == TaskStatus.SUCCESS else 1)


if __name__ == "__main__":
    main()
