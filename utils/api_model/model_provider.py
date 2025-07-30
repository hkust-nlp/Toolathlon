import asyncio
import re
from agents import (
    ModelProvider, 
    OpenAIChatCompletionsModel, 
    Model, 
    set_tracing_disabled,
)
from openai import AsyncOpenAI
from openai.types.responses import ResponseOutputMessage
from configs.global_configs import global_configs
from addict import Dict

class ContextTooLongError(Exception):
    """上下文过长异常"""
    def __init__(self, message, token_count=None, max_tokens=None):
        super().__init__(message)
        self.token_count = token_count
        self.max_tokens = max_tokens

class OpenAIChatCompletionsModelWithRetry(OpenAIChatCompletionsModel):
    def __init__(self, model: str, openai_client: AsyncOpenAI, 
                 retry_times: int = 5, # FIXME: hardcoded now, should be dynamic
                 retry_delay: float = 5.0,
                 debug: bool = True): # FIXME: hardcoded now, should be dynamic
        super().__init__(model=model, openai_client=openai_client)
        self.retry_times = retry_times
        self.retry_delay = retry_delay
        self.debug = debug

    async def get_response(self, *args, **kwargs):
        for i in range(self.retry_times):
            try:
                model_response = await super().get_response(*args, **kwargs)
                output_items = model_response.output
                if self.debug:
                    for item in output_items:
                        if isinstance(item, ResponseOutputMessage):
                            print("assistant: ", item.content[0].text)
                return model_response
            except Exception as e:
                error_str = str(e)
                
                # 检测各种形式的上下文超长错误
                context_too_long = False
                current_tokens, max_tokens = None, None
                
                # 1. 检查错误码是否为 400（通常表示请求无效）
                if "Error code: 400" in error_str:
                    # 直接在错误字符串中查找关键词
                    lower_error = error_str.lower()
                    if any(pattern in lower_error for pattern in [
                        'token count exceeds',
                        'exceeds the maximum',
                        'string too long',
                        'too long',
                        'context_length_exceeded',
                        'maximum context length',
                        'token limit exceeded',
                        'content too long',
                        'message too long',
                        'prompt is too long',
                        'maximum number of tokens'
                    ]):
                        context_too_long = True
                        
                        # 尝试提取具体的 token 数量信息
                        # 模式1: "input token count exceeds the maximum number of tokens allowed (1048576)"
                        match = re.search(r'maximum number of tokens allowed \((\d+)\)', error_str)
                        if match:
                            max_tokens = int(match.group(1))
                        
                        # 模式2: "123456 tokens > 100000 maximum"
                        match = re.search(r'(\d+) tokens > (\d+) maximum', error_str)
                        if match:
                            current_tokens, max_tokens = int(match.group(1)), int(match.group(2))
                        
                        # 模式3: "maximum length 10485760, but got a string with length 30893644"
                        match = re.search(r'maximum length (\d+).*length (\d+)', error_str)
                        if match:
                            max_tokens, current_tokens = int(match.group(1)), int(match.group(2))
                
                # 2. 尝试解析结构化错误（如果是 OpenAI API 错误对象）
                if hasattr(e, 'response') and hasattr(e.response, 'json'):
                    try:
                        error_data = e.response.json()
                        error_msg = error_data.get('error', {}).get('message', '').lower()
                        error_code = error_data.get('error', {}).get('code', '')
                        error_type = error_data.get('error', {}).get('type', '')
                        
                        if any(pattern in error_msg for pattern in [
                            'token count exceeds',
                            'exceeds the maximum',
                            'too long',
                            'context_length_exceeded',
                            'token limit exceeded'
                        ]) or error_code in ['string_above_max_length', 'context_length_exceeded', 'messages_too_long']:
                            context_too_long = True
                    except:
                        pass
                
                # 3. 额外的安全网：检查任何包含特定关键词的错误
                elif not context_too_long:  # 如果还没有检测到
                    lower_error = error_str.lower()
                    if any(pattern in lower_error for pattern in [
                        'context too long',
                        'context_length_exceeded',
                        'maximum context length',
                        'token limit exceeded',
                        'exceeds maximum',
                        'exceeds the maximum',
                        'prompt is too long'
                    ]):
                        context_too_long = True
                
                # 如果检测到上下文超长，直接抛出不重试
                if context_too_long:
                    if self.debug:
                        print(f"Context too long detected: {error_str}")
                    
                    # 创建更详细的错误信息
                    error_msg = f"Context too long: {error_str}"
                    if current_tokens and max_tokens:
                        error_msg = f"Context too long: current={current_tokens} tokens, max={max_tokens} tokens. Original error: {error_str}"
                    elif max_tokens:
                        error_msg = f"Context too long: exceeds maximum of {max_tokens} tokens. Original error: {error_str}"
                    
                    raise ContextTooLongError(
                        error_msg,
                        token_count=current_tokens,
                        max_tokens=max_tokens
                    )
                
                # 其他错误：继续重试逻辑
                if self.debug:
                    print(f"Error in get_response: {e}, retry {i+1}/{self.retry_times}, waiting {self.retry_delay} seconds...")
                
                # 如果是最后一次重试，则抛出原异常
                if i == self.retry_times - 1:
                    raise Exception(f"Failed to get response after {self.retry_times} retries, error: {e}")
                
                await asyncio.sleep(self.retry_delay)

class CustomModelProvider(ModelProvider):
    def get_model(self, model_name: str | None, debug: bool = True) -> Model:
        client = AsyncOpenAI(
            api_key=global_configs.ds_key,
            base_url=global_configs.base_url_ds
        ) if model_name == 'deepseek-chat' or model_name == 'deepseek-reasoner' else AsyncOpenAI(
            api_key=global_configs.non_ds_key,
            base_url=global_configs.base_url_non_ds,
        )
        return OpenAIChatCompletionsModelWithRetry(model=model_name, 
                                                   openai_client=client,
                                                   debug=debug)

class CustomModelProviderAiHubMix(ModelProvider):
    def get_model(self, model_name: str | None, debug: bool = True) -> Model:
        client = AsyncOpenAI(
            api_key=global_configs.non_ds_key,
            base_url=global_configs.base_url_non_ds,
        )
        return OpenAIChatCompletionsModelWithRetry(model=model_name, 
                                                   openai_client=client,
                                                   debug=debug)

model_provider_mapping = {
    "ds_internal": CustomModelProvider,
    "aihubmix": CustomModelProviderAiHubMix,
}

API_MAPPINGS = {
    'deepseek-v3-0324': Dict(
        api_model={"ds_internal": "deepseek-chat",
                   "aihubmix": "DeepSeek-V3"},
        price=[0.272/1000, 1.088/1000],
        concurrency=32,
        context_window=64000
    ),
    'deepseek-r1-0528': Dict(
        api_model={"ds_internal": "deepseek-reasoner",
                   "aihubmix": "DeepSeek-R1"},
        price=[0.546/1000, 2.184/1000],
        concurrency=32,
        context_window=64000
    ),
    'gpt-4o': Dict(
        api_model={"ds_internal": "azure-gpt-4o-2024-11-20",
                   "aihubmix": "gpt-4o-2024-11-20"},
        price=[0.005, 0.015],
        concurrency=32,
        context_window=128000
    ),
    'gpt-4o-mini': Dict(
        api_model={"ds_internal": "azure-gpt-4o-mini-2024-07-18",
                   "aihubmix": "gpt-4o-mini"},
        price=[0.00015, 0.0006],
        concurrency=32,
        context_window=128000
    ),
    'gpt-4.1-0414': Dict(
        api_model={"ds_internal": "azure-gpt-4.1-2025-04-14",
                   "aihubmix": "gpt-4.1"},
        price=[0.002, 0.008],
        concurrency=32,
        context_window=1000000
    ),
    'gpt-4.1-mini-0414': Dict(
        api_model={"ds_internal": "azure-gpt-4.1-mini-2025-04-14",
                   "aihubmix": "gpt-4.1-mini"},
        price=[0.0004, 0.0016],
        concurrency=32,
        context_window=1000000
    ),
    'gpt-4.1-nano-0414': Dict(
        api_model={"ds_internal": "azure-gpt-4.1-nano-2025-04-14",
                   "aihubmix": "gpt-4.1-nano"},
        price=[0.0001, 0.0004],
        concurrency=32,
        context_window=1000000
    ),
    'o4-mini': Dict(
        api_model={"ds_internal": "azure-o4-mini-2025-04-16",
                   "aihubmix": "o4-mini"},
        price=[0.0011, 0.0044],
        concurrency=32,
        context_window=200000
    ),
    'o3': Dict(
        api_model={"ds_internal": "?????", # no o3 in ds internal
                   "aihubmix": "o3"},
        price=[0.010, 0.040],
        concurrency=32,
        context_window=200000
    ),
    'o3-pro': Dict(
        api_model={"ds_internal": "?????", # no o3-pro in ds internal
                   "aihubmix": "o3-pro"}, # no o3-pro in aihubmix
        price=[0.022, 0.088],
        concurrency=32,
        context_window=200000
    ),
    'claude-3.7-sonnet': Dict(
        api_model={"ds_internal": "cloudsway-claude-3-7-sonnet-20250219",
                   "aihubmix": "claude-3-7-sonnet-20250219"},
        price=[0.003, 0.015],
        concurrency=32,
        context_window=200000
    ),
    'claude-4-sonnet-0514': Dict(
        api_model={"ds_internal": "oai-api-claude-sonnet-4-20250514",
                   "aihubmix": "claude-sonnet-4-20250514"},
        price=[0.003, 0.015],
        concurrency=32,
        context_window=200000
    ),
    'claude-4-opus-0514': Dict(
        api_model={"ds_internal": "oai-api-claude-opus-4-20250514",
                   "aihubmix": "claude-opus-4-20250514"},
        price=[0.015, 0.075],
        concurrency=32,
        context_window=200000
    ),
    'gemini-2.5-pro': Dict(
        api_model={"ds_internal": "cloudsway-gemini-2.5-pro",
                   "aihubmix": "gemini-2.5-pro"},
        price=[0.00125, 0.010],
        concurrency=32,
        context_window=1000000
    ),
    'gemini-2.5-flash': Dict(
        api_model={"ds_internal": "cloudsway-gemini-2.5-flash",
                   "aihubmix": "gemini-2.5-flash"},
        price=[0.00015, 0.0035],
        concurrency=32,
        context_window=1000000
    ),
    'grok-3-beta': Dict(
        api_model={"ds_internal": "grok-3-beta",
                   "aihubmix": "grok-3-beta"},
        price=[0.003, 0.015],
        concurrency=32,
        context_window=128000
    ),
    'grok-3-mini-beta': Dict(
        api_model={"ds_internal": "grok-3-mini-beta",
                   "aihubmix": "grok-3-mini-beta"},
        price=[0.0003, 0.0005],
        concurrency=32,
        context_window=128000
    ),
    'kimi-k2-instruct': Dict(
        api_model={"ds_internal": None,
                   "aihubmix": "moonshotai/kimi-k2-instruct"},
        price=[0.62/1000, 2.48/1000],
        concurrency=32,
        context_window=128000
    ),
    'glm-4.5': Dict(
        api_model={"ds_internal": None,
                   "aihubmix": "zai-org/GLM-4.5"},
        price=[0.5/1000, 2.0/1000],
        concurrency=32,
        context_window=128000
    ),
}

set_tracing_disabled(disabled=True)

def calculate_cost(model_name, input_tokens, output_tokens):
    prices = API_MAPPINGS[model_name]['price']
    input_price_per_1k = prices[0] / 1000
    output_price_per_1k = prices[1] / 1000
    
    input_cost = input_tokens * input_price_per_1k
    output_cost = output_tokens * output_price_per_1k
    total_cost = input_cost + output_cost
    
    return input_cost, output_cost, total_cost

def get_context_window(model_name):
    return API_MAPPINGS[model_name]['context_window']