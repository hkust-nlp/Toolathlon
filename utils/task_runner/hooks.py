from typing import Any
from agents import AgentHooks, RunHooks, RunContextWrapper, Agent, Tool, TContext
from utils.general.helper import print_color

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