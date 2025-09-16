import asyncio
import re
from agents import (
    ModelProvider, 
    OpenAIChatCompletionsModel, 
    Model, 
    set_tracing_disabled,
    _debug
)
from openai import AsyncOpenAI
from openai.types.responses import ResponseOutputMessage
from configs.global_configs import global_configs
from addict import Dict

from agents.models.openai_chatcompletions import *
from agents.model_settings import ModelSettings

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
        
    def _add_cache_control_to_messages(self, messages: list, min_cache_tokens: int = 2048) -> list:
        """
        为Claude模型添加cache_control breakpoints到消息中
        根据OpenRouter文档，只有文本部分可以添加cache_control
        """
        if not messages:
            return messages
            
        modified_messages = []
        
        for i, message in enumerate(messages):
            new_message = message.copy()
            
            # 对system、user和tool消息添加缓存控制，且内容要足够长
            # tool消息在多轮对话中会作为上下文重复使用，非常适合缓存
            if message.get('role') in ['system', 'user', 'tool'] and isinstance(message.get('content'), str):
                content_length = len(message['content'])
                # 粗略估算token数量（约4字符=1token）
                estimated_tokens = content_length // 4
                
                if estimated_tokens >= min_cache_tokens:
                    # 将content转换为多部分格式以支持cache_control
                    new_message['content'] = [
                        {
                            'type': 'text',
                            'text': message['content'],
                            'cache_control': {
                                'type': 'ephemeral'
                            }
                        }
                    ]
                    # if self.debug:
                    #     print(f"🔄 PROMPT CACHING: Added cache_control to {message.get('role')} message with ~{estimated_tokens} tokens")
            
            modified_messages.append(new_message)
        
        return modified_messages

    def _get_model_specific_config(self):
        """获取模型特定的配置参数"""
        if 'gpt-5' in self.model:
            return {
                'use_max_completion_tokens': True,
                'use_parallel_tool_calls': True
            }
        elif 'o4' in self.model or 'o3' in self.model:
            return {
                'use_max_completion_tokens': True,
                'use_parallel_tool_calls': False
            }
        elif 'claude' in self.model.lower():
            return {
                'use_max_completion_tokens': False,
                'use_parallel_tool_calls': True,
                'supports_prompt_caching': True,
            }
        else:
            return {
                'use_max_completion_tokens': False,
                'use_parallel_tool_calls': True
            }

    async def _fetch_response(
        self,
        system_instructions: str | None,
        input: str | list[TResponseInputItem],
        model_settings: ModelSettings,
        tools: list[Tool],
        output_schema: AgentOutputSchemaBase | None,
        handoffs: list[Handoff],
        span: Span[GenerationSpanData],
        tracing: ModelTracing,
        stream: bool = False,
    ) -> ChatCompletion | tuple[Response, AsyncStream[ChatCompletionChunk]]:
        converted_messages = Converter.items_to_messages(input)

        if system_instructions:
            converted_messages.insert(
                0,
                {
                    "content": system_instructions,
                    "role": "system",
                },
            )
        
        # 为Claude模型添加prompt caching支持
        model_config = self._get_model_specific_config()
        if model_config.get('supports_prompt_caching', False):
            # if self.debug:
            #     print(f"🔄 PROMPT CACHING: Enabled for Claude model: {self.model}")
            converted_messages = self._add_cache_control_to_messages(converted_messages)
        if tracing.include_data():
            span.span_data.input = converted_messages

        parallel_tool_calls = (
            True
            if model_settings.parallel_tool_calls and tools and len(tools) > 0
            else False
            if model_settings.parallel_tool_calls is False
            else NOT_GIVEN
        )
        tool_choice = Converter.convert_tool_choice(model_settings.tool_choice)
        response_format = Converter.convert_response_format(output_schema)

        converted_tools = [Converter.tool_to_openai(tool) for tool in tools] if tools else []

        for handoff in handoffs:
            converted_tools.append(Converter.convert_handoff_tool(handoff))

        if _debug.DONT_LOG_MODEL_DATA:
            logger.debug("Calling LLM")
        else:
            logger.debug(
                f"{json.dumps(converted_messages, indent=2)}\n"
                f"Tools:\n{json.dumps(converted_tools, indent=2)}\n"
                f"Stream: {stream}\n"
                f"Tool choice: {tool_choice}\n"
                f"Response format: {response_format}\n"
            )

        reasoning_effort = model_settings.reasoning.effort if model_settings.reasoning else None
        store = ChatCmplHelpers.get_store_param(self._get_client(), model_settings)

        stream_options = ChatCmplHelpers.get_stream_options_param(
            self._get_client(), model_settings, stream=stream
        )
        
        # 构建基础参数
        base_params = {
            'model': self.model,
            'messages': converted_messages,
            'tools': converted_tools or NOT_GIVEN,
            'temperature': self._non_null_or_not_given(model_settings.temperature),
            'top_p': self._non_null_or_not_given(model_settings.top_p),
            'frequency_penalty': self._non_null_or_not_given(model_settings.frequency_penalty),
            'presence_penalty': self._non_null_or_not_given(model_settings.presence_penalty),
            'tool_choice': tool_choice,
            'response_format': response_format,
            'stream': stream,
            'stream_options': self._non_null_or_not_given(stream_options),
            'store': self._non_null_or_not_given(store),
            'reasoning_effort': self._non_null_or_not_given(reasoning_effort),
            'extra_headers': { **HEADERS, **(model_settings.extra_headers or {}) },
            'extra_query': model_settings.extra_query,
            'extra_body': model_settings.extra_body,
            'metadata': self._non_null_or_not_given(model_settings.metadata),
        }
        
        # 根据模型类型添加特定参数
        if model_config['use_max_completion_tokens']:
            base_params['max_completion_tokens'] = self._non_null_or_not_given(model_settings.max_tokens)
        else:
            base_params['max_tokens'] = self._non_null_or_not_given(model_settings.max_tokens)
            
        if model_config['use_parallel_tool_calls']:
            base_params['parallel_tool_calls'] = parallel_tool_calls
        
        # DEBUG: Print the actual parameters being sent to OpenAI SDK
        # print("🔍 DEBUG: OpenAI SDK call parameters:")
        # print(f"  Model: {base_params.get('model')}")
        # print(f"  Temperature: {base_params.get('temperature')}")
        # print(f"  Extra Body: {base_params.get('extra_body')}")
        # print("=" * 50)
        
        ret = await self._get_client().chat.completions.create(**base_params)

        if isinstance(ret, ChatCompletion):
            return ret

        response = Response(
            id=FAKE_RESPONSES_ID,
            created_at=time.time(),
            model=self.model,
            object="response",
            output=[],
            tool_choice=cast(Literal["auto", "required", "none"], tool_choice)
            if tool_choice != NOT_GIVEN
            else "auto",
            top_p=model_settings.top_p,
            temperature=model_settings.temperature,
            tools=[],
            parallel_tool_calls=parallel_tool_calls or False,
            reasoning=model_settings.reasoning,
        )
        return response, ret

    async def get_response(self, *args, **kwargs):
        for i in range(self.retry_times):
            try:
                model_response = await super().get_response(*args, **kwargs)
                output_items = model_response.output
                if self.debug:
                    for item in output_items:
                        if isinstance(item, ResponseOutputMessage):
                            print("ASSISTANT: ", item.content[0].text)
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

class CustomModelProviderAnthropic(ModelProvider):
    def get_model(self, model_name: str | None, debug: bool = True) -> Model:
        client = AsyncOpenAI(
            api_key=global_configs.official_anthropic_key,
            base_url="https://api.anthropic.com/v1/",
        )
        return OpenAIChatCompletionsModelWithRetry(model=model_name, 
                                                   openai_client=client,
                                                   debug=debug)

class CustomModelProviderLocalVLLM(ModelProvider):
    def get_model(self, model_name: str | None, debug: bool = True) -> Model:
        import os
        vllm_base_url = os.getenv('VLLM_BASE_URL', 'http://localhost:8000/v1')
        client = AsyncOpenAI(
            api_key="fake-key",  # VLLM doesn't require a real API key
            base_url=vllm_base_url,
        )
        return OpenAIChatCompletionsModelWithRetry(model=model_name, 
                                                   openai_client=client,
                                                   debug=debug)

class CustomModelProviderOpenRouter(ModelProvider):
    def get_model(self, model_name: str | None, debug: bool = True) -> Model:
        client = AsyncOpenAI(
            api_key=global_configs.openrouter_key,
            base_url="https://openrouter.ai/api/v1",
        )
        return OpenAIChatCompletionsModelWithRetry(model=model_name, 
                                                   openai_client=client,
                                                   debug=debug)

model_provider_mapping = {
    "ds_internal": CustomModelProvider,
    "aihubmix": CustomModelProviderAiHubMix,
    "anthropic": CustomModelProviderAnthropic,
    "local_vllm": CustomModelProviderLocalVLLM,
    "openrouter": CustomModelProviderOpenRouter,
}

API_MAPPINGS = {
    'deepseek-v3-0324': Dict(
        api_model={"ds_internal": "deepseek-chat",
                   "aihubmix": "DeepSeek-V3",
                   "openrouter": "deepseek/deepseek-chat"},
        price=[0.272/1000, 1.088/1000],
        concurrency=32,
        context_window=64000,
        openrouter_config={"provider": {"only": ["deepseek"]}}
    ),
    'deepseek-r1-0528': Dict(
        api_model={"ds_internal": "deepseek-reasoner",
                   "aihubmix": "DeepSeek-R1"},
        price=[0.546/1000, 2.184/1000],
        concurrency=32,
        context_window=64000
    ),
    'deepseek-v3.1': Dict(
        api_model={"ds_internal": "",
                   "aihubmix": "DeepSeek-V3.1",
                   "openrouter": "deepseek/deepseek-chat-v3.1"},
        price=[0.56/1000, 1.68/1000],
        concurrency=32,
        context_window=128000,
        openrouter_config={"provider": {"only": ["sambanova/fp8"]}}
    ),
    'deepseek-v3.1-think': Dict(
        api_model={"ds_internal": "",
                   "aihubmix": "DeepSeek-V3.1-Think"},
        price=[0.56/1000, 1.68/1000],
        concurrency=32,
        context_window=128000
    ),
    'gpt-4o': Dict(
        api_model={"ds_internal": "azure-gpt-4o-2024-11-20",
                   "aihubmix": "gpt-4o-2024-11-20",
                   "openrouter": "openai/gpt-4o"},
        price=[0.005, 0.015],
        concurrency=32,
        context_window=128000,
        openrouter_config={"provider": {"only": ["openai"]}}
    ),
    'gpt-4o-mini': Dict(
        api_model={"ds_internal": "azure-gpt-4o-mini-2024-07-18",
                   "aihubmix": "gpt-4o-mini"},
        price=[0.00015, 0.0006],
        concurrency=32,
        context_window=128000
    ),
    # 'gpt-4.1-0414': Dict(
    #     api_model={"ds_internal": "azure-gpt-4.1-2025-04-14",
    #                "aihubmix": "gpt-4.1"},
    #     price=[0.002, 0.008],
    #     concurrency=32,
    #     context_window=1000000
    # ),
    # 'gpt-4.1-mini-0414': Dict(
    #     api_model={"ds_internal": "azure-gpt-4.1-mini-2025-04-14",
    #                "aihubmix": "gpt-4.1-mini"},
    #     price=[0.0004, 0.0016],
    #     concurrency=32,
    #     context_window=1000000
    # ),
    # 'gpt-4.1-nano-0414': Dict(
    #     api_model={"ds_internal": "azure-gpt-4.1-nano-2025-04-14",
    #                "aihubmix": "gpt-4.1-nano"},
    #     price=[0.0001, 0.0004],
    #     concurrency=32,
    #     context_window=1000000
    # ),
    'gpt-5': Dict(
        api_model={"ds_internal": "",
                   "aihubmix": "gpt-5",
                   "openrouter": "openai/gpt-5"},
        price=[1.25/1000, 10/1000.0],
        concurrency=32,
        context_window=1000000,
        openrouter_config={"provider": {"only": ["openai"]}}
    ),
    'gpt-5-mini': Dict(
        api_model={"ds_internal": "",
                   "aihubmix": "gpt-5-mini",
                   "openrouter": "openai/gpt-5-mini"},
        price=[0.25/1000,2/1000.0],
        concurrency=32,
        context_window=1000000
    ),
    'gpt-5-nano': Dict(
        api_model={"ds_internal": "",
                   "aihubmix": "gpt-5-nano"},
        price=[0.05/1000, 0.4/1000],
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
    # 'claude-3.7-sonnet': Dict(
    #     api_model={"ds_internal": "cloudsway-claude-3-7-sonnet-20250219",
    #                "aihubmix": "claude-3-7-sonnet-20250219"},
    #     price=[0.003, 0.015],
    #     concurrency=32,
    #     context_window=200000
    # ),
    'claude-4-sonnet-0514': Dict(
        api_model={"ds_internal": "oai-api-claude-sonnet-4-20250514",
                   "aihubmix": "claude-sonnet-4-20250514",
                   "anthropic": "claude-sonnet-4-20250514",
                   "openrouter": "anthropic/claude-sonnet-4"},
        price=[0.003, 0.015],
        concurrency=32,
        context_window=200000,
        openrouter_config={"provider": {"only": ["anthropic"]}}
    ),
    # 'claude-4-opus-0514': Dict(
    #     api_model={"ds_internal": "oai-api-claude-opus-4-20250514",
    #                "aihubmix": "claude-opus-4-20250514"},
    #     price=[0.015, 0.075],
    #     concurrency=32,
    #     context_window=200000
    # ),
    'claude-4.1-opus-0805': Dict(
        api_model={"ds_internal": "",
                   "aihubmix": "claude-opus-4-1-20250805",
                   "anthropic": "claude-opus-4-1-20250805"},
        price=[16.5/1000, 82.5/1000],
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
    'grok-code-fast-1': Dict(
        api_model={"ds_internal": "grok-code-fast-1",
                   "aihubmix": "grok-code-fast-1",
                   "openrouter": "x-ai/grok-code-fast-1"},
        price=[0.2/1000, 1.5/1000],
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
    'Kimi-K2-0905': Dict(
        api_model={"ds_internal": None,
                   "aihubmix": "Kimi-K2-0905",
                   "openrouter": "moonshotai/kimi-k2-0905"},
        price=[0.548/1000, 2.192/1000],
        concurrency=32,
        context_window=128000,
        openrouter_config={"provider": {"only": ["moonshotai"]}}
    ),
    'glm-4.5': Dict(
        api_model={"ds_internal": None,
                   "aihubmix": "zai-org/GLM-4.5",
                   "openrouter": "z-ai/glm-4.5"},
        price=[0.5/1000, 2.0/1000],
        concurrency=32,
        context_window=128000,
        openrouter_config={"provider": {"only": ["z-ai/fp8"]}}
    ),
    "qwen-3-coder": Dict(
        api_model={"ds_internal": None,
                   "aihubmix": "Qwen3-Coder",
                   "openrouter": "qwen/qwen3-coder"},
        price=[0.54/1000, 2.16/1000],
        concurrency=32,
        context_window=128000,
        openrouter_config={"provider": {"only": ["fireworks"]}}
    ),
    
    
}

set_tracing_disabled(disabled=True)

def calculate_cost(model_name, input_tokens, output_tokens):
    # For local VLLM models, cost is 0
    if model_name not in API_MAPPINGS:
        return 0.0, 0.0, 0.0
    
    prices = API_MAPPINGS[model_name]['price']
    input_price_per_1k = prices[0] / 1000
    output_price_per_1k = prices[1] / 1000
    
    input_cost = input_tokens * input_price_per_1k
    output_cost = output_tokens * output_price_per_1k
    total_cost = input_cost + output_cost
    
    return input_cost, output_cost, total_cost

def get_context_window(model_name):
    # For local VLLM models, assume a reasonable default context window
    if model_name not in API_MAPPINGS:
        return 128000  # Default context window for local models
    
    return API_MAPPINGS[model_name]['context_window']