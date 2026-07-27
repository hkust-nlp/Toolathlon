import json
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from scripts.decoupled.container_eval import (
    apply_trusted_agent_exit_code,
    config_for_evaluation,
    dump_line_for_persistence,
    evaluation_status_from_pass_value,
    read_task_bundle,
    remap_dump_line_paths_to_container,
    run_eval,
)
from utils.evaluation.evaluator import (
    TRUSTED_RESOLVED_CONFIG_MARKER,
    TaskEvaluator,
)


class ContainerEvalTests(unittest.TestCase):
    def test_private_bundle_can_be_consumed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_path = os.path.join(temp_dir, "bundle.json")
            with open(bundle_path, "w", encoding="utf-8") as bundle_file:
                json.dump({"schema_version": 2}, bundle_file)

            self.assertEqual(
                read_task_bundle(bundle_path, consume=True), {"schema_version": 2}
            )
            self.assertFalse(os.path.lexists(bundle_path))

    def test_evaluation_status_mapping(self) -> None:
        self.assertEqual(evaluation_status_from_pass_value(True), "pass")
        self.assertEqual(evaluation_status_from_pass_value(False), "fail")
        self.assertIsNone(evaluation_status_from_pass_value(None))

    def test_boolean_evaluation_status_mapping(self) -> None:
        self.assertIs(
            evaluation_status_from_pass_value(True, boolean_status=True), True
        )
        self.assertIs(
            evaluation_status_from_pass_value(False, boolean_status=True), False
        )
        self.assertIsNone(
            evaluation_status_from_pass_value(None, boolean_status=True)
        )

    def test_remap_dump_line_paths_to_container(self) -> None:
        bundle = {
            "container_paths": {
                "task_root": "/workspace/dumps/task",
                "agent_workspace": "/workspace/dumps/task/workspace",
                "log_file": "/workspace/dumps/task/traj_log.json",
            }
        }
        dump_line = {
            "config": {
                "task_root": "/root/host/task",
                "agent_workspace": "/root/host/task/workspace",
                "log_file": "/root/host/task/traj_log.json",
            }
        }
        mapped = remap_dump_line_paths_to_container(dump_line, bundle)
        self.assertEqual(mapped["config"]["task_root"], "/workspace/dumps/task")
        self.assertEqual(
            mapped["config"]["agent_workspace"], "/workspace/dumps/task/workspace"
        )
        self.assertEqual(
            mapped["config"]["log_file"], "/workspace/dumps/task/traj_log.json"
        )

    def test_trusted_resolved_config_replaces_trajectory_config(self) -> None:
        bundle = {
            "resolved_task_config": {
                "task_dir": "finalpool/example",
                "task_root": "/untrusted/original/path",
                "agent_workspace": "/untrusted/original/path/workspace",
                "log_file": "/untrusted/original/path/traj_log.json",
                "evaluation": {"evaluation_command": "trusted grader"},
            },
            "container_paths": {
                "task_root": "/workspace/dumps",
                "agent_workspace": "/workspace/dumps/workspace",
                "log_file": "/workspace/dumps/traj_log.json",
            },
        }
        dump_line = {
            "status": "success",
            "config": {
                "evaluation": {"evaluation_command": "agent supplied grader"}
            },
        }

        mapped = config_for_evaluation(
            dump_line, bundle, require_resolved_task_config=True
        )

        self.assertEqual(
            mapped["config"]["evaluation"]["evaluation_command"], "trusted grader"
        )
        self.assertEqual(mapped["config"]["task_root"], "/workspace/dumps")
        self.assertEqual(
            mapped["config"]["agent_workspace"], "/workspace/dumps/workspace"
        )
        self.assertEqual(
            mapped["config"]["log_file"], "/workspace/dumps/traj_log.json"
        )
        self.assertEqual(
            bundle["resolved_task_config"]["task_root"], "/untrusted/original/path"
        )
        self.assertIs(
            mapped["_toolathlon_resolved_config_marker"],
            TRUSTED_RESOLVED_CONFIG_MARKER,
        )

    def test_required_resolved_config_is_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing resolved_task_config"):
            config_for_evaluation(
                {"config": {}},
                {"container_paths": {}},
                require_resolved_task_config=True,
            )

    def test_agent_exit_code_controls_pass_eligibility(self) -> None:
        self.assertEqual(
            apply_trusted_agent_exit_code({"status": "failed"}, 0)["status"],
            "success",
        )
        self.assertEqual(
            apply_trusted_agent_exit_code({"status": "success"}, 7)["status"],
            "failed",
        )
        self.assertEqual(
            apply_trusted_agent_exit_code(
                {"status": "max_turns_reached"}, 7
            )["status"],
            "max_turns_reached",
        )

    def test_persisted_dump_line_drops_in_memory_marker(self) -> None:
        persisted = dump_line_for_persistence(
            {
                "status": "success",
                "_toolathlon_resolved_config_marker": (
                    TRUSTED_RESOLVED_CONFIG_MARKER
                ),
            }
        )
        self.assertNotIn("_toolathlon_resolved_config_marker", persisted)


class RunEvalTests(unittest.IsolatedAsyncioTestCase):
    @patch("scripts.decoupled.container_eval.TaskStatusManager")
    @patch("scripts.decoupled.container_eval.write_json_file")
    @patch("scripts.decoupled.container_eval.TaskEvaluator.evaluate_one", new_callable=AsyncMock)
    @patch("scripts.decoupled.container_eval.os.path.exists")
    @patch("scripts.decoupled.container_eval.read_json_file")
    async def test_run_eval_updates_status_manager(
        self,
        mock_read_json: MagicMock,
        mock_exists: MagicMock,
        mock_evaluate_one: AsyncMock,
        mock_write_json: MagicMock,
        mock_status_manager_cls: MagicMock,
    ) -> None:
        mock_exists.return_value = False
        mock_read_json.side_effect = [
            {
                "container_paths": {
                    "log_file": "/workspace/dumps/traj_log.json",
                    "task_root": "/workspace/dumps",
                    "agent_workspace": "/workspace/dumps/workspace",
                }
            },
            {
                "config": {
                    "task_root": "/root/host",
                    "agent_workspace": "/root/host/workspace",
                    "log_file": "/root/host/traj_log.json",
                }
            },
        ]
        mock_evaluate_one.return_value = {"pass": False, "details": "not pass"}
        mock_status_manager = MagicMock()
        mock_status_manager_cls.return_value = mock_status_manager

        result = await run_eval("/workspace/dumps/task_bundle.json", allow_resume=True)

        self.assertEqual(mock_read_json.call_count, 2)
        called_dump_line = mock_evaluate_one.await_args.args[0]
        self.assertEqual(called_dump_line["config"]["task_root"], "/workspace/dumps")
        self.assertEqual(
            called_dump_line["config"]["agent_workspace"], "/workspace/dumps/workspace"
        )
        mock_write_json.assert_called_once()
        mock_status_manager_cls.assert_called_once_with("/workspace/dumps")
        mock_status_manager.update_evaluation.assert_called_once_with("fail")
        self.assertEqual(result["pass"], False)

    @patch("scripts.decoupled.container_eval.TaskStatusManager")
    @patch("scripts.decoupled.container_eval.write_json_file")
    @patch("scripts.decoupled.container_eval.TaskEvaluator.evaluate_one", new_callable=AsyncMock)
    @patch("scripts.decoupled.container_eval.os.path.exists")
    @patch("scripts.decoupled.container_eval.read_json_file")
    async def test_run_eval_can_write_boolean_status(
        self,
        mock_read_json: MagicMock,
        mock_exists: MagicMock,
        mock_evaluate_one: AsyncMock,
        mock_write_json: MagicMock,
        mock_status_manager_cls: MagicMock,
    ) -> None:
        mock_exists.return_value = False
        mock_read_json.side_effect = [
            {
                "container_paths": {
                    "log_file": "/workspace/dumps/traj_log.json",
                    "task_root": "/workspace/dumps",
                    "agent_workspace": "/workspace/dumps/workspace",
                },
                "resolved_task_config": {"task_dir": "finalpool/example"},
            },
            {"status": "success", "config": {"agent_controlled": True}},
        ]
        mock_evaluate_one.return_value = {"pass": False}
        mock_status_manager = MagicMock()
        mock_status_manager_cls.return_value = mock_status_manager

        await run_eval(
            "/run/trusted-bundle.json",
            require_resolved_task_config=True,
            boolean_evaluation_status=True,
            agent_exit_code=9,
        )

        called_dump_line = mock_evaluate_one.await_args.args[0]
        self.assertNotIn("agent_controlled", called_dump_line["config"])
        self.assertEqual(called_dump_line["status"], "failed")
        self.assertEqual(mock_write_json.call_count, 2)
        persisted_path, persisted_dump_line = mock_write_json.call_args_list[0].args
        self.assertEqual(persisted_path, "/workspace/dumps/traj_log.json")
        self.assertEqual(persisted_dump_line["status"], "failed")
        self.assertNotIn(
            "_toolathlon_resolved_config_marker", persisted_dump_line
        )
        mock_status_manager.update_evaluation.assert_called_once_with(False)


class TaskEvaluatorResolvedConfigTests(unittest.IsolatedAsyncioTestCase):
    @patch("utils.evaluation.evaluator.TaskConfig.from_dict")
    @patch("utils.evaluation.evaluator.TaskConfig.from_resolved_dict")
    async def test_identity_marker_uses_resolved_config_loader(
        self,
        mock_from_resolved_dict: MagicMock,
        mock_from_dict: MagicMock,
    ) -> None:
        mock_from_resolved_dict.return_value = MagicMock()
        result = await TaskEvaluator.evaluate_one(
            {
                "config": {"task_root": "/workspace/dumps"},
                "status": "failed",
                "_toolathlon_resolved_config_marker": (
                    TRUSTED_RESOLVED_CONFIG_MARKER
                ),
            }
        )

        mock_from_resolved_dict.assert_called_once_with(
            {"task_root": "/workspace/dumps"}
        )
        mock_from_dict.assert_not_called()
        self.assertIsNone(result["pass"])

    @patch("utils.evaluation.evaluator.TaskConfig.from_dict")
    @patch("utils.evaluation.evaluator.TaskConfig.from_resolved_dict")
    async def test_json_value_cannot_forge_identity_marker(
        self,
        mock_from_resolved_dict: MagicMock,
        mock_from_dict: MagicMock,
    ) -> None:
        mock_from_dict.return_value = MagicMock()
        await TaskEvaluator.evaluate_one(
            {
                "config": {"task_root": "/workspace/dumps"},
                "status": "failed",
                "_toolathlon_resolved_config_marker": True,
            }
        )

        mock_from_dict.assert_called_once_with(
            {"task_root": "/workspace/dumps"}
        )
        mock_from_resolved_dict.assert_not_called()


if __name__ == "__main__":
    unittest.main()
