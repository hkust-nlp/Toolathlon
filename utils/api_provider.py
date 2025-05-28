import asyncio
import time
import json
import os
import csv
import sqlite3
import uuid
from typing import Optional, List, Dict, Any, Union, AsyncGenerator, Tuple
from datetime import datetime
from enum import Enum
from contextlib import asynccontextmanager
import threading
from functools import partial
from pathlib import Path
from dataclasses import dataclass, asdict
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator, field_serializer
from openai import AsyncOpenAI
import aiohttp
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryCallState
)
import logging

from configs.global_configs import global_configs

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from typing import Literal

from utils.model_provider import API_MAPPINGS


def log_retry(retry_state):
    """记录重试信息"""
    # 安全获取异常信息
    exception_msg = "Unknown error"
    if retry_state.outcome:
        try:
            exception = retry_state.outcome.exception()
            exception_msg = str(exception) if exception else "Unknown error"
        except Exception:
            exception_msg = "Failed to get exception info"
    
    # 安全获取等待时间
    wait_time = 0
    if retry_state.next_action and hasattr(retry_state.next_action, 'sleep'):
        wait_time = retry_state.next_action.sleep
    
    logger.warning(
        f"API 调用失败 (尝试 {retry_state.attempt_number}): "
        f"{exception_msg}, "
        f"等待时间: {wait_time} 秒"
    )

# Python 3.12+ 版本的智能信号量
class SmartAsyncSemaphore:
    """
    Python 3.12+ 的智能异步信号量
    自动检测调用环境并选择合适的信号量实现
    """
    
    def __init__(self, value: int):
        self._value = value
        self._asyncio_semaphore = None
        self._threading_semaphore = threading.Semaphore(value)
        self._loop = None
        self._warned = False
        self._lock = threading.Lock()
    
    def _get_loop_and_semaphore(self):
        """延迟初始化 asyncio 信号量"""
        try:
            loop = asyncio.get_running_loop()
            if self._asyncio_semaphore is None:
                self._asyncio_semaphore = asyncio.Semaphore(self._value)
            return loop, self._asyncio_semaphore
        except RuntimeError:
            return None, None
    
    @asynccontextmanager
    async def acquire_context(self):
        """Python 3.12+ 使用 asynccontextmanager"""
        loop, async_sem = self._get_loop_and_semaphore()
        
        # 检查是否在事件循环中
        if loop is not None and threading.current_thread() == threading.main_thread():
            # 在主事件循环中，使用 asyncio.Semaphore
            if not self._warned:
                with self._lock:
                    if not self._warned:
                        logger.debug(f"使用 asyncio.Semaphore (线程: {threading.current_thread().name})")
                        self._warned = True
            
            async with async_sem:
                yield
        else:
            # 不在事件循环或在其他线程中，使用 threading.Semaphore
            if not self._warned:
                with self._lock:
                    if not self._warned:
                        logger.debug(f"使用 threading.Semaphore (线程: {threading.current_thread().name})")
                        self._warned = True
            
            # Python 3.12+ 可以直接使用 asyncio.to_thread
            await asyncio.to_thread(self._threading_semaphore.acquire)
            try:
                yield
            finally:
                self._threading_semaphore.release()
    
    async def __aenter__(self):
        self._context = self.acquire_context()
        return await self._context.__aenter__()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return await self._context.__aexit__(exc_type, exc_val, exc_tb)

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



class RequestLogger:
    """
    请求日志记录器，支持并发安全的文件写入
    """
    
    def __init__(self, log_file: Optional[str] = None, enable_console: bool = False):
        """
        初始化日志记录器
        
        Args:
            log_file: 日志文件路径，如果为None则不记录到文件
            enable_console: 是否同时输出到控制台
        """
        self.log_file = log_file
        self.enable_console = enable_console
        self._lock = threading.Lock()
        self._request_counter = 0
        
        # 确保日志目录存在
        if self.log_file:
            Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
            # 写入日志头信息
            self._write_header()
    
    def _write_header(self):
        """写入日志文件头信息"""
        header = {
            "log_created_at": datetime.now().isoformat(),
            "log_type": "openai_chat_completion_log",
            "version": "1.0"
        }
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps(header, ensure_ascii=False) + '\n')
            f.write("=" * 80 + '\n')
    
    def get_next_request_index(self) -> int:
        """获取下一个请求索引（线程安全）"""
        with self._lock:
            self._request_counter += 1
            return self._request_counter
    
    def log_request(
        self,
        request_index: int,
        request_id: str,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: Optional[int],
        tools: Optional[List[Tool]] = None,  # 新增
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,  # 新增
        **kwargs
    ):
        """记录请求信息"""
        log_entry = {
            "type": "REQUEST",
            "request_index": request_index,
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": messages,
            "tools": [tool.model_dump() for tool in tools] if tools else None,
            "tool_choice": tool_choice,
            "extra_params": kwargs
        }
        
        self._write_log(log_entry)
    
    def log_response(
        self,
        request_index: int,
        request_id: str,
        content: str,
        reasoning_content: str,
        tool_calls: Optional[List[ToolCall]] = None,
        # usage: Optional[Dict[str, Any]] = None,
        cost_report: Optional[CostReport] = None,
        duration_ms: Optional[float] = None
    ):
        """记录响应信息"""
        log_entry = {
            "type": "RESPONSE",
            "request_index": request_index,
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
            "content": content,
            "reasoning_content": reasoning_content,
            "tool_calls": None if tool_calls is None else [tc.model_dump() for tc in tool_calls],
            # "usage": usage,
            "cost_report": cost_report.model_dump() if cost_report else None,
            "duration_ms": duration_ms
        }
        
        self._write_log(log_entry)
    
    def log_error(
        self,
        request_index: int,
        request_id: str,
        error: Exception,
        duration_ms: Optional[float] = None
    ):
        """记录错误信息"""
        log_entry = {
            "type": "ERROR",
            "request_index": request_index,
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "duration_ms": duration_ms
        }
        
        self._write_log(log_entry)
    
    def _write_log(self, log_entry: Dict[str, Any]):
        """写入日志（线程安全）"""
        with self._lock:
            # 写入文件
            if self.log_file:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False, indent=2) + '\n')
                    f.write("-" * 40 + '\n')
            
            # 输出到控制台
            if self.enable_console:
                print(f"[{log_entry['type']}] Request #{log_entry['request_index']} - {log_entry['timestamp']}")
                if log_entry['type'] == 'ERROR':
                    print(f"  Error: {log_entry['error_message']}")

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
class AsyncOpenAIClientWithRetry:
    """异步OpenAI客户端，带并发控制和请求日志"""
    
    # 全局并发控制
    _global_semaphore = None
    _model_semaphores: Dict[str, SmartAsyncSemaphore] = {}
    _lock = threading.Lock()
    
    def __init__(
        self, 
        api_key: str,
        base_url: str,
        model_name: str = "gpt-3.5-turbo",
        provider: str = "ds_internal",
        max_retries: int = 3,
        timeout: int = 30,
        base_sleep: float = 1.0,
        max_sleep: float = 60.0,
        track_costs: bool = True,
        global_concurrency: Optional[int] = None,
        use_model_concurrency: bool = True,
        log_file: Optional[str] = None,
        enable_console_log: bool = False
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.provider = provider
        self.max_retries = max_retries
        self.base_sleep = base_sleep
        self.max_sleep = max_sleep
        self.track_costs = track_costs
        self.use_model_concurrency = use_model_concurrency
        
        # 初始化客户端
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout
        )
        
        # 设置全局并发限制
        if global_concurrency is not None:
            with self._lock:
                if AsyncOpenAIClientWithRetry._global_semaphore is None:
                    AsyncOpenAIClientWithRetry._global_semaphore = SmartAsyncSemaphore(global_concurrency)
        
        # 成本跟踪
        self.total_cost = 0.0
        self.cost_history: List[CostReport] = []
        self.session = None
        
        # 初始化日志记录器
        self.logger = RequestLogger(log_file, enable_console_log) if log_file else None
    
    @classmethod
    def set_global_concurrency(cls, limit: int):
        """设置全局并发限制"""
        with cls._lock:
            cls._global_semaphore = SmartAsyncSemaphore(limit)
    
    def _get_model_semaphore(self, model: str) -> Optional[SmartAsyncSemaphore]:
        """获取模型特定的信号量"""
        if not self.use_model_concurrency:
            return None
            
        if model in API_MAPPINGS:
            concurrency = API_MAPPINGS[model].get('concurrency', 32)
            
            with self._lock:
                if model not in self._model_semaphores:
                    self._model_semaphores[model] = SmartAsyncSemaphore(concurrency)
                return self._model_semaphores[model]
        
        return None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        if self.session:
            await self.session.close()
    
    def _get_actual_model_name(self, model: Optional[str] = None) -> str:
        """获取实际的 API 模型名称"""
        model_key = model or self.model_name
        
        if model_key in API_MAPPINGS:
            api_models = API_MAPPINGS[model_key]['api_model']
            actual_model = api_models.get(self.provider)
            if actual_model:
                return actual_model
            logger.warning(f"模型 {model_key} 不支持提供商 {self.provider}")
        
        return model_key
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> CostReport:
        """计算使用成本"""
        if model not in API_MAPPINGS:
            return CostReport(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                input_cost=0,
                output_cost=0,
                total_cost=0,
                model=model,
                provider=self.provider
            )
        
        prices = API_MAPPINGS[model]['price']
        input_price_per_1k = prices[0] / 1000
        output_price_per_1k = prices[1] / 1000
        
        input_cost = input_tokens * input_price_per_1k
        output_cost = output_tokens * output_price_per_1k
        total_cost = input_cost + output_cost
        
        report = CostReport(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            model=model,
            provider=self.provider
        )
        
        self.total_cost += total_cost
        self.cost_history.append(report)
        
        return report
    
    @asynccontextmanager
    async def _acquire_semaphores(self, model: str):
        """获取所需的信号量"""
        semaphores = []
        
        # 全局信号量
        if self._global_semaphore:
            semaphores.append(self._global_semaphore)
        
        # 模型特定信号量
        model_sem = self._get_model_semaphore(model)
        if model_sem:
            semaphores.append(model_sem)
        
        # 依次获取所有信号量
        acquired = []
        try:
            for sem in semaphores:
                await sem.__aenter__()
                acquired.append(sem)
            yield
        finally:
            # 反向释放信号量
            for sem in reversed(acquired):
                await sem.__aexit__(None, None, None)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        retry=retry_if_exception_type((Exception,)),
        after=log_retry
    )
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        return_cost: bool = False,
        # 新增tool相关参数
        tools: Optional[List[Tool]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        return_tool_calls: bool = False,  # 是否返回tool_calls
        **kwargs
    ) -> Union[str, Tuple[str, CostReport], Tuple[Optional[str], Optional[List[ToolCall]], Optional[CostReport]]]:
        """带自动重试、并发控制和日志记录的聊天完成方法"""
        model_key = model or self.model_name
        
        # 生成请求ID和索引
        request_id = str(uuid.uuid4())
        request_index = self.logger.get_next_request_index() if self.logger else 0
        start_time = time.time()
        
        # 记录请求
        if self.logger:
            self.logger.log_request(
                request_index=request_index,
                request_id=request_id,
                messages=messages,
                model=model_key,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
        
        async with self._acquire_semaphores(model_key):
            try:
                actual_model = self._get_actual_model_name(model)

                # 构建请求参数
                request_params = {
                    "model": actual_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    **kwargs
                }
                # 添加tools参数
                if tools:
                    request_params["tools"] = [tool.model_dump() for tool in tools]
                if tool_choice is not None:
                    request_params["tool_choice"] = tool_choice

                response = await self.client.chat.completions.create(**request_params)

                # 处理响应
                choice = response.choices[0]
                content = choice.message.content
                try:
                    reasoning_content = choice.message.reasoning_content
                except:
                    reasoning_content = None
                tool_calls = None
                duration_ms = (time.time() - start_time) * 1000
                
                # 处理成本
                cost_report = None
                if self.track_costs and hasattr(response, 'usage'):
                    cost_report = self._calculate_cost(
                        model_key,
                        response.usage.prompt_tokens,
                        response.usage.completion_tokens
                    )
                

                
                # 提取tool_calls
                if hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
                    tool_calls = [
                        ToolCall(
                            id=tc.id,
                            type=tc.type,
                            function=FunctionCall(
                                name=tc.function.name,
                                arguments=tc.function.arguments
                            )
                        )
                        for tc in choice.message.tool_calls
                    ]

                # 记录响应
                if self.logger:
                    # usage_dict = None
                    # if hasattr(response, 'usage'):
                    #     usage_dict = {
                    #         "prompt_tokens": response.usage.prompt_tokens,
                    #         "completion_tokens": response.usage.completion_tokens,
                    #         "total_tokens": response.usage.total_tokens
                    #     }
                    
                    self.logger.log_response(
                        request_index=request_index,
                        request_id=request_id,
                        content=content,
                        reasoning_content=reasoning_content,
                        tool_calls=tool_calls,
                        # usage=usage_dict,
                        cost_report=cost_report,
                        duration_ms=duration_ms
                    )

                # 根据return_tool_calls决定返回格式
                if return_tool_calls:
                    if return_cost:
                        return content, tool_calls, cost_report
                    return content, tool_calls, None
                else:
                    if return_cost:
                        return content, cost_report
                    return content
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                # 记录错误
                if self.logger:
                    self.logger.log_error(
                        request_index=request_index,
                        request_id=request_id,
                        error=e,
                        duration_ms=duration_ms
                    )
                
                logger.error(f"聊天完成请求失败: {e}")
                raise

    def get_cost_summary(self) -> Dict[str, Any]:
        """获取成本摘要"""
        if not self.cost_history:
            return {
                "total_cost": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "request_count": 0,
                "by_model": {}
            }
        
        by_model = {}
        for report in self.cost_history:
            if report.model not in by_model:
                by_model[report.model] = {
                    "cost": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "count": 0
                }
            
            by_model[report.model]["cost"] += report.total_cost
            by_model[report.model]["input_tokens"] += report.input_tokens
            by_model[report.model]["output_tokens"] += report.output_tokens
            by_model[report.model]["count"] += 1
        
        return {
            "total_cost": self.total_cost,
            "total_input_tokens": sum(r.input_tokens for r in self.cost_history),
            "total_output_tokens": sum(r.output_tokens for r in self.cost_history),
            "request_count": len(self.cost_history),
            "by_model": by_model
        }

    async def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        tools: Optional[List[Tool]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncGenerator[Union[str, ToolCall], None]:
        """流式响应，支持tool calls"""
        model_key = model or self.model_name
        
        async with self._acquire_semaphores(model_key):
            actual_model = self._get_actual_model_name(model)
            
            request_params = {
                "model": actual_model,
                "messages": messages,
                "stream": True,
                **kwargs
            }
            
            if tools:
                request_params["tools"] = [tool.model_dump() for tool in tools]
            if tool_choice is not None:
                request_params["tool_choice"] = tool_choice
            
            stream = await self.client.chat.completions.create(**request_params)
            
            current_tool_call = None
            tool_calls_buffer = []
            
            async for chunk in stream:
                delta = chunk.choices[0].delta
                
                # 处理文本内容
                if delta.content:
                    yield delta.content
                
                # 处理tool calls
                if hasattr(delta, 'tool_calls') and delta.tool_calls:
                    for tool_call_delta in delta.tool_calls:
                        # 新的tool call
                        if tool_call_delta.id:
                            if current_tool_call:
                                tool_calls_buffer.append(current_tool_call)
                            current_tool_call = {
                                "id": tool_call_delta.id,
                                "type": "function",
                                "function": {
                                    "name": tool_call_delta.function.name,
                                    "arguments": ""
                                }
                            }
                        
                        # 累积arguments
                        if current_tool_call and tool_call_delta.function.arguments:
                            current_tool_call["function"]["arguments"] += tool_call_delta.function.arguments
            
            # 处理最后一个tool call
            if current_tool_call:
                tool_calls_buffer.append(current_tool_call)
            
            # 转换并返回tool calls
            for tc in tool_calls_buffer:
                yield ToolCall(
                    id=tc["id"],
                    type=tc["type"],
                    function=FunctionCall(
                        name=tc["function"]["name"],
                        arguments=tc["function"]["arguments"]
                    )
                )

    # async def batch_chat_completions_with_tools(
    #     self,
    #     message_batches: List[Dict[str, Any]],  # 包含messages和tools
    # ) -> List[Union[str, Tuple[str, List[ToolCall]]]]:
    #     """批量处理支持tools的请求"""
    #     results = []
        
    #     async with asyncio.TaskGroup() as tg:
    #         tasks = []
    #         for batch in message_batches:
    #             task = tg.create_task(
    #                 self.chat_completion(
    #                     messages=batch["messages"],
    #                     tools=batch.get("tools"),
    #                     tool_choice=batch.get("tool_choice"),
    #                     return_tool_calls=batch.get("return_tool_calls", False),
    #                     **batch.get("kwargs", {})
    #                 )
    #             )
    #             tasks.append(task)
        
    #     for task in tasks:
    #         results.append(task.result())
        
    #     return results

    # # Python 3.12+ 可以使用 TaskGroup 进行批量处理
    # async def batch_chat_completions_with_taskgroup(
    #     self,
    #     message_batches: List[List[Dict[str, str]]],
    #     model: Optional[str] = None
    # ) -> List[Optional[str]]:
    #     """使用 Python 3.12+ 的 TaskGroup 进行批量处理"""
    #     results = [None] * len(message_batches)
        
    #     async with asyncio.TaskGroup() as tg:
    #         tasks = []
    #         for i, messages in enumerate(message_batches):
    #             async def process(idx, msgs):
    #                 try:
    #                     results[idx] = await self.chat_completion(msgs, model=model)
    #                 except Exception as e:
    #                     logger.error(f"批量请求 {idx} 失败: {e}")
    #                     results[idx] = None
                
    #             task = tg.create_task(process(i, messages))
    #             tasks.append(task)
        
    #     return results

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

# 日志分析工具
class LogAnalyzer:
    """日志文件分析工具"""
    
    def __init__(self, log_file: str):
        self.log_file = log_file
        self.entries = []
        self._load_logs()
    
    def _load_logs(self):
        """加载日志文件"""
        with open(self.log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        current_entry = ""
        for line in lines:
            if line.strip() == "-" * 40:
                if current_entry:
                    try:
                        entry = json.loads(current_entry)
                        if isinstance(entry, dict) and 'type' in entry:
                            self.entries.append(entry)
                    except json.JSONDecodeError:
                        pass
                current_entry = ""
            elif not line.startswith("="):
                current_entry += line
    
    def get_request_response_pairs(self) -> List[Dict[str, Any]]:
        """获取请求-响应对"""
        pairs = []
        request_map = {}
        
        for entry in self.entries:
            if entry['type'] == 'REQUEST':
                request_map[entry['request_index']] = entry
            elif entry['type'] in ['RESPONSE', 'ERROR']:
                request = request_map.get(entry['request_index'])
                if request:
                    pairs.append({
                        'request': request,
                        'response': entry,
                        'success': entry['type'] == 'RESPONSE',
                        'duration_ms': entry.get('duration_ms')
                    })
        
        return pairs
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        pairs = self.get_request_response_pairs()
        
        total_requests = len(pairs)
        successful_requests = sum(1 for p in pairs if p['success'])
        failed_requests = total_requests - successful_requests
        
        durations = [p['duration_ms'] for p in pairs if p.get('duration_ms')]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        total_cost = 0
        total_tokens = {'input': 0, 'output': 0}
        
        for pair in pairs:
            if pair['success'] and pair['response'].get('cost_report'):
                cost_report = pair['response']['cost_report']
                total_cost += cost_report.get('total_cost', 0)
                total_tokens['input'] += cost_report.get('input_tokens', 0)
                total_tokens['output'] += cost_report.get('output_tokens', 0)
        
        return {
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'success_rate': successful_requests / total_requests if total_requests > 0 else 0,
            'average_duration_ms': avg_duration,
            'total_cost': total_cost,
            'total_tokens': total_tokens,
            'requests_by_model': self._count_by_model(pairs)
        }
    
    def _count_by_model(self, pairs: List[Dict[str, Any]]) -> Dict[str, int]:
        """按模型统计请求数"""
        model_counts = {}
        for pair in pairs:
            model = pair['request'].get('model', 'unknown')
            model_counts[model] = model_counts.get(model, 0) + 1
        return model_counts
    
    def export_to_csv(self, output_file: str):
        """导出到CSV文件"""
        pairs = self.get_request_response_pairs()
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Request Index', 'Request ID', 'Timestamp', 'Model', 
                'User Message', 'Assistant Response', 'Success', 
                'Duration (ms)', 'Input Tokens', 'Output Tokens', 'Cost'
            ])
            
            for pair in pairs:
                request = pair['request']
                response = pair['response']
                
                # 提取用户消息
                user_message = ""
                for msg in request.get('messages', []):
                    if msg.get('role') == 'user':
                        user_message = msg.get('content', '')
                        break
                
                # 提取助手响应
                assistant_response = ""
                if pair['success']:
                    assistant_response = response.get('content', '')
                else:
                    assistant_response = f"ERROR: {response.get('error_message', 'Unknown error')}"
                
                # 提取成本信息
                cost_report = response.get('cost_report', {})
                
                writer.writerow([
                    request['request_index'],
                    request['request_id'],
                    request['timestamp'],
                    request.get('model', ''),
                    user_message,
                    assistant_response,
                    'Yes' if pair['success'] else 'No',
                    response.get('duration_ms', ''),
                    cost_report.get('input_tokens', ''),
                    cost_report.get('output_tokens', ''),
                    cost_report.get('total_cost', '')
                ])

# 高级并发管理器
class ConcurrencyManager:
    """
    高级并发管理器，支持：
    - 动态调整并发限制
    - 基于时间窗口的速率限制
    - 优先级队列
    """
    
    def __init__(self, default_limit: int = 10):
        self.default_limit = default_limit
        self.semaphores: Dict[str, SmartAsyncSemaphore] = {}
        self.rate_limiters: Dict[str, 'RateLimiter'] = {}
        self._lock = threading.Lock()
    
    def get_semaphore(self, key: str, limit: Optional[int] = None) -> SmartAsyncSemaphore:
        """获取或创建信号量"""
        with self._lock:
            if key not in self.semaphores:
                self.semaphores[key] = SmartAsyncSemaphore(limit or self.default_limit)
            return self.semaphores[key]
    
    def update_limit(self, key: str, new_limit: int):
        """动态更新并发限制"""
        with self._lock:
            # 创建新的信号量替换旧的
            self.semaphores[key] = SmartAsyncSemaphore(new_limit)
            logger.info(f"更新 {key} 的并发限制为 {new_limit}")

class RateLimiter:
    """基于滑动窗口的速率限制器"""
    
    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = []
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """获取许可"""
        async with self._lock:
            now = time.time()
            # 清理过期的请求记录
            self.requests = [t for t in self.requests if now - t < self.window_seconds]
            
            if len(self.requests) >= self.max_requests:
                # 需要等待
                sleep_time = self.window_seconds - (now - self.requests[0])
                await asyncio.sleep(sleep_time)
                # 递归调用重新检查
                return await self.acquire()
            
            # 记录新请求
            self.requests.append(now)

# 带优先级的请求队列
class PriorityRequestQueue:
    """优先级请求队列"""
    
    def __init__(self, client: AsyncOpenAIClientWithRetry):
        self.client = client
        self.queue = asyncio.PriorityQueue()
        self.workers = []
        self.running = False
    
    async def add_request(
        self,
        messages: List[Dict[str, str]],
        priority: int = 0,  # 数字越小优先级越高
        callback: Optional[callable] = None
    ):
        """添加请求到队列"""
        request_id = id(messages)
        await self.queue.put((priority, request_id, messages, callback))
        return request_id
    
    async def _worker(self, worker_id: int):
        """工作协程"""
        while self.running:
            try:
                # 设置超时避免永久阻塞
                priority, request_id, messages, callback = await asyncio.wait_for(
                    self.queue.get(), timeout=1.0
                )
                
                logger.debug(f"Worker {worker_id} 处理请求 {request_id}")
                
                try:
                    result = await self.client.chat_completion(messages)
                    if callback:
                        await callback(request_id, result, None)
                except Exception as e:
                    logger.error(f"请求 {request_id} 失败: {e}")
                    if callback:
                        await callback(request_id, None, e)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} 错误: {e}")
    
    async def start(self, num_workers: int = 5):
        """启动工作协程"""
        self.running = True
        self.workers = [
            asyncio.create_task(self._worker(i))
            for i in range(num_workers)
        ]
    
    async def stop(self):
        """停止工作协程"""
        self.running = False
        await asyncio.gather(*self.workers, return_exceptions=True)

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

# 实时日志监控器
class LogMonitor:
    """实时监控日志文件的变化"""
    
    def __init__(self, log_file: str, callback: callable):
        self.log_file = log_file
        self.callback = callback
        self._stop_event = threading.Event()
        self._monitor_thread = None
    
    def start(self):
        """开始监控"""
        self._monitor_thread = threading.Thread(target=self._monitor_loop)
        self._monitor_thread.daemon = True
        self._monitor_thread.start()
    
    def stop(self):
        """停止监控"""
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join()
    
    def _monitor_loop(self):
        """监控循环"""
        last_position = 0
        
        while not self._stop_event.is_set():
            try:
                if os.path.exists(self.log_file):
                    with open(self.log_file, 'r', encoding='utf-8') as f:
                        f.seek(last_position)
                        new_content = f.read()
                        if new_content:
                            self.callback(new_content)
                            last_position = f.tell()
            except Exception as e:
                logger.error(f"监控日志文件时出错: {e}")
            
            time.sleep(0.5)  # 每0.5秒检查一次

# 高级日志记录器，支持SQLite存储
class AdvancedRequestLogger(RequestLogger):
    """高级请求日志记录器，支持SQLite存储以便查询"""
    
    def __init__(self, log_file: Optional[str] = None, db_file: Optional[str] = None):
        super().__init__(log_file)
        self.db_file = db_file
        
        if self.db_file:
            self._init_database()
    
    def _init_database(self):
        """初始化SQLite数据库"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # 创建表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS requests (
                request_index INTEGER PRIMARY KEY,
                request_id TEXT UNIQUE,
                timestamp TEXT,
                model TEXT,
                temperature REAL,
                max_tokens INTEGER,
                messages TEXT,
                extra_params TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS responses (
                request_index INTEGER PRIMARY KEY,
                request_id TEXT,
                timestamp TEXT,
                content TEXT,
                usage TEXT,
                cost_report TEXT,
                duration_ms REAL,
                success BOOLEAN,
                error_message TEXT,
                FOREIGN KEY (request_id) REFERENCES requests(request_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def log_request(self, request_index: int, request_id: str, messages: List[Dict[str, str]], 
                   model: str, temperature: float, max_tokens: Optional[int], **kwargs):
        """记录请求到文件和数据库"""
        super().log_request(request_index, request_id, messages, model, temperature, max_tokens, **kwargs)
        
        if self.db_file:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO requests 
                (request_index, request_id, timestamp, model, temperature, max_tokens, messages, extra_params)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                request_index,
                request_id,
                datetime.now().isoformat(),
                model,
                temperature,
                max_tokens,
                json.dumps(messages, ensure_ascii=False),
                json.dumps(kwargs, ensure_ascii=False)
            ))
            
            conn.commit()
            conn.close()

# 批量处理辅助函数
async def batch_process_with_progress(
    client: AsyncOpenAIClientWithRetry,
    tasks: List[Dict[str, Any]],
    batch_size: int = 10,
    progress_callback: Optional[callable] = None
) -> List[Any]:
    """带进度回调的批量处理"""
    results = []
    total_tasks = len(tasks)
    
    for i in range(0, total_tasks, batch_size):
        batch = tasks[i:i + batch_size]
        
        # 使用 TaskGroup 处理批次 (Python 3.12+)
        async with asyncio.TaskGroup() as tg:
            batch_tasks = []
            for task_data in batch:
                task = tg.create_task(
                    client.chat_completion(
                        task_data['messages'],
                        **task_data.get('kwargs', {})
                    )
                )
                batch_tasks.append(task)
        
        # 收集结果
        batch_results = [t.result() for t in batch_tasks]
        results.extend(batch_results)
        
        # 进度回调
        if progress_callback:
            await progress_callback(len(results), total_tasks)
    
    return results

# 使用示例
async def basic_example():
    """基础使用示例"""
    # 创建客户端
    client = AsyncOpenAIClientWithRetry(
        api_key=global_configs.non_ds_key,
        base_url=global_configs.base_url_non_ds,
        model_name="gpt-4o-mini",
        provider="ds_internal",
    )
    
    async with client:
        # 简单请求
        response = await client.chat_completion([
            {"role": "user", "content": "你好，请介绍一下自己"}
        ])
        print(f"响应: {response}")
        
        # 获取成本信息
        response, cost_report = await client.chat_completion(
            [{"role": "user", "content": "解释量子计算"}],
            return_cost=True
        )
        print(f"响应: {response}")
        print(f"成本: ${cost_report.total_cost:.4f}")

async def example_with_logging():
    """带日志记录的使用示例"""
    # 创建带日志记录的客户端
    client = AsyncOpenAIClientWithRetry(
        api_key=global_configs.non_ds_key,
        base_url=global_configs.base_url_non_ds,
        model_name="gpt-4o-mini",
        provider="ds_internal",
        log_file="./logs/openai_requests.log",  # 指定日志文件
        enable_console_log=True  # 同时输出到控制台
    )
    
    # 创建对话管理器
    conversation_manager = ConversationManager(max_history=10)
    conversation_manager.set_client(client)
    
    async with client:
        # 示例1：单个请求
        response = await client.chat_completion([
            {"role": "system", "content": "你是一个有用的助手"},
            {"role": "user", "content": "请解释什么是机器学习"}
        ])
        print(f"响应: {response}\n")
        
        # 示例2：并发请求
        tasks = []
        for i in range(5):
            task = asyncio.create_task(
                client.chat_completion([
                    {"role": "user", "content": f"问题 {i}: 生成一个随机数"}
                ])
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 示例3：使用对话管理器
        conv_id = "test_conversation"
        
        # 第一轮对话
        response1 = await conversation_manager.generate_response(
            conv_id,
            "你好，我想了解Python",
            system_prompt="你是一个Python编程专家"
        )
        print(f"助手响应1: {response1}\n")
        
        # 第二轮对话（会包含历史）
        response2 = await conversation_manager.generate_response(
            conv_id,
            "能详细说说装饰器吗？"
        )
        print(f"助手响应2: {response2}\n")
    
    # 分析日志
    print("\n=== 日志分析 ===")
    analyzer = LogAnalyzer("./logs/openai_requests.log")
    stats = analyzer.get_statistics()
    
    print(f"总请求数: {stats['total_requests']}")
    print(f"成功率: {stats['success_rate']:.2%}")
    print(f"平均响应时间: {stats['average_duration_ms']:.2f}ms")
    print(f"总成本: ${stats['total_cost']:.4f}")
    print(f"总Token使用: 输入={stats['total_tokens']['input']}, 输出={stats['total_tokens']['output']}")
    print(f"模型使用统计: {stats['requests_by_model']}")
    
    # 导出到CSV
    analyzer.export_to_csv("./logs/request_analysis.csv")
    print("\n日志已导出到 request_analysis.csv")

async def advanced_example():
    """高级使用示例"""
    
    # 1. 设置全局并发限制
    AsyncOpenAIClientWithRetry.set_global_concurrency(50)
    
    # 2. 创建带并发控制和日志的客户端
    client = AsyncOpenAIClientWithRetry(
        api_key=global_configs.non_ds_key,
        base_url=global_configs.base_url_non_ds,
        model_name="gpt-4o-mini",
        provider="ds_internal",
        global_concurrency=50,  # 全局最多50个并发
        use_model_concurrency=True,  # 使用模型特定的并发限制
        log_file="./logs/advanced_openai_requests.log"
    )
    
    # 3. 创建优先级队列
    priority_queue = PriorityRequestQueue(client)
    
    # 4. 结果收集器
    results = {}
    
    async def handle_result(request_id, result, error):
        """处理结果的回调"""
        if error:
            results[request_id] = f"Error: {error}"
        else:
            results[request_id] = result
    
    async with client:
        # 启动队列处理
        await priority_queue.start(num_workers=10)
        
        try:
            # 添加不同优先级的请求
            high_priority_tasks = []
            for i in range(5):
                req_id = await priority_queue.add_request(
                    [{"role": "user", "content": f"高优先级请求 {i}"}],
                    priority=0,  # 最高优先级
                    callback=handle_result
                )
                high_priority_tasks.append(req_id)
            
            normal_priority_tasks = []
            for i in range(10):
                req_id = await priority_queue.add_request(
                    [{"role": "user", "content": f"普通优先级请求 {i}"}],
                    priority=1,
                    callback=handle_result
                )
                normal_priority_tasks.append(req_id)
            
            low_priority_tasks = []
            for i in range(20):
                req_id = await priority_queue.add_request(
                    [{"role": "user", "content": f"低优先级请求 {i}"}],
                    priority=2,
                    callback=handle_result
                )
                low_priority_tasks.append(req_id)
            
            # 等待所有任务完成
            while len(results) < 35:
                await asyncio.sleep(0.1)
            
            # 统计处理顺序
            print("请求处理统计:")
            print(f"高优先级完成: {sum(1 for t in high_priority_tasks if t in results)}/5")
            print(f"普通优先级完成: {sum(1 for t in normal_priority_tasks if t in results)}/10")
            print(f"低优先级完成: {sum(1 for t in low_priority_tasks if t in results)}/20")
            
        finally:
            # 停止队列
            await priority_queue.stop()
    
    # 打印成本统计
    print("\n成本统计:")
    summary = client.get_cost_summary()
    print(f"总成本: ${summary['total_cost']:.4f}")
    print(f"总请求数: {summary['request_count']}")
    print(f"总输入Token: {summary['total_input_tokens']}")
    print(f"总输出Token: {summary['total_output_tokens']}")
    
    print("\n按模型统计:")
    for model, stats in summary['by_model'].items():
        print(f"  {model}:")
        print(f"    请求数: {stats['count']}")
        print(f"    成本: ${stats['cost']:.4f}")
        print(f"    输入Token: {stats['input_tokens']}")
        print(f"    输出Token: {stats['output_tokens']}")

async def batch_processing_example():
    """批量处理示例"""
    
    # 创建客户端
    client = AsyncOpenAIClientWithRetry(
        api_key=global_configs.non_ds_key,
        base_url=global_configs.base_url_non_ds,
        model_name="gpt-4o-mini",
        provider="ds_internal",
        log_file="./logs/batch_requests.log"
    )
    
    # 准备批量任务
    tasks = []
    for i in range(100):
        tasks.append({
            'messages': [
                {"role": "user", "content": f"为产品 {i} 生成一个创意描述"}
            ],
            'kwargs': {
                'temperature': 0.8,
                'max_tokens': 100
            }
        })
    
    # 进度回调
    async def progress_callback(completed, total):
        print(f"进度: {completed}/{total} ({completed/total*100:.1f}%)")
    
    async with client:
        print("开始批量处理...")
        results = await batch_process_with_progress(
            client,
            tasks,
            batch_size=10,
            progress_callback=progress_callback
        )
        
        print(f"\n完成! 成功处理 {len([r for r in results if r])} 个请求")
        
        # 显示成本
        summary = client.get_cost_summary()
        print(f"总成本: ${summary['total_cost']:.4f}")

async def monitor_example():
    """日志监控示例"""
    
    # 创建日志监控器
    def on_log_update(new_content):
        """处理新的日志内容"""
        lines = new_content.strip().split('\n')
        for line in lines:
            if line and not line.startswith('-') and not line.startswith('='):
                try:
                    entry = json.loads(line)
                    if entry.get('type') == 'REQUEST':
                        print(f"[监控] 新请求 #{entry['request_index']}: {entry['model']}")
                    elif entry.get('type') == 'RESPONSE':
                        print(f"[监控] 响应 #{entry['request_index']}: {entry.get('duration_ms', 0):.1f}ms")
                    elif entry.get('type') == 'ERROR':
                        print(f"[监控] 错误 #{entry['request_index']}: {entry['error_message']}")
                except:
                    pass
    
    # 启动监控
    monitor = LogMonitor("./logs/openai_requests.log", on_log_update)
    monitor.start()
    
    # 创建客户端并发送请求
    client = AsyncOpenAIClientWithRetry(
        api_key=global_configs.non_ds_key,
        base_url=global_configs.base_url_non_ds,
        model_name="gpt-4o-mini",
        provider="ds_internal",
        log_file="./logs/openai_requests.log"
    )
    
    async with client:
        # 发送一些请求以触发监控
        for i in range(5):
            await client.chat_completion([
                {"role": "user", "content": f"测试消息 {i}"}
            ])
            await asyncio.sleep(1)  # 间隔1秒
    
    # 停止监控
    monitor.stop()
    print("监控已停止")

async def rate_limiting_example():
    """速率限制示例"""
    
    # 创建速率限制器 (每10秒最多20个请求)
    rate_limiter = RateLimiter(max_requests=20, window_seconds=10)
    
    # 创建客户端
    client = AsyncOpenAIClientWithRetry(
        api_key=global_configs.non_ds_key,
        base_url=global_configs.base_url_non_ds,
        model_name="gpt-4o-mini",
        provider="ds_internal",
    )
    
    async def rate_limited_request(index: int):
        """受速率限制的请求"""
        await rate_limiter.acquire()
        start_time = time.time()
        
        response = await client.chat_completion([
            {"role": "user", "content": f"速率限制测试 {index}"}
        ])
        
        elapsed = time.time() - start_time
        print(f"请求 {index} 完成，耗时: {elapsed:.2f}s")
        return response
    
    async with client:
        print("开始速率限制测试 (20请求/10秒)...")
        
        # 尝试发送30个请求
        tasks = []
        for i in range(30):
            task = asyncio.create_task(rate_limited_request(i))
            tasks.append(task)
        
        # 等待所有任务完成
        await asyncio.gather(*tasks)
        
        print("所有请求完成!")

# 实用工具函数
def format_messages_for_display(messages: List[Dict[str, str]], max_length: int = 50) -> str:
    """格式化消息列表用于显示"""
    formatted = []
    for msg in messages:
        role = msg.get('role', 'unknown')
        content = msg.get('content', '')
        if len(content) > max_length:
            content = content[:max_length] + "..."
        formatted.append(f"{role}: {content}")
    return " | ".join(formatted)

def estimate_tokens(text: str) -> int:
    """估算文本的token数量（简单估算）"""
    # 粗略估算：平均每4个字符算1个token
    return len(text) // 4

def calculate_batch_cost(messages_list: List[List[Dict[str, str]]], model: str) -> float:
    """估算批量请求的成本"""
    if model not in API_MAPPINGS:
        return 0.0
    
    total_tokens = 0
    for messages in messages_list:
        for msg in messages:
            total_tokens += estimate_tokens(msg.get('content', ''))
    
    # 假设输入输出比例为 1:2
    input_tokens = total_tokens
    output_tokens = total_tokens * 2
    
    prices = API_MAPPINGS[model]['price']
    input_cost = (input_tokens / 1000) * prices[0]
    output_cost = (output_tokens / 1000) * prices[1]
    
    return input_cost + output_cost

# 性能测试函数
async def performance_test():
    """性能测试"""
    
    print("=== OpenAI客户端性能测试 ===\n")
    
    # 测试配置
    test_configs = [
        {"concurrency": 10, "requests": 50, "model": "gpt-4.1-nano"},
        {"concurrency": 20, "requests": 100, "model": "gpt-4o-mini"},
        {"concurrency": 5, "requests": 20, "model": "gpt-4o-mini"},
    ]
    
    for config in test_configs:
        print(f"\n测试配置: {config}")
        
        # 创建客户端
        client = AsyncOpenAIClientWithRetry(
            api_key=global_configs.non_ds_key,
            base_url=global_configs.base_url_non_ds,
            model_name=config['model'],
            provider="ds_internal",
            global_concurrency=config['concurrency'],
            log_file=f"./logs/perf_test_{config['model']}_{config['concurrency']}.log"
        )
        
        async with client:
            start_time = time.time()
            
            # 创建请求任务
            tasks = []
            for i in range(config['requests']):
                task = asyncio.create_task(
                    client.chat_completion([
                        {"role": "user", "content": f"性能测试请求 {i}"}
                    ])
                )
                tasks.append(task)
            
            # 执行并计时
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            elapsed = time.time() - start_time
            
            # 统计结果
            successes = sum(1 for r in results if not isinstance(r, Exception))
            failures = sum(1 for r in results if isinstance(r, Exception))
            
            print(f"  完成时间: {elapsed:.2f}秒")
            print(f"  请求/秒: {config['requests']/elapsed:.2f}")
            print(f"  成功: {successes}, 失败: {failures}")
            
            summary = client.get_cost_summary()
            print(f"  总成本: ${summary['total_cost']:.4f}")
            print(f"  平均成本/请求: ${summary['total_cost']/config['requests']:.4f}")

# 错误处理示例
async def error_handling_example():
    """错误处理示例"""
    
    # 创建客户端，故意使用错误的配置
    client = AsyncOpenAIClientWithRetry(
        api_key="invalid-key",  # 无效的API密钥
        base_url=global_configs.base_url_non_ds,
        model_name="gpt-4o-mini",
        provider="ds_internal",
        max_retries=2,  # 减少重试次数以加快测试
        log_file="./logs/error_handling.log"
    )
    
    async with client:
        try:
            # 这应该会失败
            response = await client.chat_completion([
                {"role": "user", "content": "这个请求应该会失败"}
            ])
        except Exception as e:
            print(f"捕获到预期的错误: {type(e).__name__}: {e}")
        
        # 测试超长输入
        try:
            very_long_message = "很长的消息 " * 10000  # 创建一个非常长的消息
            response = await client.chat_completion([
                {"role": "user", "content": very_long_message}
            ])
        except Exception as e:
            print(f"超长输入错误: {type(e).__name__}: {e}")

async def tool_call_example():
    """Tool call 使用示例"""
    
    # 定义工具函数
    def get_weather(location: str, unit: str = "celsius") -> str:
        """获取天气的模拟函数"""
        return f"The weather in {location} is 22°{unit[0].upper()} and sunny."
    
    def calculate(expression: str) -> str:
        """计算数学表达式"""
        try:
            result = eval(expression)
            return f"The result is: {result}"
        except Exception as e:
            return f"Error calculating: {str(e)}"
    
    # 创建工具管理器
    tool_manager = ToolManager()
    
    # 定义工具
    tool_manager.create_tool(
        name="get_weather",
        description="Get the current weather for a location",
        parameters={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city and country, e.g. San Francisco, USA"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "The unit for temperature"
                }
            },
            "required": ["location"]
        }
    )
    
    tool_manager.create_tool(
        name="calculate",
        description="Calculate a mathematical expression",
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The mathematical expression to calculate"
                }
            },
            "required": ["expression"]
        }
    )
    
    # 注册函数
    tool_manager.register_function("get_weather", get_weather)
    tool_manager.register_function("calculate", calculate)
    
    # 创建客户端
    client = AsyncOpenAIClientWithRetry(
        api_key=global_configs.non_ds_key,
        base_url=global_configs.base_url_non_ds,
        model_name="gpt-4o-mini",
        provider="ds_internal",
        log_file="./logs/tool_calls.log"
    )
    
    async with client:
        # 测试1：天气查询
        messages = [
            {"role": "user", "content": "What's the result of pi^9.19111, round to 10 decimal"}
        ]

        content, tool_calls, _ = await client.chat_completion(
            messages,
            tools=tool_manager.get_tools_list(),
            return_tool_calls=True
        )
        
        if tool_calls:
            print("Tool calls detected:")
            for tc in tool_calls:
                print(f"  - {tc.function.name}({tc.function.arguments})")
            
            # 添加assistant的tool_calls消息
            messages.append({
                "role": "assistant",
                "content": content,
                "tool_calls": [tc.model_dump() for tc in tool_calls]
            })
            
            # 执行tool calls
            for tool_call in tool_calls:
                result = await tool_manager.execute_tool_call(tool_call)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": result
                })
            
            # 获取最终响应
            final_response = await client.chat_completion(messages)
            print(f"Final response: {final_response}")
        else:
            print(f"Direct response: {content}")

# 命令行接口
def main():
    """主函数 - 命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="OpenAI客户端示例")
    parser.add_argument("example", choices=[
        "basic", "logging", "advanced", "batch", "monitor", 
        "rate_limit", "performance", "error", "tool"  # 添加tool
    ], help="要运行的示例")
    
    args = parser.parse_args()
    
    example_map = {
        "basic": basic_example,
        "logging": example_with_logging,
        "advanced": advanced_example,
        "batch": batch_processing_example,
        "monitor": monitor_example,
        "rate_limit": rate_limiting_example,
        "performance": performance_test,
        "error": error_handling_example,
        "tool": tool_call_example,
    }
    
    # 运行选定的示例
    asyncio.run(example_map[args.example]())

if __name__ == "__main__":
    # 如果直接运行，执行一个默认示例
    main()