"""
Task status management utility for tracking task execution status.
"""
import json
import os
from typing import Optional, Dict, Any


class TaskStatusManager:
    """管理任务状态的工具类"""

    def __init__(self, task_dir: str):
        """
        初始化状态管理器

        Args:
            task_dir: 任务目录路径
        """
        self.task_dir = task_dir
        self.status_file = os.path.join(task_dir, "status.json")
        self._ensure_status_file()

    def _ensure_status_file(self):
        """确保状态文件存在"""
        os.makedirs(self.task_dir, exist_ok=True)
        if not os.path.exists(self.status_file):
            self._write_status({"preprocess": None, "running": None, "evaluation": None})

    def _write_status(self, status: Dict[str, Any]):
        """写入状态文件"""
        with open(self.status_file, 'w', encoding='utf-8') as f:
            json.dump(status, f, indent=2, ensure_ascii=False)

    def _read_status(self) -> Dict[str, Any]:
        """读取当前状态"""
        try:
            with open(self.status_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"preprocess": None, "running": None, "evaluation": None}

    def update_preprocess(self, status: str):
        """
        更新预处理状态

        Args:
            status: 状态值，可选: None/"running"/"done"/"fail"
        """
        current = self._read_status()
        current['preprocess'] = status
        self._write_status(current)

    def update_running(self, status: str):
        """
        更新运行状态

        Args:
            status: 状态值，可选: None/"running"/"done"/"timeout"/"max_turn_exceeded"/"fail"
        """
        current = self._read_status()
        current['running'] = status
        self._write_status(current)

    def update_evaluation(self, status: str):
        """
        更新评估状态

        Args:
            status: 状态值，可选: None/"pass"/"fail"
        """
        current = self._read_status()
        current['evaluation'] = status
        self._write_status(current)

    def get_status(self) -> Dict[str, Any]:
        """获取当前完整状态"""
        return self._read_status()

    def is_completed(self) -> bool:
        """
        检查任务是否完全完成

        Returns:
            True 如果预处理成功 + 运行完成 + 有评估结果
        """
        status = self._read_status()
        return (status.get('preprocess') == 'done' and
                status.get('running') == 'done' and
                status.get('evaluation') is not None)