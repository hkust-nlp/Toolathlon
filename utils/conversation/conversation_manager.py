from typing import Optional, List, Dict, Any
from utils.general.base_models import Message, MessageRole, Tool
from utils.api_model.openai_client import AsyncOpenAIClientWithRetry


class ConversationManager:
    """Conversation history manager"""
    
    def __init__(self, max_history: int = 10, log_file: Optional[str] = None):
        self.max_history = max_history
        self.conversations: Dict[str, List[Message]] = {}
        self.client = None
        self.log_file = log_file
    
    def set_client(self, client: AsyncOpenAIClientWithRetry):
        """Set the API client"""
        self.client = client
    
    def add_message(self, conversation_id: str, role: MessageRole, content: str):
        """Add a message to the conversation history"""
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        
        message = Message(role=role, content=content)
        self.conversations[conversation_id].append(message)
        
        # Limit conversation history length
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
        """Generate a response and update the conversation history"""
        # Add user message
        self.add_message(conversation_id, MessageRole.USER, user_input)
        
        # Build messages list
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history messages
        for msg in self.conversations.get(conversation_id, []):
            msg_dict = {"role": msg.role.value, "content": msg.content}
            # Handle tool message special fields
            if hasattr(msg, 'tool_call_id'):
                msg_dict['tool_call_id'] = msg.tool_call_id
            if hasattr(msg, 'tool_calls'):
                msg_dict['tool_calls'] = msg.tool_calls
            messages.append(msg_dict)
        
        # Generate model response
        if tools and tool_functions:
            # Support tool calls
            content, tool_calls, _ = await self.client.chat_completion(
                messages, 
                tools=tools,
                return_tool_calls=True,
                **kwargs
            )
            
            if tool_calls:
                # Execute tool calls
                response = await self.client.execute_tool_calls(
                    tool_calls,
                    tool_functions,
                    messages,
                    **kwargs
                )
            else:
                response = content
        else:
            # Standard model response
            response = await self.client.chat_completion(messages, **kwargs)
        
        # Add assistant response to history
        self.add_message(conversation_id, MessageRole.ASSISTANT, response)
        
        return response
