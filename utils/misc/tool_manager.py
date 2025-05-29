import json
import asyncio
from typing import Dict, List, Any, Tuple, Optional
from utils.general.base_models import Tool, ToolCall, FunctionDefinition


class ToolManager:
    """工具管理器，仅负责工具的定义、验证和执行"""
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self.tool_functions: Dict[str, callable] = {}
    
    def create_tool(self, name: str, description: str, parameters: Dict[str, Any]) -> Tool:
        """创建工具的辅助方法"""
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
        """注册工具函数"""
        if name not in self.tools:
            raise ValueError(f"Tool {name} not defined")
        self.tool_functions[name] = func
    
    def get_tools_list(self) -> List[Tool]:
        """获取所有工具列表"""
        return list(self.tools.values())
    
    async def execute_tool_call(self, tool_call: ToolCall) -> str:
        """执行单个工具调用"""
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


# 工具参数验证器
class ToolValidator:
    """工具参数验证器"""
    
    @staticmethod
    def validate_parameters(tool: Tool, arguments: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """验证函数参数是否符合定义"""
        params = tool.function.parameters
        
        # 检查必需参数
        required = params.required or []
        for req_param in required:
            if req_param not in arguments:
                return False, f"Missing required parameter: {req_param}"
        
        # 检查参数类型
        properties = params.properties or {}
        for arg_name, arg_value in arguments.items():
            if arg_name in properties:
                param_def = properties[arg_name]
                
                # 类型检查
                expected_type = param_def.type
                if not ToolValidator._check_type(arg_value, expected_type):
                    return False, f"Parameter '{arg_name}' type mismatch. Expected: {expected_type}"
                
                # 枚举检查
                if param_def.enum and arg_value not in param_def.enum:
                    return False, f"Parameter '{arg_name}' must be one of: {param_def.enum}"
        
        return True, None
    
    @staticmethod
    def _check_type(value: Any, expected_type: str) -> bool:
        """检查值的类型是否匹配"""
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
