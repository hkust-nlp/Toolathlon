import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from utils.roles.task_agent import TaskAgent, TaskStatus


def build_agent_harness(root: str, workspace_prepared: bool) -> TaskAgent:
    workspace = os.path.join(root, "custom-workspace")
    os.makedirs(workspace, exist_ok=True)
    os.makedirs(os.path.join(root, "workspace"), exist_ok=True)

    agent = TaskAgent.__new__(TaskAgent)
    agent.task_config = SimpleNamespace(
        id="finalpool-demo",
        task_root=root,
        log_file=os.path.join(root, "custom-log.json"),
        agent_workspace=workspace,
        local_token_key_session={"token": "from-preprocess"},
        load_local_token_key_session=Mock(),
    )
    agent.workspace_prepared = workspace_prepared
    agent.status_manager = SimpleNamespace(
        update_preprocess=Mock(),
        update_running=Mock(),
    )
    agent.initialize_workspace = AsyncMock(return_value=True)
    agent.setup_mcp_servers = AsyncMock()
    agent.setup_agent = AsyncMock()
    agent.setup_user_simulator = AsyncMock()
    agent.run_interaction_loop = AsyncMock()
    agent.save_results = AsyncMock()
    agent.cleanup = AsyncMock()
    agent.get_cost_summary = Mock(return_value=({}, {}))
    agent._remove_checkpoint = Mock()
    agent._debug_print = Mock()
    agent.task_status = TaskStatus.FAILED
    agent.debug = False
    agent.stats = {}
    agent.agent_config = SimpleNamespace(model=SimpleNamespace(short_name="agent"))
    agent.user_config = SimpleNamespace(model=SimpleNamespace(short_name="user"))
    return agent


class TaskAgentPreparedTests(unittest.IsolatedAsyncioTestCase):
    async def test_prepared_mode_skips_preprocess_and_preserves_paths(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            agent = build_agent_harness(root, workspace_prepared=True)
            original_log = agent.task_config.log_file
            original_workspace = agent.task_config.agent_workspace

            status = await agent.run()

            self.assertEqual(status, TaskStatus.SUCCESS)
            self.assertEqual(agent.task_config.log_file, original_log)
            self.assertEqual(agent.task_config.agent_workspace, original_workspace)
            agent.initialize_workspace.assert_not_awaited()
            agent.task_config.load_local_token_key_session.assert_not_called()
            agent.status_manager.update_preprocess.assert_not_called()
            agent.setup_mcp_servers.assert_awaited_once_with(
                {"token": "from-preprocess"}
            )
            agent.setup_agent.assert_awaited_once_with()
            agent.setup_user_simulator.assert_awaited_once_with()
            agent.run_interaction_loop.assert_awaited_once_with(os.path.abspath(root))
            agent.status_manager.update_running.assert_any_call("running")
            agent.status_manager.update_running.assert_any_call("done")
            agent.save_results.assert_awaited_once_with()
            agent.cleanup.assert_awaited_once_with()

    async def test_legacy_mode_still_initializes_and_loads_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            agent = build_agent_harness(root, workspace_prepared=False)

            status = await agent.run()

            self.assertEqual(status, TaskStatus.SUCCESS)
            self.assertEqual(
                agent.task_config.log_file,
                os.path.join(root, "traj_log.json"),
            )
            self.assertEqual(
                agent.task_config.agent_workspace,
                os.path.join(root, "workspace"),
            )
            agent.initialize_workspace.assert_awaited_once_with()
            agent.task_config.load_local_token_key_session.assert_called_once_with()
            self.assertEqual(
                agent.status_manager.update_preprocess.call_args_list,
                [unittest.mock.call("running"), unittest.mock.call("done")],
            )


if __name__ == "__main__":
    unittest.main()
