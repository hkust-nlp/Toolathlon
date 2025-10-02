# Adapter Integration Guide

## Overview

This guide explains how to integrate the newly created `MCPToolAdapter` with the existing `task_agent.py` to complete the migration to OpenHands SDK.

## What Has Been Created

### 1. Adapter Layer (COMPLETED ✅)

**Location**: `utils/openhands_adapter/`

**Files**:
- `__init__.py` - Package initialization
- `mcp_tool_adapter.py` - Core adapter implementation (~330 lines)

**Key Components**:

```python
# 1. MCPToolAction - Generic action wrapper for MCP tools
class MCPToolAction(ActionBase):
    data: Dict[str, Any]  # Arbitrary tool arguments

# 2. MCPToolObservation - Result wrapper
class MCPToolObservation(ObservationBase):
    content: str
    is_error: bool
    tool_name: str

# 3. MCPToolAdapterExecutor - Calls persistent connections
class MCPToolAdapterExecutor(ToolExecutor):
    # Uses call_tool_with_retry from mcpbench_dev
    # Maintains retry_time=5 by default

# 4. MCPToolAdapter - Bridge to OpenHands Tool interface
class MCPToolAdapter(Tool):
    # Wraps connected MCP server
    # Dynamically creates action types from MCP schema

# 5. Helper function
async def create_adapted_mcp_tools(mcp_manager, ...) -> List[MCPToolAdapter]
```

## Next Steps: Modify task_agent.py

### Step 1: Add Imports

**Location**: `utils/roles/task_agent.py` (top of file)

```python
# Add these imports after existing imports
from utils.openhands_adapter import MCPToolAdapter, create_adapted_mcp_tools

# OpenHands SDK imports
try:
    from openhands.sdk.agent.agent import Agent
    from openhands.sdk.conversation.conversation import Conversation
    from openhands.sdk.conversation.impl.local_conversation import LocalConversation
except ImportError:
    import sys
    from pathlib import Path
    agent_sdk_path = Path(__file__).parent.parent.parent / 'agent-sdk'
    if agent_sdk_path.exists():
        sys.path.insert(0, str(agent_sdk_path))
    from openhands.sdk.agent.agent import Agent
    from openhands.sdk.conversation.conversation import Conversation
    from openhands.sdk.conversation.impl.local_conversation import LocalConversation
```

### Step 2: Modify setup_agent() Method

**Location**: `task_agent.py:~350-400` (approximate)

**Current Implementation** (simplified):
```python
async def setup_agent(self):
    # Setup LLM
    self.llm = LLM(...)

    # Setup tools
    self.tools = register_tools(...)

    # Create OpenAI Agent
    self.agent = openai_agent.Agent(...)
    self.runner = ContextManagedRunner(...)
```

**New Implementation** (OpenHands SDK):
```python
async def setup_agent(self):
    # 1. Setup LLM (keep existing)
    self.llm = LLM(...)

    # 2. Setup local tools (keep existing)
    local_tool_specs = register_tools(...)

    # 3. Create adapted MCP tools from connected servers
    mcp_tools = await create_adapted_mcp_tools(
        mcp_manager=self.mcp_manager,
        server_names=None,  # None = all connected servers
        retry_time=5
    )

    # 4. Combine all tools
    all_tools = list(local_tool_specs) + mcp_tools

    # 5. Create OpenHands Agent (NO mcp_config, we handle MCP externally)
    self.agent = Agent(
        llm=self.llm,
        tools=all_tools,
        mcp_config={},  # Empty - we use mcpbench_dev's MCP manager
        # Add other config as needed
    )

    # 6. Create Conversation
    persistence_dir = self.task_config.agent_workspace / 'conversation_state'
    persistence_dir.mkdir(exist_ok=True)

    self.conversation = LocalConversation(
        agent=self.agent,
        persistence_dir=str(persistence_dir)
    )

    # Note: No need for ContextManagedRunner - OpenHands has built-in Condenser
```

### Step 3: Replace run_interaction_loop()

**Location**: `task_agent.py:~505-795`

**Current Implementation**: Manual loop with OpenAI Runner
```python
async def run_interaction_loop(self, task_query: str):
    # Initialize logs
    self.logs = []

    # Manual loop
    while True:
        # Get LLM response
        response = await self.runner.run(...)

        # Handle tools
        for tool_call in response.tool_calls:
            result = await self._execute_tool(...)

        # Check completion
        if self._is_finished():
            break

    return self.final_answer
```

**New Implementation**: Use Conversation.run()
```python
async def run_interaction_loop(self, task_query: str):
    """
    Execute agent interaction loop using OpenHands SDK

    This replaces the manual loop with Conversation.run(),
    which handles:
    - Event storage (file-backed EventLog)
    - Context management (Condenser for summarization)
    - Tool execution
    - State persistence
    """

    # Send initial task message
    self.conversation.send_message(task_query)

    # Define callbacks for monitoring
    def on_event(event):
        """Log events as they occur"""
        if self.debug:
            print(f"Event: {event.type} - {getattr(event, 'content', '')[:100]}")

    try:
        # Run conversation loop (blocking until completion)
        final_state = await self.conversation.run(
            on_event=on_event,
            max_turns=self.task_config.max_turns or 50
        )

        # Extract final answer from conversation state
        self.final_answer = self._extract_final_answer(final_state)

        return self.final_answer

    except Exception as e:
        print(f"Conversation error: {e}")
        raise

def _extract_final_answer(self, state) -> str:
    """Extract final answer from conversation state"""
    # Look for the last agent message
    for event in reversed(state.events):
        if hasattr(event, 'type') and event.type == 'message':
            if hasattr(event, 'source') and event.source == 'agent':
                return event.content

    return "No final answer found"
```

### Step 4: Remove Obsolete Methods

These methods are no longer needed with OpenHands SDK:

1. **Context Management** (handled by Condenser):
   - `_check_context_overflow()`
   - `_handle_context_overflow()`
   - Manual truncation logic

2. **Runner Management** (handled by Conversation):
   - `ContextManagedRunner` instantiation
   - Runner state management

3. **Manual Logging** (handled by EventLog):
   - `self.logs` manipulation
   - Manual message history tracking

### Step 5: Update cleanup() Method

**Current**: Cleanup runner + MCP servers
```python
async def cleanup(self):
    # Cleanup runner
    if hasattr(self, 'runner'):
        await self.runner.cleanup()

    # Disconnect MCP servers
    await self.mcp_manager.disconnect_servers(...)
```

**New**: Only cleanup MCP servers (Conversation auto-persists)
```python
async def cleanup(self):
    # Conversation state is already persisted to disk
    # Just disconnect MCP servers
    await self.mcp_manager.disconnect_servers(
        list(self.mcp_manager.connected_servers.keys())
    )
```

## Summary of Changes

| Component | Before (OpenAI SDK) | After (OpenHands SDK) |
|-----------|-------------------|---------------------|
| **Agent Creation** | `openai_agent.Agent(...)` | `Agent(llm, tools, mcp_config={})` |
| **MCP Tools** | Separate management | Adapted via `MCPToolAdapter` |
| **Loop Execution** | Manual `while` loop | `conversation.run()` |
| **Context Management** | Manual truncation | Automatic Condenser |
| **State Storage** | `self.logs` list | File-backed EventLog |
| **Tool Execution** | Manual retry logic | Built-in + adapter's retry |

## File Modification Checklist

- [x] Create `utils/openhands_adapter/__init__.py`
- [x] Create `utils/openhands_adapter/mcp_tool_adapter.py`
- [ ] Modify `utils/roles/task_agent.py`:
  - [ ] Add OpenHands SDK imports
  - [ ] Update `setup_agent()` method
  - [ ] Replace `run_interaction_loop()` method
  - [ ] Update `cleanup()` method
  - [ ] Remove obsolete context management methods
- [ ] Test integration:
  - [ ] MCP server connection
  - [ ] Tool adapter creation
  - [ ] Conversation execution
  - [ ] Event persistence

## Estimated Work Remaining

- **Code Modification**: ~2-3 hours
- **Testing**: ~4-6 hours
- **Debugging**: ~2-4 hours
- **Total**: ~1-2 days

## Testing Strategy

1. **Unit Test**: Adapter creation
   ```python
   # Test: Can we create adapted tools?
   mcp_manager = MCPServerManager(...)
   await mcp_manager.connect_servers(['filesystem'])
   tools = await create_adapted_mcp_tools(mcp_manager)
   assert len(tools) > 0
   ```

2. **Integration Test**: Simple task execution
   ```python
   # Test: Can agent execute a simple task?
   task_agent = TaskAgent(...)
   await task_agent.setup_mcp_servers()
   await task_agent.setup_agent()
   result = await task_agent.run_interaction_loop("List files in current directory")
   assert result is not None
   ```

3. **End-to-End Test**: Full benchmark task
   ```python
   # Test: Can it complete a real benchmark task?
   # Use demo.py or existing test suite
   ```

## Rollback Plan

If issues arise, the adapter layer is isolated and can be removed without affecting mcpbench_dev's core MCP management. Simply revert task_agent.py changes and remove the adapter directory.

## Next Action

Ready to modify `task_agent.py` following the steps above. Should I proceed with Step 2 (modifying the setup_agent method)?
