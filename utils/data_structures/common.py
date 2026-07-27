from dataclasses import dataclass, field, fields
from typing import Any, Optional, Union, Literal, Dict

from openai._types import Body, Headers, Query
from openai.types.shared import Reasoning

from utils.api_model.model_provider import API_MAPPINGS

@dataclass
class Model:
    """Model configuration"""
    short_name: str
    provider: str
    real_name: Optional[str] = None
    context_window: Optional[int] = None
    
    def __post_init__(self):
        """By default, use short_name as real_name if not provided"""
        if self.real_name is None:
            # For local VLLM provider, use the model name as-is without mapping
            if self.provider in ["local_vllm", "unified", "openai_stateful_responses"]:
                self.real_name = self.short_name
            else:
                self.real_name = API_MAPPINGS[self.short_name].api_model[self.provider]
        if "claude" in self.real_name and "3.7" in self.real_name:
            print("\033[91m" + "Warning: we suggest you to use **claude-4.5-sonnet** instead of **claude-3.7-sonnet**, as they have the same price and obviously the former is better." + "\033[0m")

@dataclass
class Generation:
    """Generation parameter configuration"""
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None

    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    truncation: Optional[Literal["auto", "disabled"]] = None
    extra_headers: Optional[Headers] = None
    extra_query: Optional[Query] = None
    store: Optional[bool] = None
    reasoning: Optional[Reasoning] = None
    metadata: Optional[dict[str, str]] = None
    extra_body: Optional[Body] = None
    include_usage: Optional[bool] = None
    extra_request_params: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "Generation":
        """Create Generation while preserving unknown request parameters."""
        data = (data or {}).copy()
        known_fields = {item.name for item in fields(cls)}
        generation_data = {key: value for key, value in data.items() if key in known_fields}
        extra_request_params = generation_data.get("extra_request_params") or {}
        if not isinstance(extra_request_params, dict):
            raise ValueError("generation.extra_request_params must be a dictionary when provided")

        unknown_params = {key: value for key, value in data.items() if key not in known_fields}
        if unknown_params:
            extra_request_params = {**extra_request_params, **unknown_params}
            generation_data["extra_request_params"] = extra_request_params

        return cls(**generation_data)
    
    def __post_init__(self):
        """Validate the reasonableness of generation parameters"""
        if self.temperature is not None and not 0 <= self.temperature <= 2:
            raise ValueError(f"temperature should be between 0 and 2, but got {self.temperature}")
        
        if self.top_p is not None and not 0 < self.top_p <= 1:
            raise ValueError(f"top_p should be between 0 and 1, but got {self.top_p}")
        
        if self.max_tokens is not None and self.max_tokens < 1:
            raise ValueError(f"max_tokens should be greater than 0, but got {self.max_tokens}")

        if self.extra_request_params is None:
            self.extra_request_params = {}
        elif not isinstance(self.extra_request_params, dict):
            raise ValueError("extra_request_params should be a dictionary")
