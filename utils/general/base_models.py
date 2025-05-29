from enum import Enum
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, model_validator, field_serializer

class TimestampMixin(BaseModel):
    """带时间戳的基类"""
    timestamp: datetime = Field(default_factory=datetime.now)
    
    @field_serializer('timestamp')
    def serialize_timestamp(self, timestamp: datetime, _info):
        return timestamp.isoformat()

class CostReport(BaseModel):
    """成本报告模型"""
    input_tokens: int = 0
    output_tokens: int = 0
    input_cost: float = 0.0
    output_cost: float = 0.0
    total_cost: float = 0.0
    model: str = ""
    provider: str = ""

# Tool相关的Pydantic模型
class ToolType(str, Enum):
    """工具类型枚举"""
    FUNCTION = "function"

class FunctionDefinition(BaseModel):
    """函数定义"""
    name: str
    description: str
    parameters: Dict[str, Any]

class Tool(BaseModel):
    """工具定义"""
    type: Literal["function"] = "function"
    function: FunctionDefinition

class ToolCall(BaseModel):
    """工具调用"""
    id: str
    type: ToolType = ToolType.FUNCTION
    function: 'FunctionCall'

class FunctionCall(BaseModel):
    """函数调用"""
    name: str
    arguments: str  # JSON string

class MessageRole(str, Enum):
    """消息角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"

class Message(TimestampMixin):
    """增强的消息模型"""
    role: MessageRole
    content: Optional[str] = None
    reasoning_content: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @model_validator(mode='after')
    def validate_tool_fields(self):
        """验证工具相关字段的一致性"""
        if self.role == MessageRole.TOOL and not self.tool_call_id:
            raise ValueError("Tool messages must have tool_call_id")
        if self.role != MessageRole.TOOL and self.tool_call_id:
            raise ValueError("Only tool messages can have tool_call_id")
        if self.role != MessageRole.ASSISTANT and self.tool_calls:
            raise ValueError("Only assistant messages can have tool_calls")
        return self
    
    # 工厂方法
    @classmethod
    def user(cls, content: str, **kwargs) -> "Message":
        """创建用户消息"""
        return cls(role=MessageRole.USER, content=content, **kwargs)
    
    @classmethod
    def system(cls, content: str, **kwargs) -> "Message":
        """创建系统消息"""
        return cls(role=MessageRole.SYSTEM, content=content, **kwargs)
    
    @classmethod
    def assistant(
        cls, 
        content: str = None, 
        tool_calls: Optional[List[ToolCall]] = None,
        reasoning_content: Optional[str] = None,
        **kwargs
    ) -> "Message":
        """创建助手消息"""
        return cls(
            role=MessageRole.ASSISTANT, 
            content=content,
            tool_calls=tool_calls,
            reasoning_content=reasoning_content,
            **kwargs
        )
    
    @classmethod
    def tool(cls, tool_call_id: str, content: str, **kwargs) -> "Message":
        """创建工具消息"""
        return cls(
            role=MessageRole.TOOL, 
            content=content, 
            tool_call_id=tool_call_id,
            **kwargs
        )
    
    def update_metadata(self, metadata: Dict[str, Any]) -> None:
        """更新元数据"""
        self.metadata.update(metadata)
    
    def add_tool_call(self, tool_call: ToolCall) -> None:
        """添加工具调用"""
        if self.role != MessageRole.ASSISTANT:
            raise ValueError("Only assistant messages can have tool calls")
        
        if self.tool_calls is None:
            self.tool_calls = []
        self.tool_calls.append(tool_call)
    
    def __repr__(self) -> str:
        """友好的字符串表示"""
        msg = f"[{self.role.value.capitalize()}]: {self.content or '(empty)'}"
        
        if self.reasoning_content:
            msg += f"\n>>> Reasoning: {self.reasoning_content}"
        
        if self.tool_calls:
            for tool_call in self.tool_calls:
                msg += f"\n>>> Tool call ({tool_call.function.name}/{tool_call.id}): {tool_call.function.arguments}"
        
        if self.tool_call_id:
            msg += f"\n>>> Tool response for: {self.tool_call_id}"
        
        return msg
    
    def __str__(self) -> str:
        """简短的字符串表示"""
        content_preview = (self.content[:50] + "...") if self.content and len(self.content) > 50 else self.content
        return f"{self.role.value}: {content_preview or '(empty)'}"
    
    def to_api_dict(self) -> Dict[str, Any]:
        """转换为 API 兼容的字典格式"""
        # 使用内置的 exclude 和 exclude_none
        return self.model_dump(
            exclude={'metadata', 'timestamp'}, 
            exclude_none=True,
            mode='json'  # 确保 JSON 兼容
        )
