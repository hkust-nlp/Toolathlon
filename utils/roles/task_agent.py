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


# from utils.roles.context_managed_runner import ContextManagedRunner
# from utils.api_model.model_provider import ContextTooLongError

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
    INTERRUPTED = "interrupted"  # New status: task interrupted

class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON Encoder: write Python booleans as lowercase 'true'/'false'."""
    def default(self, o):
        if isinstance(o, bool):
            return str(o).lower()
        if isinstance(o, uuid.UUID):
            return str(o)
        return super().default(o)

class TaskAgent:
    """Encapsulates an agent class to execute tasks."""
    
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
        
        # Stats info
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
            # global prompt session
            self._session = PromptSession()
        
        # Checkpoint file path
        self.checkpoint_file = None
        self.checkpoint_interval = 1  # Save checkpoint every N turns

        self.single_turn_mode = single_turn_mode

        self.shared_context = {}

        # Save first-round user input for context reset
        self.first_user_input = None
        self.cumulative_inner_steps = 0  # Total count of assistant "inner steps"

        # Task status manager
        self.status_manager = TaskStatusManager(task_config.task_root)

    async def ainput(self, prompt='> '):
        """Async version of input()."""
        with patch_stdout():
            return await self._session.prompt_async(prompt)

    def _debug_print(self, *args):
        if self.debug:
            print(*args)

    def _patch_agent_error_event_for_claude(self):
        """
        Monkey patch AgentErrorEvent.to_llm_message() for Claude API compatibility

        Claude API requires tool_result messages to have a corresponding tool_use block.
        When AgentErrorEvent is created (e.g., tool not found, argument validation error),
        there's no ActionEvent created, so Claude API rejects the error message.

        Solution: Convert AgentErrorEvent to a user message instead of tool message.
        This allows the agent to see the error and adjust its strategy without
        violating Claude API's strict tool_use/tool_result pairing requirement.
        """
        from openhands.sdk.event.llm_convertible import AgentErrorEvent
        from openhands.sdk.llm import Message, TextContent

        # Store original method
        original_to_llm_message = AgentErrorEvent.to_llm_message

        def patched_to_llm_message(self):
            """
            Patched version that converts error to user message for Claude compatibility

            Original behavior (causes Claude API error):
                role="tool", tool_call_id=<id>

            New behavior (Claude compatible):
                role="user", content="[Tool Error - {tool_name}] {error}"
            """
            return Message(
                role="user",
                content=[TextContent(text=f"[Tool Error - {self.tool_name}] {self.error}")],
            )

        # Apply patch
        AgentErrorEvent.to_llm_message = patched_to_llm_message

        if self.debug:
            print_color("[Patch] Applied AgentErrorEvent patch for Claude API compatibility", "green")

    def _default_termination_checker(self, content: str, recent_tools: List[Dict], check_target: str = "user") -> bool:
        """Default termination checker."""
        if check_target == 'user':
            return '#### STOP' in content
        return False
    
    def _get_checkpoint_path(self) -> str:
        """Get checkpoint file path."""
        if self.checkpoint_file is None:
            self.checkpoint_file = os.path.join(self.task_config.task_root, "checkpoint.pkl")
        return self.checkpoint_file
    
    async def _save_checkpoint(self) -> None:
        """Save current state to checkpoint."""
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
        """Restore state from checkpoint, if possible."""
        if not self.allow_resume:
            return False

        checkpoint_path = self._get_checkpoint_path()
        if not os.path.exists(checkpoint_path):
            self._debug_print("No checkpoint found")
            return False

        try:
            with open(checkpoint_path, 'rb') as f:
                checkpoint_data = pickle.load(f)
            
            # Version check
            version = checkpoint_data.get('version', '1.0')
            if version in ['1.0', '2.0']:
                self._debug_print("Old checkpoint version detected, cannot resume with OpenHands")
                return False

            # Restore state
            self.logs_to_record = checkpoint_data['logs_to_record']
            self.all_tools = checkpoint_data['all_tools']
            self.stats = checkpoint_data['stats']

            # Restore session info
            self.session_id = checkpoint_data.get('session_id')
            self.initial_run_time = checkpoint_data.get('initial_run_time', 'unknown')
            
            # Restore usage object
            usage_data = checkpoint_data['usage']
            self.usage.input_tokens = usage_data['input_tokens']
            self.usage.output_tokens = usage_data['output_tokens']
            self.usage.requests = usage_data['requests']
            
            # Restore user simulator state
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
        """Remove checkpoint file."""
        checkpoint_path = self._get_checkpoint_path()
        if os.path.exists(checkpoint_path):
            try:
                os.remove(checkpoint_path)
                self._debug_print("Checkpoint removed")
            except Exception as e:
                self._debug_print(f"Failed to remove checkpoint: {e}")

    async def initialize_workspace(self, show_traceback=False) -> bool:
        """Initialize workspace."""
        self._debug_print(f"\n\nStarting to initialize workspace for {self.task_config.id} ...")
        
        log_file = self.task_config.log_file
        agent_workspace = self.task_config.agent_workspace
        initial_state_workspace = self.task_config.initialization.workspace

        try:
            # If resume is allowed and checkpoint exists, skip reinitializing
            if self.allow_resume and os.path.exists(agent_workspace) and os.path.exists(self._get_checkpoint_path()):
                self._debug_print("Found existing workspace and checkpoint, will attempt to resume")
                return True
            
            # Otherwise do a normal workspace init
            if os.path.exists(agent_workspace):
                self._debug_print("Reset/Remove an existing agent workspace.")
                shutil.rmtree(agent_workspace)

            if os.path.exists(log_file):
                self._debug_print("Reset/Remove an existing log file.")
                os.remove(log_file)
            
            # Remove old checkpoint
            self._remove_checkpoint()
            
            # Copy initial state files
            await copy_folder_contents(initial_state_workspace, agent_workspace, self.debug)

            # Pre-processing command if any
            if self.task_config.initialization.process_command is not None:
                args = f"--agent_workspace {self.task_config.agent_workspace} --launch_time \"{self.task_config.launch_time}\""
                command = f"{self.task_config.initialization.process_command} {args}"
                output, error, returncode = await run_command(command, debug=self.debug)
                if self.debug:
                    print_color("== PreProcess STDOUT ==", "red")
                self._debug_print(output)
                if self.debug:
                    print_color("== PreProcess STDERR ==", "red")
                self._debug_print(error)
                if returncode != 0:
                    raise RuntimeError(f"PreProcess command failed! returncode: {returncode}")
                
            # MCP-specific workspace initialization
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
        Setup and initialize MCP servers (using OpenHands SDK)

        This method will:
        1. Convert YAML config to OpenHands format
        2. Use OpenHands SDK's create_mcp_tools to create tools
        3. Store tool list for setup_agent use
        """
        if self.debug:
            print_color("\n=== Starting to setup MCP servers (OpenHands) ===", "blue")

        # Create OpenHands MCP config
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

        # Use OpenHands SDK to create MCP tools
        # Note: This will temporarily connect to servers to get tool list, then disconnect
        if openhands_create_mcp_tools is not None:
            try:
                self.mcp_tools = openhands_create_mcp_tools(
                    config=self.openhands_mcp_config,
                    timeout=30.0
                )

                if self.debug:
                    print_color(f"Successfully created {len(self.mcp_tools)} MCP tools from OpenHands SDK", "green")
                    # Show first few tools
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

        # Keep reference to original MCPServerManager (compatibility)
        # But no longer actually use it for connections
        self.mcp_manager = None
    
    async def setup_agent(self) -> None:
        """
        Initialize OpenHands Agent and Conversation

        Replace original OpenAI Agents SDK with OpenHands SDK:
        1. Create OpenHands LLM
        2. Collect local tools + MCP tools
        3. Convert local tools to OpenHands format
        4. Create OpenHands Agent
        5. Create Conversation
        """
        self._debug_print(">>Initialize OpenHands agent and conversation")

        # Monkey patch AgentErrorEvent for Claude API compatibility
        # This fixes the issue where Claude API rejects tool_result messages
        # with tool_use_id that don't have a corresponding tool_use block
        self._patch_agent_error_event_for_claude()

        # 1. Create OpenHands LLM (replace original Model)
        self.llm = create_openhands_llm_from_config(
            agent_config=self.agent_config,
            agent_model_provider=self.agent_model_provider,
            debug=self.debug,
        )

        if self.debug:
            print_color(f"Created OpenHands LLM: {self.llm.model}", "blue")

        # 2. Collect local FunctionTool objects
        local_function_tools = []
        if self.task_config.needed_local_tools is not None:
            for tool_name in self.task_config.needed_local_tools:
                tool_or_toolsets = local_tool_mappings[tool_name]
                if isinstance(tool_or_toolsets, list):
                    local_function_tools.extend(tool_or_toolsets)
                else:
                    local_function_tools.append(tool_or_toolsets)

        # 3. Convert local tools to OpenHands ToolSpec and register
        # This will create full Tool objects, register to OpenHands tool registry, and return ToolSpec list
        local_toolspecs = register_function_tools(local_function_tools) if local_function_tools else []

        if self.debug and local_toolspecs:
            print_color(f"Registered {len(local_toolspecs)} local tools to OpenHands registry", "blue")
            for spec in local_toolspecs[:3]:  # Show first 3
                print_color(f"  - {spec.name}", "blue")

        # 4. Process and register MCP tools
        all_toolspecs = local_toolspecs
        if hasattr(self, 'mcp_tools') and self.mcp_tools:
            # MCP tools are Tool instances, need to register to global registry
            from openhands.sdk.tool import ToolSpec, register_tool

            mcp_toolspecs = []
            for mcp_tool in self.mcp_tools:
                # Register MCP Tool instance to global registry
                register_tool(mcp_tool.name, mcp_tool)

                # Create ToolSpec (no params, because it's fixed instance)
                mcp_toolspecs.append(ToolSpec(
                    name=mcp_tool.name,
                    params={}  # Fixed instance doesn't support params
                ))

            all_toolspecs = local_toolspecs + mcp_toolspecs

            if self.debug:
                print_color(f"Agent will use {len(local_toolspecs)} local tools + {len(mcp_toolspecs)} MCP tools", "blue")
                print_color(f"Registered {len(mcp_toolspecs)} MCP tools to OpenHands registry", "blue")
        else:
            if self.debug:
                print_color(f"Agent will use {len(local_toolspecs)} local tools (no MCP tools)", "yellow")

        # 5. Create OpenHands Agent (using ToolSpec list)
        # Create AgentContext to add builtin tools usage instructions (fix kind field problem)
        from openhands.sdk.context import AgentContext

        context = AgentContext(
            system_message_suffix="""
<CRITICAL_TOOL_USAGE_RULES>
IMPORTANT: When calling tools, DO NOT manually provide the 'kind' field.
The 'kind' field is automatically managed by the system and should NEVER be included in your tool call arguments.

Correct tool usage:
- think tool: {"thought": "your reasoning and analysis"}
- finish tool: {"message": "task completion summary"}

Incorrect usage (will cause validation errors):
- {"kind": "planning", "thought": "..."}  ❌ WRONG
- {"kind": "success", "message": "..."}   ❌ WRONG

The 'kind' field may appear in tool schemas but is SYSTEM-MANAGED ONLY.
Never include it in your tool call arguments.
</CRITICAL_TOOL_USAGE_RULES>

<TASK_COMPLETION_PROTOCOL>
CRITICAL: When you have completed the task, you MUST call the 'finish' tool.

Usage: finish(message="summary of accomplishments")

Call this when:
- You have successfully completed the user's requested task
- All objectives have been met
- No further actions are needed

WITHOUT calling finish, the system will NOT recognize task completion!
</TASK_COMPLETION_PROTOCOL>
"""
        )

        self.agent = OpenHandsAgent(
            llm=self.llm,
            tools=all_toolspecs,  # Pass ToolSpec list
            agent_context=context,  # Add tool usage instructions
            system_message=self.task_config.system_prompts.agent,
            filter_tools_regex="^(?!think|finish).*$",  # Filter out think and finish tools (exist kind validation problem)
        )

        # 6. Create Conversation (explicitly enable stuck detection)
        persistence_dir = Path(self.task_config.agent_workspace) / 'conversation_state'
        persistence_dir.mkdir(parents=True, exist_ok=True)

        self.conversation = Conversation(
            agent=self.agent,
            workspace=str(self.task_config.agent_workspace),  # Correct parameter name: workspace
            persistence_dir=str(persistence_dir),
            max_iteration_per_run=self.agent_config.tool.max_inner_turns,  # Maximum steps per single run()
            callbacks=[self._on_event],
            visualize=False,  # Disable default visualization
            stuck_detection=True,  # Explicitly enable stuck detection
        )

        if self.debug:
            print_color(f"Created OpenHands Conversation: {self.conversation.id}", "green")
            print_color(f"  Max iteration per run: {self.conversation.max_iteration_per_run}", "green")
            print_color(f"  Stuck detection: {self.conversation.stuck_detector is not None}", "green")

        # 7. Maintain self.all_tools (for User simulator)
        # Extract OpenAI format from local FunctionTool
        for function_tool in local_function_tools:
            self.all_tools.append({
                "type": "function",
                "function": {
                    "name": function_tool.name,
                    "description": function_tool.description,
                    "parameters": function_tool.params_json_schema
                }
            })

        # Extract OpenAI format from MCP tools
        if hasattr(self, 'mcp_tools') and self.mcp_tools:
            for mcp_tool in self.mcp_tools:
                if hasattr(mcp_tool, 'to_openai_tool'):
                    openai_tool = mcp_tool.to_openai_tool()
                    self.all_tools.append(openai_tool)

        if self.debug:
            print_color(f"Populated {len(self.all_tools)} tools for User simulator compatibility", "blue")

    def _on_event(self, event) -> None:
        """
        OpenHands event callback

        Handle events produced by Conversation, for:
        1. Maintain logs_to_record (for final recording)
        2. Update statistics
        3. Debug output
        """
        # Update logs_to_record
        if isinstance(event, MessageEvent):
            if event.source == "user":
                # User message already added in run_interaction_loop
                pass
            elif event.source == "agent":
                # Agent message - use helper method to extract text
                content = self._extract_text_from_message_event(event)

                self.logs_to_record.append({
                    "role": "assistant",
                    "content": content
                })

                if self.debug:
                    preview = content[:100] + "..." if len(content) > 100 else content
                    print_color(f"[Agent Message] {preview}", "yellow")

        elif isinstance(event, ActionEvent):
            # Tool calls (all tools, including local and MCP)
            # Note: No longer manually update self.stats, statistics are managed by OpenHands conversation.state
            if self.debug:
                print_color(f"[Action] {event.tool_name}", "cyan")

        elif isinstance(event, ObservationEvent):
            # Tool result (normal case)
            if self.debug:
                # Show first 100 characters of tool result
                content = str(event.observation.to_llm_content) if hasattr(event.observation, 'to_llm_content') else str(event.observation)
                preview = content[:100] + "..." if len(content) > 100 else content
                print_color(f"[Observation] {event.tool_name}: {preview}", "green")

        elif isinstance(event, (AgentErrorEvent, UserRejectObservation)):
            # Error or rejection
            if self.debug:
                if isinstance(event, AgentErrorEvent):
                    print_color(f"[Agent Error] {event.tool_name}: {event.error}", "red")
                else:
                    print_color(f"[User Reject] {event.tool_name}: {event.rejection_reason}", "red")

        # Track token usage (from LLM response event)
        # OpenHands maintains statistics in conversation.state, here only do debug output
        if self.debug and hasattr(event, 'usage'):
            usage = event.usage
            if usage:
                self._debug_print(f"[Token Usage] Input: {usage.get('input_tokens', 0)}, Output: {usage.get('output_tokens', 0)}")

    def _extract_stats_from_conversation(self) -> None:
        """
        Extract statistics from conversation.state to self.stats and self.usage

        This method is for compatibility - when needed, extract information from OpenHands' single data source
        """
        if not self.conversation or not hasattr(self.conversation, 'state'):
            return

        # Get statistics from OpenHands
        metrics = self.conversation.state.stats.get_combined_metrics()

        # Update self.usage (compatibility)
        if metrics.accumulated_token_usage:
            self.usage.input_tokens = metrics.accumulated_token_usage.prompt_tokens
            self.usage.output_tokens = metrics.accumulated_token_usage.completion_tokens
            # Estimate number of requests through costs list
            self.usage.requests = len(metrics.costs)

        # Update self.stats (compatibility)
        self.stats["total_tokens"] = self.usage.input_tokens + self.usage.output_tokens
        self.stats["input_tokens"] = self.usage.input_tokens
        self.stats["output_tokens"] = self.usage.output_tokens
        self.stats["agent_llm_requests"] = self.usage.requests

        # Count tool calls from events
        if hasattr(self.conversation.state, 'events'):
            action_events = [e for e in self.conversation.state.events if isinstance(e, ActionEvent)]
            self.stats["cumulative_tool_calls"] = len(action_events)
            self.stats["tool_calls"] = len(action_events)

    @staticmethod
    def _extract_text_from_message_event(event: MessageEvent) -> str:
        """
        Extract text content from MessageEvent

        MessageEvent.llm_message.content is List[TextContent | ImageContent]
        """
        text_parts = []
        for content_item in event.llm_message.content:
            if hasattr(content_item, 'text'):
                text_parts.append(content_item.text)
        return "".join(text_parts)

    async def setup_user_simulator(self) -> None:
        """Initialize user simulator."""
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
        Run interaction loop (fully OpenHands SDK version - Scheme A)

       充分利用 OpenHands 的完整循环机制：
        - conversation.run() handles inner loop (max_iteration_per_run)
        - outer loop manages user-agent interaction turns (max_turns)
        - automatic stuck detection and state management
        - AgentExecutionStatus-driven termination conditions

        Loop semantics:
        - max_turns: Maximum user-agent interaction turns (outer loop)
        - max_iteration_per_run: Maximum agent steps per single run() (inner loop, set in Conversation initialization)
        """
        # Initialize session id (for compatibility)
        self.session_id = f"task_{self.task_config.id}_session"
        self.initial_run_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Determine maximum user interaction turns
        max_user_turns = 1 if self.single_turn_mode else self.task_config.max_turns

        if self.debug:
            print_color("=== Starting interaction loop (OpenHands Full Mode) ===", "blue")
            print_color(f"  Max user turns: {max_user_turns}", "blue")
            print_color(f"  Max iterations per run: {self.conversation.max_iteration_per_run}", "blue")
            print_color(f"  Stuck detection: {self.conversation.stuck_detector is not None}", "blue")

        # Main interaction loop - each turn corresponds to one user input and agent full response
        for turn in range(max_user_turns):
            try:
                # === Stage 1: Get user input ===
                # This part is the user simulator part, keeping the original framework logic
                if self.single_turn_mode:
                    user_query = self.task_config.task_str
                elif self.manual:
                    user_query = await self.ainput("USER: ")
                else:
                    user_query = await self.user_simulator.interact()
                    self._debug_print(f"USER: {user_query}")

                # Save first user input for context reset
                if self.first_user_input is None:
                    self.first_user_input = user_query

                # Check termination condition for user input
                if self.termination_checker(user_query, [], 'user'):
                    self._debug_print("Termination condition met by user input")
                    self.task_status = TaskStatus.SUCCESS
                    break

                # Record user message
                self.logs_to_record.append({"role": "user", "content": user_query})

                # === Stage 2: Send message and run OpenHands full loop ===
                self.conversation.send_message(user_query)

                # Record current event number (for extracting new events)
                events_before = len(self.conversation.state.events)

                # Run OpenHands full loop
                # conversation.run() handles:
                # 1. max_iteration_per_run limit (inner loop)
                # 2. AgentExecutionStatus.FINISHED detection
                # 3. Stuck detection (repetitive pattern, error loop, etc.)
                # 4. Error recovery (AgentErrorEvent converted to user message)
                try:
                    self.conversation.run()
                except Exception as e:
                    self._debug_print(f"Error during conversation.run(): {e}")
                    if self.debug:
                        import traceback
                        traceback.print_exc()
                    # Mark as failed and continue processing
                    self.task_status = TaskStatus.FAILED
                    raise

                # === Stage 3: Extract new events and agent response ===
                new_events = self.conversation.state.events[events_before:]

                # Extract last agent message
                last_agent_message = None
                for event in reversed(new_events):
                    if isinstance(event, MessageEvent) and event.source == "agent":
                        last_agent_message = self._extract_text_from_message_event(event)
                        break

                # Send agent response to user simulator
                if last_agent_message and not self.manual and not self.single_turn_mode:
                    self.user_simulator.receive_message(last_agent_message)

                # Update interaction turns
                self.stats["interaction_turns"] = turn + 1

                # === Stage 4: Check termination conditions driven by OpenHands status ===
                agent_status = self.conversation.state.agent_status

                # Termination condition 1: Agent finished task
                if agent_status == AgentExecutionStatus.FINISHED:
                    self._debug_print("Agent finished task successfully")
                    self.task_status = TaskStatus.SUCCESS
                    break

                # Termination condition 2: Stuck detection triggered
                if agent_status == AgentExecutionStatus.STUCK:
                    self._debug_print("Agent stuck detected by OpenHands")
                    if self.debug and self.conversation.stuck_detector:
                        # Print stuck details
                        print_color("[Stuck Detection] Agent is stuck in repetitive pattern", "red")
                    self.task_status = TaskStatus.FAILED
                    break

                # === Stage 5: Special handling for single-turn mode ===
                if self.single_turn_mode:
                    # Single-turn mode: exit after first turn
                    self._debug_print("Single-turn mode: exiting after first turn")
                    # Determine task status based on agent status
                    if agent_status == AgentExecutionStatus.FINISHED:
                        self.task_status = TaskStatus.SUCCESS
                    elif agent_status == AgentExecutionStatus.STUCK:
                        self.task_status = TaskStatus.FAILED
                    else:
                        # Agent not explicitly finished, possibly reached max_iteration_per_run
                        self.task_status = TaskStatus.MAX_TURNS_REACHED
                    break

                # === Stage 6: Save checkpoint periodically ===
                if self.allow_resume and (turn + 1) % self.checkpoint_interval == 0:
                    await self._save_checkpoint()
                    if self.debug:
                        print_color(f"[Checkpoint] Saved at turn {turn + 1}", "green")

            except KeyboardInterrupt:
                # User interrupted
                self._debug_print("\nInterrupted by user")
                if self.allow_resume:
                    await self._save_checkpoint()
                self.task_status = TaskStatus.INTERRUPTED
                raise
            except Exception as e:
                # Handle other exceptions
                self._debug_print(f"\nError during interaction turn {turn + 1}: {e}")
                if self.allow_resume:
                    await self._save_checkpoint()
                self.task_status = TaskStatus.FAILED
                raise

        # === Final status check ===
        # If loop ends normally but task status is not set, it means maximum turns reached
        if self.task_status is None and self.stats["interaction_turns"] >= max_user_turns:
            self._debug_print(f"Maximum user turns ({max_user_turns}) reached")
            self.task_status = TaskStatus.MAX_TURNS_REACHED

        # Extract final statistics from conversation.state (single data source)
        self._extract_stats_from_conversation()

        # Print final status summary
        if self.debug:
            print_color("\n=== Interaction Loop Completed ===", "blue")
            print_color(f"  Final status: {self.task_status}", "blue")
            print_color(f"  Agent status: {self.conversation.state.agent_status}", "blue")
            print_color(f"  Total turns: {self.stats['interaction_turns']}", "blue")
            print_color(f"  Total tool calls: {self.stats.get('cumulative_tool_calls', 0)}", "blue")

    def get_cost_summary(self) -> Tuple[Dict, Dict]:
        """Get cost summary (from OpenHands conversation.state)"""
        # Ensure statistics are up to date
        self._extract_stats_from_conversation()

        # Add null check for self.user_simulator
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
            "total_cost": round(total_cost, 4),
            "total_input_tokens": self.usage.input_tokens,
            "total_output_tokens": self.usage.output_tokens,
            "total_requests": self.usage.requests,
        }

        return user_cost, agent_cost
    
    async def save_results(self) -> None:
        """
        Save running results to log file (OpenHands version)

        Statistics sources:
        - self.stats and self.usage: extracted from conversation.state by _extract_stats_from_conversation()
        - session_stats: calculated directly from conversation.state.events
        - logs_to_record: maintained in _on_event callback
        """
        # Ensure statistics are up to date
        self._extract_stats_from_conversation()

        res_log_file = self.task_config.log_file

        if not os.path.exists(os.path.dirname(res_log_file)):
            os.makedirs(os.path.dirname(res_log_file))

        # Use logs_to_record (maintained in _on_event and run_interaction_loop)
        complete_messages = self.logs_to_record

        # Calculate session stats from conversation.state
        session_stats = {}
        if hasattr(self, 'conversation') and self.conversation:
            # Count events
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
        Clean up resources

        Note: After using OpenHands MCP, manual disconnection of MCP servers is no longer required
        because OpenHands tools automatically connect/disconnect when called
        """
        # OpenHands MCP tools automatically manage connections, no need to manually clean up
        # Keep method for compatibility
        if self.debug:
            print_color("Cleanup: OpenHands MCP tools handle connections automatically", "blue")
        pass
    
    async def run(self) -> TaskStatus:
        """Run the whole task, including initialization, main loop, and saving results."""

        # Cache current working directory
        current_dir = os.path.abspath(os.getcwd())

        try:
            # Set log file and workspace dir
            self.task_config.log_file = os.path.join(self.task_config.task_root, "traj_log.json")
            self.task_config.agent_workspace = os.path.join(self.task_config.task_root, "workspace")

            # Preprocess status
            self.status_manager.update_preprocess("running")

            # Initialize workspace (skip if checkpoint will be used)
            if not await self.initialize_workspace():
                self.status_manager.update_preprocess("fail")
                return TaskStatus.FAILED

            self.status_manager.update_preprocess("done")
            
            # After preprocess, load task-specific local_token_key_session
            self.task_config.load_local_token_key_session()

            # Setup MCP servers
            await self.setup_mcp_servers(self.task_config.local_token_key_session)
            
            # Setup agent (LLM assistant)
            await self.setup_agent()
            
            # Setup user simulator
            await self.setup_user_simulator()
            
            # Switch working dir to agent_workspace
            os.chdir(self.task_config.agent_workspace)
            self._debug_print(f"Switched working directory to {self.task_config.agent_workspace}")

            # Enter running status
            self.status_manager.update_running("running")

            # Main interaction loop
            await self.run_interaction_loop(os.path.abspath(self.task_config.task_root))

            # Switch back to the original cwd
            os.chdir(current_dir)
            self._debug_print(f"Switched back working directory to {current_dir}")
            
            # If not interrupted or max turns reached, mark done
            if self.task_status not in [TaskStatus.MAX_TURNS_REACHED, TaskStatus.INTERRUPTED]:
                self.task_status = TaskStatus.SUCCESS
                self.status_manager.update_running("done")
            elif self.task_status == TaskStatus.MAX_TURNS_REACHED:
                self.status_manager.update_running("max_turn_exceeded")
            
            # Remove checkpoint after successful completion
            if self.task_status == TaskStatus.SUCCESS:
                self._remove_checkpoint()
                
        except KeyboardInterrupt:
            self._debug_print("Task interrupted by user")
            if self.task_status != TaskStatus.INTERRUPTED:
                self.task_status = TaskStatus.INTERRUPTED
                
        except Exception as e:
            # max-turn logic updates the status in the interaction loop
            # but RuntimeError("Failed to get agent response...") brings us here,
            # so update status here as well
            self._debug_print("Error when running agent -", e)
            if self.debug:
                traceback.print_exc()
            if self.task_status == TaskStatus.MAX_TURNS_REACHED:
                self.status_manager.update_running("max_turn_exceeded")
            else:
                self.task_status = TaskStatus.FAILED
                self.status_manager.update_running("fail")
            
        finally:
            # Always restore working dir
            os.chdir(current_dir)
            self._debug_print(f"Switched back working directory to {current_dir}")

            # Gather final cost summary (updates token stats)
            user_cost, agent_cost = self.get_cost_summary()
            self.user_cost = user_cost
            self.agent_cost = agent_cost

            # Print cost/statistics summary (in English)
            self._debug_print(f"=== LLM-simulator ({self.user_config.model.short_name}) Cost Summary ===")
            for k, v in user_cost.items():
                self._debug_print(f"{k} : {v}")
            self._debug_print(f"=== Agent ({self.agent_config.model.short_name}) Cost Summary ===")
            for k, v in agent_cost.items():
                self._debug_print(f"{k} : {v}")
            self._debug_print("=== Key Statistics ===")
            for k, v in self.stats.items():
                self._debug_print(f"{k} : {v}")
            
            # Save final results to file
            await self.save_results()
            # Cleanup/close resources
            await self.cleanup()
            
        return self.task_status