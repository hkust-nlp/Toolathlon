import unittest
from unittest.mock import patch

from utils.data_structures.task_config import SystemPrompts, TaskConfig


def resolved_config():
    return {
        "task_dir": "finalpool/demo-task",
        "id": "finalpool-demo-task",
        "needed_mcp_servers": ["demo-mcp"],
        "needed_local_tools": ["python_execute"],
        "task_root": "/trusted/out/SingleUserTurn-demo-task",
        "task_str": "already loaded task",
        "log_file": "/trusted/out/SingleUserTurn-demo-task/traj_log.json",
        "agent_workspace": "/trusted/out/SingleUserTurn-demo-task/workspace",
        "max_turns": 12,
        "max_steps_under_single_turn_mode": 34,
        "single_turn_mode": True,
        "cn_mode": False,
        "meta": {"kind": "demo"},
        "launch_time": "2026-06-28 09:00:00 Sunday",
        "agent_short_name": "demo/model",
        "global_task_config": {"dump_path": "/trusted/out"},
        "local_token_key_session": {"token": "secret"},
        "system_prompts": {
            "agent": "rendered /trusted/out/SingleUserTurn-demo-task/workspace",
            "user": "rendered task prompt",
        },
        "initialization": {
            "workspace": "tasks/finalpool/demo-task/initial_workspace",
            "process_command": "uv run -m hidden.preprocess.main",
        },
        "evaluation": {
            "groundtruth_workspace": "tasks/finalpool/demo-task/groundtruth_workspace",
            "evaluation_command": "uv run -m hidden.evaluation.main",
        },
        "stop": {
            "user_phrases": ["STOP"],
            "tool_names": ["local-claim_done"],
        },
    }


class ResolvedTaskConfigTests(unittest.TestCase):
    def test_hydrate_does_not_reapply_derived_state(self) -> None:
        source = resolved_config()

        with patch.object(
            SystemPrompts,
            "apply",
            side_effect=AssertionError("prompt transformation must not run"),
        ):
            task_config = TaskConfig.from_resolved_dict(source)

        self.assertEqual(task_config.task_root, source["task_root"])
        self.assertEqual(task_config.agent_workspace, source["agent_workspace"])
        self.assertEqual(task_config.system_prompts.agent, source["system_prompts"]["agent"])
        self.assertEqual(
            task_config.evaluation.evaluation_command,
            "uv run -m hidden.evaluation.main",
        )
        self.assertEqual(task_config.local_token_key_session, {"token": "secret"})

    def test_round_trip_is_complete_and_independent(self) -> None:
        task_config = TaskConfig.from_resolved_dict(resolved_config())

        snapshot = task_config.to_resolved_dict()
        snapshot["local_token_key_session"]["token"] = "changed"
        snapshot["system_prompts"]["agent"] = "changed"

        self.assertEqual(task_config.local_token_key_session["token"], "secret")
        self.assertNotEqual(task_config.system_prompts.agent, "changed")
        self.assertEqual(
            TaskConfig.from_resolved_dict(task_config.to_resolved_dict()).to_resolved_dict(),
            task_config.to_resolved_dict(),
        )

    def test_rejects_incomplete_snapshot(self) -> None:
        source = resolved_config()
        del source["evaluation"]

        with self.assertRaisesRegex(ValueError, "evaluation"):
            TaskConfig.from_resolved_dict(source)


if __name__ == "__main__":
    unittest.main()
