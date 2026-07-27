import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path, PurePosixPath

from scripts.containerized.task_artifact_guard import (
    ArtifactGuardError,
    ContainerEntry,
    ContainerRuntimeClient,
    TaskSnapshot,
    cleanup_stash,
    restore_artifacts,
    stash_artifacts,
)


RUNTIME = "docker"
CONTAINER = "toolathlon-test-container"
TASK_PATH = "/workspace/tasks/finalpool/demo-task"


class FakeRuntimeClient:
    """Filesystem-backed stand-in for docker/podman used by guard tests."""

    runtime = RUNTIME
    container = CONTAINER

    def __init__(self, task_root: Path) -> None:
        self.task_root = task_root
        self.copy_from_failures: set[str] = set()
        self.copy_to_failures: set[str] = set()
        self.remove_error = False
        self.remove_calls: list[list[str]] = []

    def inspect_task(self, task_path: str) -> TaskSnapshot:
        self._assert_task_path(task_path)
        if not os.path.lexists(self.task_root):
            return TaskSnapshot(root_kind="missing", entries=())
        root_kind = self._kind(self.task_root)
        entries: list[ContainerEntry] = []
        if root_kind == "directory":
            for child in sorted(
                self.task_root.iterdir(), key=lambda path: (path.name.casefold(), path.name)
            ):
                entries.append(ContainerEntry(name=child.name, kind=self._kind(child)))
        return TaskSnapshot(root_kind=root_kind, entries=tuple(entries))

    def copy_from(self, container_path: str, host_destination: Path) -> None:
        source = self._translate(container_path)
        if source.name in self.copy_from_failures:
            raise ArtifactGuardError(f"injected copy-from failure for {source.name}")
        self._copy(source, host_destination)

    def copy_to(self, host_source: Path, container_path: str) -> None:
        destination = self._translate(container_path)
        if destination.name in self.copy_to_failures:
            raise ArtifactGuardError(f"injected copy-to failure for {destination.name}")
        self._copy(host_source, destination)

    def remove(self, container_paths: list[str]) -> None:
        self.remove_calls.append(list(container_paths))
        if self.remove_error:
            raise ArtifactGuardError("injected remove failure")
        for container_path in container_paths:
            path = self._translate(container_path)
            if path.is_symlink() or path.is_file():
                path.unlink(missing_ok=True)
            elif path.is_dir():
                shutil.rmtree(path)

    def _translate(self, container_path: str) -> Path:
        path = PurePosixPath(container_path)
        root = PurePosixPath(TASK_PATH)
        if path == root:
            return self.task_root
        try:
            relative = path.relative_to(root)
        except ValueError as exc:
            raise AssertionError(f"unexpected fake container path: {path}") from exc
        return self.task_root.joinpath(*relative.parts)

    @staticmethod
    def _copy(source: Path, destination: Path) -> None:
        if os.path.lexists(destination):
            raise AssertionError(f"guard attempted a merging copy to {destination}")
        if source.is_symlink():
            destination.symlink_to(os.readlink(source))
        elif source.is_dir():
            shutil.copytree(source, destination, symlinks=True)
        else:
            shutil.copy2(source, destination, follow_symlinks=False)

    @staticmethod
    def _kind(path: Path) -> str:
        mode = path.lstat().st_mode
        if stat.S_ISDIR(mode):
            return "directory"
        if stat.S_ISREG(mode):
            return "file"
        if stat.S_ISLNK(mode):
            return "symlink"
        return "other"

    @staticmethod
    def _assert_task_path(task_path: str) -> None:
        if task_path != TASK_PATH:
            raise AssertionError(f"unexpected fake task path: {task_path}")


class TaskArtifactGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.task_root = self.root / "container-task"
        self.task_root.mkdir()
        self.stash_root = self.root / "stashes"
        self.client = FakeRuntimeClient(self.task_root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _mkdir_with_file(self, name: str, filename: str, content: str) -> None:
        directory = self.task_root / name
        directory.mkdir()
        (directory / filename).write_text(content, encoding="utf-8")

    def _make_complete_task(self) -> None:
        self._mkdir_with_file("evaluation", "main.py", "TRUSTED EVALUATOR")
        self._mkdir_with_file("preprocess", "helper.py", "TRUSTED HELPER")
        self._mkdir_with_file("groundtruth_workspace", "answer.txt", "TRUSTED ANSWER")
        (self.task_root / "README.MD").write_text("TRUSTED README", encoding="utf-8")
        (self.task_root / "gt_record.md").write_text("TRUSTED RECORD", encoding="utf-8")
        (self.task_root / "expected_results.json").write_text(
            '{"answer": 42}', encoding="utf-8"
        )
        (self.task_root / "task_config.json").write_text("{}", encoding="utf-8")
        self._mkdir_with_file("workspace", "agent.txt", "AGENT OUTPUT")

    def _stash(self) -> Path:
        return stash_artifacts(
            RUNTIME,
            CONTAINER,
            TASK_PATH,
            stash_root=self.stash_root,
            client=self.client,
        )

    def test_stash_and_clean_restore_preserve_only_trusted_entries(self) -> None:
        self._make_complete_task()

        stash_dir = self._stash()

        self.assertEqual(stat.S_IMODE(stash_dir.stat().st_mode), 0o700)
        manifest = json.loads((stash_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(
            {entry["name"] for entry in manifest["entries"]},
            {
                "evaluation",
                "preprocess",
                "groundtruth_workspace",
                "README.MD",
                "gt_record.md",
                "expected_results.json",
            },
        )
        for entry in manifest["entries"]:
            self.assertRegex(entry["sha256"], r"^[0-9a-f]{64}$")
            self.assertGreaterEqual(entry["node_count"], 1)

        self.assertFalse((self.task_root / "evaluation").exists())
        self.assertFalse((self.task_root / "README.MD").exists())
        self.assertTrue((self.task_root / "task_config.json").exists())
        self.assertEqual(
            (self.task_root / "workspace" / "agent.txt").read_text(encoding="utf-8"),
            "AGENT OUTPUT",
        )

        # Simulate an agent pre-creating every collision, including two README
        # casing variants and extra files within fake grader directories.
        self._mkdir_with_file("evaluation", "main.py", "FAKE EVALUATOR")
        (self.task_root / "evaluation" / "backdoor.py").write_text(
            "FAKE EXTRA", encoding="utf-8"
        )
        self._mkdir_with_file("preprocess", "helper.py", "FAKE HELPER")
        (self.task_root / "README.md").write_text("FAKE README", encoding="utf-8")
        (self.task_root / "readme.md").write_text("FAKE README 2", encoding="utf-8")
        (self.task_root / "gt_record.md").write_text("FAKE RECORD", encoding="utf-8")
        (self.task_root / "expected_results.json").mkdir()

        restore_artifacts(
            RUNTIME,
            CONTAINER,
            TASK_PATH,
            stash_dir,
            client=self.client,
        )

        self.assertEqual(
            (self.task_root / "evaluation" / "main.py").read_text(encoding="utf-8"),
            "TRUSTED EVALUATOR",
        )
        self.assertFalse((self.task_root / "evaluation" / "backdoor.py").exists())
        self.assertEqual(
            (self.task_root / "preprocess" / "helper.py").read_text(encoding="utf-8"),
            "TRUSTED HELPER",
        )
        self.assertEqual(
            (self.task_root / "README.MD").read_text(encoding="utf-8"),
            "TRUSTED README",
        )
        self.assertFalse((self.task_root / "README.md").exists())
        self.assertFalse((self.task_root / "readme.md").exists())
        self.assertEqual(
            (self.task_root / "expected_results.json").read_text(encoding="utf-8"),
            '{"answer": 42}',
        )
        self.assertTrue((self.task_root / "task_config.json").exists())
        self.assertTrue(stash_dir.exists(), "restore must retain stash for EXIT cleanup")

        cleanup_stash(stash_dir)
        self.assertFalse(stash_dir.exists())
        cleanup_stash(stash_dir)  # EXIT traps may clean an already-absent stash.

    def test_copy_failure_happens_before_any_container_deletion(self) -> None:
        self._make_complete_task()
        self.client.copy_from_failures.add("groundtruth_workspace")

        with self.assertRaisesRegex(ArtifactGuardError, "copy-from failure"):
            self._stash()

        self.assertEqual(self.client.remove_calls, [])
        self.assertEqual(
            (self.task_root / "evaluation" / "main.py").read_text(encoding="utf-8"),
            "TRUSTED EVALUATOR",
        )
        self.assertTrue((self.task_root / "README.MD").exists())
        if self.stash_root.exists():
            self.assertEqual(list(self.stash_root.iterdir()), [])

    def test_evaluation_is_required_but_other_entries_are_optional(self) -> None:
        with self.assertRaisesRegex(ArtifactGuardError, "evaluation"):
            self._stash()
        self.assertEqual(self.client.remove_calls, [])

        self._mkdir_with_file("evaluation", "main.py", "TRUSTED")
        stash_dir = self._stash()
        manifest = json.loads((stash_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual([entry["name"] for entry in manifest["entries"]], ["evaluation"])

    def test_tampered_stash_is_rejected_before_fake_grader_is_deleted(self) -> None:
        self._mkdir_with_file("evaluation", "main.py", "TRUSTED")
        stash_dir = self._stash()
        self._mkdir_with_file("evaluation", "main.py", "FAKE")
        (stash_dir / "payload" / "evaluation" / "main.py").write_text(
            "TAMPERED", encoding="utf-8"
        )
        remove_call_count = len(self.client.remove_calls)

        with self.assertRaisesRegex(ArtifactGuardError, "hash mismatch"):
            restore_artifacts(
                RUNTIME,
                CONTAINER,
                TASK_PATH,
                stash_dir,
                client=self.client,
            )

        self.assertEqual(len(self.client.remove_calls), remove_call_count)
        self.assertEqual(
            (self.task_root / "evaluation" / "main.py").read_text(encoding="utf-8"),
            "FAKE",
        )

    def test_restore_deletes_fake_optional_entries_absent_from_manifest(self) -> None:
        self._mkdir_with_file("evaluation", "main.py", "TRUSTED")
        stash_dir = self._stash()

        self._mkdir_with_file("preprocess", "helper.py", "FAKE")
        self._mkdir_with_file("groundtruth_workspace", "answer.txt", "FAKE")
        (self.task_root / "ReAdMe.Md").write_text("FAKE", encoding="utf-8")
        (self.task_root / "gt_record.md").mkdir()
        (self.task_root / "expected_results.json").write_text("FAKE", encoding="utf-8")
        self._mkdir_with_file("evaluation", "main.py", "FAKE EVALUATOR")

        restore_artifacts(
            RUNTIME,
            CONTAINER,
            TASK_PATH,
            stash_dir,
            client=self.client,
        )

        self.assertEqual(
            (self.task_root / "evaluation" / "main.py").read_text(encoding="utf-8"),
            "TRUSTED",
        )
        for name in (
            "preprocess",
            "groundtruth_workspace",
            "ReAdMe.Md",
            "gt_record.md",
            "expected_results.json",
        ):
            self.assertFalse(os.path.lexists(self.task_root / name), name)

    def test_remove_failure_retains_recoverable_stash(self) -> None:
        self._mkdir_with_file("evaluation", "main.py", "TRUSTED")
        self.client.remove_error = True

        with self.assertRaisesRegex(ArtifactGuardError, "remove failure"):
            self._stash()

        stashes = list(self.stash_root.glob("artifact-*"))
        self.assertEqual(len(stashes), 1)
        self.assertTrue((stashes[0] / "payload" / "evaluation" / "main.py").exists())
        self.assertTrue((stashes[0] / "manifest.json").exists())

    def test_restore_copy_failure_is_fatal(self) -> None:
        self._mkdir_with_file("evaluation", "main.py", "TRUSTED")
        stash_dir = self._stash()
        self._mkdir_with_file("evaluation", "main.py", "FAKE")
        self.client.copy_to_failures.add("evaluation")

        with self.assertRaisesRegex(ArtifactGuardError, "copy-to failure"):
            restore_artifacts(
                RUNTIME,
                CONTAINER,
                TASK_PATH,
                stash_dir,
                client=self.client,
            )

        self.assertFalse((self.task_root / "evaluation").exists())

    def test_refuses_unsafe_task_path_and_unmarked_cleanup(self) -> None:
        self._mkdir_with_file("evaluation", "main.py", "TRUSTED")
        with self.assertRaisesRegex(ArtifactGuardError, "not normalized"):
            stash_artifacts(
                RUNTIME,
                CONTAINER,
                "/workspace/tasks/finalpool/../escape",
                stash_root=self.stash_root,
                client=self.client,
            )

        unmarked = self.root / "artifact-not-a-stash"
        unmarked.mkdir()
        with self.assertRaisesRegex(ArtifactGuardError, "manifest is missing"):
            cleanup_stash(unmarked)
        self.assertTrue(unmarked.exists())


class ContainerRuntimeClientTests(unittest.TestCase):
    def test_nonzero_subprocess_return_is_always_an_error(self) -> None:
        calls: list[list[str]] = []

        def failed_runner(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            return subprocess.CompletedProcess(command, 23, stdout="", stderr="denied")

        client = ContainerRuntimeClient(
            RUNTIME,
            CONTAINER,
            command_runner=failed_runner,
        )
        with self.assertRaisesRegex(ArtifactGuardError, "exit 23"):
            client.remove([f"{TASK_PATH}/evaluation"])

        self.assertEqual(calls[0][:4], ["docker", "exec", CONTAINER, "rm"])
        self.assertNotIn("bash", calls[0])


if __name__ == "__main__":
    unittest.main()
