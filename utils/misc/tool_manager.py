import json
import asyncio
from typing import Dict, List, Any, Tuple, Optional
from utils.general.base_models import Tool, ToolCall, FunctionDefinition


class ToolManager:
    """Tool manager: responsible for tool definition, validation, and execution only."""
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self.tool_functions: Dict[str, callable] = {}
    
    def create_tool(self, name: str, description: str, parameters: Dict[str, Any]) -> Tool:
        """Helper method to create a tool."""
        tool = Tool(
            function=FunctionDefinition(
                name=name,
                description=description,
                parameters=parameters
            )
        )
        self.tools[name] = tool
        return tool
    
    def register_function(self, name: str, func: callable):
        """Register a function that implements a tool."""
        if name not in self.tools:
            raise ValueError(f"Tool {name} not defined")
        self.tool_functions[name] = func
    
    def get_tools_list(self) -> List[Tool]:
        """Get a list of all defined tools."""
        return list(self.tools.values())
    
    async def execute_tool_call(self, tool_call: ToolCall) -> str:
        """Execute a single tool call."""
        function_name = tool_call.function.name
        if function_name not in self.tool_functions:
            raise ValueError(f"Function {function_name} not registered")
        
        function_args = json.loads(tool_call.function.arguments)
        func = self.tool_functions[function_name]
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(**function_args)
            else:
                result = func(**function_args)
            return str(result)
        except Exception as e:
            return f"Error executing function: {str(e)}"


class ToolValidator:
    """Tool parameter validator."""
    
    @staticmethod
    def validate_parameters(tool: Tool, arguments: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate if function arguments conform to the tool definition."""
        params = tool.function.parameters
        
        # Check for required parameters
        required = params.required or []
        for req_param in required:
            if req_param not in arguments:
                return False, f"Missing required parameter: {req_param}"
        
        # Check parameter types and enums
        properties = params.properties or {}
        for arg_name, arg_value in arguments.items():
            if arg_name in properties:
                param_def = properties[arg_name]
                
                # Type check
                expected_type = param_def.type
                if not ToolValidator._check_type(arg_value, expected_type):
                    return False, f"Parameter '{arg_name}' type mismatch. Expected: {expected_type}"
                
                # Enum check
                if param_def.enum and arg_value not in param_def.enum:
                    return False, f"Parameter '{arg_name}' must be one of: {param_def.enum}"
        
        return True, None
    
    @staticmethod
    def _check_type(value: Any, expected_type: str) -> bool:
        """Check if the value matches the expected type."""
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict
        }
        
        expected = type_map.get(expected_type)
        if expected:
            return isinstance(value, expected)
        return True
