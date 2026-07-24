import re
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "run_single_decoupled.sh"
RUN_PARALLEL_PATH = Path(__file__).resolve().parents[3] / "run_parallel.py"


class DecoupledIsolationRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.script = SCRIPT_PATH.read_text(encoding="utf-8")
        cls.parallel_runner = RUN_PARALLEL_PATH.read_text(encoding="utf-8")

    def position(self, needle: str, start: int = 0) -> int:
        position = self.script.find(needle, start)
        self.assertNotEqual(position, -1, f"missing runner fragment: {needle}")
        return position

    def test_artifacts_are_hidden_before_gateway_and_restored_before_eval(self) -> None:
        preprocess_done = self.position('echo "✓ Preprocess completed"')
        stash = self.position("task_artifact_guard stash", preprocess_done)
        gateway = self.position("# Step 4: Start single-port gateway", stash)
        host_exit = self.position("HOST_LOOP_EXIT_CODE=$?", gateway)
        restore = self.position("task_artifact_guard restore", host_exit)
        remove_fake_eval = self.position(
            'rm -rf -- "$CONTAINER_EVAL_RESULT_PATH"', restore
        )
        evaluation = self.position("# Step 6: Container evaluation", remove_fake_eval)

        self.assertLess(preprocess_done, stash)
        self.assertLess(stash, gateway)
        self.assertLess(host_exit, restore)
        self.assertLess(restore, remove_fake_eval)
        self.assertLess(remove_fake_eval, evaluation)

        # A failed host loop must still reach the checked restore path.
        self.assertIsNone(
            re.search(r"(?m)^\s*exit\b", self.script[host_exit:restore])
        )

        # No stop/start of the task container between the host loop and the
        # evaluation, with or without options such as `-t 0` — evaluator-
        # visible task services must stay up.  cleanup()'s quiesce/restart
        # lives outside this segment.
        live_container_segment = self.script[host_exit:evaluation]
        self.assertIsNone(
            re.search(r"\$CONTAINER_RUNTIME (stop|start)\b", live_container_segment)
        )

    def test_evaluator_uses_consumed_private_bundle_and_trusted_inputs(self) -> None:
        evaluation = self.position("# Step 6: Container evaluation")
        evaluation_segment = self.script[evaluation:]

        self.assertIn("stage_trusted_bundle", evaluation_segment)
        self.assertIn("--require_resolved_task_config", evaluation_segment)
        self.assertIn("--consume_bundle", evaluation_segment)
        self.assertIn('--agent_exit_code "$HOST_LOOP_EXIT_CODE"', evaluation_segment)
        self.assertNotIn("--boolean_evaluation_status", evaluation_segment)

        self.assertIn(
            'TRUSTED_STASH_DIR=$(mktemp -d "/tmp/toolathlon-decoupled.XXXXXX")',
            self.script,
        )
        self.assertIn(
            "mktemp /run/toolathlon-preprocess-bundle.XXXXXX.json", self.script
        )
        self.assertIn(
            'rm -rf -- "$output_folder/task_bundle.json"', self.script
        )
        evaluation_exit = self.position("EVAL_EXIT_CODE=$?", evaluation)
        publish_bundle = self.position(
            'cp -- "$TRUSTED_BUNDLE_FILE" "$PUBLISHED_BUNDLE_FILE"',
            evaluation_exit,
        )
        self.assertLess(evaluation_exit, publish_bundle)
        self.assertNotIn(
            "--bundle_file /workspace/dumps/task_bundle.json", self.script
        )

    def test_task_copy_and_cleanup_are_collision_safe(self) -> None:
        copy_task = self.position(
            '$CONTAINER_RUNTIME cp "$TASK_SOURCE" '
            '"$CONTAINER_NAME:/workspace/tasks/$TARGET_PARENT_DIR/"'
        )
        remove_existing = self.script.rfind(
            'rm -rf -- "$CONTAINER_TASK_PATH"', 0, copy_task
        )
        self.assertNotEqual(remove_existing, -1)
        self.assertLess(remove_existing, copy_task)

        self.assertIn("cleanup_exit_code=$?", self.script)
        self.assertIn('exit "$cleanup_exit_code"', self.script)
        self.assertNotIn("ARTIFACTS_RESTORED", self.script)
        self.assertEqual(self.script.count("task_artifact_guard restore"), 1)
        cleanup_start = self.position("cleanup() {")
        container_stop = self.position(
            '$CONTAINER_RUNTIME stop -t 0 "$CONTAINER_NAME"', cleanup_start
        )
        stash_cleanup = self.position(
            "task_artifact_guard cleanup", container_stop
        )
        self.assertLess(container_stop, stash_cleanup)
        self.assertNotIn(
            'cp "$CONTAINER_NAME:/workspace/logs/', self.script
        )
        self.assertIn(
            '[ "$parent_captures_run_log" != "1" ]', self.script
        )

        decoupled_branch_start = self.parallel_runner.index(
            'if runner == "decoupled":'
        )
        containerized_branch_start = self.parallel_runner.index(
            "        else:", decoupled_branch_start
        )
        decoupled_branch = self.parallel_runner[
            decoupled_branch_start:containerized_branch_start
        ]
        self.assertIn(
            'TOOLATHLON_PARENT_CAPTURES_RUN_LOG=1', decoupled_branch
        )


if __name__ == "__main__":
    unittest.main()
