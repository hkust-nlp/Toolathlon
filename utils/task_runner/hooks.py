from typing import Any
from agents import AgentHooks, RunHooks, RunContextWrapper, Agent, Tool, TContext
from utils.general.helper import print_color

class AgentLifecycle(AgentHooks):
    """Agent生命周期钩子"""
    
    def __init__(self):
        super().__init__()
        
    async def on_start(self, context: RunContextWrapper, agent: Agent) -> None:
        """Agent启动时的钩子"""
        pass
        
    async def on_end(self, context: RunContextWrapper, agent: Agent, output: Any) -> None:
        """Agent结束时的钩子"""
        pass

class RunLifecycle(RunHooks):
    """运行生命周期钩子"""
    
    def __init__(self,debug):
        super().__init__()
        self.debug = debug
        
    async def on_agent_start(self, context: RunContextWrapper, agent: Agent) -> None:
        """Agent开始运行时的钩子"""
        if self.debug:
            pass
        
    async def on_agent_end(self, context: RunContextWrapper, agent: Agent, output: Any) -> None:
        """Agent结束运行时的钩子"""
        if self.debug:
            pass
        
    async def on_tool_start(
        self,
        context: RunContextWrapper[TContext],
        agent: Agent[TContext],
        tool: Tool,
    ) -> None:
        """工具调用开始时的钩子"""
        if self.debug:
            print_color(f'>>>>Invoking tool: {tool.name}', "cyan")
        
    async def on_tool_end(
        self,
        context: RunContextWrapper[TContext],
        agent: Agent[TContext],
        tool: Tool,
        result: str,
    ) -> None:
        """工具调用结束时的钩子"""
        if self.debug:
            print_color(f'>>>>Tool execution result: {tool.name}', "cyan")