import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any


TASK_BUNDLE_SCHEMA_VERSION = 2


def read_json_file(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json_file(path: str, data: dict) -> None:
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    with open(path_obj, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare task workspace in container only")
    parser.add_argument("--eval_config", required=True)
    parser.add_argument("--task_dir", required=True)
    parser.add_argument("--model_short_name", default=None)
    parser.add_argument("--provider", default="unified")
    parser.add_argument("--max_steps_under_single_turn_mode", type=int, default=None)
    parser.add_argument("--with_proxy", action="store_true")
    parser.add_argument("--multi_turn_mode", action="store_true")
    parser.add_argument("--cn_mode", action="store_true")
    parser.add_argument("--bundle_file", default="/workspace/dumps/task_bundle.json")
    parser.add_argument("--host_output_folder", default="")
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


def build_eval_config_dict(args: argparse.Namespace) -> dict:
    eval_config_dict = read_json_file(args.eval_config)
    if args.model_short_name is not None:
        eval_config_dict["agent"]["model"]["short_name"] = args.model_short_name
        eval_config_dict["agent"]["model"]["provider"] = args.provider
    if args.max_steps_under_single_turn_mode is not None:
        eval_config_dict["global_task_config"][
            "max_steps_under_single_turn_mode"
        ] = args.max_steps_under_single_turn_mode
    return eval_config_dict


def build_task_bundle(
    task_config: Any,
    eval_config_dict: dict,
    host_output_folder: str,
    bundle_file: str,
) -> dict:
    container_task_root = os.path.abspath(task_config.task_root)
    container_workspace = os.path.abspath(task_config.agent_workspace)
    container_log_file = os.path.abspath(task_config.log_file)

    if host_output_folder:
        host_task_root = os.path.abspath(host_output_folder)
    else:
        host_task_root = container_task_root

    host_workspace = os.path.abspath(os.path.join(host_task_root, "workspace"))
    host_log_file = os.path.abspath(os.path.join(host_task_root, "traj_log.json"))

    bundle = {
        "schema_version": TASK_BUNDLE_SCHEMA_VERSION,
        "task_dir": task_config.task_dir,
        "launch_time": task_config.launch_time,
        "single_turn_mode": task_config.single_turn_mode,
        "cn_mode": task_config.cn_mode,
        "task_str": task_config.task_str,
        "system_prompts": {
            "agent": task_config.system_prompts.agent,
            "user": task_config.system_prompts.user,
        },
        "needed_mcp_servers": task_config.needed_mcp_servers,
        "needed_local_tools": task_config.needed_local_tools,
        "stop": {
            "user_phrases": task_config.stop.user_phrases,
            "tool_names": task_config.stop.tool_names,
        },
        "max_turns": task_config.max_turns,
        "max_steps_under_single_turn_mode": task_config.max_steps_under_single_turn_mode,
        "container_paths": {
            "task_root": container_task_root,
            "agent_workspace": container_workspace,
            "log_file": container_log_file,
        },
        "host_paths": {
            "task_root": host_task_root,
            "agent_workspace": host_workspace,
            "log_file": host_log_file,
        },
        "eval_config": eval_config_dict,
        "local_token_key_session": task_config.local_token_key_session,
        "resolved_task_config": task_config.to_resolved_dict(),
        "bundle_file": os.path.abspath(bundle_file),
    }
    return bundle


async def main() -> int:
    from utils.data_structures.task_config import TaskConfig
    from utils.general.helper import (
        build_agent_model_provider,
        build_user_client,
        setup_proxy,
    )
    from utils.roles.task_agent import TaskAgent
    from utils.task_runner.runner import TaskRunner

    args = parse_args()

    setup_proxy(args.with_proxy)
    eval_config_dict = build_eval_config_dict(args)

    mcp_config, agent_config, user_config = TaskRunner.load_configs(eval_config_dict)

    task_config = TaskConfig.build(
        args.task_dir,
        agent_config.model.short_name,
        eval_config_dict["global_task_config"],
        single_turn_mode=not args.multi_turn_mode,
        cn_mode=args.cn_mode,
    )

    # Align with TaskAgent.run() output location convention.
    task_config.log_file = os.path.join(task_config.task_root, "traj_log.json")
    task_config.agent_workspace = os.path.join(task_config.task_root, "workspace")

    agent_model_provider = build_agent_model_provider(agent_config)
    user_client = build_user_client(user_config)

    task_agent = TaskAgent(
        task_config=task_config,
        agent_config=agent_config,
        agent_model_provider=agent_model_provider,
        user_config=user_config,
        user_client=user_client,
        mcp_config=mcp_config,
        debug=args.debug,
        allow_resume=False,
        manual=False,
        single_turn_mode=not args.multi_turn_mode,
    )

    task_agent.status_manager.update_preprocess("running")
    ok = await task_agent.initialize_workspace(show_traceback=True)
    if not ok:
        task_agent.status_manager.update_preprocess("fail")
        return 1
    task_agent.status_manager.update_preprocess("done")
    task_config.load_local_token_key_session()

    bundle = build_task_bundle(
        task_config=task_config,
        eval_config_dict=eval_config_dict,
        host_output_folder=args.host_output_folder,
        bundle_file=args.bundle_file,
    )

    bundle_path = Path(args.bundle_file)
    write_json_file(str(bundle_path), bundle)
    print(f"Preprocess done. Bundle written to: {bundle_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
