from dataclasses import dataclass, field
from typing import Optional, Union, Literal, Dict
from utils.data_structures.common import Model, Generation
import os


@dataclass
class Tool:
    """Tool call configuration"""
    tool_choice: Union[Literal["auto", "none", "required"], str] = "auto"
    parallel_tool_calls: bool = False
    max_inner_turns: int = 20
    
    def __post_init__(self):
        """Validate the reasonability of tool call parameters"""
        if self.max_inner_turns < 1:
            raise ValueError(f"max_inner_turns should be greater than 0, but got {self.max_inner_turns}")

@dataclass
class AgentConfig:
    """Agent configuration"""
    model: Model
    generation: Generation
    tool: Tool
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AgentConfig':
        """Create AgentConfig instance from dictionary"""
        # If data directly contains agent field
        if 'agent' in data:
            data = data['agent']
        
        # Automatically inject OpenRouter configuration
        generation_data = data['generation'].copy()
        model_data = data['model']
        
        # If using OpenRouter provider, automatically add provider routing configuration
        if model_data.get('provider') == 'openrouter' or (model_data.get('provider') == 'unified' and os.getenv('TOOLATHLON_OPENAI_BASE_URL')=="https://openrouter.ai/api/v1"):
            from utils.api_model.model_provider import API_MAPPINGS
            model_short_name = model_data.get('short_name')
            
            if model_short_name in API_MAPPINGS:
                mapping = API_MAPPINGS[model_short_name]
                if 'openrouter_config' in mapping:
                    # Automatically inject complete OpenRouter configuration into extra_body
                    openrouter_config = mapping['openrouter_config']
                    
                    # Merge existing extra_body (if any)
                    existing_extra_body = generation_data.get('extra_body', {})
                    if existing_extra_body:
                        existing_extra_body.update(openrouter_config)
                        generation_data['extra_body'] = existing_extra_body
                    else:
                        generation_data['extra_body'] = openrouter_config
        
        return cls(
            model=Model(**model_data),
            generation=Generation(**generation_data),
            tool=Tool(**data['tool'])
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "agent": {
                "model": {
                    "short_name": self.model.short_name,
                    "provider": self.model.provider,
                },
                "generation": {
                    "temperature": self.generation.temperature,
                    "top_p": self.generation.top_p,
                    "max_tokens": self.generation.max_tokens,
                    "extra_body": self.generation.extra_body,
                },
                "tool": {
                    "tool_choice": self.tool.tool_choice,
                    "parallel_tool_calls": self.tool.parallel_tool_calls,
                    "max_inner_turns": self.tool.max_inner_turns,
                }
            }
        }
    
    def to_dict_without_agent_key(self) -> dict:
        """Convert to dictionary without agent key"""
        return {
            "model": {
                "short_name": self.model.short_name,
                "provider": self.model.provider,
            },
            "generation": {
                "temperature": self.generation.temperature,
                "top_p": self.generation.top_p,
                "max_tokens": self.generation.max_tokens,
                "extra_body": self.generation.extra_body,
            },
            "tool": {
                "tool_choice": self.tool.tool_choice,
                "parallel_tool_calls": self.tool.parallel_tool_calls,
                "max_inner_turns": self.tool.max_inner_turns,
            }
        }
    
    def get_api_params(self) -> dict:
        """Get parameters for API calls"""
        return {
            "model": self.model.real_name or self.model.short_name,
            "temperature": self.generation.temperature,
            "top_p": self.generation.top_p,
            "max_tokens": self.generation.max_tokens,
        }
    
    def copy_with_updates(self, updates: dict) -> 'AgentConfig':
        """Create a copy with nested updates"""
        import copy
        current_dict = self.to_dict_without_agent_key()
        
        # Deep merge updates
        def deep_merge(base: dict, update: dict) -> dict:
            result = copy.deepcopy(base)
            for key, value in update.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result
        
        merged_dict = deep_merge(current_dict, updates)
        return self.__class__.from_dict(merged_dict)
    
    # Convenient attribute access
    @property
    def model_name(self) -> str:
        return self.model.short_name
    
    @property
    def provider(self) -> str:
        return self.model.provider
    
    @property
    def temperature(self) -> float:
        return self.generation.temperature
    
    @property
    def max_tokens(self) -> int:
        return self.generation.max_tokens
    
    @property
    def tool_choice(self) -> str:
        return self.tool.tool_choice

# Convenient constructor
def create_agent_config(
    model_name: str,
    provider: str,
    temperature: float = 0.0,
    top_p: float = 1.0,
    max_tokens: int = 4096,
    tool_choice: str = "auto",
    parallel_tool_calls: bool = False,
    max_inner_turns: int = 20
) -> AgentConfig:
    """Convenient constructor, using flat parameters"""
    return AgentConfig(
        model=Model(short_name=model_name, provider=provider),
        generation=Generation(temperature=temperature, top_p=top_p, max_tokens=max_tokens),
        tool=Tool(tool_choice=tool_choice, parallel_tool_calls=parallel_tool_calls, max_inner_turns=max_inner_turns)
    )