from dataclasses import dataclass, field
from typing import Optional, Union, Literal, Dict
from utils.data_structures.common import Model, Generation


@dataclass
class Tool:
    """工具调用配置"""
    tool_choice: Union[Literal["auto", "none", "required"], str] = "auto"
    parallel_tool_calls: bool = False
    max_inner_turns: int = 20
    
    def __post_init__(self):
        """验证工具调用参数的合理性"""
        if self.max_inner_turns < 1:
            raise ValueError(f"max_inner_turns 应该大于 0，但得到了 {self.max_inner_turns}")

@dataclass
class AgentConfig:
    """Agent配置"""
    model: Model
    generation: Generation
    tool: Tool
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AgentConfig':
        """从字典创建AgentConfig实例"""
        # 如果data直接包含agent字段
        if 'agent' in data:
            data = data['agent']
        
        return cls(
            model=Model(**data['model']),
            generation=Generation(**data['generation']),
            tool=Tool(**data['tool'])
        )
    
    def to_dict(self) -> dict:
        """转换为字典"""
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
                },
                "tool": {
                    "tool_choice": self.tool.tool_choice,
                    "parallel_tool_calls": self.tool.parallel_tool_calls,
                    "max_inner_turns": self.tool.max_inner_turns,
                }
            }
        }
    
    def to_dict_without_agent_key(self) -> dict:
        """转换为不带agent键的字典"""
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
            "tool": {
                "tool_choice": self.tool.tool_choice,
                "parallel_tool_calls": self.tool.parallel_tool_calls,
                "max_inner_turns": self.tool.max_inner_turns,
            }
        }
    
    def get_api_params(self) -> dict:
        """获取用于 API 调用的参数"""
        return {
            "model": self.model.real_name or self.model.short_name,
            "temperature": self.generation.temperature,
            "top_p": self.generation.top_p,
            "max_tokens": self.generation.max_tokens,
        }
    
    def copy_with_updates(self, updates: dict) -> 'AgentConfig':
        """创建一个副本，支持嵌套更新"""
        import copy
        current_dict = self.to_dict_without_agent_key()
        
        # 深度合并更新
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
    
    # 便捷的属性访问
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

# 便捷的构造函数
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
    """便捷的构造函数，使用扁平参数"""
    return AgentConfig(
        model=Model(short_name=model_name, provider=provider),
        generation=Generation(temperature=temperature, top_p=top_p, max_tokens=max_tokens),
        tool=Tool(tool_choice=tool_choice, parallel_tool_calls=parallel_tool_calls, max_inner_turns=max_inner_turns)
    )

# 使用示例
if __name__ == "__main__":
    # 示例1：使用您提供的格式
    print("示例1 - 标准格式初始化：")
    config_dict = {
        "agent": {
            "model": {
                "short_name": "gpt-4o-mini",
                "provider": "ds_internal"
            },
            "generation": {
                "temperature": 0.0,
                "top_p": 1.0,
                "max_tokens": 4096
            },
            "tool": {
                "tool_choice": "auto",
                "parallel_tool_calls": False,
                "max_inner_turns": 20
            }
        }
    }
    
    # 直接传入字典
    agent_config = AgentConfig(config_dict)
    print(f"Model: {agent_config.model.short_name}")
    print(f"Provider: {agent_config.model.provider}")
    print(f"Temperature: {agent_config.generation.temperature}")
    print(f"Tool choice: {agent_config.tool.tool_choice}")
    
    # 示例2：不带agent键的字典
    print("\n示例2 - 不带agent键：")
    config_dict_no_agent = {
        "model": {
            "short_name": "claude-3",
            "provider": "anthropic"
        },
        "generation": {
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 8000
        },
        "tool": {
            "tool_choice": "required",
            "parallel_tool_calls": True,
            "max_inner_turns": 15
        }
    }
    
    agent_config2 = AgentConfig(config_dict_no_agent)
    print(f"Model: {agent_config2.model.short_name}")
    print(f"Max tokens: {agent_config2.generation.max_tokens}")
    
    # 示例3：使用结构化初始化
    print("\n示例3 - 结构化初始化：")
    agent_config3 = AgentConfig(
        model=Model(short_name="gemini-pro", provider="google"),
        generation=Generation(temperature=0.5, max_tokens=2048),
        tool=Tool(tool_choice="none")
    )
    print(agent_config3)
    
    # 示例4：使用便捷构造函数
    print("\n示例4 - 便捷构造函数：")
    agent_config4 = create_agent_config(
        model_name="gpt-4-turbo",
        provider="openai",
        temperature=0.8,
        max_tokens=4096,
        tool_choice="auto"
    )
    print(f"Model: {agent_config4.model_name}")
    print(f"Temperature: {agent_config4.temperature}")
    
    # 示例5：部分更新
    print("\n示例5 - 部分更新：")
    updated_config = agent_config.copy_with_updates({
        "generation": {"temperature": 1.0},
        "tool": {"max_inner_turns": 30}
    })
    print(f"原始 temperature: {agent_config.temperature}")
    print(f"更新后 temperature: {updated_config.temperature}")
    print(f"原始 max_inner_turns: {agent_config.tool.max_inner_turns}")
    print(f"更新后 max_inner_turns: {updated_config.tool.max_inner_turns}")
    
    # 示例6：获取API参数
    print("\n示例6 - API参数：")
    api_params = agent_config.get_api_params()
    print(api_params)
    
    # 示例7：转换回字典
    print("\n示例7 - 转换为字典：")
    dict_with_agent = agent_config.to_dict()
    dict_without_agent = agent_config.to_dict_without_agent_key()
    print("带agent键:", dict_with_agent.keys())
    print("不带agent键:", dict_without_agent.keys())