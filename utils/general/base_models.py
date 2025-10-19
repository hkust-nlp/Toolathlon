from enum import Enum
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, model_validator, field_serializer

class TimestampMixin(BaseModel):
    """Timestamp mixin"""
    timestamp: datetime = Field(default_factory=datetime.now)
    
    @field_serializer('timestamp')
    def serialize_timestamp(self, timestamp: datetime, _info):
        return timestamp.isoformat()

class CostReport(BaseModel):
    """Cost report model"""
    input_tokens: int = 0
    output_tokens: int = 0
    input_cost: float = 0.0
    output_cost: float = 0.0
    total_cost: float = 0.0
    model: str = ""
    provider: str = ""

# Tool related Pydantic models
class ToolType(str, Enum):
    """Tool type enum"""
    FUNCTION = "function"

class FunctionDefinition(BaseModel):
    """Function definition"""
    name: str
    description: str
    parameters: Dict[str, Any]

class Tool(BaseModel):
    """Tool definition"""
    type: Literal["function"] = "function"
    function: FunctionDefinition

class ToolCall(BaseModel):
    """Tool call"""
    id: str
    type: ToolType = ToolType.FUNCTION
    function: 'FunctionCall'

class FunctionCall(BaseModel):
    """Function call"""
    name: str
    arguments: str  # JSON string

class MessageRole(str, Enum):
    """Message role enum"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"

class Message(TimestampMixin):
    """Enhanced message model"""
    role: MessageRole
    content: Optional[str] = None
    reasoning_content: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @model_validator(mode='after')
    def validate_tool_fields(self):
        """Validate consistency of tool related fields"""
        if self.role == MessageRole.TOOL and not self.tool_call_id:
            raise ValueError("Tool messages must have tool_call_id")
        if self.role != MessageRole.TOOL and self.tool_call_id:
            raise ValueError("Only tool messages can have tool_call_id")
        if self.role != MessageRole.ASSISTANT and self.tool_calls:
            raise ValueError("Only assistant messages can have tool_calls")
        return self
    
    # Factory method
    @classmethod
    def user(cls, content: str, **kwargs) -> "Message":
        """Create user message"""
        return cls(role=MessageRole.USER, content=content, **kwargs)
    
    @classmethod
    def system(cls, content: str, **kwargs) -> "Message":
        """Create system message"""
        return cls(role=MessageRole.SYSTEM, content=content, **kwargs)
    
    @classmethod
    def assistant(
        cls, 
        content: str = None, 
        tool_calls: Optional[List[ToolCall]] = None,
        reasoning_content: Optional[str] = None,
        **kwargs
    ) -> "Message":
        """Create assistant message"""
        return cls(
            role=MessageRole.ASSISTANT, 
            content=content,
            tool_calls=tool_calls,
            reasoning_content=reasoning_content,
            **kwargs
        )
    
    @classmethod
    def tool(cls, tool_call_id: str, content: str, **kwargs) -> "Message":
        """Create tool message"""
        return cls(
            role=MessageRole.TOOL, 
            content=content, 
            tool_call_id=tool_call_id,
            **kwargs
        )
    
    def update_metadata(self, metadata: Dict[str, Any]) -> None:
        """Update metadata"""
        self.metadata.update(metadata)
    
    def add_tool_call(self, tool_call: ToolCall) -> None:
        """Add tool call"""
        if self.role != MessageRole.ASSISTANT:
            raise ValueError("Only assistant messages can have tool calls")
        
        if self.tool_calls is None:
            self.tool_calls = []
        self.tool_calls.append(tool_call)
    
    def __repr__(self) -> str:
        """Friendly string representation"""
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
        """Short string representation"""
        content_preview = (self.content[:50] + "...") if self.content and len(self.content) > 50 else self.content
        return f"{self.role.value}: {content_preview or '(empty)'}"
    
    def to_api_dict(self) -> Dict[str, Any]:
        """Convert to API compatible dictionary format"""
        # Use built-in exclude and exclude_none
        return self.model_dump(
            exclude={'metadata', 'timestamp'}, 
            exclude_none=True,
            mode='json'  # Ensure JSON compatible
        )
