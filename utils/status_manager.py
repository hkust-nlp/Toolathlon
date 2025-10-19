"""
Task status management utility for tracking task execution status.
"""
import json
import os
from typing import Optional, Dict, Any


class TaskStatusManager:
    """Utility class for managing task execution status."""

    def __init__(self, task_dir: str):
        """
        Initialize the status manager.

        Args:
            task_dir: Path to the task directory.
        """
        self.task_dir = task_dir
        self.status_file = os.path.join(task_dir, "status.json")
        self._ensure_status_file()

    def _ensure_status_file(self):
        """Ensure the status file exists."""
        os.makedirs(self.task_dir, exist_ok=True)
        if not os.path.exists(self.status_file):
            self._write_status({"preprocess": None, "running": None, "evaluation": None})

    def _write_status(self, status: Dict[str, Any]):
        """Write status to the status file."""
        with open(self.status_file, 'w', encoding='utf-8') as f:
            json.dump(status, f, indent=2, ensure_ascii=False)

    def _read_status(self) -> Dict[str, Any]:
        """Read and return the current status."""
        try:
            with open(self.status_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {"preprocess": None, "running": None, "evaluation": None}

    def update_preprocess(self, status: str):
        """
        Update the preprocess status.

        Args:
            status: Status value. Possible values: None/"running"/"done"/"fail"
        """
        current = self._read_status()
        current['preprocess'] = status
        self._write_status(current)

    def update_running(self, status: str):
        """
        Update the running status.

        Args:
            status: Status value. Possible values: None/"running"/"done"/"timeout"/"max_turn_exceeded"/"fail"
        """
        current = self._read_status()
        current['running'] = status
        self._write_status(current)

    def update_evaluation(self, status: str):
        """
        Update the evaluation status.

        Args:
            status: Status value. Possible values: None/"pass"/"fail"
        """
        current = self._read_status()
        current['evaluation'] = status
        self._write_status(current)

    def get_status(self) -> Dict[str, Any]:
        """Get the current full status."""
        return self._read_status()

    def is_completed(self) -> bool:
        """
        Check if the task is fully completed.

        Returns:
            True if preprocess succeeded, run succeeded, and there is an evaluation result.
        """
        status = self._read_status()
        return (status.get('preprocess') == 'done' and
                status.get('running') == 'done' and
                status.get('evaluation') is not None)