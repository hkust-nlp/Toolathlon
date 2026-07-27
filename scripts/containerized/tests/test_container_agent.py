import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from scripts.containerized.container_agent import (
    consume_task_bundle,
    run_agent_phase,
)
from utils.roles.task_agent import TaskStatus


class ConsumeTaskBundleTests(unittest.TestCase):
    def write_bundle(self, data):
        handle = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        with handle:
            json.dump(data, handle)
        return handle.name

    def test_consumes_supported_bundle(self) -> None:
        path = self.write_bundle(
            {
                "schema_version": 2,
                "resolved_task_config": {"task_dir": "finalpool/demo"},
                "eval_config": {"agent": {}},
            }
        )

        bundle = consume_task_bundle(path)

        self.assertEqual(bundle["schema_version"], 2)
        self.assertFalse(os.path.exists(path))

    def test_removes_bundle_before_rejecting_schema(self) -> None:
        path = self.write_bundle(
            {
                "schema_version": 1,
                "resolved_task_config": {},
                "eval_config": {},
            }
        )

        with self.assertRaisesRegex(ValueError, "schema_version"):
            consume_task_bundle(path)

        self.assertFalse(os.path.exists(path))


class RunAgentPhaseTests(unittest.IsolatedAsyncioTestCase):
    @patch("scripts.containerized.container_agent.TaskRunner.run_single_task", new_callable=AsyncMock)
    @patch("scripts.containerized.container_agent.TaskRunner.load_configs")
    @patch("scripts.containerized.container_agent.TaskConfig.from_resolved_dict")
    async def test_uses_resolved_config_and_prepared_lifecycle(
        self,
        from_resolved_dict,
        load_configs,
        run_single_task,
    ) -> None:
        task_config = SimpleNamespace(single_turn_mode=True)
        from_resolved_dict.return_value = task_config
        load_configs.return_value = ("mcp", "agent", "user")
        run_single_task.return_value = TaskStatus.SUCCESS
        resolved = {"task_dir": "finalpool/demo"}
        eval_config = {"agent": {"model": {"short_name": "demo"}}}

        result = await run_agent_phase(
            {
                "resolved_task_config": resolved,
                "eval_config": eval_config,
            },
            debug=True,
        )

        self.assertEqual(result, TaskStatus.SUCCESS)
        from_resolved_dict.assert_called_once_with(resolved)
        load_configs.assert_called_once_with(eval_config)
        run_single_task.assert_awaited_once_with(
            task_config=task_config,
            agent_config="agent",
            user_config="user",
            mcp_config="mcp",
            debug=True,
            allow_resume=False,
            manual=False,
            single_turn_mode=True,
            workspace_prepared=True,
        )


if __name__ == "__main__":
    unittest.main()
