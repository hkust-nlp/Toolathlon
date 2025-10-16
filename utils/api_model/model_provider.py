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
    """Context length exceeded error"""
    def __init__(self, message, token_count=None, max_tokens=None):
        super().__init__(message)
        self.token_count = token_count
        self.max_tokens = max_tokens

class OpenAIChatCompletionsModelWithRetry(OpenAIChatCompletionsModel):
    def __init__(self, model: str, 
                 openai_client: AsyncOpenAI, 
                 retry_times: int = 5, # FIXME: hardcoded now, should be dynamic
                 retry_delay: float = 5.0,
                 debug: bool = True,
                 short_model_name: str | None = None): # FIXME: hardcoded now, should be dynamic
        super().__init__(model=model, openai_client=openai_client)
        self.retry_times = retry_times
        self.retry_delay = retry_delay
        self.debug = debug
        self.short_model_name = short_model_name

    def _add_cache_control_to_messages(self, messages: list, min_cache_tokens: int = 2048) -> list:
        """
        Add cache_control breakpoints to messages for Claude models.
        According to OpenRouter docs, only text parts can have cache_control.
        Anthropic allows up to 4 cache control breakpoints.
        """
        if not messages:
            return messages
        
        # Collect all eligible messages and their token count
        cacheable_messages = []
        
        for i, message in enumerate(messages):
            # Add cache_control to system, user, and tool messages
            if message.get('role') in ['system', 'user', 'tool'] and isinstance(message.get('content'), str):
                content_length = len(message['content'])
                # Roughly estimate token count (~4 chars = 1 token)
                estimated_tokens = content_length // 4
                
                if estimated_tokens >= min_cache_tokens:
                    cacheable_messages.append({
                        'index': i,
                        'tokens': estimated_tokens,
                        'role': message.get('role')
                    })
        
        # Sort by token count descending, take top 4
        cacheable_messages.sort(key=lambda x: x['tokens'], reverse=True)
        top_cacheable = cacheable_messages[:4]
        
        # Indices that should get cache_control
        cache_indices = {item['index'] for item in top_cacheable}
        
        # Build modified message list
        modified_messages = []
        
        for i, message in enumerate(messages):
            new_message = message.copy()
            
            # Only add cache_control if message is in cache_indices
            if i in cache_indices:
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
                #     # Retrieve token count for debug output
                #     tokens = next(item['tokens'] for item in top_cacheable if item['index'] == i)
                #     print(f"🔄 PROMPT CACHING: Added cache_control to {message.get('role')} message with ~{tokens} tokens")
            
            modified_messages.append(new_message)
        
        return modified_messages

    def _get_model_specific_config(self):
        """Get model-specific configuration parameters"""
        if 'gpt-5' in self.model:
            basic = {
                'use_max_completion_tokens': True,
                'use_parallel_tool_calls': True
            }
            if "low" in self.short_model_name:
                basic['reasoning_effort'] = "low"
            elif "medium" in self.short_model_name:
                basic['reasoning_effort'] = "medium"
            elif "high" in self.short_model_name:
                basic['reasoning_effort'] = "high"
            return basic
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
        
        # Add prompt caching for Claude models
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
        
        # Build base parameters
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
        
        # Add model-specific parameters
        if model_config['use_max_completion_tokens']:
            base_params['max_completion_tokens'] = self._non_null_or_not_given(model_settings.max_tokens)
        else:
            base_params['max_tokens'] = self._non_null_or_not_given(model_settings.max_tokens)
            
        if model_config['use_parallel_tool_calls']:
            base_params['parallel_tool_calls'] = parallel_tool_calls
        
        # override reasoning_effort
        if model_config.get('reasoning_effort') is not None:
            base_params['reasoning_effort'] = model_config['reasoning_effort']
        
        # for claude-4.5-sonnet, top_p and temperament cannot be set simultaneously
        if "claude-sonnet-4.5" in self.model or "claude-sonnet-4-5" in self.model:
            base_params.pop('top_p')
        
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
                
                # Detect various forms of context too long errors
                context_too_long = False
                current_tokens, max_tokens = None, None
                
                # 1. Check if error code is 400 (usually means bad request)
                if "Error code: 400" in error_str:
                    # Directly search for keywords in error string
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
                        'maximum number of tokens',
                        r'This model\'s maximum prompt length is', # for xAI model
                        'Your request exceeded model token limit: ' # for kimi
                    ]):
                        context_too_long = True
                        
                        # Try to extract token numbers from message
                        # Pattern 1: "input token count exceeds the maximum number of tokens allowed (1048576)"
                        match = re.search(r'maximum number of tokens allowed \((\d+)\)', error_str)
                        if match:
                            max_tokens = int(match.group(1))
                        
                        # Pattern 2: "123456 tokens > 100000 maximum"
                        match = re.search(r'(\d+) tokens > (\d+) maximum', error_str)
                        if match:
                            current_tokens, max_tokens = int(match.group(1)), int(match.group(2))
                        
                        # Pattern 3: "maximum length 10485760, but got a string with length 30893644"
                        match = re.search(r'maximum length (\d+).*length (\d+)', error_str)
                        if match:
                            max_tokens, current_tokens = int(match.group(1)), int(match.group(2))
                        
                        # Pattern 4: xAI
                        match = re.search(r'This model\'s maximum prompt length is (\d+).*request contains (\d+)', error_str)
                        if match:
                            max_tokens, current_tokens = int(match.group(1)), int(match.group(2))
                        
                        # Pattern 5: kimi
                        match = re.search(r'Your request exceeded model token limit: (\d+)', error_str)
                        if match:
                            max_tokens = int(match.group(1))
                
                # 2. Try parsing structured error (OpenAI API error object)
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
                
                # 3. Extra safety: check for any error containing a certain keyword
                elif not context_too_long:
                    lower_error = error_str.lower()
                    if any(pattern in lower_error for pattern in [
                        'context too long',
                        'context_length_exceeded',
                        'maximum context length',
                        'token limit exceeded',
                        'exceeds maximum',
                        'exceeds the maximum',
                        'prompt is too long',
                        'Your request exceeded model token limit: ',
                    ]):
                        context_too_long = True
                
                # If context too long detected, do not retry, raise
                if context_too_long:
                    if self.debug:
                        print(f"Context too long detected: {error_str}")
                    
                    # Create more detailed error message
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
                
                # For other errors: continue retry logic
                if self.debug:
                    print(f"Error in get_response: {e}, retry {i+1}/{self.retry_times}, waiting {self.retry_delay} seconds...")
                
                # Raise if it's the last try
                if i == self.retry_times - 1:
                    raise Exception(f"Failed to get response after {self.retry_times} retries, error: {e}")
                
                await asyncio.sleep(self.retry_delay)

class CustomModelProviderAiHubMix(ModelProvider):
    def get_model(self, model_name: str | None, debug: bool = True, short_model_name: str | None = None) -> Model:
        client = AsyncOpenAI(
            api_key=global_configs.aihubmix_key,
            base_url="https://aihubmix.com/v1",
        )
        return OpenAIChatCompletionsModelWithRetry(model=model_name, 
                                                   openai_client=client,
                                                   debug=debug,
                                                   short_model_name=short_model_name)

class CustomModelProviderAnthropic(ModelProvider):
    def get_model(self, model_name: str | None, debug: bool = True, short_model_name: str | None = None) -> Model:
        client = AsyncOpenAI(
            api_key=global_configs.anthropic_official_key,
            base_url="https://api.anthropic.com/v1/",
        )
        return OpenAIChatCompletionsModelWithRetry(model=model_name, 
                                                   openai_client=client,
                                                   debug=debug,
                                                   short_model_name=short_model_name)

class CustomModelProviderLocalVLLM(ModelProvider):
    def get_model(self, model_name: str | None, debug: bool = True, short_model_name: str | None = None) -> Model:
        import os
        vllm_base_url = os.getenv('VLLM_BASE_URL', 'http://localhost:8000/v1')
        client = AsyncOpenAI(
            api_key="fake-key",  # VLLM doesn't require a real API key
            base_url=vllm_base_url,
        )
        return OpenAIChatCompletionsModelWithRetry(model=model_name, 
                                                   openai_client=client,
                                                   debug=debug,
                                                   short_model_name=short_model_name)

class CustomModelProviderOpenRouter(ModelProvider):
    def get_model(self, model_name: str | None, debug: bool = True, short_model_name: str | None = None) -> Model:
        client = AsyncOpenAI(
            api_key=global_configs.openrouter_key,
            base_url="https://openrouter.ai/api/v1",
        )
        return OpenAIChatCompletionsModelWithRetry(model=model_name, 
                                                   openai_client=client,
                                                   debug=debug,
                                                   short_model_name=short_model_name)

class CustomModelProviderQwenOfficial(ModelProvider):
    def get_model(self, model_name: str | None, debug: bool = True, short_model_name: str | None = None) -> Model:
        client = AsyncOpenAI(
            api_key=global_configs.qwen_official_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        return OpenAIChatCompletionsModelWithRetry(model=model_name, 
                                                   openai_client=client,
                                                   debug=debug,
                                                   short_model_name=short_model_name)

class CustomModelProviderKimiOfficial(ModelProvider):
    def get_model(self, model_name: str | None, debug: bool = True, short_model_name: str | None = None) -> Model:
        client = AsyncOpenAI(
            api_key=global_configs.kimi_official_key,
            base_url="https://api.moonshot.cn/v1",
        )
        return OpenAIChatCompletionsModelWithRetry(model=model_name, 
                                                   openai_client=client,
                                                   debug=debug,
                                                   short_model_name=short_model_name)

class CustomModelProviderDeepSeekOfficial(ModelProvider):
    def get_model(self, model_name: str | None, debug: bool = True, short_model_name: str | None = None) -> Model:
        client = AsyncOpenAI(
            api_key=global_configs.deepseek_official_key,
            base_url="https://api.deepseek.com/v1",
        )
        return OpenAIChatCompletionsModelWithRetry(model=model_name, 
                                                   openai_client=client,
                                                   debug=debug,
                                                   short_model_name=short_model_name)

model_provider_mapping = {
    "aihubmix": CustomModelProviderAiHubMix,
    "anthropic": CustomModelProviderAnthropic,
    "local_vllm": CustomModelProviderLocalVLLM,
    "openrouter": CustomModelProviderOpenRouter,
    "qwen_official": CustomModelProviderQwenOfficial,
    "kimi_official": CustomModelProviderKimiOfficial,
    "deepseek_official": CustomModelProviderDeepSeekOfficial,
}

API_MAPPINGS = {
    'deepseek-v3.2-exp': Dict(
        api_model={"deepseek_official": "deepseek-chat"}, # 2025/9/29, this model may become other model later
        price=[2/7000, 3/7000], # an estimated price, no cache considered
        concurrency=32,
        context_window=128000,
    ),
    'gpt-5': Dict(
        api_model={"ds_internal": "",
                   "aihubmix": "gpt-5",
                   "openrouter": "openai/gpt-5"},
        price=[1.25/1000, 10/1000.0],
        concurrency=32,
        context_window=400000,
        openrouter_config={"provider": {"only": ["openai/default"]}}
    ),
    'gpt-5-low': Dict(
        api_model={"openrouter": "openai/gpt-5"},
        price=[1.25/1000, 10/1000.0],
        concurrency=32,
        context_window=400000,
        openrouter_config={"provider": {"only": ["openai"]}}
    ),
    'gpt-5-medium': Dict(
        api_model={"openrouter": "openai/gpt-5"},
        price=[1.25/1000, 10/1000.0],
        concurrency=32,
        context_window=400000,
        openrouter_config={"provider": {"only": ["openai"]}}
    ),
    'gpt-5-high': Dict(
        api_model={"openrouter": "openai/gpt-5"},
        price=[1.25/1000, 10/1000.0],
        concurrency=32,
        context_window=400000,
        openrouter_config={"provider": {"only": ["openai"]}}
    ),
    'gpt-5-mini': Dict(
        api_model={"ds_internal": "",
                   "aihubmix": "gpt-5-mini",
                   "openrouter": "openai/gpt-5-mini"},
        price=[0.25/1000,2/1000.0],
        concurrency=32,
        context_window=400000,
        openrouter_config={"provider": {"only": ["openai"]}}
    ),
    'o4-mini': Dict(
        api_model={"ds_internal": "azure-o4-mini-2025-04-16",
                   "aihubmix": "o4-mini",
                   "openrouter": "openai/o4-mini"},
        price=[0.0011, 0.0044],
        concurrency=32,
        context_window=200000,
        openrouter_config={"provider": {"only": ["openai"]}}
    ),
    'o3': Dict(
        api_model={"ds_internal": "?????", # no o3 in ds internal
                   "aihubmix": "o3",
                   "openrouter": "openai/o3"},
        price=[0.010, 0.040],
        concurrency=32,
        context_window=200000,
        openrouter_config={"provider": {"only": ["openai"]}}
    ),
    'o3-pro': Dict(
        api_model={"ds_internal": "?????", # no o3-pro in ds internal
                   "aihubmix": "o3-pro"}, # no o3-pro in aihubmix
        price=[0.022, 0.088],
        concurrency=32,
        context_window=200000,
        openrouter_config={"provider": {"only": ["openai"]}}
    ),
    'claude-4.5-sonnet-0929': Dict(
        api_model={"aihubmix": "claude-sonnet-4-5-20250929",
                   "anthropic": "claude-sonnet-4-5-20250929",
                   "openrouter": "anthropic/claude-sonnet-4.5"},
        price=[0.003, 0.015],
        concurrency=32,
        context_window=1000000,
        openrouter_config={"provider": {"only": ["anthropic"]}}
    ),
    'claude-4.5-haiku-1001': Dict(
        api_model={"anthropic": "claude-haiku-4-5-20251001",
                   "openrouter": "anthropic/claude-haiku-4.5"},
        price=[0.003, 0.015],
        concurrency=32,
        context_window=1000000,
        openrouter_config={"provider": {"only": ["anthropic"]}}
    ),
    'claude-4-sonnet-0514': Dict(
        api_model={"aihubmix": "claude-sonnet-4-20250514",
                   "anthropic": "claude-sonnet-4-20250514",
                   "openrouter": "anthropic/claude-sonnet-4"},
        price=[0.003, 0.015],
        concurrency=32,
        context_window=1000000,
        openrouter_config={"provider": {"only": ["anthropic"]}}
    ),
    'claude-4.1-opus-0805': Dict(
        api_model={"ds_internal": "",
                   "aihubmix": "claude-opus-4-1-20250805",
                   "openrouter": "anthropic/claude-opus-4.1",
                   "anthropic": "claude-opus-4-1-20250805"},
        price=[16.5/1000, 82.5/1000],
        concurrency=32,
        context_window=200000,
        openrouter_config={"provider": {"only": ["anthropic"]}}
    ),
    'gemini-2.5-pro': Dict(
        api_model={"ds_internal": "cloudsway-gemini-2.5-pro",
                   "aihubmix": "gemini-2.5-pro",
                   "openrouter": "google/gemini-2.5-pro"},
        price=[0.00125, 0.010],
        concurrency=32,
        context_window=1000000,
        openrouter_config={"provider": {"only": ["google-vertex"]}}
    ),
    'gemini-2.5-flash': Dict(
        api_model={"ds_internal": "cloudsway-gemini-2.5-flash",
                   "aihubmix": "gemini-2.5-flash",
                   "openrouter": "google/gemini-2.5-flash"},
        price=[0.00015, 0.0035],
        concurrency=32,
        context_window=1000000,
        openrouter_config={"provider": {"only": ["google-vertex"]}}
    ),
    'grok-4': Dict(
        api_model={"openrouter": "x-ai/grok-4"},
        price=[3/1000, 15/1000],
        concurrency=32,
        context_window=256000,
        openrouter_config={"provider": {"only": ["xai"]}}
    ),
    'grok-code-fast-1': Dict(
        api_model={"ds_internal": "grok-code-fast-1",
                   "aihubmix": "grok-code-fast-1",
                   "openrouter": "x-ai/grok-code-fast-1"},
        price=[0.2/1000, 1.5/1000],
        concurrency=32,
        context_window=256000,
        openrouter_config={"provider": {"only": ["xai"]}}
    ),    
    'grok-4-fast': Dict(
        api_model={"ds_internal": None,
                   "openrouter": "x-ai/grok-4-fast:free"},
        price=[0.2/1000, 0.5/1000],
        concurrency=32,
        context_window=2000000,
        openrouter_config={"provider": {"only": ["xai"]}}
    ),
    'kimi-k2-0905': Dict(
        api_model={"ds_internal": None,
                   "aihubmix": "Kimi-K2-0905",
                   "openrouter": "moonshotai/kimi-k2-0905",
                   "kimi_official": "kimi-k2-0905-preview"},
        price=[0.548/1000, 2.192/1000],
        concurrency=32,
        context_window=256000,
        openrouter_config={"provider": {"only": ["moonshotai"]}}
    ),
    # 'glm-4.5': Dict(
    #     api_model={"ds_internal": None,
    #                "aihubmix": "zai-org/GLM-4.5",
    #                "openrouter": "z-ai/glm-4.5"},
    #     price=[0.5/1000, 2.0/1000],
    #     concurrency=32,
    #     context_window=128000,
    #     openrouter_config={"provider": {"only": ["z-ai/fp8"]}}
    # ),
    'glm-4.6': Dict(
        api_model={"openrouter": "z-ai/glm-4.6"},
        price=[0.6/1000, 2.2/1000],
        concurrency=32,
        context_window=128000,
        openrouter_config={"provider": {"only": ["z-ai"]}}
    ),
    "qwen-3-coder": Dict(
        api_model={"ds_internal": None,
                   "aihubmix": "Qwen3-Coder",
                   "openrouter": "qwen/qwen3-coder",
                   "qwen_official": "qwen3-coder-plus"},
        price=[0.54/1000, 2.16/1000],
        concurrency=32,
        context_window=256000,
    ),
    "qwen-3-max": Dict(
        api_model={
            "qwen_official": "qwen3-max-2025-09-23",
            "openrouter": "qwen/qwen3-max"},
        price=[1.2/1000, 6/1000],
        concurrency=32,
        context_window=256000,
        openrouter_config={"provider": {"only": ["alibaba"]}}
    ),
    # "gpt-oss-120b": Dict(
    #     api_model={"openrouter": "openai/gpt-oss-120b"},
    #     price=[0.00125, 0.010],
    #     concurrency=32,
    #     context_window=256000,
    #     openrouter_config={"provider": {"only": ["fireworks"]}}
    # ),
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