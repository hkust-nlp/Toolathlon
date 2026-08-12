from typing import Any
from agents import AgentHooks, RunHooks, RunContextWrapper, Agent, Tool, TContext
from agents.exceptions import AgentsException
from utils.general.helper import print_color


class TaskDoneError(AgentsException):
    """Raised when the agent invokes ``local-claim_done``.

    The system prompt promises the model that calling ``local-claim_done``
    immediately terminates the task.  The openai-agents Runner, however, only
    stops on a text-only final output: it keeps executing turns while the
    model keeps calling tools, and the termination check in
    ``TaskAgent.run_interaction_loop`` only runs *after* the Runner returns,
    so it never fires.  Raising from ``on_tool_start`` aborts the run loop the
    moment the stop tool is invoked, so tasks complete as intended instead of
    dying with "Failed to get agent response within N inner steps" (or, worse,
    "Context too long" from the loop piling up history).
    """


class AgentLifecycle(AgentHooks):
    """Hook for Agent lifecycle"""
    
    def __init__(self):
        super().__init__()
        
    async def on_start(self, context: RunContextWrapper, agent: Agent) -> None:
        """Hook for Agent start"""
        pass
        
    async def on_end(self, context: RunContextWrapper, agent: Agent, output: Any) -> None:
        """Hook for Agent end"""
        pass

class RunLifecycle(RunHooks):
    """Hook for Run lifecycle"""
    
    def __init__(self,debug):
        super().__init__()
        self.debug = debug
        
    async def on_agent_start(self, context: RunContextWrapper, agent: Agent) -> None:
        """Hook for Agent start"""
        if self.debug:
            pass
        
    async def on_agent_end(self, context: RunContextWrapper, agent: Agent, output: Any) -> None:
        """Hook for Agent end"""
        if self.debug:
            pass
        
    async def on_tool_start(
        self,
        context: RunContextWrapper[TContext],
        agent: Agent[TContext],
        tool: Tool,
    ) -> None:
        """Hook for Tool start"""
        if self.debug:
            print_color(f'>>>>Invoking tool: {tool.name}', "cyan")

        # ``local-claim_done`` is the stop tool: abort the run immediately.
        # The tool itself only returns a string, so without this the Runner
        # would keep looping on further tool calls until max_turns.
        if tool.name in ("local-claim_done", "local_claim_done"):
            raise TaskDoneError("Task completed via local-claim_done")
        
    async def on_tool_end(
        self,
        context: RunContextWrapper[TContext],
        agent: Agent[TContext],
        tool: Tool,
        result: str,
    ) -> None:
        """Hook for Tool end"""
        if self.debug:
            print_color(f'>>>>Tool execution result: {tool.name}', "cyan")