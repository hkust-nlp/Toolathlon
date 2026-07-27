import argparse
import json
import tempfile
import unittest
from types import SimpleNamespace

from scripts.decoupled.container_preprocess import (
    build_eval_config_dict,
    build_task_bundle,
)


class ContainerPreprocessTests(unittest.TestCase):
    def test_build_eval_config_dict_applies_overrides(self) -> None:
        base_eval_config = {
            "agent": {"model": {"short_name": "old-model", "provider": "old-provider"}},
            "global_task_config": {"max_steps_under_single_turn_mode": 8},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(base_eval_config, f)
            eval_config_path = f.name

        args = argparse.Namespace(
            eval_config=eval_config_path,
            model_short_name="new-model",
            provider="new-provider",
            max_steps_under_single_turn_mode=42,
        )
        result = build_eval_config_dict(args)

        self.assertEqual(result["agent"]["model"]["short_name"], "new-model")
        self.assertEqual(result["agent"]["model"]["provider"], "new-provider")
        self.assertEqual(
            result["global_task_config"]["max_steps_under_single_turn_mode"], 42
        )

    def test_build_task_bundle_uses_host_output_folder(self) -> None:
        task_config = SimpleNamespace(
            task_root="/container/dumps/finalpool/demo-task",
            agent_workspace="/container/dumps/finalpool/demo-task/workspace",
            log_file="/container/dumps/finalpool/demo-task/traj_log.json",
            task_dir="finalpool/demo-task",
            launch_time="2026-02-24-10-00-00",
            single_turn_mode=True,
            cn_mode=False,
            task_str="demo instruction",
            system_prompts=SimpleNamespace(agent="agent prompt", user="user prompt"),
            needed_mcp_servers=["mcp-a"],
            needed_local_tools=["local-claim_done"],
            stop=SimpleNamespace(
                user_phrases=["done"], tool_names=["local-claim_done"]
            ),
            max_turns=15,
            max_steps_under_single_turn_mode=30,
            local_token_key_session={"x": "y"},
            to_resolved_dict=lambda: {
                "task_dir": "finalpool/demo-task",
                "local_token_key_session": {"x": "y"},
            },
        )

        bundle = build_task_bundle(
            task_config=task_config,
            eval_config_dict={"k": "v"},
            host_output_folder="/host/out/demo-task",
            bundle_file="/tmp/task_bundle.json",
        )

        self.assertEqual(bundle["host_paths"]["task_root"], "/host/out/demo-task")
        self.assertEqual(
            bundle["host_paths"]["agent_workspace"], "/host/out/demo-task/workspace"
        )
        self.assertEqual(
            bundle["host_paths"]["log_file"], "/host/out/demo-task/traj_log.json"
        )
        self.assertEqual(
            bundle["container_paths"]["task_root"],
            "/container/dumps/finalpool/demo-task",
        )
        self.assertEqual(bundle["schema_version"], 2)
        self.assertEqual(
            bundle["resolved_task_config"]["local_token_key_session"], {"x": "y"}
        )

    def test_build_task_bundle_falls_back_to_container_paths(self) -> None:
        task_config = SimpleNamespace(
            task_root="/container/dumps/finalpool/demo-task",
            agent_workspace="/container/dumps/finalpool/demo-task/workspace",
            log_file="/container/dumps/finalpool/demo-task/traj_log.json",
            task_dir="finalpool/demo-task",
            launch_time="2026-02-24-10-00-00",
            single_turn_mode=True,
            cn_mode=False,
            task_str="demo instruction",
            system_prompts=SimpleNamespace(agent="agent prompt", user="user prompt"),
            needed_mcp_servers=[],
            needed_local_tools=[],
            stop=SimpleNamespace(user_phrases=[], tool_names=[]),
            max_turns=15,
            max_steps_under_single_turn_mode=30,
            local_token_key_session=None,
            to_resolved_dict=lambda: {
                "task_dir": "finalpool/demo-task",
                "local_token_key_session": None,
            },
        )

        bundle = build_task_bundle(
            task_config=task_config,
            eval_config_dict={},
            host_output_folder="",
            bundle_file="/tmp/task_bundle.json",
        )

        self.assertEqual(
            bundle["host_paths"]["task_root"], "/container/dumps/finalpool/demo-task"
        )
        self.assertEqual(
            bundle["host_paths"]["agent_workspace"],
            "/container/dumps/finalpool/demo-task/workspace",
        )


if __name__ == "__main__":
    unittest.main()
