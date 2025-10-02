from typing import Any, Optional, Dict, List, Tuple, Callable
import os
import json
import uuid
import datetime
import traceback
from enum import Enum
import pickle
from pathlib import Path

# 移除 OpenAI Agents SDK 导入
# from agents import (
#     Agent,
#     RunConfig,
#     Usage,
#     ModelSettings,
#     ToolCallItem,
#     ModelProvider,
#     ItemHelpers
# )
# from agents.exceptions import MaxTurnsExceeded

# 添加 OpenHands SDK 导入
try:
    from openhands.sdk.agent.agent import Agent as OpenHandsAgent
    from openhands.sdk.conversation import Conversation
    from openhands.sdk.conversation.state import ConversationState, AgentExecutionStatus
    from openhands.sdk.event import (
        MessageEvent,
        ActionEvent,
        ObservationEvent,
        AgentErrorEvent,
        UserRejectObservation,
        SystemPromptEvent,
        LLMConvertibleEvent,
    )
    from openhands.sdk.llm import Message, TextContent
except ImportError:
    # Fallback to agent-sdk path
    import sys
    agent_sdk_path = Path(__file__).parent.parent.parent.parent / 'agent-sdk'
    if agent_sdk_path.exists():
        sys.path.insert(0, str(agent_sdk_path))
    from openhands.sdk.agent.agent import Agent as OpenHandsAgent
    from openhands.sdk.conversation import Conversation
    from openhands.sdk.conversation.state import ConversationState, AgentExecutionStatus
    from openhands.sdk.event import (
        MessageEvent,
        ActionEvent,
        ObservationEvent,
        AgentErrorEvent,
        UserRejectObservation,
        SystemPromptEvent,
        LLMConvertibleEvent,
    )
    from openhands.sdk.llm import Message, TextContent

from utils.roles.context_managed_runner import ContextManagedRunner
from utils.api_model.model_provider import ContextTooLongError

from utils.mcp.tool_servers import MCPServerManager
from utils.mcp.openhands_mcp_config import create_openhands_mcp_config

# Import OpenHands SDK for MCP tools
from openhands.sdk.mcp.utils import create_mcp_tools as openhands_create_mcp_tools

# Import LLM adapter
from utils.openhands_adapter import create_openhands_llm_from_config, register_function_tools
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
from utils.aux_tools.overlong_tool_manager import overlong_tool_tools

from utils.general.helper import print_color
from utils.status_manager import TaskStatusManager

# Simple Usage class for compatibility (replaces OpenAI Agents SDK Usage)
class Usage:
    """Simple usage tracking class"""
    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.requests = 0

    def add(self, usage_dict):
        """Add usage from a dictionary"""
        self.input_tokens += usage_dict.get('input_tokens', 0)
        self.output_tokens += usage_dict.get('output_tokens', 0)
        self.requests += 1

local_tool_mappings = {
    "ai_webpage_summary": tool_ai_webpage_summary,
    "sleep": tool_sleep,
    "claim_done": tool_done,
    "manage_context": context_management_tools,
    "history": history_tools,
    'python_execute': tool_python_execute,
    "web_search": tool_web_search,
    "handle_overlong_tool_outputs": overlong_tool_tools,
}

class TaskStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    MAX_TURNS_REACHED = "max_turns_reached"
    INTERRUPTED = "interrupted"  # 新增状态：表示任务被中断

class CustomJSONEncoder(json.JSONEncoder):
    """自定义JSON编码器，用于处理将Python中的布尔值转换为小写的'true'和'false'形式输出，以及处理 UUID 对象"""
    def default(self, o):
        if isinstance(o, bool):
            return str(o).lower()
        if isinstance(o, uuid.UUID):
            return str(o)
        return super().default(o)

class TaskAgent:
    """封装了任务执行的Agent类"""
    
    def __init__(
        self,
        task_config: TaskConfig,
        agent_config: AgentConfig,
        agent_model_provider: Any,  # ModelProvider from utils.api_model.model_provider
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

        self.agent: Optional[OpenHandsAgent] = None  # OpenHands Agent
        self.conversation: Optional[Conversation] = None  # OpenHands Conversation
        self.llm: Optional[Any] = None  # OpenHands LLM
        self.local_tool_executors: Dict[str, Callable] = {}  # 本地工具执行器映射
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
            "cumulative_tool_calls": 0,
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

        # 保存第一轮用户输入，用于上下文重置
        self.first_user_input = None
        self.cumulative_inner_steps = 0  # 累积的inner steps计数

        # 初始化状态管理器
        self.status_manager = TaskStatusManager(task_config.task_root)

    


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
        """
        保存当前执行状态到检查点

        Note: OpenHands Conversation 自动保存状态到 persistence_dir
        这里只保存兼容性数据
        """
        if not self.allow_resume:
            return

        checkpoint_data = {
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
            'initial_run_time': getattr(self, 'initial_run_time', 'unknown'),
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'version': '3.0'  # OpenHands version
        }

        try:
            with open(self._get_checkpoint_path(), 'wb') as f:
                pickle.dump(checkpoint_data, f)
            self._debug_print(f"Checkpoint saved at turn {self.stats['interaction_turns']}")
        except Exception as e:
            self._debug_print(f"Failed to save checkpoint: {e}")

    async def _load_checkpoint(self) -> bool:
        """
        从检查点恢复执行状态

        Note: OpenHands Conversation 会从 persistence_dir 自动恢复
        这里只恢复兼容性数据
        """
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
            if version in ['1.0', '2.0']:
                self._debug_print("Old checkpoint version detected, cannot resume with OpenHands")
                return False

            # 恢复状态
            self.logs_to_record = checkpoint_data['logs_to_record']
            self.all_tools = checkpoint_data['all_tools']
            self.stats = checkpoint_data['stats']

            # 恢复会话信息
            self.session_id = checkpoint_data.get('session_id')
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
        self._debug_print(f"\n\nStarting to initialize workspace for {self.task_config.id} ...")
        
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
                args = f"--agent_workspace {self.task_config.agent_workspace} --launch_time \"{self.task_config.launch_time}\""
                command = f"{self.task_config.initialization.process_command} {args}"
                output, error, returncode = await run_command(command,debug=self.debug)
                if self.debug:
                    print_color("== PreProcess STDOUT ==", "red")
                # self._debug_print("== PreProcess STDOUT ==")
                self._debug_print(output)
                if self.debug:
                    print_color("== PreProcess STDERR ==", "red")
                # self._debug_print("== PreProcess STDERR ==")
                self._debug_print(error)
                if returncode != 0:
                    raise RuntimeError(f"PreProcess command failed! returncode: {returncode}")
                
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
        """
        设置并初始化 MCP 服务器（使用 OpenHands SDK）

        这个方法会：
        1. 将 YAML 配置转换为 OpenHands 格式
        2. 使用 OpenHands SDK 的 create_mcp_tools 创建工具
        3. 存储工具列表供 setup_agent 使用
        """
        if self.debug:
            print_color("\n=== Starting to setup MCP servers (OpenHands) ===", "blue")

        # 创建 OpenHands 格式的 MCP 配置
        self.openhands_mcp_config = create_openhands_mcp_config(
            agent_workspace=self.task_config.agent_workspace,
            config_dir=self.mcp_config.server_config_path,
            server_names=self.task_config.needed_mcp_servers,
            local_token_key_session=local_token_key_session,
            debug=self.debug
        )

        if self.debug:
            print_color(f"Created OpenHands MCP config for {len(self.openhands_mcp_config.get('mcpServers', {}))} servers", "blue")
            for server_name in self.openhands_mcp_config.get('mcpServers', {}).keys():
                print_color(f"  - {server_name}", "blue")

        # 使用 OpenHands SDK 创建 MCP 工具
        # 注意：这会临时连接服务器获取工具列表，然后断开
        if openhands_create_mcp_tools is not None:
            try:
                self.mcp_tools = openhands_create_mcp_tools(
                    config=self.openhands_mcp_config,
                    timeout=30.0
                )

                if self.debug:
                    print_color(f"Successfully created {len(self.mcp_tools)} MCP tools from OpenHands SDK", "green")
                    # 显示前几个工具
                    tool_names = [t.name for t in self.mcp_tools[:5]]
                    print_color(f"Sample tools: {tool_names}", "blue")
                    if len(self.mcp_tools) > 5:
                        print_color(f"... and {len(self.mcp_tools) - 5} more tools", "blue")

            except Exception as e:
                print_color(f"Error creating MCP tools from OpenHands SDK: {e}", "red")
                if self.debug:
                    import traceback
                    traceback.print_exc()
                self.mcp_tools = []
        else:
            print_color("Warning: OpenHands SDK not available, no MCP tools created", "yellow")
            self.mcp_tools = []

        # 保留对原 MCPServerManager 的引用（兼容性）
        # 但不再实际使用它进行连接
        self.mcp_manager = None
    
    async def setup_agent(self) -> None:
        """
        初始化 OpenHands Agent 和 Conversation

        替换原有的 OpenAI Agents SDK，使用 OpenHands SDK：
        1. 创建 OpenHands LLM
        2. 收集本地工具 + MCP 工具
        3. 转换本地工具为 OpenHands 格式
        4. 创建 OpenHands Agent
        5. 创建 Conversation
        """
        self._debug_print(">>初始化 OpenHands agent 和 conversation")

        # 1. 创建 OpenHands LLM（替代原来的 Model）
        self.llm = create_openhands_llm_from_config(
            agent_config=self.agent_config,
            agent_model_provider=self.agent_model_provider,
            debug=self.debug,
        )

        if self.debug:
            print_color(f"Created OpenHands LLM: {self.llm.model}", "blue")

        # 2. 收集本地 FunctionTool 对象
        local_function_tools = []
        if self.task_config.needed_local_tools is not None:
            for tool_name in self.task_config.needed_local_tools:
                tool_or_toolsets = local_tool_mappings[tool_name]
                if isinstance(tool_or_toolsets, list):
                    local_function_tools.extend(tool_or_toolsets)
                else:
                    local_function_tools.append(tool_or_toolsets)

        # 3. 转换本地工具为 OpenHands ToolSpec 并注册
        # 这会创建完整的 Tool 对象，注册到 OpenHands 工具注册表，并返回 ToolSpec 列表
        local_toolspecs = register_function_tools(local_function_tools) if local_function_tools else []

        if self.debug and local_toolspecs:
            print_color(f"Registered {len(local_toolspecs)} local tools to OpenHands registry", "blue")
            for spec in local_toolspecs[:3]:  # 显示前3个
                print_color(f"  - {spec.name}", "blue")

        # 4. 处理并注册 MCP tools
        all_toolspecs = local_toolspecs
        if hasattr(self, 'mcp_tools') and self.mcp_tools:
            # MCP tools 是 Tool 实例，需要注册到全局注册表
            from openhands.sdk.tool import ToolSpec, register_tool

            mcp_toolspecs = []
            for mcp_tool in self.mcp_tools:
                # 注册 MCP Tool 实例到全局注册表
                register_tool(mcp_tool.name, mcp_tool)

                # 创建 ToolSpec（不带 params，因为是固定实例）
                mcp_toolspecs.append(ToolSpec(
                    name=mcp_tool.name,
                    params={}  # 固定实例不支持 params
                ))

            all_toolspecs = local_toolspecs + mcp_toolspecs

            if self.debug:
                print_color(f"Agent will use {len(local_toolspecs)} local tools + {len(mcp_toolspecs)} MCP tools", "blue")
                print_color(f"Registered {len(mcp_toolspecs)} MCP tools to OpenHands registry", "blue")
        else:
            if self.debug:
                print_color(f"Agent will use {len(local_toolspecs)} local tools (no MCP tools)", "yellow")

        # 5. 创建 OpenHands Agent（使用 ToolSpec 列表）
        self.agent = OpenHandsAgent(
            llm=self.llm,
            tools=all_toolspecs,  # 传入 ToolSpec 列表
            system_message=self.task_config.system_prompts.agent,
        )

        # 6. 创建 Conversation
        persistence_dir = Path(self.task_config.agent_workspace) / 'conversation_state'
        persistence_dir.mkdir(parents=True, exist_ok=True)

        self.conversation = Conversation(
            agent=self.agent,
            workspace=str(self.task_config.agent_workspace),  # 正确参数名：workspace
            persistence_dir=str(persistence_dir),
            max_iteration_per_run=self.agent_config.tool.max_inner_turns,
            callbacks=[self._on_event],
            visualize=False,  # 禁用默认可视化
        )

        if self.debug:
            print_color(f"Created OpenHands Conversation: {self.conversation.id}", "green")

        # 7. 维护 self.all_tools（用于 User simulator）
        # 从本地 FunctionTool 提取 OpenAI 格式
        for function_tool in local_function_tools:
            self.all_tools.append({
                "type": "function",
                "function": {
                    "name": function_tool.name,
                    "description": function_tool.description,
                    "parameters": function_tool.params_json_schema
                }
            })

        # 从 MCP tools 提取 OpenAI 格式
        if hasattr(self, 'mcp_tools') and self.mcp_tools:
            for mcp_tool in self.mcp_tools:
                if hasattr(mcp_tool, 'to_openai_tool'):
                    openai_tool = mcp_tool.to_openai_tool()
                    self.all_tools.append(openai_tool)

        if self.debug:
            print_color(f"Populated {len(self.all_tools)} tools for User simulator compatibility", "blue")

    def _on_event(self, event) -> None:
        """
        OpenHands 事件回调

        处理 Conversation 产生的事件，用于：
        1. 维护 logs_to_record（用于最终记录）
        2. 更新统计信息
        3. 调试输出
        """
        # 更新 logs_to_record
        if isinstance(event, MessageEvent):
            if event.source == "user":
                # 用户消息已经在 run_interaction_loop 中添加
                pass
            elif event.source == "agent":
                # Agent 消息 - 使用辅助方法提取文本
                content = self._extract_text_from_message_event(event)

                self.logs_to_record.append({
                    "role": "assistant",
                    "content": content
                })

                if self.debug:
                    preview = content[:100] + "..." if len(content) > 100 else content
                    print_color(f"[Agent Message] {preview}", "yellow")

        elif isinstance(event, ActionEvent):
            # 工具调用（所有工具，包括本地和 MCP）
            # 注意：不再手动更新 self.stats，统计信息由 OpenHands conversation.state 管理
            if self.debug:
                print_color(f"[Action] {event.tool_name}", "cyan")

        elif isinstance(event, ObservationEvent):
            # 工具结果（正常情况）
            if self.debug:
                # 显示工具结果的前100个字符
                content = str(event.observation.to_llm_content) if hasattr(event.observation, 'to_llm_content') else str(event.observation)
                preview = content[:100] + "..." if len(content) > 100 else content
                print_color(f"[Observation] {event.tool_name}: {preview}", "green")

        elif isinstance(event, (AgentErrorEvent, UserRejectObservation)):
            # 错误或拒绝
            if self.debug:
                if isinstance(event, AgentErrorEvent):
                    print_color(f"[Agent Error] {event.tool_name}: {event.error}", "red")
                else:
                    print_color(f"[User Reject] {event.tool_name}: {event.rejection_reason}", "red")

        # 追踪 token 使用（从 LLM 响应事件）
        # OpenHands 在 conversation.state 中维护统计，这里只做调试输出
        if self.debug and hasattr(event, 'usage'):
            usage = event.usage
            if usage:
                self._debug_print(f"[Token Usage] Input: {usage.get('input_tokens', 0)}, Output: {usage.get('output_tokens', 0)}")

    def _extract_stats_from_conversation(self) -> None:
        """
        从 conversation.state 提取统计信息到 self.stats 和 self.usage

        这个方法用于兼容性 - 在需要时从 OpenHands 的单一数据源提取信息
        """
        if not self.conversation or not hasattr(self.conversation, 'state'):
            return

        # 获取 OpenHands 的统计信息
        metrics = self.conversation.state.stats.get_combined_metrics()

        # 更新 self.usage（兼容性）
        if metrics.accumulated_token_usage:
            self.usage.input_tokens = metrics.accumulated_token_usage.prompt_tokens
            self.usage.output_tokens = metrics.accumulated_token_usage.completion_tokens
            # 通过 costs 列表估算请求数
            self.usage.requests = len(metrics.costs)

        # 更新 self.stats（兼容性）
        self.stats["total_tokens"] = self.usage.input_tokens + self.usage.output_tokens
        self.stats["input_tokens"] = self.usage.input_tokens
        self.stats["output_tokens"] = self.usage.output_tokens
        self.stats["agent_llm_requests"] = self.usage.requests

        # 从事件中统计工具调用次数
        if hasattr(self.conversation.state, 'events'):
            action_events = [e for e in self.conversation.state.events if isinstance(e, ActionEvent)]
            self.stats["cumulative_tool_calls"] = len(action_events)
            self.stats["tool_calls"] = len(action_events)

    @staticmethod
    def _extract_text_from_message_event(event: MessageEvent) -> str:
        """
        从 MessageEvent 提取文本内容

        MessageEvent.llm_message.content 是 List[TextContent | ImageContent]
        """
        text_parts = []
        for content_item in event.llm_message.content:
            if hasattr(content_item, 'text'):
                text_parts.append(content_item.text)
        return "".join(text_parts)

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

    async def run_interaction_loop(self,
                                   abs_original_task_root: str) -> None:
        """
        运行交互循环（OpenHands SDK 版本）

        使用 Conversation.run() 替代原有的 ContextManagedRunner.run()
        OpenHands 自动管理上下文和事件历史
        """
        # 初始化 session id（保持兼容性）
        self.session_id = f"task_{self.task_config.id}_session"
        self.initial_run_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 确定最大轮次
        max_turns = 1 if self.single_turn_mode else self.task_config.max_turns

        if self.debug:
            print_color("=== Starting interaction loop (OpenHands) ===", "blue")

        # 主交互循环
        while self.stats["interaction_turns"] < max_turns:
            try:
                # 1. 获取用户输入
                if self.single_turn_mode:
                    user_query = self.task_config.task_str
                elif self.manual:
                    user_query = await self.ainput("USER: ")
                else:
                    user_query = await self.user_simulator.interact()
                    self._debug_print(f"USER: {user_query}")

                # 保存第一轮用户输入
                if self.first_user_input is None:
                    self.first_user_input = user_query

                # 检查用户输入的终止条件
                if self.termination_checker(user_query, [], 'user'):
                    self._debug_print("Termination condition met by user input")
                    break

                # 记录用户消息
                self.logs_to_record.append({"role": "user", "content": user_query})

                # 2. 发送消息到 Conversation
                self.conversation.send_message(user_query)

                # 记录当前事件数量（用于提取新事件）
                events_before = len(self.conversation.state.events)

                # 3. 运行 Conversation（同步调用，OpenHands 内部处理异步）
                try:
                    self.conversation.run()
                except Exception as e:
                    self._debug_print(f"Error during conversation.run(): {e}")
                    if self.debug:
                        import traceback
                        traceback.print_exc()
                    # 继续执行，让外层错误处理逻辑处理
                    raise

                # 4. 提取新事件并更新统计
                new_events = self.conversation.state.events[events_before:]

                # 从新事件中提取最后一条 agent 消息（如果有）
                last_agent_message = None
                for event in reversed(new_events):
                    if isinstance(event, MessageEvent) and event.source == "agent":
                        # 使用辅助方法提取文本
                        last_agent_message = self._extract_text_from_message_event(event)
                        break

                # 5. 发送 agent 响应给 user simulator
                if last_agent_message and not self.manual and not self.single_turn_mode:
                    self.user_simulator.receive_message(last_agent_message)

                # 6. 增加交互轮次
                self.stats["interaction_turns"] += 1

                # 7. 检查终止条件
                # 检查 agent 状态
                if self.conversation.state.agent_status == AgentExecutionStatus.FINISHED:
                    self._debug_print("Agent finished execution")
                    break

                # 检查 agent 响应的终止条件
                if last_agent_message:
                    # 从新事件中提取工具调用（用于终止检查）
                    recent_tool_calls = []
                    for event in new_events:
                        if isinstance(event, ActionEvent):
                            recent_tool_calls.append({
                                "type": "function",
                                "function": {"name": event.tool_name}
                            })

                    if self.termination_checker(last_agent_message, recent_tool_calls, 'agent'):
                        self._debug_print("Termination condition met by agent response")
                        break

                # 8. 单轮模式只执行一次
                if self.single_turn_mode:
                    break

                # 9. 定期保存检查点
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
        if self.stats["interaction_turns"] >= max_turns:
            self._debug_print(f"Maximum turns ({max_turns}) reached")
            self.task_status = TaskStatus.MAX_TURNS_REACHED

        # 从 conversation.state 提取最终统计信息（单一数据源）
        self._extract_stats_from_conversation()

    def get_cost_summary(self) -> Tuple[Dict, Dict]:
        """获取成本摘要（从 OpenHands conversation.state 提取）"""
        # 确保统计信息是最新的
        self._extract_stats_from_conversation()

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

        agent_cost = {
            "total_cost": round(total_cost,4),
            "total_input_tokens": self.usage.input_tokens,
            "total_output_tokens": self.usage.output_tokens,
            "total_requests": self.usage.requests,
        }

        return user_cost, agent_cost
    
    async def save_results(self) -> None:
        """
        保存运行结果到日志文件（OpenHands 版本）

        统计信息来源：
        - self.stats 和 self.usage: 通过 _extract_stats_from_conversation() 从 conversation.state 提取
        - session_stats: 直接从 conversation.state.events 计算
        - logs_to_record: 在 _on_event 回调中维护
        """
        # 确保统计信息是最新的
        self._extract_stats_from_conversation()

        res_log_file = self.task_config.log_file

        if not os.path.exists(os.path.dirname(res_log_file)):
            os.makedirs(os.path.dirname(res_log_file))

        # 使用 logs_to_record（已经在 _on_event 和 run_interaction_loop 中维护）
        complete_messages = self.logs_to_record

        # 从 conversation.state 计算 session stats
        session_stats = {}
        if hasattr(self, 'conversation') and self.conversation:
            # 统计事件数量
            total_events = len(self.conversation.state.events)
            action_events = sum(1 for e in self.conversation.state.events if isinstance(e, ActionEvent))
            message_events = sum(1 for e in self.conversation.state.events if isinstance(e, MessageEvent))

            session_stats = {
                'total_events': total_events,
                'action_events': action_events,
                'message_events': message_events,
                'agent_status': str(self.conversation.state.agent_status) if hasattr(self.conversation.state, 'agent_status') else 'unknown'
            }

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
                'conversation_id': self.conversation.id if hasattr(self, 'conversation') and self.conversation else None
            }

            json_output = json.dumps(result, ensure_ascii=False, cls=CustomJSONEncoder)
            f.write(json_output)

    
    async def cleanup(self) -> None:
        """
        清理资源

        注意：使用 OpenHands MCP 后，不再需要手动断开 MCP 服务器
        因为 OpenHands 的工具在每次调用时自动连接/断开
        """
        # OpenHands MCP 工具会自动管理连接，无需手动清理
        # 保留方法以维持兼容性
        if self.debug:
            print_color("Cleanup: OpenHands MCP tools handle connections automatically", "blue")
        pass
    
    async def run(self) -> TaskStatus:
        """运行整个任务"""

        # 保存当前工作目录
        current_dir = os.path.abspath(os.getcwd())

        try:
            # 设置日志文件路径
            self.task_config.log_file = os.path.join(self.task_config.task_root, "traj_log.json")
            self.task_config.agent_workspace = os.path.join(self.task_config.task_root, "workspace")

            # 开始预处理
            self.status_manager.update_preprocess("running")

            # 初始化工作区（如果允许恢复且有检查点，则跳过重新初始化）
            if not await self.initialize_workspace():
                self.status_manager.update_preprocess("fail")
                return TaskStatus.FAILED

            # 预处理成功
            self.status_manager.update_preprocess("done")
            
            # 在这里读取预处理后task-specific的token_key_session.py，并赋值给task_config.local_token_key_session
            self.task_config.load_local_token_key_session()

            # 设置MCP服务器
            await self.setup_mcp_servers(self.task_config.local_token_key_session)
            
            # 设置Agent
            await self.setup_agent()
            
            # 设置用户模拟器
            await self.setup_user_simulator()
            
            # 切换工作目录为agent_workspace
            os.chdir(self.task_config.agent_workspace)
            self._debug_print(f"Switched working directory to {self.task_config.agent_workspace}")

            # 开始运行任务
            self.status_manager.update_running("running")

            # 运行交互循环
            await self.run_interaction_loop(os.path.abspath(self.task_config.task_root))

            # 切换回原工作目录
            os.chdir(current_dir)
            self._debug_print(f"Switched back working directory to {current_dir}")
            
            # 如果没有设置其他状态，则为成功
            if self.task_status not in [TaskStatus.MAX_TURNS_REACHED, TaskStatus.INTERRUPTED]:
                self.task_status = TaskStatus.SUCCESS
                self.status_manager.update_running("done")
            elif self.task_status == TaskStatus.MAX_TURNS_REACHED:
                self.status_manager.update_running("max_turn_exceeded")
            
            # 任务完成，删除检查点
            if self.task_status == TaskStatus.SUCCESS:
                self._remove_checkpoint()
                
        except KeyboardInterrupt:
            self._debug_print("Task interrupted by user")
            if self.task_status != TaskStatus.INTERRUPTED:
                self.task_status = TaskStatus.INTERRUPTED
                
        except Exception as e:
            # a strange logic, 
            #  - max-turn update the task status in `self._debug_print(f"[THIS IS A TAG FOR MAX TURNS EXCEEDED] Max turns exceeded: {e}")`
            #  - but it will will raise an error in `raise RuntimeError(f"Failed to get agent response within {max_inner_steps} inner steps")`, leading us to this block
            #  - so we need to use status_manager to update status here
            self._debug_print("Error when running agent -", e)
            if self.debug:
                traceback.print_exc()
            if self.task_status == TaskStatus.MAX_TURNS_REACHED:
                self.status_manager.update_running("max_turn_exceeded")
            else:
                self.task_status = TaskStatus.FAILED
                # 运行阶段失败（预处理已经成功了，否则不会到这里）
                self.status_manager.update_running("fail")
            
        finally:
            # 切换回原工作目录，in all cases
            os.chdir(current_dir)
            self._debug_print(f"Switched back working directory to {current_dir}")

            # 计算最终的成本摘要（这会更新token统计）
            user_cost, agent_cost = self.get_cost_summary()
            
            self.user_cost = user_cost
            self.agent_cost = agent_cost

            # 打印成本摘要
            self._debug_print(f"===LLM-simulator（{self.user_config.model.short_name}）Cost Summary===")
            for k, v in user_cost.items():
                self._debug_print(f"{k} : {v}")
            self._debug_print(f"===Agent（{self.agent_config.model.short_name}）Cost Summary===")
            for k, v in agent_cost.items():
                self._debug_print(f"{k} : {v}")
            self._debug_print("===Key Statistics===")
            for k, v in self.stats.items():
                self._debug_print(f"{k} : {v}")
            
            # 保存结果
            await self.save_results()
            
            # 清理资源
            await self.cleanup()
            
        return self.task_status