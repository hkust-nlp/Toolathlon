from typing import Any, Optional, Dict, List, Tuple, Callable
import os
import json
import uuid
import datetime
import traceback
from enum import Enum
import pickle
from pathlib import Path

from agents import (
    Agent,
    RunConfig,
    Usage,
    # Runner,
    ModelSettings,
    ToolCallItem,
    # MessageOutputItem,
    # ToolCallOutputItem,
    ModelProvider,
    ItemHelpers
)

from utils.roles.context_managed_runner import ContextManagedRunner

from utils.mcp.tool_servers import MCPServerManager
from utils.api_model.model_provider import calculate_cost, get_context_window
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
from utils.aux_tools.ai_webpage_summary import tool_ai_webpage_summary
from utils.aux_tools.context_management_tools import context_management_tools
from utils.aux_tools.history_tools import history_tools
from utils.aux_tools.python_interpretor import tool_python_execute
from utils.aux_tools.web_search import tool_web_search

local_tool_mappings = {
    "ai_webpage_summary": tool_ai_webpage_summary,
    "sleep": tool_sleep,
    "claim_done": tool_done,
    "manage_context": context_management_tools,
    "history": history_tools,
    'python_execute': tool_python_execute,
    "web_search": tool_web_search,
}

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
        # self.logs: List[Dict] = []
        self.session_id: Optional[str] = None
        self.history_dir: Optional[str] = None
        self.initial_run_time: Optional[str] = None
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

        self.shared_context = {}

    


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
            'logs': self.logs.copy(),
            'logs_to_record': self.logs_to_record.copy(),
            'all_tools': self.all_tools.copy(),
            'stats': self.stats.copy(),
            'usage': {
                'input_tokens': self.usage.input_tokens,
                'output_tokens': self.usage.output_tokens,
                'requests': self.usage.requests
            },
            'user_simulator_state': self.user_simulator.get_state() if hasattr(self.user_simulator, 'get_state') else {
                'conversation_history': self.user_simulator.conversation_history if self.user_simulator else []
            },
            'session_id': self.session_id,
            'history_dir': self.history_dir,
            'initial_run_time': getattr(self, 'initial_run_time', 'unknown'),
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'version': '2.0'
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
            
            # 检查版本兼容性
            version = checkpoint_data.get('version', '1.0')
            if version == '1.0':
                self._debug_print("Old checkpoint version detected, cannot resume")
                return False
            
            # 恢复状态
            self.logs = checkpoint_data['logs']
            self.logs_to_record = checkpoint_data['logs_to_record']
            self.all_tools = checkpoint_data['all_tools']
            self.stats = checkpoint_data['stats']
            
            # 恢复会话信息
            self.session_id = checkpoint_data.get('session_id')
            self.history_dir = checkpoint_data.get('history_dir')
            self.initial_run_time = checkpoint_data.get('initial_run_time', 'unknown')
            
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
                    self.user_simulator.conversation_history = checkpoint_data['user_simulator_state'].get('conversation_history', [])
            
            self._debug_print(f"Checkpoint loaded from {checkpoint_data['timestamp']}")
            self._debug_print(f"Resuming from turn {self.stats['interaction_turns']}")
            self._debug_print(f"Session ID: {self.session_id}")
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

    
    async def setup_mcp_servers(self, local_token_key_session: Dict) -> None:
        """设置并连接MCP服务器"""
        self.mcp_manager = MCPServerManager(
            agent_workspace=self.task_config.agent_workspace,
            config_dir=self.mcp_config.server_config_path,
            debug=self.debug,
            local_token_key_session=local_token_key_session
        )
        await self.mcp_manager.connect_servers(self.task_config.needed_mcp_servers)
    
    async def setup_agent(self) -> None:
        """初始化Agent"""
        self._debug_print(">>初始化agent loop")
        
        local_tools = []
        if self.task_config.needed_local_tools is not None:
            for tool_name in self.task_config.needed_local_tools:
                tool_or_toolsets = local_tool_mappings[tool_name]
                if isinstance(tool_or_toolsets, list):
                    local_tools.extend(tool_or_toolsets)
                else:
                    local_tools.append(tool_or_toolsets)

        self.agent = Agent(
            name="Assistant",
            instructions=self.task_config.system_prompts.agent,
            model=self.agent_model_provider.get_model(self.agent_config.model.real_name, 
                                                      debug = self.debug),
            mcp_servers=[*self.mcp_manager.get_all_connected_servers()],
            tools=local_tools,
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
        """处理Agent的响应，返回工具调用列表（简化版本）"""
        tool_calls_in_response = []  # 记录这次响应中的所有工具调用
        
        # 只需要提取工具调用信息用于终止条件检查
        for item in result.new_items:
            if isinstance(item, ToolCallItem):
                tool_item = item.to_input_item()
                tool_call = {
                    "id": tool_item['call_id'],
                    "type": "function",
                    "function": {
                        "name": tool_item["name"],
                        "arguments": tool_item["arguments"]
                    }
                }
                tool_calls_in_response.append(tool_call)
        
        # 更新工具调用统计
        self.stats["tool_calls"] += len(tool_calls_in_response)
        
        # 简化的日志记录（只记录关键信息）
        if result.final_output:
            self.logs_to_record.append({
                "role": "assistant",
                "content": result.final_output,
                "tool_calls_count": len(tool_calls_in_response)
            })
        
        return tool_calls_in_response

    async def run_interaction_loop(self) -> None:
        """运行交互循环"""
        # 使用固定的 session_id
        self.session_id = f"task_{self.task_config.id}_session"
        self.history_dir = os.path.join(self.task_config.task_root, "conversation_history")
        
        # 初始化对话历史
        self.logs = []  # 保留这个，用于传给 Runner
        
        # 初始化共享的 context（重要！）
        self.shared_context = {
            "_agent_workspace": self.task_config.agent_workspace,

            "_session_id": self.session_id,
            "_history_dir": self.history_dir,
            "_context_meta": {
                "session_id": self.session_id,
                "history_dir": self.history_dir,
                "started_at": datetime.datetime.now().isoformat(),
                "current_turn": 0,
                "total_turns_ever": 0,
                "turns_in_current_sequence": 0,
                "mini_turns_in_current_sequence": 0,
                "boundary_in_current_sequence": [],
                "truncated_turns": 0,
                "truncation_history": []
            },
            "_context_limit": get_context_window(self.agent_config.model.short_name)
        }

        # 如果是恢复模式，尝试加载检查点
        resumed = False
        if self.allow_resume:
            resumed = await self._load_checkpoint()
        
        # 处理历史文件
        history_file = os.path.join(self.history_dir, f"{self.session_id}_history.jsonl")
        
        if resumed:
            # 恢复模式：从历史文件重建 logs
            self.logs = self._rebuild_logs_from_history(history_file)
            self._debug_print(f"Resuming session {self.session_id} with {len(self.logs)} messages")
        else:
            # 非恢复模式
            self.initial_run_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 如果存在旧的历史文件，删除它
            if os.path.exists(history_file):
                self._debug_print(f"Removing old history file for session {self.session_id}")
                os.remove(history_file)
            
            self.logs = []
        
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

                # 添加到历史
                self.logs.append({"role": "user", "content": user_query})

                # 在这里单独处理用户轮
                current_turn_in_seq = self.shared_context["_context_meta"]["turns_in_current_sequence"]
                mini_turns_in_current_sequence = self.shared_context["_context_meta"]["mini_turns_in_current_sequence"]
                self.shared_context["_context_meta"]["boundary_in_current_sequence"].append((mini_turns_in_current_sequence, 
                                                                                             mini_turns_in_current_sequence+1))
                
                self.shared_context["_context_meta"]["turns_in_current_sequence"] = current_turn_in_seq + 1
                self.shared_context["_context_meta"]["mini_turns_in_current_sequence"] += 1
                self.shared_context["_context_meta"]["total_turns_ever"] += 1
                self.shared_context["_context_meta"]["current_turn"] += 1

                # 保存用户输入到历史
                current_turn = self.shared_context["_context_meta"]["current_turn"]
                ContextManagedRunner._save_user_input_to_history(
                    session_id=self.session_id,
                    user_input=user_query,
                    history_dir=self.history_dir,
                    turn_number=current_turn
                )

                # 添加到记录
                self.logs_to_record.append({"role": "user", "content": user_query})
                
                # 增加交互轮次计数
                self.stats["interaction_turns"] += 1
                
                # 检查用户输入的终止条件
                if self.termination_checker(user_query, [], 'user'):
                    self._debug_print("Termination condition met by user input")
                    break
                
                # Agent 响应 - 传入完整历史
                result = await ContextManagedRunner.run(
                    starting_agent=self.agent,
                    input=self.logs,  # 传入完整历史
                    context=self.shared_context,  # 使用共享的 context！
                    run_config=RunConfig(model_provider=self.agent_model_provider),
                    hooks=self.run_hooks,
                    max_turns=self.agent_config.tool.max_inner_turns if not self.single_turn_mode else self.task_config.max_steps_under_single_turn_mode,
                    history_dir=self.history_dir,
                    session_id=self.session_id,
                )
                
                # 更新统计信息
                for raw_response in result.raw_responses:
                    self.usage.add(raw_response.usage)
                    self.stats["agent_llm_requests"] += 1

                # 这里是多部执行后，已经合并原始输入和新生成的内容的input
                self.logs = self.build_new_logs(result.input,result.new_items)
                
                # 添加新的响应到历史
                # self.logs.extend([item.to_input_item() for item in result.new_items])
                
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

    def build_new_logs(self, input, generated_items):
        input_items = ItemHelpers.input_to_new_input_list(input)
        input_items.extend([generated_item.to_input_item() for generated_item in generated_items])
        return input_items

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
            os.makedirs(os.path.dirname(res_log_file))
        
        # 从 ContextManagedRunner 获取完整的格式化历史
        if self.session_id and self.history_dir:
            complete_messages = ContextManagedRunner.get_formatted_history(
                self.history_dir,
                self.session_id
            )
            session_stats = ContextManagedRunner.get_session_stats(
                self.history_dir,
                self.session_id
            )
        else:
            # 降级到使用 logs_to_record
            complete_messages = self.logs_to_record
            session_stats = {}

        with open(res_log_file, "w", encoding='utf-8') as f:
            result = {
                'config': self.task_config.to_dict(),
                'request_id': str(uuid.uuid4()),
                'initial_run_time': getattr(self, 'initial_run_time', 'unknown'),
                'completion_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'tool_calls': {
                    'tools': self.all_tools,
                    'tool_choice': self.agent_config.tool.tool_choice,
                },
                "status": self.task_status.value,
                'messages': complete_messages,
                'key_stats': {**self.stats, **session_stats},
                'agent_cost': self.agent_cost,
                'user_cost': self.user_cost,
                'resumed': self.allow_resume,
                'session_id': self.session_id,
                'history_file': str(Path(self.history_dir) / f"{self.session_id}_history.jsonl") if self.session_id else None
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
            await self.setup_mcp_servers(self.task_config.local_token_key_session)
            
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