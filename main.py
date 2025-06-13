import asyncio
import argparse
import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import logging
from tqdm.asyncio import tqdm

from utils.general.helper import read_json, setup_proxy
from utils.task_runner.runner import TaskRunner
from utils.evaluation.evaluator import TaskEvaluator

# monkey patch to solve
from utils.openai_agents_monkey_patch.custom_run_impl import *
from utils.openai_agents_monkey_patch.custom_mcp_util import *

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BatchTaskProcessor:
    """批量任务处理器"""
    
    def __init__(self, eval_config_path: str, max_concurrent: int = 1, debug: bool = False, allow_resume: bool = False):
        self.eval_config_dict = read_json(eval_config_path)
        self.global_task_config = self.eval_config_dict.get("global_task_config")
        self.mcp_config, self.agent_config, self.user_config = TaskRunner.load_configs(self.eval_config_dict)
        self.max_concurrent = max_concurrent
        self.debug = debug
        self.allow_resume = allow_resume
        
    def find_task_configs(self, directory: str) -> List[str]:
        """递归查找目录下所有的任务配置文件"""
        task_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.json'):
                    file_path = os.path.join(root, file)
                    task_files.append(file_path)
        return sorted(task_files)
    
    async def process_tasks(self, task_files: List[str]) -> Dict[str, Any]:
        """批量处理任务"""
        logger.info(f"Starting batch processing of {len(task_files)} tasks")
        
        # 使用信号量控制并发数
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def process_with_semaphore(task_file):
            async with semaphore:
                return await TaskRunner.run_task_with_result(
                    task_config_path=task_file,
                    agent_config=self.agent_config,
                    user_config=self.user_config,
                    mcp_config=self.mcp_config,
                    global_task_config=self.global_task_config,
                    debug = self.debug,
                    allow_resume=self.allow_resume
                )
        
        # 创建进度条
        tasks = [process_with_semaphore(task_file) for task_file in task_files]
        
        # 运行所有任务
        run_results = []
        for coro in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Running tasks"):
            result = await coro
            run_results.append(result)
            
        # 评估所有任务
        logger.info("Starting batch evaluation")
        eval_results = await TaskEvaluator.batch_evaluate(run_results,allow_resume = self.allow_resume)
        
        # 汇总结果
        summary = self.summarize_results(run_results, eval_results)
        
        return {
            "summary": summary,
            "run_results": run_results,
            "eval_results": eval_results
        }
    
    def summarize_results(self, run_results: List[Dict], eval_results: List[Dict]) -> Dict[str, Any]:
        """汇总批量处理结果"""
        total_tasks = len(run_results)
        successful_runs = sum(1 for r in run_results if r.get("success", False))
        passed_evaluations = sum(1 for r in eval_results if r.get("pass", False))
        
        total_execution_time = sum(r.get("execution_time", 0) for r in run_results)
        
        # 统计失败原因
        failure_reasons = {}
        for result in eval_results:
            if not result.get("pass", False):
                reason = result["evaluation"].get("failure", "unknown")
                failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
        
        # 计算总成本
        total_agent_cost = 0
        total_user_cost = 0
        for result in run_results:
            if "agent_cost" in result:
                total_agent_cost += result["agent_cost"].get("total_cost", 0)
            if "user_cost" in result:
                total_user_cost += result["user_cost"].get("total_cost", 0)
        
        return {
            "total_tasks": total_tasks,
            "successful_runs": successful_runs,
            "passed_evaluations": passed_evaluations,
            "success_rate": f"{(passed_evaluations/total_tasks)*100:.2f}%" if total_tasks > 0 else "0%",
            "total_execution_time": f"{total_execution_time:.2f} seconds",
            "total_agent_cost": total_agent_cost,
            "total_user_cost": total_user_cost,
            "failure_reasons": failure_reasons
        }

async def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="Run batch agent evaluation")
    parser.add_argument("--task_dir", help="Directory containing task config files")
    parser.add_argument("--with_proxy", action="store_true", 
                       help="Use proxy for HTTP/HTTPS requests")
    parser.add_argument("--eval_config", default="scripts/eval_config.json", 
                       help="Path to evaluation config file")
    parser.add_argument("--max_concurrent", type=int, default=1,
                       help="Maximum number of concurrent tasks")
    parser.add_argument("--debug", action="store_true", 
                       help="Whether to enable debug print")
    parser.add_argument("--allow_resume", action="store_true", 
                       help="Whether to enable resume")
    parser.add_argument("--output", default="batch_results.json",
                       help="Output file for batch results")
    parser.add_argument("--filter", help="Filter task files by pattern (e.g., 'filesystem_*')")
    args = parser.parse_args()
    
    # 设置代理（如果需要）
    setup_proxy(args.with_proxy)
    
    # 创建批处理器
    processor = BatchTaskProcessor(
        eval_config_path=args.eval_config,
        max_concurrent=args.max_concurrent,
        debug=args.debug,
        allow_resume=args.allow_resume
    )
    
    # 查找任务配置文件
    print(f"Searching for task configs in: {args.task_dir}")
    task_files = processor.find_task_configs(args.task_dir)
    
    # 应用过滤器（如果指定）
    if args.filter:
        import fnmatch
        task_files = [f for f in task_files if fnmatch.fnmatch(os.path.basename(f), args.filter)]
    
    if not task_files:
        print("No task configuration files found!")
        return 1
    
    print(f"Found {len(task_files)} task configuration files")
    
    # 批量处理任务
    start_time = datetime.now()
    results = await processor.process_tasks(task_files)
    end_time = datetime.now()
    
    # 添加总体执行时间
    results["total_batch_time"] = (end_time - start_time).total_seconds()
    results["start_time"] = start_time.isoformat()
    results["end_time"] = end_time.isoformat()
    
    # 打印摘要
    print("\n" + "="*80)
    print("BATCH EXECUTION SUMMARY")
    print("="*80)
    summary = results["summary"]
    print(f"Total Tasks: {summary['total_tasks']}")
    print(f"Successful Runs: {summary['successful_runs']}")
    print(f"Passed Evaluations: {summary['passed_evaluations']}")
    print(f"Success Rate: {summary['success_rate']}")
    print(f"Total Execution Time: {summary['total_execution_time']}")
    print(f"Total Batch Time: {results['total_batch_time']:.2f} seconds")
    print(f"Total Agent Cost: ${summary['total_agent_cost']:.4f}")
    print(f"Total User Cost: ${summary['total_user_cost']:.4f}")
    
    if summary['failure_reasons']:
        print("\nFailure Reasons:")
        for reason, count in summary['failure_reasons'].items():
            print(f"  - {reason}: {count}")
    
    # 打印失败的任务详情
    failed_tasks = [r for r in results["eval_results"] if not r.get("pass", False)]
    if failed_tasks:
        print(f"\n{len(failed_tasks)} Failed Tasks:")
        for task in failed_tasks[:10]:  # 只显示前10个失败的任务
            print(f"  - {task['task_id']}: {task['evaluation']['failure']}")
        if len(failed_tasks) > 10:
            print(f"  ... and {len(failed_tasks) - 10} more")
    
    # 保存详细结果
    if not os.path.exists(args.output):
        os.makedirs(os.path.dirname(args.output))
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed results saved to: {args.output}")
    
    # 创建简化的结果报告
    report_file = args.output.replace('.json', '_report.json')
    report = {
        "summary": summary,
        "failed_tasks": [
            {
                "task_id": t["task_id"],
                "task_path": t["task_config_path"],
                "failure": t["evaluation"]["failure"],
                "details": t["evaluation"]["details"]
            }
            for t in failed_tasks
        ],
        "execution_info": {
            "start_time": results["start_time"],
            "end_time": results["end_time"],
            "total_batch_time": results["total_batch_time"],
            "max_concurrent": args.max_concurrent
        }
    }
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"Summary report saved to: {report_file}")
    
    # 返回退出码（如果有失败的任务则返回1）
    return 0 if summary['passed_evaluations'] == summary['total_tasks'] else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)