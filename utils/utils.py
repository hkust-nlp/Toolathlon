import os
import logging
import json
from typing import List, Dict
import filelock

def setup_logger(name='code_agent', log_path=None, level=logging.INFO):
    # 创建 logger 对象
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    logger.propagate = False  # 添加这一行
    logger.handlers = []
    
    # 创建格式器
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    if log_path is None:
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        # 将处理器添加到 logger
        logger.addHandler(console_handler)
    else:
        if not os.path.exists(os.path.dirname(log_path)):
            os.makedirs(os.path.dirname(log_path), exist_ok=True)

        # 创建文件处理器
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        # 将处理器添加到 logger
        logger.addHandler(file_handler)

    return logger

def load_jsonl(file_path):
    data = []
    with open(file_path, 'r') as f:
        for line in f:
            data.append(json.loads(line))
    return data

def load_json(file_path):
    with open(file_path, 'r') as fr:
        return json.load(fr)

def save_json(data, file_path):
    with open(file_path, 'w') as fw:
        json.dump(data, fw)

def save_jsonl(data, file_path, mode="w"):
    with open(file_path, mode) as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

def save_jsonl_with_lock(data: List[Dict[str, any]], path: str, mode: str='a'):
    _lock  = filelock.FileLock(path + ".lock")
    with _lock:
        with open(path, mode) as fw:
            for item in data:
                fw.write(json.dumps(item) + "\n")

def load_jsonl_with_lock(path: str, verbose: bool=False) -> List[Dict[str, any]]:
    _lock  = filelock.FileLock(path + ".lock")
    with _lock:
        with open(path, 'r') as fr:
            data = [json.loads(line.strip()) for line in fr]
        if verbose:
            print(f">>> Load(w/lock) {len(data)} items from {path} ...")
    return data

import aiofiles
import asyncio

class AsyncFileWriter:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.tasks: Dict[str, asyncio.Task] = {}

    async def write(self, file_path: str, file_content: str):
        async with self.lock:
            if file_path in self.tasks and not self.tasks[file_path].done():
                self.tasks[file_path].cancel()
                try:
                    await self.tasks[file_path]
                except asyncio.CancelledError:
                    pass
            self.tasks[file_path] = asyncio.create_task(self._write_async(file_path, file_content))
            self.tasks[file_path].add_done_callback(
                lambda t, path=file_path: self._cleanup_task(path)
            )

    def _cleanup_task(self, file_path: str):
        """Remove completed task from the tasks dictionary."""
        if file_path in self.tasks and self.tasks[file_path].done():
            del self.tasks[file_path]

    async def _write_async(self, file_path: str, file_content: str):
        try:
            async with aiofiles.open(file_path, 'w') as fw:
                await fw.write(file_content)
        except Exception as e:
            print(f"Error writing to {file_path}: {e}")
            raise
    
    async def flush(self):
        """Wait for all pending write operations to complete."""
        async with self.lock:
            pending_tasks = list(self.tasks.values())
        
        # Wait outside of the lock to avoid blocking new writes
        for task in pending_tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"Error during flush: {e}")

