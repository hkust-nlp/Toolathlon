import threading
import time
import json
import uuid
from typing import Optional, List, Dict, Any, Union, AsyncGenerator, Tuple
from openai import AsyncOpenAI
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import logging
from contextlib import asynccontextmanager

from utils.general.base_models import *
from utils.api_model.semaphore import SmartAsyncSemaphore
from utils.logging.logging_utils import RequestLogger
from utils.api_model.model_provider import API_MAPPINGS, calculate_cost

# 设置日志
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

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
        model_name: str = None,
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
        if self.model_name is not None:
            logger.warning("A default model name is set to the client, however, it will be override if another model name is provided in `chat_completion(...)`. Please be careful to this point!")
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

        input_cost, output_cost, total_cost = calculate_cost(model,input_tokens,output_tokens)
        
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

                if "gpt-5" in actual_model:
                    request_params['max_completion_tokens'] = request_params.pop('max_tokens')

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
            
            if "gpt-5" in actual_model:
                if 'max_tokens' in request_params:
                    request_params['max_completion_tokens'] = request_params.pop('max_tokens')

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