from typing import Any, Optional, Dict, List, Tuple, Callable
import os
import json
import uuid
import datetime
import traceback
from enum import Enum
import pickle

from agents import (
    Agent,
    RunConfig,
    Usage,
    Runner,
    ModelSettings,
    ToolCallItem,
    MessageOutputItem,
    ToolCallOutputItem,
    ModelProvider
)

from utils.mcp.tool_servers import MCPServerManager
from utils.api_model.model_provider import calculate_cost
from utils.roles.user import User, UserRuntimeConfig
from utils.api_model.openai_client import AsyncOpenAIClientWithRetry
from utils.general.helper import copy_folder_contents, run_command, specifical_inialize_for_mcp
from utils.data_structures.task_config import TaskConfig
from utils.data_structures.agent_config import AgentConfig
from utils.data_structures.mcp_config import MCPConfig
from utils.data_structures.user_config import UserConfig
import shutil

import asyncio
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

from utils.aux_tools.basic import tool_sleep, tool_done

class TaskStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    MAX_TURNS_REACHED = "max_turns_reached"
    INTERRUPTED = "interrupted"  # 新增状态：表示任务被中断

class CustomJSONEncoder(json.JSONEncoder):
    """自定义JSON编码器，用于处理将Python中的布尔值转换为小写的'true'和'false'形式输出"""
    def default(self, o):
        if isinstance(o, bool):
            return str(o).lower()
        return super().default(o)

class TaskAgent:
    """封装了任务执行的Agent类"""
    
    def __init__(
        self,
        task_config: TaskConfig,
        agent_config: AgentConfig,
        agent_model_provider: ModelProvider,
        user_config: UserConfig,
        user_client: AsyncOpenAIClientWithRetry,
        mcp_config: MCPConfig,
        agent_hooks=None,
        run_hooks=None,
        termination_checker: Optional[Callable[[str, List[Dict], str], bool]] = None,
        debug: bool = False,
        allow_resume: bool = False,
        manual: bool = False,
        single_turn_mode: bool = False,
    ):
        self.task_config = task_config
        self.agent_config = agent_config
        self.agent_model_provider = agent_model_provider
        self.user_config = user_config
        self.user_client = user_client
        self.mcp_config = mcp_config
        self.agent_hooks = agent_hooks
        self.run_hooks = run_hooks
        self.termination_checker = termination_checker or self._default_termination_checker
        
        self.agent: Optional[Agent] = None
        self.mcp_manager: Optional[MCPServerManager] = None
        self.user_simulator: Optional[User] = None
        self.all_tools: List[Dict] = []
        self.logs: List[Dict] = []
        self.logs_to_record: List[Dict] = []
        self.usage = Usage()
        self.task_status = TaskStatus.FAILED
        
        # 新增统计信息
        self.stats = {
            "interaction_turns": 0,
            "tool_calls": 0,
            "agent_llm_requests": 0,
            "total_tokens": 0,
            "input_tokens": 0,
            "output_tokens": 0
        }

        self.debug = debug
        self.allow_resume = allow_resume
        self.manual = manual
        if self.manual:
            # 全局会话，避免重复创建
            self._session = PromptSession()
        
        # 新增：检查点文件路径
        self.checkpoint_file = None
        self.checkpoint_interval = 1  # 每隔多少轮保存一次检查点

        self.single_turn_mode = single_turn_mode
    


    async def ainput(self,prompt='> '):
        """异步版本的 input() 函数"""
        with patch_stdout():
            return await self._session.prompt_async(prompt)

    def _debug_print(self, *args):
        if self.debug:
            print(*args)

    def _default_termination_checker(self, content: str, recent_tools: List[Dict], check_target: str = "user") -> bool:
        """默认的终止条件检查器"""
        if check_target=='user':
            return '#### STOP' in content
        return False
    
    def _get_checkpoint_path(self) -> str:
        """获取检查点文件路径"""
        if self.checkpoint_file is None:
            self.checkpoint_file = os.path.join(self.task_config.task_root, "checkpoint.pkl")
        return self.checkpoint_file
    
    async def _save_checkpoint(self) -> None:
        """保存当前执行状态到检查点"""
        if not self.allow_resume:
            return
            
        checkpoint_data = {
            # 保存核心状态
            'logs': self.logs.copy(),
            'logs_to_record': self.logs_to_record.copy(),
            'all_tools': self.all_tools.copy(),
            'stats': self.stats.copy(),
            'usage': {
                'input_tokens': self.usage.input_tokens,
                'output_tokens': self.usage.output_tokens,
                'requests': self.usage.requests
            },
            # 保存用户模拟器状态
            'user_simulator_state': self.user_simulator.get_state() if hasattr(self.user_simulator, 'get_state') else {
                'conversation_history': self.user_simulator.conversation_history if self.user_simulator else []
            },
            # 保存时间戳
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            # 版本信息，用于兼容性检查
            'version': '1.0'
        }
        
        try:
            with open(self._get_checkpoint_path(), 'wb') as f:
                pickle.dump(checkpoint_data, f)
            self._debug_print(f"Checkpoint saved at turn {self.stats['interaction_turns']}")
        except Exception as e:
            self._debug_print(f"Failed to save checkpoint: {e}")
    
    async def _load_checkpoint(self) -> bool:
        """从检查点恢复执行状态"""
        if not self.allow_resume:
            return False
            
        checkpoint_path = self._get_checkpoint_path()
        if not os.path.exists(checkpoint_path):
            self._debug_print("No checkpoint found")
            return False
            
        try:
            with open(checkpoint_path, 'rb') as f:
                checkpoint_data = pickle.load(f)
            
            # 恢复状态
            self.logs = checkpoint_data['logs']
            self.logs_to_record = checkpoint_data['logs_to_record']
            self.all_tools = checkpoint_data['all_tools']
            self.stats = checkpoint_data['stats']
            
            # 恢复Usage对象
            usage_data = checkpoint_data['usage']
            self.usage.input_tokens = usage_data['input_tokens']
            self.usage.output_tokens = usage_data['output_tokens']
            self.usage.requests = usage_data['requests']
            
            # 恢复用户模拟器状态
            if self.user_simulator:
                if hasattr(self.user_simulator, 'set_state'):
                    self.user_simulator.set_state(checkpoint_data['user_simulator_state'])
                else:
                    # 简单恢复对话历史
                    self.user_simulator.conversation_history = checkpoint_data['user_simulator_state'].get('conversation_history', [])
            
            self._debug_print(f"Checkpoint loaded from {checkpoint_data['timestamp']}")
            self._debug_print(f"Resuming from turn {self.stats['interaction_turns']}")
            return True
            
        except Exception as e:
            self._debug_print(f"Failed to load checkpoint: {e}")
            return False
    
    def _remove_checkpoint(self) -> None:
        """删除检查点文件"""
        checkpoint_path = self._get_checkpoint_path()
        if os.path.exists(checkpoint_path):
            try:
                os.remove(checkpoint_path)
                self._debug_print("Checkpoint removed")
            except Exception as e:
                self._debug_print(f"Failed to remove checkpoint: {e}")
    
    async def initialize_workspace(self, show_traceback=False) -> bool:
        """初始化工作空间"""
        self._debug_print(f"Starting to initialize workspace for {self.task_config.id} ...")
        
        log_file = self.task_config.log_file
        agent_workspace = self.task_config.agent_workspace
        initial_state_workspace = self.task_config.initialization.workspace

        try:
            # 如果允许恢复，检查是否已有工作空间和检查点
            if self.allow_resume and os.path.exists(agent_workspace) and os.path.exists(self._get_checkpoint_path()):
                self._debug_print("Found existing workspace and checkpoint, will attempt to resume")
                return True
            
            # 否则，执行正常的初始化流程
            if os.path.exists(agent_workspace):
                self._debug_print("Reset/Remove an existing agent workspace.")
                shutil.rmtree(agent_workspace)

            if os.path.exists(log_file):
                self._debug_print("Reset/Remove an existing log file.")
                os.remove(log_file)
            
            # 删除旧的检查点（如果有）
            self._remove_checkpoint()
            
            # 复制初始状态文件
            await copy_folder_contents(initial_state_workspace, agent_workspace, self.debug)

            # 执行预处理命令（如果有）
            if self.task_config.initialization.process_command is not None:
                args = f"--agent_workspace {self.task_config.agent_workspace}"
                command = f"{self.task_config.initialization.process_command} {args}"
                await run_command(command, show_output=True)
                
            # MCP服务器特定的初始化操作
            await specifical_inialize_for_mcp(self.task_config)

        except Exception as e:
            self._debug_print("Workspace initialization failed, reason:", e)
            if show_traceback:
                traceback.print_exc()
            return False

        self._debug_print(f"Successfully initialize workspace for {self.task_config.id}!")
        return True
    
    async def setup_mcp_servers(self) -> None:
        """设置并连接MCP服务器"""
        self.mcp_manager = MCPServerManager(
            agent_workspace=self.task_config.agent_workspace,
            config_dir=self.mcp_config.server_config_path,
            debug=self.debug
        )
        await self.mcp_manager.connect_servers(self.task_config.needed_mcp_servers)
    
    async def setup_agent(self) -> None:
        """初始化Agent"""
        self._debug_print(">>初始化agent loop")
        
        self.agent = Agent(
            name="Assistant",
            instructions=self.task_config.system_prompts.agent,
            model=self.agent_model_provider.get_model(self.agent_config.model.real_name),
            mcp_servers=[*self.mcp_manager.get_all_connected_servers()],
            tools=[tool_sleep, tool_done], # FIXME: hardcoded now, should be dynamic
            hooks=self.agent_hooks,
            model_settings=ModelSettings(
                temperature=self.agent_config.generation.temperature,
                top_p=self.agent_config.generation.top_p,
                max_tokens=self.agent_config.generation.max_tokens,
                tool_choice=self.agent_config.tool.tool_choice,
                parallel_tool_calls=self.agent_config.tool.parallel_tool_calls,
            ),
        )
        
        # 获取所有可用工具
        available_tools = await self.agent.get_all_tools()
        self._debug_print(f">>可用工具列表 (x{len(available_tools)})")
        for tool in available_tools:
            self._debug_print(f"[{tool.name}]", tool.description)
            self.all_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.params_json_schema
                }
            })
    
    async def setup_user_simulator(self) -> None:
        """初始化用户模拟器"""
        user_runtime_config = UserRuntimeConfig(
            global_config=self.user_config,
            starting_system_prompt=self.task_config.system_prompts.user,
        )
        self.user_simulator = User(
            client=self.user_client,
            user_config=user_runtime_config
        )
        self.user_simulator.initialize_conversation()
    
    async def process_agent_response(self, result) -> List[Dict]:
        """处理Agent的响应并格式化日志，返回工具调用列表"""
        tool_calls_in_response = []  # 新增：记录这次响应中的所有工具调用
        item_index = 0
        
        while item_index < len(result.new_items):
            current_item = result.new_items[item_index]
            
            if isinstance(current_item, MessageOutputItem):
                if item_index == len(result.new_items) - 1:
                    # 最后一条消息，为assistant的最终回复
                    self.logs_to_record.append({
                        "role": "assistant",
                        "content": current_item.to_input_item()['content'][0]['text']
                    })
                    item_index += 1
                else:
                    # 不是最后一条消息，必然调用工具
                    tool_calls = []
                    for i in range(item_index + 1, len(result.new_items)):
                        if not isinstance(result.new_items[i], ToolCallItem):
                            break
                        tool_item = result.new_items[i].to_input_item()
                        tool_call = {
                            "id": tool_item['call_id'],
                            "type": "function",
                            "function": {
                                "name": tool_item["name"],
                                "arguments": tool_item["arguments"]
                            }
                        }
                        tool_calls.append(tool_call)
                        tool_calls_in_response.append(tool_call)  # 记录工具调用
                        
                    self.logs_to_record.append({
                        "role": "assistant",
                        "content": current_item.to_input_item()['content'][0]['text'],
                        "tool_calls": tool_calls
                    })
                    item_index += (1 + len(tool_calls))
                    
            elif isinstance(current_item, ToolCallItem):
                # 不带content的tool_call调用
                tool_calls = []
                for i in range(item_index, len(result.new_items)):
                    if not isinstance(result.new_items[i], ToolCallItem):
                        break
                    tool_item = result.new_items[i].to_input_item()
                    tool_call = {
                        "id": tool_item['call_id'],
                        "type": "function",
                        "function": {
                            "name": tool_item["name"],
                            "arguments": tool_item["arguments"]
                        }
                    }
                    tool_calls.append(tool_call)
                    tool_calls_in_response.append(tool_call)  # 记录工具调用
                    
                self.logs_to_record.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": tool_calls
                })
                item_index += len(tool_calls)
                
            elif isinstance(current_item, ToolCallOutputItem):
                # tool执行结果
                tool_output = current_item.to_input_item()
                self.logs_to_record.append({
                    "role": "tool",
                    "content": tool_output["output"],
                    "tool_call_id": tool_output["call_id"]
                })
                item_index += 1
        
        # 更新工具调用统计
        self.stats["tool_calls"] += len(tool_calls_in_response)
        
        return tool_calls_in_response
    
    async def run_interaction_loop(self) -> None:
        """运行交互循环"""
        # 如果是恢复模式，尝试加载检查点
        resumed = False
        if self.allow_resume:
            resumed = await self._load_checkpoint()
        
        if self.single_turn_mode:
            real_max_turns = 1
        else:
            real_max_turns = self.task_config.max_turns

        while self.stats["interaction_turns"] < real_max_turns:
            try:
                # 获取用户输入
                if self.single_turn_mode:
                    user_query = self.task_config.task_str
                elif self.manual:
                    user_query = await self.ainput("user: ")
                else:
                    user_query = await self.user_simulator.interact()
                    self._debug_print(f"user: {user_query}")
                
                self.logs.append({"role": "user", "content": user_query})
                self.logs_to_record.append({"role": "user", "content": user_query})
                
                # 增加交互轮次计数
                self.stats["interaction_turns"] += 1
                
                # 检查用户输入的终止条件
                if self.termination_checker(user_query, [], 'user'):
                    self._debug_print("Termination condition met by user input")
                    break
                
                # Agent 响应
                result = await Runner.run(
                    starting_agent=self.agent,
                    input=self.logs,
                    run_config=RunConfig(model_provider=self.agent_model_provider),
                    hooks=self.run_hooks,
                    max_turns=self.agent_config.tool.max_inner_turns if not self.single_turn_mode else self.task_config.max_steps_under_single_turn_mode,
                )
                
                # 更新统计信息
                for raw_response in result.raw_responses:
                    self.usage.add(raw_response.usage)
                    self.stats["agent_llm_requests"] += 1
                
                self._debug_print(f"assistant: {result.final_output}")
                self.logs.extend([item.to_input_item() for item in result.new_items])
                
                self.user_simulator.receive_message(result.final_output)
                
                # 处理响应并获取工具调用
                recent_tool_calls = await self.process_agent_response(result)
                
                # 检查Agent响应的终止条件
                if self.termination_checker(result.final_output, recent_tool_calls, 'agent'):
                    self._debug_print("Termination condition met by agent response")
                    break
                
                # 定期保存检查点
                if self.allow_resume and self.stats["interaction_turns"] % self.checkpoint_interval == 0:
                    await self._save_checkpoint()
                    
            except KeyboardInterrupt:
                # 处理用户中断
                self._debug_print("\nInterrupted by user")
                if self.allow_resume:
                    await self._save_checkpoint()
                    self.task_status = TaskStatus.INTERRUPTED
                raise
            except Exception as e:
                # 处理其他异常
                self._debug_print(f"\nError during interaction: {e}")
                if self.allow_resume:
                    await self._save_checkpoint()
                raise
        
        # 检查是否因为达到最大轮次而终止
        if self.stats["interaction_turns"] >= self.task_config.max_turns:
            self._debug_print(f"Maximum turns ({self.task_config.max_turns}) reached")
            self.task_status = TaskStatus.MAX_TURNS_REACHED
    
    def get_cost_summary(self) -> Tuple[Dict, Dict]:
        """获取成本摘要"""
        # 添加空值检查，防止 user_simulator 为 None
        if self.user_simulator is None:
            user_cost = {"total_cost": 0, "total_input_tokens": 0, "total_output_tokens": 0, "total_requests": 0}
        else:
            user_cost = self.user_simulator.get_cost_summary()
        
        _, _, total_cost = calculate_cost(
            self.agent_config.model.short_name,
            self.usage.input_tokens,
            self.usage.output_tokens
        )
        
        # 更新token统计
        self.stats["input_tokens"] = self.usage.input_tokens
        self.stats["output_tokens"] = self.usage.output_tokens
        self.stats["total_tokens"] = self.usage.input_tokens + self.usage.output_tokens
        
        agent_cost = {
            "total_cost": round(total_cost,4),
            "total_input_tokens": self.usage.input_tokens,
            "total_output_tokens": self.usage.output_tokens,
            "total_requests": self.usage.requests,
        }
        
        return user_cost, agent_cost
    
    async def save_results(self) -> None:
        """保存运行结果到日志文件"""
        res_log_file = self.task_config.log_file
        
        if not os.path.exists(os.path.dirname(res_log_file)):
            # in case the folder is not built in initialization stage
            os.makedirs(os.path.dirname(res_log_file))

        with open(res_log_file, "w", encoding='utf-8') as f:
            result = {
                'config': self.task_config.to_dict(),
                'request_id': str(uuid.uuid4()),
                'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'tool_calls': {
                    'tools': self.all_tools,
                    'tool_choice': self.agent_config.tool.tool_choice,
                },
                "status": self.task_status.value,
                'messages': self.logs_to_record,
                'key_stats': self.stats,
                'agent_cost': self.agent_cost,
                'user_cost': self.user_cost,
                'resumed': self.allow_resume,  # 标记是否使用了恢复功能
            }
            
            json_output = json.dumps(result, ensure_ascii=False, cls=CustomJSONEncoder)
            f.write(json_output)
    
    async def cleanup(self) -> None:
        """清理资源"""
        if self.mcp_manager:
            await self.mcp_manager.disconnect_servers()
    
    async def run(self) -> TaskStatus:
        """运行整个任务"""
        try:
            # 设置日志文件路径
            self.task_config.log_file = os.path.join(self.task_config.task_root, "log.json")
            self.task_config.agent_workspace = os.path.join(self.task_config.task_root, "workspace")
            
            # 初始化工作区（如果允许恢复且有检查点，则跳过重新初始化）
            if not await self.initialize_workspace():
                return TaskStatus.FAILED
            
            # 设置MCP服务器
            await self.setup_mcp_servers()
            
            # 设置Agent
            await self.setup_agent()
            
            # 设置用户模拟器
            await self.setup_user_simulator()
            
            # 运行交互循环
            await self.run_interaction_loop()
            
            # 如果没有设置其他状态，则为成功
            if self.task_status not in [TaskStatus.MAX_TURNS_REACHED, TaskStatus.INTERRUPTED]:
                self.task_status = TaskStatus.SUCCESS
            
            # 任务完成，删除检查点
            if self.task_status == TaskStatus.SUCCESS:
                self._remove_checkpoint()
                
        except KeyboardInterrupt:
            self._debug_print("Task interrupted by user")
            if self.task_status != TaskStatus.INTERRUPTED:
                self.task_status = TaskStatus.INTERRUPTED
                
        except Exception as e:
            self._debug_print("Error when running agent -", e)
            if self.debug:
                traceback.print_exc()
            self.task_status = TaskStatus.FAILED
            
        finally:
            # 计算最终的成本摘要（这会更新token统计）
            user_cost, agent_cost = self.get_cost_summary()
            
            self.user_cost = user_cost
            self.agent_cost = agent_cost

            # 打印成本摘要
            self._debug_print(f"===模拟用户（{self.user_config.model.short_name}）的开销如下===")
            for k, v in user_cost.items():
                self._debug_print(f"{k} : {v}")
            self._debug_print(f"===Agent（{self.agent_config.model.short_name}）的开销如下===")
            for k, v in agent_cost.items():
                self._debug_print(f"{k} : {v}")
            self._debug_print("===关键统计信息===")
            for k, v in self.stats.items():
                self._debug_print(f"{k} : {v}")
            
            # 保存结果
            await self.save_results()
            
            # 清理资源
            await self.cleanup()
            
        return self.task_status