import asyncio
import argparse
import shortuuid
import os
import json
import signal
import sys
import psutil
import shutil
from utils.general.helper import read_json
import subprocess
from typing import List, Optional, Dict
import time
from datetime import datetime
from pathlib import Path
import random


async def run_command_async(command: str, log_file: str, timeout_seconds: int = 1800, scheduler: 'AsyncTaskScheduler' = None):
    """
    异步执行shell命令，带超时控制和日志记录
    timeout_seconds: 默认30分钟 = 1800秒
    scheduler: 任务调度器，用于进程跟踪
    """
    # 确保日志目录存在
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    try:
        # 创建进程，同时重定向输出到日志文件
        with open(log_file, 'w') as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Command: {command}\n")
            f.write("="*80 + "\n")
            f.flush()

            process = await asyncio.create_subprocess_shell(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # 将stderr重定向到stdout
                preexec_fn=os.setsid  # 创建新的进程组，便于后续清理
            )

            # 如果有调度器，添加到活跃进程集合中
            if scheduler:
                scheduler.active_processes.add(process)
                active_processes.add(process)
            
            # 实时写入日志
            async def write_output():
                while True:
                    line = await process.stdout.readline()
                    if not line:
                        break
                    line_decoded = line.decode('utf-8', errors='ignore')
                    f.write(line_decoded)
                    f.flush()
            
            # 等待进程完成，最多等待timeout_seconds秒
            try:
                await asyncio.wait_for(write_output(), timeout=timeout_seconds)
                await asyncio.wait_for(process.wait(), timeout=5)  # 额外等待进程结束
            except asyncio.TimeoutError:
                raise
            
            f.write(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Process ended with code: {process.returncode}\n")

            # 从活跃进程集合中移除
            if scheduler:
                scheduler.active_processes.discard(process)
            active_processes.discard(process)

            return {
                'success': process.returncode == 0,
                'returncode': process.returncode,
                'log_file': log_file
            }
    
    except asyncio.TimeoutError:
        # 超时时终止进程及其子进程
        try:
            if process.returncode is None:
                # 终止整个进程组
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                await asyncio.sleep(3)  # 给进程组3秒优雅退出
                if process.returncode is None:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)  # 强制杀死进程组
        except:
            pass

        # 从活跃进程集合中移除
        if scheduler:
            scheduler.active_processes.discard(process)
        active_processes.discard(process)

        # 记录超时信息到日志
        with open(log_file, 'a') as f:
            f.write(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] TIMEOUT after {timeout_seconds} seconds\n")

        raise TimeoutError(f"Command timed out after {timeout_seconds} seconds")
    
    except Exception as e:
        # 从活跃进程集合中移除
        if scheduler:
            scheduler.active_processes.discard(process)
        active_processes.discard(process)

        # 记录错误到日志
        with open(log_file, 'a') as f:
            f.write(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: {str(e)}\n")
        raise Exception(f"Command failed with error: {str(e)}")

class TaskResult:
    """任务结果统计"""
    def __init__(self):
        self.not_executed = []  # 未执行成功的任务
        self.passed = []        # pass=true的任务
        self.failed = []        # pass=false的任务
        self.timeout = []       # 超时的任务
        self.error = []         # 执行出错的任务

# 全局进程跟踪器
active_processes = set()

class AsyncTaskScheduler:
    def __init__(self, conflict_groups: Optional[List[List[str]]], max_workers: int):
        self.max_workers = max_workers
        self.conflict_locks = {}  # 任务名到锁的映射
        self.semaphore = asyncio.Semaphore(max_workers)  # 限制并发数

        # 新增：任务队列管理
        self.pending_tasks = asyncio.Queue()  # 待执行任务队列
        self.running_count = 0  # 实际运行中的任务数
        self.waiting_for_lock = set()  # 等待锁的任务

        # 统计信息
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.timeout_tasks = 0
        self.total_tasks = 0
        self.start_time = time.time()

        self.correct_tasks = 0
        self.incorrect_tasks = 0
        self.unknown_but_finished_tasks = 0

        # 任务结果
        self.task_results = TaskResult()

        # 进程跟踪
        self.active_processes = set()  # 跟踪活跃的子进程

        # 添加进程清理方法
        def cleanup_processes():
            """清理所有活跃的子进程"""
            print("\n🧹 Cleaning up active processes...")
            for process in list(self.active_processes):
                try:
                    if process.returncode is None:
                        print(f"  Terminating process {process.pid}...")
                        # 终止整个进程组
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                        # 等待一会儿让进程优雅退出
                        time.sleep(2)
                        if process.returncode is None:
                            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                            print(f"  Force killed process group {process.pid}")
                        else:
                            print(f"  Gracefully terminated process group {process.pid}")
                    self.active_processes.discard(process)
                except Exception as e:
                    print(f"  Error terminating process {process.pid}: {e}")
                    try:
                        process.kill()
                    except:
                        pass
                    self.active_processes.discard(process)

            # 清理全局进程集合
            for process in list(active_processes):
                if process.returncode is None:
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    except:
                        pass
                active_processes.discard(process)

            if self.active_processes or active_processes:
                print(f"  Remaining processes: {len(self.active_processes)} local, {len(active_processes)} global")
            else:
                print("  ✅ All processes cleaned up")

        self.cleanup_processes = cleanup_processes

        # 为冲突组创建锁
        if conflict_groups:
            for group in conflict_groups:
                shared_lock = asyncio.Lock()
                for task_name in group:
                    self.conflict_locks[task_name] = shared_lock

    def get_task_lock(self, task_path: str) -> Optional[asyncio.Lock]:
        """获取任务对应的锁"""
        # 从路径中提取任务名
        task_name = os.path.basename(task_path)
        return self.conflict_locks.get(task_name, None)
    
    async def run_single_task(self, task_dir_arg: str, tag: str, 
                             model_short_name: str, provider: str, 
                             maxstep: str, timeout: int = 1800, eval_config: str = "scripts/foraml_run_v0.json",
                             dump_path: str = "./dumps", image_name: str = "lockon0927/mcpbench-task-image-v2:latest"):
        """改进版：更智能的任务调度"""
        
        conflict_lock = self.get_task_lock(task_dir_arg)
        
        # 如果有冲突锁且锁被占用，不要占用semaphore
        if conflict_lock and conflict_lock.locked():
            # 等待锁，但不占用worker位置
            self.waiting_for_lock.add(task_dir_arg)
            try:
                async with conflict_lock:  # 等待锁释放
                    self.waiting_for_lock.discard(task_dir_arg)
                    async with self.semaphore:  # 获得锁后再占用worker
                        return await self._execute_task(
                            task_dir_arg, tag, model_short_name, 
                            provider, maxstep, timeout, has_lock=True, eval_config=eval_config, dump_path=dump_path, image_name=image_name
                        )
            finally:
                self.waiting_for_lock.discard(task_dir_arg)
        
        elif conflict_lock:
            # 有锁但锁是空闲的，正常执行
            async with conflict_lock:
                async with self.semaphore:
                    return await self._execute_task(
                        task_dir_arg, tag, model_short_name, 
                        provider, maxstep, timeout, has_lock=True, eval_config=eval_config, dump_path=dump_path, image_name=image_name
                    )
        
        else:
            # 无冲突，直接执行
            async with self.semaphore:
                return await self._execute_task(
                    task_dir_arg, tag, model_short_name, 
                    provider, maxstep, timeout, has_lock=False, eval_config=eval_config, dump_path=dump_path, image_name=image_name
                )
    
    def _archive_previous_results(self, dump_path: str, tasks_folder: str, task_name: str):
        """将之前的运行结果归档到 legacy_results"""
        task_result_dir = os.path.join(dump_path, tasks_folder, task_name)

        if not os.path.exists(task_result_dir):
            return  # 没有之前的结果，直接返回

        # 获取目录中所有文件和子目录（除了 legacy_results）
        items_to_archive = []
        try:
            for item in os.listdir(task_result_dir):
                if item != "legacy_results":  # 排除 legacy_results 目录
                    items_to_archive.append(item)
        except OSError:
            return  # 目录读取失败

        if not items_to_archive:
            return  # 没有文件需要归档

        # 如果只有 container.log，直接删除，不进行归档
        if len(items_to_archive) == 1 and items_to_archive[0] == "container.log":
            try:
                container_log_path = os.path.join(task_result_dir, "container.log")
                os.remove(container_log_path)
                print(f"  🗑️ Removed incomplete container.log")
            except Exception as e:
                print(f"  ⚠️ Failed to remove container.log: {e}")
            return

        # 创建 legacy_results 目录
        legacy_dir = os.path.join(task_result_dir, "legacy_results")
        os.makedirs(legacy_dir, exist_ok=True)

        # 找到下一个运行编号
        run_number = 1
        while os.path.exists(os.path.join(legacy_dir, f"run{run_number}")):
            run_number += 1

        # 创建本次归档目录
        archive_dir = os.path.join(legacy_dir, f"run{run_number}")
        os.makedirs(archive_dir, exist_ok=True)

        # 移动所有文件到归档目录
        archived_count = 0
        for item in items_to_archive:
            item_path = os.path.join(task_result_dir, item)
            try:
                archive_path = os.path.join(archive_dir, item)
                shutil.move(item_path, archive_path)
                archived_count += 1
            except Exception as e:
                print(f"  ⚠️ Failed to archive {item}: {e}")

        if archived_count > 0:
            print(f"  📦 Archived {archived_count} items to legacy_results/run{run_number}")

    async def _execute_task(self, task_dir_arg: str, tag: str,
                           model_short_name: str, provider: str,
                           maxstep: str, timeout: int, has_lock: bool, eval_config: str = "scripts/foraml_run_v0.json",
                           dump_path: str = "./dumps", image_name: str = "lockon0927/mcpbench-task-image-v2:latest"):
        """实际执行任务"""
        command = f"bash scripts/run_single_containerized.sh " \
                 f"{task_dir_arg} {tag} {model_short_name} {provider} {maxstep} {eval_config} {dump_path} {image_name}"

        # 构建日志文件路径
        # task_dir_arg 格式: tasks_folder/task
        parts = task_dir_arg.split('/')
        if len(parts) >= 2:
            tasks_folder = parts[0]
            task_name = parts[1]
        else:
            tasks_folder = ""
            task_name = task_dir_arg

        # 归档之前的结果文件
        self._archive_previous_results(dump_path, tasks_folder, task_name)

        # Updated to use container log path in dump_path structure
        log_file = os.path.join(dump_path, tasks_folder, task_name, "container.log")
        
        task_start = datetime.now()
        lock_status = "with lock" if has_lock else "no lock"
        
        print(f"\n🚀 [{task_start.strftime('%H:%M:%S')}] STARTING: {task_dir_arg}")
        print(f"   📝 Log: {log_file}")
        if has_lock:
            print(f"   🔒 Running with conflict lock")
        
        try:
            result = await run_command_async(command, log_file, timeout_seconds=timeout, scheduler=self)
            
            self.completed_tasks += 1
            elapsed = (datetime.now() - task_start).total_seconds()
            
            print(f"\n🔚 [{datetime.now().strftime('%H:%M:%S')}] SUCCESS: {task_dir_arg}")
            print(f"   ⏱️ Time: {elapsed:.1f}s | Progress: {self.completed_tasks}/{self.total_tasks}")
            
            eval_res_file = os.path.join(dump_path, tasks_folder, task_name, "eval_res.json")
            # 如果存在该路径则读出
            eval_res = read_json(eval_res_file).get('pass', False) if os.path.exists(eval_res_file) else None
            
            if eval_res is None: 
                self.unknown_but_finished_tasks += 1
                eval_res_emoji = "❓"
            else: eval_res_emoji = "✅" if eval_res else "❌"
            self.correct_tasks += 1 if eval_res else 0
            self.incorrect_tasks += 1 if not eval_res else 0
            print(f"   🔍 Eval res: {eval_res_emoji} | Eval log: {eval_res_file}")

            return {
                'task': task_dir_arg, 
                'status': 'success', 
                'elapsed': elapsed,
                'log_file': log_file,
                'eval_res_file': eval_res_file,
                'eval_res': eval_res,
                'tag': tag,
                'model_short_name': model_short_name
            }
            
        except TimeoutError as e:
            self.timeout_tasks += 1
            self.failed_tasks += 1
            elapsed = (datetime.now() - task_start).total_seconds()

            # 更新状态为 timeout
            from utils.status_manager import TaskStatusManager
            try:
                status_manager = TaskStatusManager(os.path.join(dump_path, tasks_folder, task_name))
                status_manager.update_running("timeout")
            except Exception:
                pass  # 如果状态更新失败，不影响主要逻辑

            print(f"\n⏰ [{datetime.now().strftime('%H:%M:%S')}] TIMEOUT: {task_dir_arg}")
            print(f"   ⚠️ Killed after {elapsed:.1f}s (limit: {timeout}s) | Progress: {self.completed_tasks + self.failed_tasks}/{self.total_tasks}")

            return {
                'task': task_dir_arg,
                'status': 'timeout',
                'elapsed': elapsed,
                'error': str(e),
                'log_file': log_file,
                'tag': tag,
                'model_short_name': model_short_name
            }
            
        except Exception as e:
            self.failed_tasks += 1
            elapsed = (datetime.now() - task_start).total_seconds()
            
            print(f"\n❌ [{datetime.now().strftime('%H:%M:%S')}] FAILED: {task_dir_arg}")
            print(f"   💥 Error: {str(e)[:100]}...")  # 只显示前100个字符
            print(f"   ⏱️ Time: {elapsed:.1f}s | Progress: {self.completed_tasks + self.failed_tasks}/{self.total_tasks}")
            
            return {
                'task': task_dir_arg, 
                'status': 'failed', 
                'elapsed': elapsed, 
                'error': str(e),
                'log_file': log_file,
                'tag': tag,
                'model_short_name': model_short_name
            }
    
    def print_progress(self):
        """打印进度统计"""
        elapsed_total = time.time() - self.start_time
        print(f"\n{'='*60}")
        print(f"Progress Report:")
        print(f"  Total tasks: {self.total_tasks}")
        print(f"  Completed: {self.completed_tasks}")
        print(f"  Failed: {self.failed_tasks} (including {self.timeout_tasks} timeouts)")
        print(f"  Remaining: {self.total_tasks - self.completed_tasks - self.failed_tasks}")
        print(f"  Correct: {self.correct_tasks}")
        print(f"  Incorrect: {self.incorrect_tasks}")
        print(f"  Unknown but finished: {self.unknown_but_finished_tasks}")
        print(f"  Elapsed time: {elapsed_total:.1f}s")
        print(f"  Max concurrent workers: {self.max_workers}")
        print(f"{'='*60}\n")

def filter_tasks_with_existing_results(all_task_dir_args: List[str], dump_path: str = "dumps") -> tuple[List[str], List[str]]:
    """
    过滤已有完整结果的任务
    优先检查 status.json，如果不存在则回退到原有逻辑
    排除超时和超过轮数限制的任务
    返回 (待执行的任务列表, 已完成的任务列表)
    """
    tasks_to_execute = []
    tasks_already_completed = []

    for task_dir_arg in all_task_dir_args:
        # 解析路径
        parts = task_dir_arg.split('/')
        if len(parts) >= 2:
            tasks_folder = parts[0]
            task_name = parts[1]
        else:
            tasks_folder = ""
            task_name = task_dir_arg

        # 构建文件路径
        task_dir = os.path.join(dump_path, tasks_folder, task_name)
        status_file = os.path.join(task_dir, "status.json")

        # 优先检查 status.json
        if os.path.exists(status_file):
            try:
                with open(status_file, 'r', encoding='utf-8') as f:
                    status_data = json.load(f)

                running_status = status_data.get('running', None)

                # 如果是超时或超过轮数限制，跳过执行（视为已完成）
                if running_status in ['timeout', 'max_turn_exceeded']:
                    tasks_already_completed.append(task_dir_arg)
                    continue

                # 如果预处理成功 + 运行完成 + 有评估结果，则跳过
                if (status_data.get('preprocess') == 'done' and
                    running_status == 'done' and
                    status_data.get('evaluation') is not None):
                    tasks_already_completed.append(task_dir_arg)
                    continue
                else:
                    # 状态不完整，需要重新执行
                    tasks_to_execute.append(task_dir_arg)
                    continue
            except:
                # status.json 读取失败，回退到原有逻辑
                pass

        # 回退到原有逻辑：检查 eval_res.json 和 traj_log.json
        eval_res_path = os.path.join(task_dir, "eval_res.json")
        traj_log_path = os.path.join(task_dir, "traj_log.json")
        run_log_path = os.path.join(task_dir, "run.log")

        # 检查是否是超时或超过轮数限制（原有逻辑）
        if os.path.exists(run_log_path):
            try:
                with open(run_log_path, 'r') as f:
                    run_log_content = f.read()
                if "raise MaxTurnsExceeded(" in run_log_content:
                    # 超过轮数限制，跳过执行
                    tasks_already_completed.append(task_dir_arg)
                    continue
            except:
                pass

        # 检查eval_res.json是否存在
        if not os.path.exists(eval_res_path):
            tasks_to_execute.append(task_dir_arg)
            continue

        # 检查traj_log.json是否存在且状态为success
        if os.path.exists(traj_log_path):
            try:
                with open(traj_log_path, 'r') as f:
                    log_data = json.load(f)
                task_status = log_data.get('status', 'unknown')

                if task_status == 'success':
                    tasks_already_completed.append(task_dir_arg)
                else:
                    # 状态不是success，需要重新执行
                    tasks_to_execute.append(task_dir_arg)
            except (json.JSONDecodeError, Exception):
                # traj_log.json读取失败，需要重新执行
                tasks_to_execute.append(task_dir_arg)
        else:
            # traj_log.json不存在，需要重新执行
            tasks_to_execute.append(task_dir_arg)

    return tasks_to_execute, tasks_already_completed

def analyze_results(all_task_dir_args: List[str], model_short_name: str, tag: str, dump_path: str = "dumps") -> TaskResult:
    """
    分析任务执行结果
    检查 dumps/{task_folder}/{task}/{model_short_name}_{tag}_output/eval_res.json
    """
    result = TaskResult()
    
    for task_dir_arg in all_task_dir_args:
        # 解析路径
        parts = task_dir_arg.split('/')
        if len(parts) >= 2:
            tasks_folder = parts[0]
            task_name = parts[1]
        else:
            tasks_folder = ""
            task_name = task_dir_arg
        
        # 构建输出文件路径 - 现在文件直接在任务目录下，不在{model}_{tag}_output子目录
        eval_res_path = os.path.join(
            dump_path, tasks_folder, task_name, "eval_res.json"
        )
        
        if not os.path.exists(eval_res_path):
            # 文件不存在，任务未执行成功
            result.not_executed.append(task_dir_arg)
            print(f"  ✗ {task_dir_arg}: eval_res.json not found")
        else:
            try:
                # 读取结果文件
                with open(eval_res_path, 'r') as f:
                    eval_data = json.load(f)
                
                # 检查pass字段
                if isinstance(eval_data, dict) and 'pass' in eval_data:
                    if eval_data['pass'] is True:
                        result.passed.append(task_dir_arg)
                        print(f"  ✓ {task_dir_arg}: PASSED")
                    else:
                        result.failed.append(task_dir_arg)
                        print(f"  ✗ {task_dir_arg}: FAILED")
                else:
                    # 格式不正确
                    result.error.append(task_dir_arg)
                    print(f"  ? {task_dir_arg}: Invalid format (no 'pass' field)")
                    
            except json.JSONDecodeError as e:
                result.error.append(task_dir_arg)
                print(f"  ? {task_dir_arg}: JSON decode error - {str(e)}")
            except Exception as e:
                result.error.append(task_dir_arg)
                print(f"  ? {task_dir_arg}: Error reading file - {str(e)}")
    
    return result

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks_folder", required=True)
    parser.add_argument("--tag", required=False, default=None)
    parser.add_argument("--model_short_name", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--maxstep", required=True)
    parser.add_argument("--workers", required=False, default=100, type=int)
    parser.add_argument("--timeout", required=False, default=1800, type=int, 
                       help="Timeout for each task in seconds (default: 1800 = 30 minutes)")
    parser.add_argument("--dump_path", required=False, default=None,
                       help="Custom path to save results (optional)")
    parser.add_argument("--task_list", required=False, default=None,
                       help="Path to task list file to filter tasks (optional, e.g., filtered_tasks.txt)")
    parser.add_argument("--eval_config", required=False, default="scripts/foraml_run_v0.json",
                       help="Path to evaluation config file (default: scripts/foraml_run_v0.json)")
    parser.add_argument("--image_name", required=False, default="lockon0927/mcpbench-task-image-v2:latest",
                       help="Docker image name to use (default: lockon0927/mcpbench-task-image-v2:latest)")
    
    args = parser.parse_args()
    
    # 生成或使用提供的tag
    if args.tag is None:
        tag = shortuuid.uuid()
    else:
        tag = args.tag
    
    # 获取所有任务目录
    full_tasks_folder = os.path.join('tasks', args.tasks_folder)
    all_tasks = sorted(os.listdir(full_tasks_folder))  # 排序以保证顺序一致
    all_task_dir_args = [f"{args.tasks_folder}/{task}" for task in all_tasks 
                         if os.path.isdir(os.path.join(full_tasks_folder, task))]
    
    # 如果提供了任务列表文件，则过滤任务
    if args.task_list:
        if not os.path.exists(args.task_list):
            print(f"Error: Task list file '{args.task_list}' not found!")
            return
        
        # 读取任务列表文件
        try:
            with open(args.task_list, 'r', encoding='utf-8') as f:
                task_names = []
                for line in f:
                    line = line.strip()
                    # 跳过空行和注释行（以#开头）
                    if line and not line.startswith('#'):
                        task_names.append(line)
            
            # 过滤任务目录参数，只保留列表中的任务
            filtered_task_dir_args = []
            for task_dir_arg in all_task_dir_args:
                task_name = task_dir_arg.split('/')[-1]  # 获取任务名称
                if task_name in task_names:
                    filtered_task_dir_args.append(task_dir_arg)
            
            all_task_dir_args = filtered_task_dir_args
            print(f"Filtered to {len(all_task_dir_args)} tasks from task list: {args.task_list}")
            
        except Exception as e:
            print(f"Error reading task list file '{args.task_list}': {e}")
            return
    
    if not all_task_dir_args:
        print("No tasks found!")
        return

    # 使用dump_path参数，如果没有提供则使用默认值
    dump_path = args.dump_path if args.dump_path else "dumps"

    # 过滤已有eval_res.json的任务
    tasks_to_execute, tasks_already_completed = filter_tasks_with_existing_results(all_task_dir_args, dump_path)

    # 显示过滤结果
    print(f"\n{'='*60}")
    print(f"TASK FILTERING RESULTS")
    print(f"{'='*60}")
    print(f"  Original tasks: {len(all_task_dir_args)}")
    print(f"  Tasks with successful completion (SKIP): {len(tasks_already_completed)}")
    print(f"  Tasks to execute: {len(tasks_to_execute)}")

    if tasks_already_completed:
        print(f"\n📋 Tasks being SKIPPED (have eval_res.json + traj_log.json with status='success'):")
        for task in tasks_already_completed:
            eval_path = os.path.join(dump_path, *task.split('/'), "eval_res.json")
            traj_path = os.path.join(dump_path, *task.split('/'), "traj_log.json")
            print(f"  ✓ {task}")

    if tasks_to_execute:
        print(f"\n🚀 Tasks to be EXECUTED:")
        for task in tasks_to_execute:
            task_dir = os.path.join(dump_path, *task.split('/'))
            eval_path = os.path.join(task_dir, "eval_res.json")
            traj_path = os.path.join(task_dir, "traj_log.json")

            reason = ""
            if not os.path.exists(eval_path):
                reason = "missing eval_res.json"
            elif not os.path.exists(traj_path):
                reason = "missing traj_log.json"
            else:
                try:
                    with open(traj_path, 'r') as f:
                        log_data = json.load(f)
                    status = log_data.get('status', 'unknown')
                    reason = f"traj_log.json status='{status}' (not 'success')"
                except:
                    reason = "invalid traj_log.json"

            print(f"  ○ {task} ({reason})")
    else:
        print(f"\n🎉 All tasks already completed! Nothing to execute.")
        return
    print(f"{'='*60}\n")

    # 更新任务列表为需要执行的任务
    all_task_dir_args = tasks_to_execute

    print(f"Shuffling tasks...")
    random.shuffle(all_task_dir_args)
    
    # 读取任务冲突信息
    task_conflict_info = None
    config_path = os.path.join(full_tasks_folder, "task_conflict.json")
    if os.path.exists(config_path):
        try:
            config = read_json(config_path)
            # 假设冲突信息存储在 'conflict_groups' 字段
            task_conflict_info = config.get('conflict_groups', None)
        except Exception as e:
            print(f"Warning: Could not read task config: {e}")
    
    # 打印启动信息
    print(f"\n{'='*60}")
    print(f"Task Execution Starting")
    print(f"  Tasks folder: {args.tasks_folder}")
    print(f"  Total tasks: {len(all_task_dir_args)}")
    print(f"  Tag: {tag}")
    print(f"  Model: {args.model_short_name}")
    print(f"  Provider: {args.provider}")
    print(f"  Max steps: {args.maxstep}")
    print(f"  Max concurrent workers: {args.workers}")
    print(f"  Timeout per task: {args.timeout}s ({args.timeout/60:.1f} minutes)")
    if args.dump_path:
        print(f"  Custom dump path: {args.dump_path}")
    else:
        print(f"  Default dump path: ./results")
    if args.task_list:
        print(f"  Task list filter: {args.task_list}")
    else:
        print(f"  Task list filter: None (all tasks)")
    print(f"  Eval config: {args.eval_config}")
    print(f"  Docker image: {args.image_name}")
    
    if task_conflict_info:
        print(f"  Conflict groups: {len(task_conflict_info)} groups")
        for i, group in enumerate(task_conflict_info):
            print(f"    Group {i+1}: {group}")
    else:
        print(f"  No conflict groups defined")
    print(f"{'='*60}\n")
    
    # 创建调度器并运行任务
    scheduler = AsyncTaskScheduler(task_conflict_info, args.workers)
    scheduler.total_tasks = len(all_task_dir_args)
    
    # 创建所有任务
    tasks = [
        scheduler.run_single_task(
            task_dir_arg, tag, args.model_short_name, 
            args.provider, args.maxstep, args.timeout, args.eval_config, args.dump_path, args.image_name
        )
        for task_dir_arg in all_task_dir_args
    ]
    
    # 定期打印进度的任务
    async def progress_reporter():
        while scheduler.completed_tasks + scheduler.failed_tasks < scheduler.total_tasks:
            await asyncio.sleep(60)  # 每60秒报告一次进度
            scheduler.print_progress()
    
    # 启动进度报告器
    progress_task = asyncio.create_task(progress_reporter())
    
    # 运行所有任务
    print("Starting task execution...\n")
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 取消进度报告器
    progress_task.cancel()
    try:
        await progress_task
    except asyncio.CancelledError:
        pass
    
    # 最终统计
    print(f"\n{'='*60}")
    print(f"EXECUTION COMPLETE!")
    scheduler.print_progress()

    # 程序结束时的清理
    if hasattr(scheduler, 'cleanup_processes'):
        scheduler.cleanup_processes()
    
    # 打印失败的任务详情
    failed_tasks = [r for r in results if isinstance(r, dict) and r.get('status') != 'success']
    if failed_tasks:
        print(f"\nExecution Failed Tasks ({len(failed_tasks)}):")
        for task in failed_tasks:
            print(f"  - {task['task']}: {task.get('status', 'unknown')} - {task.get('error', 'N/A')}")
    
    print(f"{'='*60}\n")
    
    # 分析任务结果
    print(f"{'='*60}")
    print(f"ANALYZING RESULTS FROM OUTPUT FILES")
    print(f"{'='*60}")
    print(f"Checking eval_res.json files in {args.dump_path}/{args.tasks_folder}/*/\n")
    
    task_result = analyze_results(all_task_dir_args, args.model_short_name, tag, args.dump_path)
    
    # 打印最终统计
    print(f"\n{'='*60}")
    print(f"FINAL RESULTS SUMMARY")
    print(f"{'='*60}")
    
    total_tasks = len(all_task_dir_args)
    passed_count = len(task_result.passed)
    failed_count = len(task_result.failed)
    not_executed_count = len(task_result.not_executed)
    error_count = len(task_result.error)
    
    print(f"\nTask Statistics:")
    print(f"  Total tasks:        {total_tasks}")
    print(f"  ✓ Passed:          {passed_count}")
    print(f"  ✗ Failed:          {failed_count}")
    print(f"  ⚠ Not executed:    {not_executed_count}")
    print(f"  ? Error/Invalid:   {error_count}")
    
    print(f"\nSuccess Rates:")
    # true/all (通过数/总任务数)
    if total_tasks > 0:
        pass_rate_all = (passed_count / total_tasks) * 100
        print(f"  Pass rate (true/all):              {passed_count}/{total_tasks} = {pass_rate_all:.2f}%")
    else:
        print(f"  Pass rate (true/all):              N/A (no tasks)")
    
    # true/(true+false) (通过数/有效执行数)
    valid_executed = passed_count + failed_count
    if valid_executed > 0:
        pass_rate_executed = (passed_count / valid_executed) * 100
        print(f"  Pass rate (true/(true+false)):    {passed_count}/{valid_executed} = {pass_rate_executed:.2f}%")
    else:
        print(f"  Pass rate (true/(true+false)):    N/A (no valid executions)")
    
    # 详细列表（可选）
    if not_executed_count > 0:
        print(f"\n⚠ Not Executed Tasks ({not_executed_count}):")
        for task in task_result.not_executed[:10]:  # 只显示前10个
            print(f"    - {task}")
        if not_executed_count > 10:
            print(f"    ... and {not_executed_count - 10} more")
    
    if error_count > 0:
        print(f"\n? Error/Invalid Tasks ({error_count}):")
        for task in task_result.error[:10]:  # 只显示前10个
            print(f"    - {task}")
        if error_count > 10:
            print(f"    ... and {error_count - 10} more")
    
    if failed_count > 0 and failed_count <= 20:  # 如果失败数较少，显示所有
        print(f"\n✗ Failed Tasks ({failed_count}):")
        for task in task_result.failed:
            print(f"    - {task}")
    
    # 生成结果报告文件
    if args.dump_path:
        # 使用自定义保存路径
        results_dir = args.dump_path
    else:
        # 使用默认路径
        results_dir = "./results"
    
    report_file = f"{results_dir}/execution_report_{args.tasks_folder}_{args.model_short_name}_{tag}.json"
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    report_data = {
        "execution_time": datetime.now().isoformat(),
        "configuration": {
            "tasks_folder": args.tasks_folder,
            "model_short_name": args.model_short_name,
            "provider": args.provider,
            "maxstep": args.maxstep,
            "workers": args.workers,
            "timeout": args.timeout,
            "tag": tag
        },
        "summary": {
            "total_tasks": total_tasks,
            "passed": passed_count,
            "failed": failed_count,
            "not_executed": not_executed_count,
            "error": error_count,
            "pass_rate_all": f"{passed_count}/{total_tasks}" if total_tasks > 0 else "N/A",
            "pass_rate_all_percent": pass_rate_all if total_tasks > 0 else None,
            "pass_rate_executed": f"{passed_count}/{valid_executed}" if valid_executed > 0 else "N/A",
            "pass_rate_executed_percent": pass_rate_executed if valid_executed > 0 else None
        },
        "details": {
            "passed_tasks": task_result.passed,
            "failed_tasks": task_result.failed,
            "not_executed_tasks": task_result.not_executed,
            "error_tasks": task_result.error
        }
    }
    
    try:
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        print(f"\n📊 Detailed report saved to: {report_file}")
    except Exception as e:
        print(f"\n⚠ Could not save report file: {e}")
    
    print(f"\n{'='*60}")
    print("EXECUTION FINISHED")
    print(f"{'='*60}\n")

def sync_cleanup_processes():
    """同步清理所有活跃进程（用于信号处理器）"""
    print("\n🧹 Emergency cleanup of all active processes...")
    processes_to_cleanup = list(active_processes)

    if not processes_to_cleanup:
        print("  No active processes to clean up")
        return

    for process in processes_to_cleanup:
        try:
            if process.returncode is None:
                print(f"  Force terminating process {process.pid}...")
                # 直接使用 SIGKILL 强制终止整个进程组
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    print(f"  ✅ Killed process group {process.pid}")
                except:
                    # 如果进程组终止失败，尝试终止单个进程
                    process.kill()
                    print(f"  ✅ Killed process {process.pid}")
        except Exception as e:
            print(f"  Error terminating process {process.pid}: {e}")

    active_processes.clear()
    print("  ✅ Emergency cleanup completed")

async def async_cleanup_processes():
    """异步清理所有活跃进程"""
    print("\n🧹 Cleaning up all active processes...")
    processes_to_cleanup = list(active_processes)

    if not processes_to_cleanup:
        print("  No active processes to clean up")
        return

    # 并行终止所有进程
    cleanup_tasks = []
    for process in processes_to_cleanup:
        task = asyncio.create_task(cleanup_single_process(process))
        cleanup_tasks.append(task)

    # 等待所有清理任务完成
    await asyncio.gather(*cleanup_tasks, return_exceptions=True)
    active_processes.clear()
    print("  ✅ All processes cleaned up")

async def cleanup_single_process(process):
    """清理单个进程"""
    try:
        if process.returncode is None:
            print(f"  Terminating process group {process.pid}...")
            # 终止整个进程组
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            # 等待一会儿让进程优雅退出
            await asyncio.sleep(1)  # 减少等待时间
            if process.returncode is None:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                print(f"  Force killed process group {process.pid}")
            else:
                print(f"  Gracefully terminated process group {process.pid}")
    except Exception as e:
        print(f"  Error terminating process {process.pid}: {e}")
        try:
            process.kill()
        except:
            pass

async def main_with_signal_handling():
    """主函数，包含信号处理"""
    # 设置信号处理
    loop = asyncio.get_running_loop()

    def handle_sigint():
        print("\n🛑 SIGINT received, performing emergency cleanup...")
        sync_cleanup_processes()
        # 强制退出
        os._exit(1)

    def handle_sigterm():
        print("\n🛑 SIGTERM received, performing emergency cleanup...")
        sync_cleanup_processes()
        # 强制退出
        os._exit(1)

    # 在 asyncio 事件循环中处理信号
    loop.add_signal_handler(signal.SIGINT, handle_sigint)
    loop.add_signal_handler(signal.SIGTERM, handle_sigterm)

    try:
        await main()
    except KeyboardInterrupt:
        print("\n🛑 KeyboardInterrupt in main...")
        sync_cleanup_processes()
    except Exception as e:
        print(f"\n⚠ Exception in main: {e}")
        sync_cleanup_processes()
    finally:
        # 正常退出时的异步清理
        await async_cleanup_processes()

if __name__ == "__main__":
    # 运行带有信号处理的主程序
    asyncio.run(main_with_signal_handling())