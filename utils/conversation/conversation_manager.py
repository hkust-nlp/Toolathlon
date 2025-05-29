from typing import Optional, List, Dict, Any
from utils.general.base_models import Message, MessageRole, Tool
from utils.api_model.openai_client import AsyncOpenAIClientWithRetry


# 对话历史管理器
class ConversationManager:
    """对话历史管理器"""
    
    def __init__(self, max_history: int = 10, log_file: Optional[str] = None):
        self.max_history = max_history
        self.conversations: Dict[str, List[Message]] = {}
        self.client = None
        self.log_file = log_file
    
    def set_client(self, client: AsyncOpenAIClientWithRetry):
        """设置API客户端"""
        self.client = client
    
    def add_message(self, conversation_id: str, role: MessageRole, content: str):
        """添加消息到对话历史"""
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        
        message = Message(role=role, content=content)
        self.conversations[conversation_id].append(message)
        
        # 限制历史长度
        if len(self.conversations[conversation_id]) > self.max_history:
            self.conversations[conversation_id] = self.conversations[conversation_id][-self.max_history:]
    
    async def generate_response(
        self,
        conversation_id: str,
        user_input: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Tool]] = None,
        tool_functions: Optional[Dict[str, callable]] = None,
        **kwargs
    ) -> str:
        """生成响应并更新对话历史"""
        # 添加用户消息
        self.add_message(conversation_id, MessageRole.USER, user_input)
        
        # 构建消息列表
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # 添加历史消息
        for msg in self.conversations.get(conversation_id, []):
            msg_dict = {"role": msg.role.value, "content": msg.content}
            # 处理tool消息的特殊字段
            if hasattr(msg, 'tool_call_id'):
                msg_dict['tool_call_id'] = msg.tool_call_id
            if hasattr(msg, 'tool_calls'):
                msg_dict['tool_calls'] = msg.tool_calls
            messages.append(msg_dict)
        
        # 生成响应
        if tools and tool_functions:
            # 支持tool calls
            content, tool_calls, _ = await self.client.chat_completion(
                messages, 
                tools=tools,
                return_tool_calls=True,
                **kwargs
            )
            
            if tool_calls:
                # 执行tool calls
                response = await self.client.execute_tool_calls(
                    tool_calls,
                    tool_functions,
                    messages,
                    **kwargs
                )
            else:
                response = content
        else:
            # 普通响应
            response = await self.client.chat_completion(messages, **kwargs)
        
        # 添加助手响应到历史
        self.add_message(conversation_id, MessageRole.ASSISTANT, response)
        
        return response
