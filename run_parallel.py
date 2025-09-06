import asyncio
import argparse
import shortuuid
import os
import json
from utils.general.helper import read_json
import subprocess
from typing import List, Optional, Dict
import time
from datetime import datetime
from pathlib import Path


async def run_command_async(command: str, log_file: str, timeout_seconds: int = 1800):
    """
    异步执行shell命令，带超时控制和日志记录
    timeout_seconds: 默认30分钟 = 1800秒
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
                stderr=subprocess.STDOUT  # 将stderr重定向到stdout
            )
            
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
            
            return {
                'success': process.returncode == 0,
                'returncode': process.returncode,
                'log_file': log_file
            }
    
    except asyncio.TimeoutError:
        # 超时时终止进程
        try:
            process.terminate()
            await asyncio.sleep(5)  # 给进程5秒优雅退出
            if process.returncode is None:
                process.kill()  # 如果还没退出，强制杀死
        except:
            pass
        
        # 记录超时信息到日志
        with open(log_file, 'a') as f:
            f.write(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] TIMEOUT after {timeout_seconds} seconds\n")
        
        raise TimeoutError(f"Command timed out after {timeout_seconds} seconds")
    
    except Exception as e:
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
        
        # 任务结果
        self.task_results = TaskResult()
        
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
                             maxstep: str, timeout: int = 1800):
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
                            provider, maxstep, timeout, has_lock=True
                        )
            finally:
                self.waiting_for_lock.discard(task_dir_arg)
        
        elif conflict_lock:
            # 有锁但锁是空闲的，正常执行
            async with conflict_lock:
                async with self.semaphore:
                    return await self._execute_task(
                        task_dir_arg, tag, model_short_name, 
                        provider, maxstep, timeout, has_lock=True
                    )
        
        else:
            # 无冲突，直接执行
            async with self.semaphore:
                return await self._execute_task(
                    task_dir_arg, tag, model_short_name, 
                    provider, maxstep, timeout, has_lock=False
                )
    
    async def _execute_task(self, task_dir_arg: str, tag: str, 
                           model_short_name: str, provider: str, 
                           maxstep: str, timeout: int, has_lock: bool):
        """实际执行任务"""
        command = f"bash scripts/run_single_containerized.sh " \
                 f"{task_dir_arg} {tag} {model_short_name} {provider} {maxstep}"
        
        # 构建日志文件路径
        # task_dir_arg 格式: tasks_folder/task
        parts = task_dir_arg.split('/')
        if len(parts) >= 2:
            tasks_folder = parts[0]
            task_name = parts[1]
        else:
            tasks_folder = ""
            task_name = task_dir_arg
        
        log_file = os.path.join("logs_containers", tasks_folder, task_name, 
                               f"{model_short_name}_{tag}.log")
        
        task_start = datetime.now()
        lock_status = "with lock" if has_lock else "no lock"
        
        print(f"\n🚀 [{task_start.strftime('%H:%M:%S')}] STARTING: {task_dir_arg}")
        print(f"   📝 Log: {log_file}")
        if has_lock:
            print(f"   🔒 Running with conflict lock")
        
        try:
            result = await run_command_async(command, log_file, timeout_seconds=timeout)
            
            self.completed_tasks += 1
            elapsed = (datetime.now() - task_start).total_seconds()
            
            print(f"\n✅ [{datetime.now().strftime('%H:%M:%S')}] SUCCESS: {task_dir_arg}")
            print(f"   ⏱️ Time: {elapsed:.1f}s | Progress: {self.completed_tasks}/{self.total_tasks}")
            
            return {
                'task': task_dir_arg, 
                'status': 'success', 
                'elapsed': elapsed,
                'log_file': log_file,
                'tag': tag,
                'model_short_name': model_short_name
            }
            
        except TimeoutError as e:
            self.timeout_tasks += 1
            self.failed_tasks += 1
            elapsed = (datetime.now() - task_start).total_seconds()
            
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
        print(f"  Elapsed time: {elapsed_total:.1f}s")
        print(f"  Max concurrent workers: {self.max_workers}")
        print(f"{'='*60}\n")

def analyze_results(all_task_dir_args: List[str], model_short_name: str, tag: str) -> TaskResult:
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
        
        # 构建输出文件路径
        eval_res_path = os.path.join(
            "dumps", tasks_folder, task_name, 
            f"{model_short_name}_{tag}_output", "eval_res.json"
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
    
    if not all_task_dir_args:
        print("No tasks found!")
        return
    
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
            args.provider, args.maxstep, args.timeout
        )
        for task_dir_arg in all_task_dir_args
    ]
    
    # 定期打印进度的任务
    async def progress_reporter():
        while scheduler.completed_tasks + scheduler.failed_tasks < scheduler.total_tasks:
            await asyncio.sleep(30)  # 每30秒报告一次进度
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
    print(f"Checking eval_res.json files in dumps/{args.tasks_folder}/*/{{model}}_{tag}_output/\n")
    
    task_result = analyze_results(all_task_dir_args, args.model_short_name, tag)
    
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
    report_file = f"./results/execution_report_{args.tasks_folder}_{args.model_short_name}_{tag}.json"
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

if __name__ == "__main__":
    # 运行主程序
    asyncio.run(main())