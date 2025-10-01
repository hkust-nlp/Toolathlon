"""
OpenHands Adapter Layer

This module provides adapters to bridge mcpbench_dev with OpenHands SDK:
- LLM adapter: Convert model_provider to OpenHands LLM
- Tool adapter: Convert FunctionTool to OpenHands Tool
"""

from .llm_adapter import create_openhands_llm, create_openhands_llm_from_config
from .tool_adapter import (
    convert_function_tool_to_openhands,
    convert_function_tool_to_toolspec,
    register_function_tools
)

__all__ = [
    'create_openhands_llm',
    'create_openhands_llm_from_config',
    'convert_function_tool_to_openhands',
    'convert_function_tool_to_toolspec',
    'register_function_tools'
]

