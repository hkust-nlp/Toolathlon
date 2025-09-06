from typing import Dict, Any, Optional
from utils.roles.task_agent import TaskAgent, TaskStatus
from utils.task_runner.hooks import AgentLifecycle, RunLifecycle
from utils.general.helper import build_agent_model_provider, build_user_client,print_color
from utils.data_structures.task_config import TaskConfig
from utils.data_structures.agent_config import AgentConfig
from utils.data_structures.mcp_config import MCPConfig
from utils.data_structures.user_config import UserConfig
from utils.task_runner.termination_checkers import default_termination_checker
from functools import partial
import logging
from utils.data_structures.common import Model
# 在 runner.py 的开头添加
import os
from pprint import pprint

class TaskRunner:
    """任务运行器"""
    
    @staticmethod
    async def run_single_task(
        task_config: TaskConfig,
        agent_config: AgentConfig,
        user_config: UserConfig,
        mcp_config: MCPConfig,
        debug: bool=False,
        allow_resume: bool=False,
        manual: bool=False,
        single_turn_mode: bool=False,
    ) -> TaskStatus:
        """运行单个任务"""
        # 构建模型提供者和客户端
        agent_model_provider = build_agent_model_provider(agent_config)
        user_client = build_user_client(user_config)
        
        # 创建hooks
        agent_hooks = AgentLifecycle()
        run_hooks = RunLifecycle(debug)

        print_color("=== Actual task config ===", "magenta")
        pprint(task_config)
        print_color("=== Actual agent config ===", "magenta")
        pprint(agent_config)
        print_color("=== Actual user config ===", "magenta")
        pprint(user_config)
        print_color("=== Actual mcp config ===", "magenta")
        pprint(mcp_config)

        # 创建并运行TaskAgent
        task_agent = TaskAgent(
            task_config=task_config,
            agent_config=agent_config,
            agent_model_provider=agent_model_provider,
            user_config=user_config,
            user_client=user_client,
            mcp_config=mcp_config,
            agent_hooks=agent_hooks,
            run_hooks=run_hooks,
            termination_checker=partial(default_termination_checker,
                                        user_stop_phrases=task_config.stop.user_phrases,
                                        agent_stop_tools=task_config.stop.tool_names),
            debug=debug,
            allow_resume=allow_resume,
            manual=manual,
            single_turn_mode=single_turn_mode,
        )
        
        return await task_agent.run()

    @staticmethod
    async def run_task_with_result(
        task_config_path: str,
        agent_config: AgentConfig,
        user_config: UserConfig,
        mcp_config: MCPConfig,
        global_task_config: dict,
        debug: bool = False,
        allow_resume: bool = False
    ) -> Dict[str, Any]:
        """运行单个任务并返回详细结果"""
        from utils.general.helper import read_json
        from datetime import datetime
        
        start_time = datetime.now()
        result = {
            "task_config_path": task_config_path,
            "start_time": start_time.isoformat(),
        }
        
        try:
            # 加载任务配置
            task_config_dict = read_json(task_config_path)
            task_config = TaskConfig.from_dict(task_config_dict, 
                                               agent_config.model.short_name,
                                               global_task_config)
            result["task_id"] = task_config_dict.get("id", "unknown")
            
            can_skip=False
            if task_config.log_file and os.path.exists(task_config.log_file):
                dump_line = read_json(task_config.log_file)
                if dump_line.get('status', None) == TaskStatus.SUCCESS.value:
                    can_skip = True

            if not can_skip:
                # 运行任务
                task_status = await TaskRunner.run_single_task(
                    task_config=task_config,
                    agent_config=agent_config,
                    user_config=user_config,
                    mcp_config=mcp_config,
                    debug=debug,
                    allow_resume=allow_resume,
                )
                
                result["status"] = task_status.value
            else:
                # 直接使用之前已经跑好的结果
                result["status"] = TaskStatus.SUCCESS.value

            result["execution_time"] = (datetime.now() - start_time).total_seconds()
            result["log_file"] = task_config.log_file
            
            # 读取执行日志
            if task_config.log_file and os.path.exists(task_config.log_file):
                dump_line = read_json(task_config.log_file)
                result["key_stats"] = dump_line.get("key_stats", {})
                result["agent_cost"] = dump_line.get("agent_cost", {})
                result["user_cost"] = dump_line.get("user_cost", {})
            
            result["success"] = True
            
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            result["execution_time"] = (datetime.now() - start_time).total_seconds()
            logging.error(f"Error running task {task_config_path}: {e}")
            
        return result

    @staticmethod
    def load_configs(eval_config_dict: Dict[str, Any],) -> tuple:
        """加载配置文件"""
        mcp_config = MCPConfig.from_dict(eval_config_dict['mcp'])
        agent_config = AgentConfig.from_dict(eval_config_dict['agent'])
        user_config = UserConfig.from_dict(eval_config_dict['user'])
        
        return mcp_config, agent_config, user_config