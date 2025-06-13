import asyncio
import argparse
from distutils.command.config import dump_file
from utils.general.helper import read_json
from utils.data_structures.task_config import TaskConfig
from utils.task_runner.runner import TaskRunner
from utils.evaluation.evaluator import TaskEvaluator
from utils.general.helper import setup_proxy

from utils.openai_agents_monkey_patch.custom_run_impl import *
from utils.openai_agents_monkey_patch.custom_mcp_util import *


async def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="Run demo agent evaluation")
    parser.add_argument("--with_proxy", action="store_true", 
                       help="Use proxy for HTTP/HTTPS requests")
    parser.add_argument("--eval_config", default="scripts/eval_config.json", 
                       help="Path to evaluation config file")
    parser.add_argument("--task_config", default="tasks/dev/filesystem_001.json", 
                       help="Path to task config file")
    parser.add_argument("--debug", action="store_true", 
                       help="Whether to enable debug print")
    parser.add_argument("--allow_resume", action="store_true", 
                       help="Whether to enable resume")
    parser.add_argument("--manual", action="store_true", 
                       help="Whether to enable manual input")
    args = parser.parse_args()
    
    # 设置代理（如果需要）
    setup_proxy(args.with_proxy)
    
    # 加载配置
    eval_config_dict = read_json(args.eval_config)
    task_config_dict = read_json(args.task_config)
    
    # 解析配置
    mcp_config, agent_config, user_config = TaskRunner.load_configs(eval_config_dict)
    task_config = TaskConfig.from_dict(task_config_dict, 
                                       agent_config.model.short_name,
                                       eval_config_dict['global_task_config'],)

    # 运行任务
    print("=== Starting Task Execution ===")
    task_status = await TaskRunner.run_single_task(
        task_config=task_config,
        agent_config=agent_config,
        user_config=user_config,
        mcp_config=mcp_config,
        debug=args.debug,
        allow_resume=args.allow_resume,
        manual=args.manual,
    )
    
    print(f"\n=== Task completed with status: {task_status.value} ===")
    
    # 评估结果
    print("\n=== Starting Task Evaluation ===")
    log_file = task_config.log_file
    dump_line = read_json(log_file)
    eval_res = await TaskEvaluator.evaluate_from_log_file(log_file, allow_resume=args.allow_resume)
    
    print(f"\n=== Evaluation Results ===")
    print(f"Pass: {eval_res.get('pass', False)}")
    print(f"Key statistics: {dump_line.get('key_stats', 'N/A')}")
    print(f"Total Cost: {dump_line.get('agent_cost', 'N/A').get('total_cost')} (agent) + {dump_line.get('user_cost', 'N/A').get('total_cost')} (user)")
    print(f"Details: {eval_res.get('details', 'N/A')}")
    if not eval_res.get('pass', False):
        print(f"Failure Reason: {eval_res.get('failure', 'Unknown')}")

    return 0 if eval_res.get("pass", False) else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)