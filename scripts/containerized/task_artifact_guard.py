"""Temporarily withhold task-local grading artifacts from an agent container.

The guard deliberately has a small allow-list.  It runs after preprocess and
before the agent, copies every protected entry to a private host directory,
and only then removes the container copies.  Before grading, ``restore``
removes any agent-created collisions and restores the exact stashed entries.

This module is intended to be called by ``run_single_containerized.sh``::

    python -m scripts.containerized.task_artifact_guard stash ...
    python -m scripts.containerized.task_artifact_guard restore ...
    python -m scripts.containerized.task_artifact_guard cleanup ...

All container-runtime commands are argv based (never shell based) and every
return code is checked.  A failed stash/restore is therefore an infrastructure
failure, not a reason to continue with an untrusted grader.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Callable, Iterable, Sequence


MANIFEST_VERSION = 1
MANIFEST_FILENAME = "manifest.json"
PAYLOAD_DIRNAME = "payload"
DEFAULT_STASH_ROOT = Path(tempfile.gettempdir()) / "toolathlon-task-stash"

PROTECTED_DIRECTORIES = (
    "preprocess",
    "evaluation",
    "groundtruth_workspace",
    # Per-task subdir that leaks the answer:
    "golden",  # oil-price: contains golden/main.py — the reference
               # implementation script the grader cites as "source of
               # truth" for backtest computation.
)
REQUIRED_DIRECTORIES = frozenset({"evaluation"})
PROTECTED_EXACT_FILES = frozenset({
    "gt_record.md",
    "expected_results.json",
    # ── Newly identified task-root leaks (audited 2026-06-30 on the
    # v3 branch; porting equivalents here) ──
    #
    # Snapshot files at task root that carry the expected answer
    # in plain text (same shape as expected_results.json):
    "setup_results.json",                     # woocommerce-new-product
    "recalled_products_info.json",            # woocommerce-product-recall
    "test_customers_info.json",               # woocommerce-product-recall
    # Author scripts whose code IS the answer — the agent could read
    # the expected output or even run the generator:
    "create_excel_report.py",                 # canvas-submit-late-work
    "send_reminder_emails.py",                # canvas-submit-late-work
    "generate_groundtruth.py",                # sales-accounting
    "build_excel_ledger.py",                  # sales-accounting
    "verify_groundtruth.py",                  # sync-todo-to-readme
    "generate_initial_excel.py",              # woocommerce-stock-alert
    # Test files at task root that bake in pass/fail oracles:
    "test_evaluation.py",                     # paper-checker
    "test_evaluation_enhanced.py",            # paper-checker
    "test_enhanced_evaluation.py",            # game-statistics
    "test_check_local.py",                    # reimbursement-form-filler
    "test_integration.py",                    # woocommerce-customer-survey
    # Author notes / solution outlines at task root:
    "readme_xiaochen.md",                     # canvas-do-quiz (validates a
                                              # specific quiz answer)
    "guide.md",                               # ipad-edu-price (literal
                                              # 4-step solution outline);
                                              # SAFE for yahoo-analysis which
                                              # has guide.md at
                                              # initial_workspace/guide.md —
                                              # only direct children of the
                                              # task root are inspected.
    "restructure_summary.md",                 # excel-data-transformation
    "evaluation_enhancement_report.md",       # paper-checker
    "note.md",                                # personal-website-construct
    # Side-output of a stashed generator script — has the expected
    # shape + populated stock-alert records:
    "stock_alerts_initial.xlsx",              # woocommerce-stock-alert
    # Author dev artifacts at task root with no agent runtime use:
    "convert_to_backup.py",                   # apply-phd-email
    "station_english_name.txt",               # train-ticket-plan
})
PROTECTED_CASEFOLD_FILES = frozenset({"readme.md"})

_CONTAINER_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_STASH_PREFIX = "artifact-"


class ArtifactGuardError(RuntimeError):
    """Raised when the guard cannot safely complete an operation."""


@dataclass(frozen=True)
class ContainerEntry:
    """A direct child of the task directory inside the container."""

    name: str
    kind: str


@dataclass(frozen=True)
class TaskSnapshot:
    """The task root type and its direct children."""

    root_kind: str
    entries: tuple[ContainerEntry, ...]


_INSPECT_SCRIPT = r"""
import json
import os
import stat
import sys

root = sys.argv[1]

def kind(mode):
    if stat.S_ISDIR(mode):
        return "directory"
    if stat.S_ISREG(mode):
        return "file"
    if stat.S_ISLNK(mode):
        return "symlink"
    return "other"

try:
    root_stat = os.lstat(root)
except FileNotFoundError:
    print(json.dumps({"root_kind": "missing", "entries": []}))
    raise SystemExit(0)

root_kind = kind(root_stat.st_mode)
entries = []
if root_kind == "directory":
    for entry in os.scandir(root):
        entry_stat = entry.stat(follow_symlinks=False)
        entries.append({"name": entry.name, "kind": kind(entry_stat.st_mode)})

entries.sort(key=lambda item: (item["name"].casefold(), item["name"]))
print(json.dumps({"root_kind": root_kind, "entries": entries}))
""".strip()


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


class ContainerRuntimeClient:
    """Checked, shell-free wrapper around Docker or Podman commands."""

    def __init__(
        self,
        runtime: str,
        container: str,
        *,
        command_runner: CommandRunner = subprocess.run,
    ) -> None:
        self.runtime = _validate_runtime(runtime)
        self.container = _validate_container_name(container)
        self._command_runner = command_runner

    def _run(self, args: Sequence[str], *, timeout: int) -> subprocess.CompletedProcess[str]:
        command = [self.runtime, *args]
        try:
            result = self._command_runner(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ArtifactGuardError(
                f"container runtime command timed out after {timeout}s: "
                f"{_display_command(command)}"
            ) from exc
        except OSError as exc:
            raise ArtifactGuardError(
                f"could not execute container runtime command "
                f"{_display_command(command)}: {exc}"
            ) from exc

        if result.returncode != 0:
            details = (result.stderr or result.stdout or "").strip()
            if len(details) > 1000:
                details = details[-1000:]
            suffix = f": {details}" if details else ""
            raise ArtifactGuardError(
                f"container runtime command failed with exit {result.returncode}: "
                f"{_display_command(command)}{suffix}"
            )
        return result

    def inspect_task(self, task_path: str) -> TaskSnapshot:
        result = self._run(
            [
                "exec",
                self.container,
                "uv",
                "run",
                "python",
                "-c",
                _INSPECT_SCRIPT,
                task_path,
            ],
            timeout=30,
        )
        try:
            raw = json.loads(result.stdout)
            root_kind = raw["root_kind"]
            raw_entries = raw["entries"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ArtifactGuardError(
                "container returned an invalid task-directory inspection payload"
            ) from exc

        if root_kind not in {"missing", "directory", "file", "symlink", "other"}:
            raise ArtifactGuardError(f"invalid task root kind from container: {root_kind!r}")
        if not isinstance(raw_entries, list):
            raise ArtifactGuardError("task-directory inspection entries must be a list")

        entries: list[ContainerEntry] = []
        seen: set[str] = set()
        for raw_entry in raw_entries:
            if not isinstance(raw_entry, dict):
                raise ArtifactGuardError("invalid task-directory entry from container")
            name = raw_entry.get("name")
            kind = raw_entry.get("kind")
            _validate_entry_name(name)
            if kind not in {"directory", "file", "symlink", "other"}:
                raise ArtifactGuardError(f"invalid entry kind for {name!r}: {kind!r}")
            if name in seen:
                raise ArtifactGuardError(f"duplicate task-directory entry: {name!r}")
            seen.add(name)
            entries.append(ContainerEntry(name=name, kind=kind))
        return TaskSnapshot(root_kind=root_kind, entries=tuple(entries))

    def copy_from(self, container_path: str, host_destination: Path) -> None:
        self._run(
            ["cp", f"{self.container}:{container_path}", str(host_destination)],
            timeout=180,
        )

    def copy_to(self, host_source: Path, container_path: str) -> None:
        self._run(
            ["cp", str(host_source), f"{self.container}:{container_path}"],
            timeout=180,
        )

    def remove(self, container_paths: Sequence[str]) -> None:
        if not container_paths:
            return
        self._run(
            ["exec", self.container, "rm", "-rf", "--", *container_paths],
            timeout=60,
        )


def stash_artifacts(
    runtime: str,
    container: str,
    task_path: str,
    *,
    stash_root: Path | str = DEFAULT_STASH_ROOT,
    client: ContainerRuntimeClient | None = None,
) -> Path:
    """Copy protected entries out of a container, then remove the originals.

    All protected entries are copied and hashed before the first removal.  If
    copying fails, the task directory is left untouched.  If removal begins
    and a later check fails, the private stash is intentionally retained so a
    caller/operator can still recover it.
    """

    runtime = _validate_runtime(runtime)
    container = _validate_container_name(container)
    task_path = _validate_task_path(task_path)
    client = client or ContainerRuntimeClient(runtime, container)
    _validate_client_identity(client, runtime, container)

    stash_dir = _create_stash_dir(stash_root)
    payload_dir = stash_dir / PAYLOAD_DIRNAME
    payload_dir.mkdir(mode=0o700)
    deletion_started = False
    try:
        snapshot = client.inspect_task(task_path)
        selected = _entries_to_stash(snapshot)

        records: list[dict[str, object]] = []
        for entry in selected:
            destination = payload_dir / entry.name
            if os.path.lexists(destination):
                raise ArtifactGuardError(f"stash destination already exists: {destination}")
            client.copy_from(_container_child(task_path, entry.name), destination)
            if not os.path.lexists(destination):
                raise ArtifactGuardError(
                    f"runtime reported success but did not copy {entry.name!r}"
                )
            digest, size_bytes, node_count = _hash_path(destination)
            actual_kind = _host_path_kind(destination)
            if actual_kind != entry.kind:
                raise ArtifactGuardError(
                    f"copied entry {entry.name!r} changed type: "
                    f"expected {entry.kind}, got {actual_kind}"
                )
            records.append(
                {
                    "name": entry.name,
                    "kind": entry.kind,
                    "sha256": digest,
                    "size_bytes": size_bytes,
                    "node_count": node_count,
                }
            )

        manifest = {
            "version": MANIFEST_VERSION,
            "stash_id": stash_dir.name,
            "created_at": datetime.now(UTC).isoformat(),
            "runtime": runtime,
            "container": container,
            "task_path": task_path,
            "entries": records,
        }
        _write_manifest(stash_dir, manifest)

        deletion_started = True
        client.remove([_container_child(task_path, entry.name) for entry in selected])

        remaining = _protected_entries(client.inspect_task(task_path))
        if remaining:
            raise ArtifactGuardError(
                "protected task entries remained after removal: "
                + ", ".join(entry.name for entry in remaining)
            )
        return stash_dir
    except Exception:
        if not deletion_started:
            _remove_stash_dir_unchecked(stash_dir)
        raise


def restore_artifacts(
    runtime: str,
    container: str,
    task_path: str,
    stash_dir: Path | str,
    *,
    client: ContainerRuntimeClient | None = None,
) -> None:
    """Clean-replace protected task entries with their trusted stash copies."""

    runtime = _validate_runtime(runtime)
    container = _validate_container_name(container)
    task_path = _validate_task_path(task_path)
    client = client or ContainerRuntimeClient(runtime, container)
    _validate_client_identity(client, runtime, container)

    stash_path, manifest = _load_manifest(stash_dir)
    _validate_manifest_identity(manifest, runtime, container, task_path)
    entries = _validated_manifest_entries(manifest)
    payload_dir = stash_path / PAYLOAD_DIRNAME

    # Validate every trusted source before deleting anything in the container.
    for entry in entries:
        source = payload_dir / entry["name"]
        _verify_host_payload(source, entry)

    before = client.inspect_task(task_path)
    _require_task_directory(before)

    # Delete the full candidate set, not just what was in the original stash.
    # This removes agent-created evaluation/preprocess trees and README casing
    # variants before docker/podman cp can merge into them.
    names_to_remove = set(PROTECTED_DIRECTORIES) | set(PROTECTED_EXACT_FILES)
    names_to_remove.update(entry["name"] for entry in entries)
    names_to_remove.update(
        entry.name
        for entry in before.entries
        if entry.name.casefold() in PROTECTED_CASEFOLD_FILES
    )
    client.remove(
        [_container_child(task_path, name) for name in sorted(names_to_remove)]
    )

    after_delete = client.inspect_task(task_path)
    _require_task_directory(after_delete)
    protected_after_delete = _protected_entries(after_delete)
    if protected_after_delete:
        raise ArtifactGuardError(
            "protected task entries remained before restore: "
            + ", ".join(entry.name for entry in protected_after_delete)
        )

    for entry in entries:
        name = entry["name"]
        client.copy_to(payload_dir / name, _container_child(task_path, name))

    after_restore = client.inspect_task(task_path)
    _require_task_directory(after_restore)
    restored_protected = _protected_entries(after_restore)
    actual_by_name = {entry.name: entry for entry in restored_protected}
    expected_by_name = {entry["name"]: entry for entry in entries}
    if set(actual_by_name) != set(expected_by_name):
        raise ArtifactGuardError(
            "restored protected-entry set does not match manifest: "
            f"expected {sorted(expected_by_name)!r}, got {sorted(actual_by_name)!r}"
        )
    for name, expected in expected_by_name.items():
        if actual_by_name[name].kind != expected["kind"]:
            raise ArtifactGuardError(
                f"restored entry {name!r} has type {actual_by_name[name].kind!r}, "
                f"expected {expected['kind']!r}"
            )

    # Container-side content is verified by copying it back to a fresh host
    # directory and comparing the canonical tree hash from the manifest.
    with tempfile.TemporaryDirectory(prefix="artifact-verify-") as verify_tmp:
        verify_root = Path(verify_tmp)
        for entry in entries:
            name = entry["name"]
            destination = verify_root / name
            client.copy_from(_container_child(task_path, name), destination)
            _verify_host_payload(destination, entry)


def cleanup_stash(stash_dir: Path | str) -> None:
    """Delete a completed guard stash after validating its marker manifest.

    An already-absent path is accepted so shell EXIT traps can call cleanup
    unconditionally.  Existing symlinks and unmarked directories are refused.
    """

    stash_path = _absolute_host_path(stash_dir, label="stash directory")
    if not os.path.lexists(stash_path):
        return
    _load_manifest(stash_path)
    shutil.rmtree(stash_path)


def _entries_to_stash(snapshot: TaskSnapshot) -> tuple[ContainerEntry, ...]:
    _require_task_directory(snapshot)
    by_name = {entry.name: entry for entry in snapshot.entries}
    selected: list[ContainerEntry] = []

    for name in PROTECTED_DIRECTORIES:
        entry = by_name.get(name)
        if entry is None:
            if name in REQUIRED_DIRECTORIES:
                raise ArtifactGuardError(
                    f"required protected directory is missing: {name!r}"
                )
            continue
        if entry.kind != "directory":
            raise ArtifactGuardError(
                f"protected directory {name!r} has unexpected type {entry.kind!r}"
            )
        selected.append(entry)

    for entry in snapshot.entries:
        if not _is_protected_file_name(entry.name):
            continue
        if entry.kind != "file":
            raise ArtifactGuardError(
                f"protected file {entry.name!r} has unexpected type {entry.kind!r}"
            )
        selected.append(entry)

    selected.sort(key=lambda entry: (entry.name.casefold(), entry.name))
    return tuple(selected)


def _protected_entries(snapshot: TaskSnapshot) -> tuple[ContainerEntry, ...]:
    protected = [
        entry
        for entry in snapshot.entries
        if entry.name in PROTECTED_DIRECTORIES or _is_protected_file_name(entry.name)
    ]
    protected.sort(key=lambda entry: (entry.name.casefold(), entry.name))
    return tuple(protected)


def _is_protected_file_name(name: str) -> bool:
    return name in PROTECTED_EXACT_FILES or name.casefold() in PROTECTED_CASEFOLD_FILES


def _require_task_directory(snapshot: TaskSnapshot) -> None:
    if snapshot.root_kind != "directory":
        raise ArtifactGuardError(
            f"container task path must be a real directory, got {snapshot.root_kind!r}"
        )


def _create_stash_dir(stash_root: Path | str) -> Path:
    root = _absolute_host_path(stash_root, label="stash root")
    if os.path.lexists(root):
        root_stat = root.lstat()
        if stat.S_ISLNK(root_stat.st_mode) or not stat.S_ISDIR(root_stat.st_mode):
            raise ArtifactGuardError(f"stash root is not a real directory: {root}")
    else:
        root.mkdir(parents=True, mode=0o700)
        root.chmod(0o700)
    try:
        stash_dir = Path(tempfile.mkdtemp(prefix=_STASH_PREFIX, dir=root))
        stash_dir.chmod(0o700)
    except OSError as exc:
        raise ArtifactGuardError(f"could not create private stash under {root}: {exc}") from exc
    return stash_dir


def _write_manifest(stash_dir: Path, manifest: dict[str, object]) -> None:
    temporary = stash_dir / f".{MANIFEST_FILENAME}.tmp"
    final = stash_dir / MANIFEST_FILENAME
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(0o600)
        temporary.replace(final)
    except OSError as exc:
        raise ArtifactGuardError(f"could not write artifact manifest: {exc}") from exc


def _load_manifest(stash_dir: Path | str) -> tuple[Path, dict[str, object]]:
    stash_path = _absolute_host_path(stash_dir, label="stash directory")
    if not os.path.lexists(stash_path):
        raise ArtifactGuardError(f"stash directory does not exist: {stash_path}")
    stash_stat = stash_path.lstat()
    if stat.S_ISLNK(stash_stat.st_mode) or not stat.S_ISDIR(stash_stat.st_mode):
        raise ArtifactGuardError(f"stash path is not a real directory: {stash_path}")
    if not stash_path.name.startswith(_STASH_PREFIX):
        raise ArtifactGuardError(f"stash directory has an invalid name: {stash_path.name!r}")

    manifest_path = stash_path / MANIFEST_FILENAME
    if not os.path.lexists(manifest_path):
        raise ArtifactGuardError(f"stash manifest is missing: {manifest_path}")
    manifest_stat = manifest_path.lstat()
    if stat.S_ISLNK(manifest_stat.st_mode) or not stat.S_ISREG(manifest_stat.st_mode):
        raise ArtifactGuardError(f"stash manifest is not a regular file: {manifest_path}")
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactGuardError(f"could not read stash manifest: {exc}") from exc
    if not isinstance(raw, dict):
        raise ArtifactGuardError("stash manifest must be a JSON object")
    if raw.get("version") != MANIFEST_VERSION:
        raise ArtifactGuardError(
            f"unsupported stash manifest version: {raw.get('version')!r}"
        )
    if raw.get("stash_id") != stash_path.name:
        raise ArtifactGuardError("stash manifest identity does not match directory")
    _validated_manifest_entries(raw)
    return stash_path, raw


def _validated_manifest_entries(manifest: dict[str, object]) -> list[dict[str, object]]:
    raw_entries = manifest.get("entries")
    if not isinstance(raw_entries, list):
        raise ArtifactGuardError("stash manifest entries must be a list")
    entries: list[dict[str, object]] = []
    seen: set[str] = set()
    for raw in raw_entries:
        if not isinstance(raw, dict):
            raise ArtifactGuardError("invalid stash manifest entry")
        name = raw.get("name")
        kind = raw.get("kind")
        digest = raw.get("sha256")
        size_bytes = raw.get("size_bytes")
        node_count = raw.get("node_count")
        _validate_entry_name(name)
        if name in seen:
            raise ArtifactGuardError(f"duplicate manifest entry: {name!r}")
        seen.add(name)
        if name not in PROTECTED_DIRECTORIES and not _is_protected_file_name(name):
            raise ArtifactGuardError(f"manifest contains an unprotected entry: {name!r}")
        expected_kind = "directory" if name in PROTECTED_DIRECTORIES else "file"
        if kind != expected_kind:
            raise ArtifactGuardError(
                f"invalid manifest kind for {name!r}: {kind!r}"
            )
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ArtifactGuardError(f"invalid manifest hash for {name!r}")
        if not isinstance(size_bytes, int) or isinstance(size_bytes, bool) or size_bytes < 0:
            raise ArtifactGuardError(f"invalid manifest size for {name!r}")
        if not isinstance(node_count, int) or isinstance(node_count, bool) or node_count < 1:
            raise ArtifactGuardError(f"invalid manifest node count for {name!r}")
        entries.append(raw)

    names = {entry["name"] for entry in entries}
    if not REQUIRED_DIRECTORIES.issubset(names):
        missing = sorted(REQUIRED_DIRECTORIES - names)
        raise ArtifactGuardError(
            "stash manifest is missing required entries: " + ", ".join(missing)
        )
    return entries


def _validate_manifest_identity(
    manifest: dict[str, object], runtime: str, container: str, task_path: str
) -> None:
    expected = {
        "runtime": runtime,
        "container": container,
        "task_path": task_path,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ArtifactGuardError(
                f"stash manifest {key} mismatch: expected {value!r}, "
                f"got {manifest.get(key)!r}"
            )


def _verify_host_payload(path: Path, entry: dict[str, object]) -> None:
    if not os.path.lexists(path):
        raise ArtifactGuardError(f"stashed payload is missing: {path}")
    actual_kind = _host_path_kind(path)
    if actual_kind != entry["kind"]:
        raise ArtifactGuardError(
            f"payload {entry['name']!r} has type {actual_kind!r}, "
            f"expected {entry['kind']!r}"
        )
    digest, size_bytes, node_count = _hash_path(path)
    if (
        digest != entry["sha256"]
        or size_bytes != entry["size_bytes"]
        or node_count != entry["node_count"]
    ):
        raise ArtifactGuardError(f"payload hash mismatch for {entry['name']!r}")


def _hash_path(root: Path) -> tuple[str, int, int]:
    hasher = hashlib.sha256()
    hasher.update(b"toolathlon-artifact-tree-v1\0")
    total_size = 0
    node_count = 0
    for relative, path, path_stat in _walk_path_without_following_links(root):
        node_count += 1
        mode = stat.S_IMODE(path_stat.st_mode)
        if stat.S_ISDIR(path_stat.st_mode):
            kind = b"d"
            payload = b""
        elif stat.S_ISREG(path_stat.st_mode):
            kind = b"f"
            try:
                payload = path.read_bytes()
            except OSError as exc:
                raise ArtifactGuardError(f"could not hash artifact file {path}: {exc}") from exc
            total_size += len(payload)
        elif stat.S_ISLNK(path_stat.st_mode):
            kind = b"l"
            try:
                payload = os.readlink(path).encode("utf-8", errors="surrogateescape")
            except OSError as exc:
                raise ArtifactGuardError(f"could not hash artifact symlink {path}: {exc}") from exc
        else:
            raise ArtifactGuardError(f"unsupported artifact node type: {path}")
        relative_bytes = relative.encode("utf-8", errors="surrogateescape")
        hasher.update(kind)
        hasher.update(b"\0")
        hasher.update(relative_bytes)
        hasher.update(b"\0")
        hasher.update(f"{mode:o}".encode("ascii"))
        hasher.update(b"\0")
        hasher.update(str(len(payload)).encode("ascii"))
        hasher.update(b"\0")
        hasher.update(payload)
        hasher.update(b"\0")
    return hasher.hexdigest(), total_size, node_count


def _walk_path_without_following_links(
    root: Path,
) -> Iterable[tuple[str, Path, os.stat_result]]:
    def visit(path: Path, relative: str) -> Iterable[tuple[str, Path, os.stat_result]]:
        try:
            path_stat = path.lstat()
        except OSError as exc:
            raise ArtifactGuardError(f"could not inspect artifact path {path}: {exc}") from exc
        yield relative, path, path_stat
        if not stat.S_ISDIR(path_stat.st_mode):
            return
        try:
            children = sorted(os.scandir(path), key=lambda entry: entry.name)
        except OSError as exc:
            raise ArtifactGuardError(f"could not list artifact directory {path}: {exc}") from exc
        for child in children:
            child_relative = child.name if relative == "." else f"{relative}/{child.name}"
            yield from visit(Path(child.path), child_relative)

    yield from visit(root, ".")


def _host_path_kind(path: Path) -> str:
    path_stat = path.lstat()
    if stat.S_ISDIR(path_stat.st_mode):
        return "directory"
    if stat.S_ISREG(path_stat.st_mode):
        return "file"
    if stat.S_ISLNK(path_stat.st_mode):
        return "symlink"
    return "other"


def _validate_runtime(runtime: str) -> str:
    if not isinstance(runtime, str) or not runtime:
        raise ArtifactGuardError("container runtime must be docker or podman")
    if runtime not in {"docker", "podman"}:
        raise ArtifactGuardError(
            f"unsupported container runtime {runtime!r}; expected 'docker' or 'podman'"
        )
    return runtime


def _validate_container_name(container: str) -> str:
    if not isinstance(container, str) or not _CONTAINER_NAME_RE.fullmatch(container):
        raise ArtifactGuardError(f"unsafe container name: {container!r}")
    return container


def _validate_task_path(task_path: str) -> str:
    if not isinstance(task_path, str) or not task_path.startswith("/"):
        raise ArtifactGuardError("container task path must be absolute")
    if any(ord(character) < 32 for character in task_path):
        raise ArtifactGuardError("container task path contains control characters")
    raw_parts = task_path.split("/")
    if any(part in {".", "..", ""} for part in raw_parts[1:]):
        raise ArtifactGuardError(f"container task path is not normalized: {task_path!r}")
    path = PurePosixPath(task_path)
    if len(path.parts) < 4 or path.parts[:3] != ("/", "workspace", "tasks"):
        raise ArtifactGuardError(
            "container task path must be below /workspace/tasks"
        )
    return str(path)


def _validate_entry_name(name: object) -> None:
    if not isinstance(name, str) or not name or name in {".", ".."}:
        raise ArtifactGuardError(f"unsafe task entry name: {name!r}")
    if "/" in name or "\x00" in name or any(ord(character) < 32 for character in name):
        raise ArtifactGuardError(f"unsafe task entry name: {name!r}")


def _absolute_host_path(path: Path | str, *, label: str) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        raise ArtifactGuardError(f"{label} must be an absolute path: {candidate}")
    return candidate


def _container_child(task_path: str, name: str) -> str:
    _validate_entry_name(name)
    return str(PurePosixPath(task_path) / name)


def _validate_client_identity(
    client: ContainerRuntimeClient, runtime: str, container: str
) -> None:
    client_runtime = getattr(client, "runtime", runtime)
    client_container = getattr(client, "container", container)
    if client_runtime != runtime or client_container != container:
        raise ArtifactGuardError("container runtime client identity mismatch")


def _display_command(command: Sequence[str]) -> str:
    # Do not include the multiline inspection program in error messages.
    displayed = list(command)
    if _INSPECT_SCRIPT in displayed:
        displayed[displayed.index(_INSPECT_SCRIPT)] = "<inspection-script>"
    return " ".join(repr(part) for part in displayed)


def _remove_stash_dir_unchecked(stash_dir: Path) -> None:
    try:
        shutil.rmtree(stash_dir)
    except OSError:
        pass


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Withhold and restore task-local grader artifacts"
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    stash_parser = subparsers.add_parser("stash", help="stash then remove artifacts")
    _add_container_arguments(stash_parser)
    stash_parser.add_argument(
        "--stash-root",
        default=str(DEFAULT_STASH_ROOT),
        help="absolute host directory under which to create a unique stash",
    )

    restore_parser = subparsers.add_parser("restore", help="clean-restore artifacts")
    _add_container_arguments(restore_parser)
    restore_parser.add_argument("--stash-dir", required=True)

    cleanup_parser = subparsers.add_parser("cleanup", help="delete a completed stash")
    cleanup_parser.add_argument("--stash-dir", required=True)
    return parser


def _add_container_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--runtime", required=True, choices=("docker", "podman"))
    parser.add_argument("--container", required=True)
    parser.add_argument("--task-path", required=True)


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.action == "stash":
            stash_dir = stash_artifacts(
                args.runtime,
                args.container,
                args.task_path,
                stash_root=args.stash_root,
            )
            # Keep stdout machine-readable for shell command substitution.
            print(stash_dir)
        elif args.action == "restore":
            restore_artifacts(
                args.runtime,
                args.container,
                args.task_path,
                args.stash_dir,
            )
        elif args.action == "cleanup":
            cleanup_stash(args.stash_dir)
        else:  # pragma: no cover - argparse enforces the choices.
            raise ArtifactGuardError(f"unsupported action: {args.action}")
    except ArtifactGuardError as exc:
        print(f"artifact guard error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
