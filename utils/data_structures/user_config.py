from dataclasses import dataclass, field
from typing import Optional, Union, Literal, Dict
from utils.data_structures.common import Model, Generation


@dataclass
class UserConfig:
    """user config"""
    model: Model
    generation: Generation
    
    @classmethod
    def from_dict(cls, data: dict) -> 'UserConfig':
        """Create UserConfig instance from dictionary"""
        # If data directly contains user field
        if 'user' in data:
            data = data['user']
        
        return cls(
            model=Model(**data['model']),
            generation=Generation(**data['generation']),
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "user": {
                "model": {
                    "short_name": self.model.short_name,
                    "provider": self.model.provider,
                },
                "generation": {
                    "temperature": self.generation.temperature,
                    "top_p": self.generation.top_p,
                    "max_tokens": self.generation.max_tokens,
                },
            }
        }
    
    def to_dict_without_user_key(self) -> dict:
        """Convert to dictionary without user key"""
        return {
            "model": {
                "short_name": self.model.short_name,
                "provider": self.model.provider,
            },
            "generation": {
                "temperature": self.generation.temperature,
                "top_p": self.generation.top_p,
                "max_tokens": self.generation.max_tokens,
            },
        }
    
    def get_api_params(self) -> dict:
        """Get parameters for API calls"""
        return {
            "model": self.model.real_name or self.model.short_name,
            "temperature": self.generation.temperature,
            "top_p": self.generation.top_p,
            "max_tokens": self.generation.max_tokens,
        }
    
    def copy_with_updates(self, updates: dict) -> 'UserConfig':
        """Create a copy with nested updates"""
        import copy
        current_dict = self.to_dict_without_user_key()
        
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

# Convenient constructor
def create_user_config(
    model_name: str,
    provider: str,
    temperature: float = 0.0,
    top_p: float = 1.0,
    max_tokens: int = 4096,
) -> UserConfig:
    """Convenient constructor, using flat parameters"""
    return UserConfig(
        model=Model(short_name=model_name, provider=provider),
        generation=Generation(temperature=temperature, top_p=top_p, max_tokens=max_tokens),
    )