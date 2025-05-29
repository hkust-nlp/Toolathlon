from dataclasses import dataclass, field
from typing import Optional, Union, Literal, Dict
from utils.api_model.model_provider import API_MAPPINGS

@dataclass
class Model:
    """模型配置"""
    short_name: str
    provider: str
    real_name: Optional[str] = None
    
    def __post_init__(self):
        """如果没有提供real_name，默认使用short_name"""
        if self.real_name is None:
            self.real_name = API_MAPPINGS[self.short_name].api_model[self.provider]

@dataclass
class Generation:
    """生成参数配置"""
    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens: int = 4096
    
    def __post_init__(self):
        """验证生成参数的合理性"""
        if not 0 <= self.temperature <= 2:
            raise ValueError(f"temperature 应该在 0 到 2 之间，但得到了 {self.temperature}")
        
        if not 0 < self.top_p <= 1:
            raise ValueError(f"top_p 应该在 0 到 1 之间，但得到了 {self.top_p}")
        
        if self.max_tokens < 1:
            raise ValueError(f"max_tokens 应该大于 0，但得到了 {self.max_tokens}")