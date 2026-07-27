import argparse
import asyncio
import copy
import json
import os
from typing import Any, Dict, Optional, Union

from utils.evaluation.evaluator import (
    TRUSTED_RESOLVED_CONFIG_MARKER,
    TaskEvaluator,
)
from utils.status_manager import TaskStatusManager


def read_json_file(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_task_bundle(path: str, *, consume: bool = False) -> Dict[str, Any]:
    """Read a phase bundle and optionally make it inaccessible immediately."""

    try:
        return read_json_file(path)
    finally:
        if consume and os.path.lexists(path):
            os.unlink(path)


def write_json_file(path: str, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def evaluation_status_from_pass_value(
    pass_value: Optional[bool], *, boolean_status: bool = False
) -> Union[bool, str, None]:
    if boolean_status:
        return pass_value if isinstance(pass_value, bool) else None
    if pass_value is True:
        return "pass"
    if pass_value is False:
        return "fail"
    return None


def remap_dump_line_paths_to_container(
    dump_line: Dict[str, Any], bundle: Dict[str, Any]
) -> Dict[str, Any]:
    container_paths = bundle["container_paths"]
    config = dump_line.get("config")
    if not isinstance(config, dict):
        return dump_line

    config = dict(config)
    config["task_root"] = container_paths["task_root"]
    config["agent_workspace"] = container_paths["agent_workspace"]
    config["log_file"] = container_paths["log_file"]

    updated = dict(dump_line)
    updated["config"] = config
    return updated


def config_for_evaluation(
    dump_line: Dict[str, Any],
    bundle: Dict[str, Any],
    *,
    require_resolved_task_config: bool = False,
) -> Dict[str, Any]:
    """Return an evaluation input whose config comes from trusted state.

    New phased-containerized runs persist the fully resolved TaskConfig before
    the agent starts.  The trajectory lives in the agent-writable task root,
    so its embedded config must not be trusted for grading.  Older decoupled
    bundles did not contain ``resolved_task_config``; retain their path-remap
    behavior unless the caller explicitly requires the trusted config.
    """

    resolved_config = bundle.get("resolved_task_config")
    if resolved_config is None:
        if require_resolved_task_config:
            raise ValueError("bundle is missing resolved_task_config")
        return remap_dump_line_paths_to_container(dump_line, bundle)
    if not isinstance(resolved_config, dict):
        raise ValueError("bundle resolved_task_config must be an object")

    trusted_config = copy.deepcopy(resolved_config)
    container_paths = bundle.get("container_paths")
    if isinstance(container_paths, dict):
        for key in ("task_root", "agent_workspace", "log_file"):
            if key in container_paths:
                trusted_config[key] = container_paths[key]

    updated = dict(dump_line)
    updated["config"] = trusted_config
    updated["_toolathlon_resolved_config_marker"] = (
        TRUSTED_RESOLVED_CONFIG_MARKER
    )
    return updated


def apply_trusted_agent_exit_code(
    dump_line: Dict[str, Any], agent_exit_code: Optional[int]
) -> Dict[str, Any]:
    """Make pass eligibility agree with the host-observed agent result.

    ``container_agent`` exits zero only for ``TaskStatus.SUCCESS``.  The
    trajectory is agent-writable, so a phased run must not let its serialized
    status promote a failed agent process to success.  Preserve useful
    non-success statuses (for example ``max_turns_reached``), while replacing
    a forged success after a non-zero process exit with ``failed``.
    """

    if agent_exit_code is None:
        return dump_line
    if isinstance(agent_exit_code, bool) or agent_exit_code < 0:
        raise ValueError("agent_exit_code must be a non-negative integer")

    updated = dict(dump_line)
    if agent_exit_code == 0:
        updated["status"] = "success"
    elif updated.get("status") == "success":
        updated["status"] = "failed"
    return updated


def dump_line_for_persistence(dump_line: Dict[str, Any]) -> Dict[str, Any]:
    """Remove the in-memory trust marker before rewriting the trajectory."""

    persisted = dict(dump_line)
    persisted.pop("_toolathlon_resolved_config_marker", None)
    return persisted


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Container-side evaluation for decoupled pipeline")
    parser.add_argument("--bundle_file", default="/workspace/dumps/task_bundle.json")
    parser.add_argument("--allow_resume", action="store_true")
    parser.add_argument(
        "--require_resolved_task_config",
        action="store_true",
        help="Fail rather than trust trajectory config when the bundle is incomplete",
    )
    parser.add_argument(
        "--boolean_evaluation_status",
        action="store_true",
        help="Write status.json evaluation as true/false/null instead of pass/fail/null",
    )
    parser.add_argument(
        "--consume_bundle",
        action="store_true",
        help="Unlink the private phase bundle immediately after reading it",
    )
    parser.add_argument(
        "--agent_exit_code",
        type=int,
        default=None,
        help="Host-observed container_agent exit code used as trusted run status",
    )
    return parser.parse_args()


async def run_eval(
    bundle_file: str,
    allow_resume: bool = False,
    *,
    require_resolved_task_config: bool = False,
    boolean_evaluation_status: bool = False,
    consume_bundle: bool = False,
    agent_exit_code: Optional[int] = None,
) -> Dict[str, Any]:
    bundle = read_task_bundle(bundle_file, consume=consume_bundle)
    log_file = bundle["container_paths"]["log_file"]
    task_root = bundle["container_paths"]["task_root"]
    eval_file_path = os.path.join(os.path.dirname(log_file), "eval_res.json")

    if allow_resume and os.path.exists(eval_file_path):
        eval_res = read_json_file(eval_file_path)
    else:
        dump_line = read_json_file(log_file)
        dump_line = config_for_evaluation(
            dump_line,
            bundle,
            require_resolved_task_config=require_resolved_task_config,
        )
        dump_line = apply_trusted_agent_exit_code(dump_line, agent_exit_code)

        # Some task evaluators reopen --res_log_file themselves.  In the
        # fail-closed phased path, persist the trusted config/status before
        # invoking them so they cannot observe an agent-forged copy on disk.
        if require_resolved_task_config:
            write_json_file(log_file, dump_line_for_persistence(dump_line))

        eval_res = await TaskEvaluator.evaluate_one(dump_line)
        write_json_file(eval_file_path, eval_res)


    status_manager = TaskStatusManager(task_root)
    status_manager.update_evaluation(
        evaluation_status_from_pass_value(
            eval_res.get("pass"), boolean_status=boolean_evaluation_status
        )
    )

    return eval_res


def main() -> None:
    args = parse_args()
    eval_res = asyncio.run(
        run_eval(
            args.bundle_file,
            allow_resume=args.allow_resume,
            require_resolved_task_config=args.require_resolved_task_config,
            boolean_evaluation_status=args.boolean_evaluation_status,
            consume_bundle=args.consume_bundle,
            agent_exit_code=args.agent_exit_code,
        )
    )

    print("Evaluation finished.")
    print(f"Pass: {eval_res.get('pass')}")
    print(f"Details: {eval_res.get('details')}")
    if eval_res.get("failure") is not None:
        print(f"Failure: {eval_res.get('failure')}")

    raise SystemExit(0 if eval_res.get("pass") is True else 1)


if __name__ == "__main__":
    main()
