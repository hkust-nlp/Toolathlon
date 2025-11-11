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
    Asynchronously execute a shell command with timeout and log output.
    timeout_seconds: default 1800 seconds (30 min)
    scheduler: AsyncTaskScheduler instance for process tracking (may be None)
    """
    # Ensure log directory exists
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    try:
        # Start subprocess and redirect output to log file
        with open(log_file, 'w') as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Command: {command}\n")
            f.write("="*80 + "\n")
            f.flush()

            process = await asyncio.create_subprocess_shell(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Redirect stderr to stdout
                preexec_fn=os.setsid  # Start new process group for easier process cleanup
            )

            # Add process to active set
            if scheduler:
                scheduler.active_processes.add(process)
            active_processes.add(process)
            
            # Stream output to log file
            async def write_output():
                while True:
                    line = await process.stdout.readline()
                    if not line:
                        break
                    line_decoded = line.decode('utf-8', errors='ignore')
                    f.write(line_decoded)
                    f.flush()
            
            # Wait for process (and output streaming) to complete, up to timeout
            try:
                await asyncio.wait_for(write_output(), timeout=timeout_seconds)
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                raise
            
            f.write(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Process ended with code: {process.returncode}\n")

            # Remove from active set(s)
            if scheduler:
                scheduler.active_processes.discard(process)
            active_processes.discard(process)

            return {
                'success': process.returncode == 0,
                'returncode': process.returncode,
                'log_file': log_file
            }
    
    except asyncio.TimeoutError:
        # Kill process group on timeout
        try:
            if process.returncode is None:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                await asyncio.sleep(3)  # Graceful shutdown
                if process.returncode is None:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except:
            pass

        if scheduler:
            scheduler.active_processes.discard(process)
        active_processes.discard(process)

        with open(log_file, 'a') as f:
            f.write(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] TIMEOUT after {timeout_seconds} seconds\n")

        raise TimeoutError(f"Command timed out after {timeout_seconds} seconds")
    
    except Exception as e:
        if scheduler:
            scheduler.active_processes.discard(process)
        active_processes.discard(process)

        with open(log_file, 'a') as f:
            f.write(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: {str(e)}\n")
        raise Exception(f"Command failed with error: {str(e)}")

class TaskResult:
    """Task result summary/statistics"""
    def __init__(self):
        self.not_executed = []  # Tasks that were not successfully executed (no eval_res.json)
        self.passed = []        # Tasks with pass == True
        self.failed = []        # Tasks with pass == False
        self.timeout = []       # Tasks timed out (not fully used)
        self.error = []         # Tasks with result file error

# Global set to track active processes
active_processes = set()

class AsyncTaskScheduler:
    def __init__(self, conflict_groups: Optional[List[List[str]]], max_workers: int):
        self.max_workers = max_workers
        self.conflict_locks = {}  # Mapping from task name to lock
        self.semaphore = asyncio.Semaphore(max_workers)  # Concurrency limit

        # Task queue and bookkeeping
        self.pending_tasks = asyncio.Queue()  # Not used much here
        self.running_count = 0
        self.waiting_for_lock = set()

        # Progress tracking
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.timeout_tasks = 0
        self.total_tasks = 0
        self.start_time = time.time()

        self.correct_tasks = 0
        self.incorrect_tasks = 0
        self.unknown_but_finished_tasks = 0

        # Result tracking
        self.task_results = TaskResult()

        # Subprocess tracking
        self.active_processes = set()

        # Add cleanup method
        def cleanup_processes():
            """Clean up all active subprocesses (local and global)"""
            print("\n🧹 Cleaning up active processes...")
            for process in list(self.active_processes):
                try:
                    if process.returncode is None:
                        print(f"  Terminating process {process.pid}...")
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
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

        # Create locks for conflict groups
        if conflict_groups:
            for group in conflict_groups:
                shared_lock = asyncio.Lock()
                for task_name in group:
                    self.conflict_locks[task_name] = shared_lock

    def get_task_lock(self, task_path: str) -> Optional[asyncio.Lock]:
        """Get the lock object corresponding to a task name, based on path."""
        task_name = os.path.basename(task_path)
        return self.conflict_locks.get(task_name, None)
    
    async def run_single_task(self, task_dir_arg: str, tag: str, 
                             model_short_name: str, provider: str, 
                             maxstep: str, timeout: int = 1800, eval_config: str = "scripts/formal_run_v0.json",
                             dump_path: str = "./dumps", image_name: str = "lockon0927/toolathlon-task-image:1016beta"):
        """Run a single task with proper conflict lock and semaphore management."""
        
        conflict_lock = self.get_task_lock(task_dir_arg)
        
        if conflict_lock and conflict_lock.locked():
            # Wait for lock but don't take up a worker slot
            self.waiting_for_lock.add(task_dir_arg)
            try:
                async with conflict_lock:
                    self.waiting_for_lock.discard(task_dir_arg)
                    async with self.semaphore:
                        return await self._execute_task(
                            task_dir_arg, tag, model_short_name, 
                            provider, maxstep, timeout, has_lock=True, eval_config=eval_config, dump_path=dump_path, image_name=image_name
                        )
            finally:
                self.waiting_for_lock.discard(task_dir_arg)
        
        elif conflict_lock:
            # Lock available, run with lock and semaphore
            async with conflict_lock:
                async with self.semaphore:
                    return await self._execute_task(
                        task_dir_arg, tag, model_short_name, 
                        provider, maxstep, timeout, has_lock=True, eval_config=eval_config, dump_path=dump_path, image_name=image_name
                    )
        
        else:
            # No locking required, just use semaphore
            async with self.semaphore:
                return await self._execute_task(
                    task_dir_arg, tag, model_short_name, 
                    provider, maxstep, timeout, has_lock=False, eval_config=eval_config, dump_path=dump_path, image_name=image_name
                )
    
    def _archive_previous_results(self, dump_path: str, tasks_folder: str, task_name: str):
        """Move previous execution results under legacy_results/ if any exist."""
        task_result_dir = os.path.join(dump_path, tasks_folder, task_name)

        if not os.path.exists(task_result_dir):
            return

        items_to_archive = []
        try:
            for item in os.listdir(task_result_dir):
                if item != "legacy_results":
                    items_to_archive.append(item)
        except OSError:
            return

        if not items_to_archive:
            return

        # If only container.log exists, just delete it
        if len(items_to_archive) == 1 and items_to_archive[0] == "container.log":
            try:
                container_log_path = os.path.join(task_result_dir, "container.log")
                os.remove(container_log_path)
                print(f"  🗑️ Removed incomplete container.log")
            except Exception as e:
                print(f"  ⚠️ Failed to remove container.log: {e}")
            return

        legacy_dir = os.path.join(task_result_dir, "legacy_results")
        os.makedirs(legacy_dir, exist_ok=True)

        run_number = 1
        while os.path.exists(os.path.join(legacy_dir, f"run{run_number}")):
            run_number += 1

        archive_dir = os.path.join(legacy_dir, f"run{run_number}")
        os.makedirs(archive_dir, exist_ok=True)

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
                           maxstep: str, timeout: int, has_lock: bool, eval_config: str = "scripts/formal_run_v0.json",
                           dump_path: str = "./dumps", image_name: str = "lockon0927/toolathlon-task-image:1016beta"):
        """Actually run the task and collect result info."""
        command = f"bash scripts/run_single_containerized.sh {task_dir_arg} {tag} {dump_path} {model_short_name} {provider} {maxstep} {eval_config} {image_name}"

        parts = task_dir_arg.split('/')
        if len(parts) >= 2:
            tasks_folder = parts[0]
            task_name = parts[1]
        else:
            tasks_folder = ""
            task_name = task_dir_arg

        self._archive_previous_results(dump_path, tasks_folder, task_name)

        log_file = os.path.join(dump_path, tasks_folder, task_name, "run.log")
        container_log_file = os.path.join(dump_path, tasks_folder, task_name, "container.log")
        
        task_start = datetime.now()
        
        print(f"\n🚀 [{task_start.strftime('%H:%M:%S')}] STARTING: {task_dir_arg}")
        print(f"   📝 Log: {log_file}\n     Container log: {container_log_file}")
        if has_lock:
            print(f"   🔒 Running with conflict lock")
        
        try:
            result = await run_command_async(command, log_file, timeout_seconds=timeout, scheduler=self)
            
            self.completed_tasks += 1
            elapsed = (datetime.now() - task_start).total_seconds()
            
            print(f"\n🔚 [{datetime.now().strftime('%H:%M:%S')}] SUCCESS: {task_dir_arg}")
            print(f"   ⏱️ Time: {elapsed:.1f}s | Progress: {self.completed_tasks}/{self.total_tasks}")
            
            eval_res_file = os.path.join(dump_path, tasks_folder, task_name, "eval_res.json")
            eval_res = read_json(eval_res_file).get('pass', False) if os.path.exists(eval_res_file) else None
            
            if eval_res is None: 
                self.unknown_but_finished_tasks += 1
                eval_res_emoji = "❓"
            else:
                eval_res_emoji = "✅" if eval_res else "❌"
            self.correct_tasks += 1 if eval_res else 0
            self.incorrect_tasks += 1 if not eval_res else 0
            print(f"   🔍 Eval res: {eval_res_emoji}\n     Eval log: {eval_res_file}\n     Run log: {log_file}")

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

            from utils.status_manager import TaskStatusManager
            try:
                status_manager = TaskStatusManager(os.path.join(dump_path, tasks_folder, task_name))
                status_manager.update_running("timeout")
            except Exception:
                pass

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
            print(f"   💥 Error: {str(e)[:100]}...")
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
        """Print progress summary."""
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
    Filter out tasks that already have valid results.
    Prefer status.json if exists; fallback to original logic if not.
    Exclude tasks that timed out or exceeded max turns (considered completed).
    Returns: (task_to_execute_list, completed_task_list)
    """
    tasks_to_execute = []
    tasks_already_completed = []

    for task_dir_arg in all_task_dir_args:
        # Parse folder and name
        parts = task_dir_arg.split('/')
        if len(parts) >= 2:
            tasks_folder = parts[0]
            task_name = parts[1]
        else:
            tasks_folder = ""
            task_name = task_dir_arg

        task_dir = os.path.join(dump_path, tasks_folder, task_name)
        status_file = os.path.join(task_dir, "status.json")

        # Prefer status.json
        if os.path.exists(status_file):
            try:
                with open(status_file, 'r', encoding='utf-8') as f:
                    status_data = json.load(f)
                running_status = status_data.get('running', None)
                if running_status in ['timeout', 'max_turn_exceeded']:
                    tasks_already_completed.append(task_dir_arg)
                    continue
                if (status_data.get('preprocess') == 'done' and
                    running_status == 'done' and
                    status_data.get('evaluation') is not None):
                    tasks_already_completed.append(task_dir_arg)
                    continue
                else:
                    tasks_to_execute.append(task_dir_arg)
                    continue
            except:
                pass  # Malformed, fallback to next method

        # Fallback: check eval_res.json and traj_log.json
        eval_res_path = os.path.join(task_dir, "eval_res.json")
        traj_log_path = os.path.join(task_dir, "traj_log.json")
        run_log_path = os.path.join(task_dir, "run.log")

        # Check for max turn exceeded using run.log
        if os.path.exists(run_log_path):
            try:
                with open(run_log_path, 'r') as f:
                    run_log_content = f.read()
                if "raise MaxTurnsExceeded(" in run_log_content:
                    tasks_already_completed.append(task_dir_arg)
                    continue
            except:
                pass

        # Require eval_res.json
        if not os.path.exists(eval_res_path):
            tasks_to_execute.append(task_dir_arg)
            continue

        # Require valid traj_log.json (status must be "success")
        if os.path.exists(traj_log_path):
            try:
                with open(traj_log_path, 'r') as f:
                    log_data = json.load(f)
                task_status = log_data.get('status', 'unknown')
                if task_status == 'success':
                    tasks_already_completed.append(task_dir_arg)
                else:
                    tasks_to_execute.append(task_dir_arg)
            except Exception:
                tasks_to_execute.append(task_dir_arg)
        else:
            tasks_to_execute.append(task_dir_arg)

    return tasks_to_execute, tasks_already_completed

def analyze_results(all_task_dir_args: List[str], model_short_name: str, tag: str, dump_path: str = "dumps") -> TaskResult:
    """
    Analyze result files and summarize final pass/fail count.
    Checks {dump_path}/{task_folder}/{task}/eval_res.json
    """
    result = TaskResult()
    
    for task_dir_arg in all_task_dir_args:
        parts = task_dir_arg.split('/')
        if len(parts) >= 2:
            tasks_folder = parts[0]
            task_name = parts[1]
        else:
            tasks_folder = ""
            task_name = task_dir_arg
        
        eval_res_path = os.path.join(
            dump_path, tasks_folder, task_name, "eval_res.json"
        )
        
        if not os.path.exists(eval_res_path):
            result.not_executed.append(task_dir_arg)
            print(f"  ✗ {task_dir_arg}: eval_res.json not found")
        else:
            try:
                with open(eval_res_path, 'r') as f:
                    eval_data = json.load(f)
                if isinstance(eval_data, dict) and 'pass' in eval_data:
                    if eval_data['pass'] is True:
                        result.passed.append(task_dir_arg)
                        print(f"  ✓ {task_dir_arg}: PASSED")
                    else:
                        result.failed.append(task_dir_arg)
                        print(f"  ✗ {task_dir_arg}: FAILED")
                else:
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
    parser.add_argument("--eval_config", required=False, default="scripts/formal_run_v0.json",
                       help="Path to evaluation config file (default: scripts/formal_run_v0.json)")
    parser.add_argument("--image_name", required=False, default="lockon0927/toolathlon-task-image:1016beta",
                       help="Docker image name to use (default: lockon0927/toolathlon-task-image:1016beta)")
    
    args = parser.parse_args()
    
    # Generate tag or use provided
    if args.tag is None:
        tag = shortuuid.uuid()
    else:
        tag = args.tag
    
    # List tasks in the tasks folder
    full_tasks_folder = os.path.join('tasks', args.tasks_folder)
    all_tasks = sorted(os.listdir(full_tasks_folder))
    all_task_dir_args = [f"{args.tasks_folder}/{task}" for task in all_tasks 
                         if os.path.isdir(os.path.join(full_tasks_folder, task))]
    
    # Task list file filter
    if args.task_list:
        if not os.path.exists(args.task_list):
            print(f"Error: Task list file '{args.task_list}' not found!")
            return
        
        try:
            with open(args.task_list, 'r', encoding='utf-8') as f:
                task_names = []
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        task_names.append(line)
            
            filtered_task_dir_args = []
            for task_dir_arg in all_task_dir_args:
                task_name = task_dir_arg.split('/')[-1]
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

    dump_path = args.dump_path if args.dump_path else "dumps"

    tasks_to_execute, tasks_already_completed = filter_tasks_with_existing_results(all_task_dir_args, dump_path)

    # Show filter results
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

    # Update all_task_dir_args for execution
    all_task_dir_args = tasks_to_execute

    print(f"Shuffling tasks...")
    random.shuffle(all_task_dir_args)
    
    # Read potential task conflict info
    task_conflict_info = None
    config_path = os.path.join(full_tasks_folder, "task_conflict.json")
    if os.path.exists(config_path):
        try:
            config = read_json(config_path)
            task_conflict_info = config.get('conflict_groups', None)
        except Exception as e:
            print(f"Warning: Could not read task config: {e}")
    
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
    
    scheduler = AsyncTaskScheduler(task_conflict_info, args.workers)
    scheduler.total_tasks = len(all_task_dir_args)
    
    tasks = [
        scheduler.run_single_task(
            task_dir_arg, tag, args.model_short_name, 
            args.provider, args.maxstep, args.timeout, args.eval_config, args.dump_path, args.image_name
        )
        for task_dir_arg in all_task_dir_args
    ]
    
    async def progress_reporter():
        while scheduler.completed_tasks + scheduler.failed_tasks < scheduler.total_tasks:
            await asyncio.sleep(60)  # Report every 60s
            scheduler.print_progress()
    
    progress_task = asyncio.create_task(progress_reporter())
    
    print("Starting task execution...\n")
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    progress_task.cancel()
    try:
        await progress_task
    except asyncio.CancelledError:
        pass
    
    print(f"\n{'='*60}")
    print(f"EXECUTION COMPLETE!")
    scheduler.print_progress()

    if hasattr(scheduler, 'cleanup_processes'):
        scheduler.cleanup_processes()
    
    failed_tasks = [r for r in results if isinstance(r, dict) and r.get('status') != 'success']
    if failed_tasks:
        print(f"\nExecution Failed Tasks ({len(failed_tasks)}):")
        for task in failed_tasks:
            print(f"  - {task['task']}: {task.get('status', 'unknown')} - {task.get('error', 'N/A')}")
    
    print(f"{'='*60}\n")
    
    print(f"{'='*60}")
    print(f"ANALYZING RESULTS FROM OUTPUT FILES")
    print(f"{'='*60}")
    print(f"Checking eval_res.json files in {args.dump_path}/{args.tasks_folder}/*/\n")
    
    task_result = analyze_results(all_task_dir_args, args.model_short_name, tag, args.dump_path)
    
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
    if total_tasks > 0:
        pass_rate_all = (passed_count / total_tasks) * 100
        print(f"  Pass rate (true/all):              {passed_count}/{total_tasks} = {pass_rate_all:.2f}%")
    else:
        print(f"  Pass rate (true/all):              N/A (no tasks)")
    
    valid_executed = passed_count + failed_count
    if valid_executed > 0:
        pass_rate_executed = (passed_count / valid_executed) * 100
        print(f"  Pass rate (true/(true+false)):    {passed_count}/{valid_executed} = {pass_rate_executed:.2f}%")
    else:
        print(f"  Pass rate (true/(true+false)):    N/A (no valid executions)")
    
    if not_executed_count > 0:
        print(f"\n⚠ Not Executed Tasks ({not_executed_count}):")
        for task in task_result.not_executed[:10]:
            print(f"    - {task}")
        if not_executed_count > 10:
            print(f"    ... and {not_executed_count - 10} more")
    
    if error_count > 0:
        print(f"\n? Error/Invalid Tasks ({error_count}):")
        for task in task_result.error[:10]:
            print(f"    - {task}")
        if error_count > 10:
            print(f"    ... and {error_count - 10} more")
    
    if failed_count > 0 and failed_count <= 20:
        print(f"\n✗ Failed Tasks ({failed_count}):")
        for task in task_result.failed:
            print(f"    - {task}")
    
    if args.dump_path:
        results_dir = args.dump_path
    else:
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
    """Synchronous emergency cleanup of all active processes (for signal handler)."""
    print("\n🧹 Emergency cleanup of all active processes...")
    processes_to_cleanup = list(active_processes)

    if not processes_to_cleanup:
        print("  No active processes to clean up")
        return

    for process in processes_to_cleanup:
        try:
            if process.returncode is None:
                print(f"  Force terminating process {process.pid}...")
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    print(f"  ✅ Killed process group {process.pid}")
                except:
                    process.kill()
                    print(f"  ✅ Killed process {process.pid}")
        except Exception as e:
            print(f"  Error terminating process {process.pid}: {e}")

    active_processes.clear()
    print("  ✅ Emergency cleanup completed")

async def async_cleanup_processes():
    """Asynchronous cleanup of all active processes."""
    print("\n🧹 Cleaning up all active processes...")
    processes_to_cleanup = list(active_processes)

    if not processes_to_cleanup:
        print("  No active processes to clean up")
        return

    cleanup_tasks = []
    for process in processes_to_cleanup:
        task = asyncio.create_task(cleanup_single_process(process))
        cleanup_tasks.append(task)

    await asyncio.gather(*cleanup_tasks, return_exceptions=True)
    active_processes.clear()
    print("  ✅ All processes cleaned up")

async def cleanup_single_process(process):
    """Cleanup a single process and its process group."""
    try:
        if process.returncode is None:
            print(f"  Terminating process group {process.pid}...")
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            await asyncio.sleep(1)
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
    """Entry point. Registers signal handlers before running main()."""
    loop = asyncio.get_running_loop()

    def handle_sigint():
        print("\n🛑 SIGINT received, performing emergency cleanup...")
        sync_cleanup_processes()
        os._exit(1)

    def handle_sigterm():
        print("\n🛑 SIGTERM received, performing emergency cleanup...")
        sync_cleanup_processes()
        os._exit(1)

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
        await async_cleanup_processes()

if __name__ == "__main__":
    asyncio.run(main_with_signal_handling())