import asyncio
import argparse
from distutils.command.config import dump_file
from utils.general.helper import read_json
from utils.data_structures.task_config import TaskConfig
from utils.task_runner.runner import TaskRunner
from utils.evaluation.evaluator import TaskEvaluator
from utils.general.helper import setup_proxy,print_color
import os

from utils.openai_agents_monkey_patch.custom_run_impl import *
from utils.openai_agents_monkey_patch.custom_mcp_util import *


async def main():
    parser = argparse.ArgumentParser(description="Run demo agent evaluation")
    parser.add_argument("--with_proxy", action="store_true", 
                       help="Use proxy for HTTP/HTTPS requests")
    parser.add_argument("--eval_config", default="scripts/eval_config.json", 
                       help="Path to evaluation config file")
    parser.add_argument("--task_dir", default="tasks/jl/filesystem_001", 
                       help="Path to task directory")
    parser.add_argument("--debug", action="store_true", 
                       help="Whether to enable debug print")
    parser.add_argument("--allow_resume", action="store_true", 
                       help="Whether to enable resume")
    parser.add_argument("--manual", action="store_true", 
                       help="Whether to enable manual input")
    parser.add_argument("--multi_turn_mode", action="store_true", 
                       help="Whether to enable multi turn mode")
    parser.add_argument("--cn_mode", action="store_true", 
                       help="Whether to enable chinese mode")

    ## we override some parameters here
    # we now just set a hard sampling parameters: temperature = 0.6, top_p = 1.0, max_tokens = 4096
    parser.add_argument("--max_steps_under_single_turn_mode", type=int, default=None, 
                       help="Maximum number of steps under single turn mode")
    parser.add_argument("--model_short_name", type=str, default=None, 
                       help="Model name")
    parser.add_argument("--provider", type=str, default="unified", 
                       help="Provider")
    args = parser.parse_args()
    
    # Set Proxy (if needed)
    setup_proxy(args.with_proxy)
    
    # Load configurations
    eval_config_dict = read_json(args.eval_config)
    # task_config_dict = read_json(os.path.join(args.task_dir, "task_config.json"))
    if args.model_short_name is not None:
        assert args.provider is not None, "provider is required when model_short_name is provided"
        eval_config_dict['agent']['model']['short_name'] = args.model_short_name
        eval_config_dict['agent']['model']['provider'] = args.provider
    if args.max_steps_under_single_turn_mode is not None:
        eval_config_dict['global_task_config']['max_steps_under_single_turn_mode'] = args.max_steps_under_single_turn_mode
    
    # Parse configurations
    mcp_config, agent_config, user_config = TaskRunner.load_configs(eval_config_dict)
    # task_config = TaskConfig.from_dict(task_config_dict, 
    #                                    agent_config.model.short_name,
    #                                    eval_config_dict['global_task_config'],)
    task_config = TaskConfig.build(args.task_dir, 
                                   agent_config.model.short_name, 
                                   eval_config_dict['global_task_config'],
                                   not args.multi_turn_mode,
                                   args.cn_mode)

    # Run task
    print_color("====== Starting Task Execution ======", "yellow")
    task_status = await TaskRunner.run_single_task(
        task_config=task_config,
        agent_config=agent_config,
        user_config=user_config,
        mcp_config=mcp_config,
        debug=args.debug,
        allow_resume=args.allow_resume,
        manual=args.manual,
        single_turn_mode=not args.multi_turn_mode,
    )
    
    print_color(f"\n====== Task completed with status ======", "yellow")
    print(f"Status: {task_status.value} ")
    
    # Evaluate results
    print_color("\n====== Starting Task Evaluation ======", "yellow")
    log_file = task_config.log_file
    dump_line = read_json(log_file)
    eval_res = await TaskEvaluator.evaluate_from_log_file(log_file, allow_resume=args.allow_resume)
    
    print_color(f"\n====== Evaluation Results ======", "yellow")
    print(f"Pass: {eval_res.get('pass', False)}")
    print(f"Key statistics: {dump_line.get('key_stats', 'N/A')}")
    print(f"Total Cost: {dump_line.get('agent_cost', 'N/A').get('total_cost')} (agent) + {dump_line.get('user_cost', 'N/A').get('total_cost')} (user)")
    print(f"Details: {eval_res.get('details', 'N/A')}")
    if not eval_res.get('pass', False):
        print(f"Failure Reason: {eval_res.get('failure', 'Unknown')}")

    # Update evaluation status
    try:
        from utils.status_manager import TaskStatusManager
        status_manager = TaskStatusManager(task_config.task_root)
        status_manager.update_evaluation(eval_res.get('pass', None))
    except Exception as e:
        print(f"Warning: Failed to update evaluation status: {e}")

    return 0 if eval_res.get("pass", False) else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)