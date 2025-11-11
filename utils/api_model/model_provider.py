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
from openai.types.responses import ResponseOutputMessage, ResponseOutputText
from configs.global_configs import global_configs
from addict import Dict

from agents.models.openai_chatcompletions import *
from agents.model_settings import ModelSettings

from pydantic import BaseModel

from agents.models.chatcmpl_converter import *

from typing import List, Union
from typing_extensions import Literal, Annotated, TypeAlias
from openai._utils import PropertyInfo


class ResponseOutputReasoningContent(BaseModel):
    reasoning_content: str
    """The reasoning content from the model."""
    type: Literal["reasoning_content"] = "reasoning_content"

ExtendedContent: TypeAlias = Annotated[Union[ResponseOutputText, ResponseOutputRefusal, ResponseOutputReasoningContent], PropertyInfo(discriminator="type")]


class ExtendedResponseOutputMessage(ResponseOutputMessage):
    content: List[ExtendedContent]
    """The content of the output message."""


class ConverterWithExplicitReasoningContent(Converter):
    @classmethod
    def message_to_output_items(cls, message: ChatCompletionMessage) -> list[TResponseOutputItem]:
        items: list[TResponseOutputItem] = []

        message_item = ExtendedResponseOutputMessage(
            id=FAKE_RESPONSES_ID,
            content=[],
            role="assistant",
            type="message",
            status="completed",
        )
        if message.content:
            message_item.content.append(
                ResponseOutputText(text=message.content, type="output_text", annotations=[])
            )
        if message.refusal:
            message_item.content.append(
                ResponseOutputRefusal(refusal=message.refusal, type="refusal")
            )
        if hasattr(message, "reasoning_content"):
            message_item.content.append(ResponseOutputReasoningContent(reasoning_content=message.reasoning_content, type="reasoning_content"))

        if message.audio:
            raise AgentsException("Audio is not currently supported")

        if message_item.content:
            items.append(message_item)

        if message.tool_calls:
            for tool_call in message.tool_calls:
                items.append(
                    ResponseFunctionToolCall(
                        id=FAKE_RESPONSES_ID,
                        call_id=tool_call.id,
                        arguments=tool_call.function.arguments,
                        name=tool_call.function.name,
                        type="function_call",
                    )
                )

        return items


    @classmethod
    def items_to_messages(
        cls,
        items: str | Iterable[TResponseInputItem],
    ) -> list[ChatCompletionMessageParam]:
        """
        Convert a sequence of 'Item' objects into a list of ChatCompletionMessageParam.

        Rules:
        - EasyInputMessage or InputMessage (role=user) => ChatCompletionUserMessageParam
        - EasyInputMessage or InputMessage (role=system) => ChatCompletionSystemMessageParam
        - EasyInputMessage or InputMessage (role=developer) => ChatCompletionDeveloperMessageParam
        - InputMessage (role=assistant) => Start or flush a ChatCompletionAssistantMessageParam
        - response_output_message => Also produces/flushes a ChatCompletionAssistantMessageParam
        - tool calls get attached to the *current* assistant message, or create one if none.
        - tool outputs => ChatCompletionToolMessageParam
        """

        if isinstance(items, str):
            return [
                ChatCompletionUserMessageParam(
                    role="user",
                    content=items,
                )
            ]

        result: list[ChatCompletionMessageParam] = []
        current_assistant_msg: ChatCompletionAssistantMessageParam | None = None

        def flush_assistant_message() -> None:
            nonlocal current_assistant_msg
            if current_assistant_msg is not None:
                # The API doesn't support empty arrays for tool_calls
                if not current_assistant_msg.get("tool_calls"):
                    del current_assistant_msg["tool_calls"]
                result.append(current_assistant_msg)
                current_assistant_msg = None

        def ensure_assistant_message() -> ChatCompletionAssistantMessageParam:
            nonlocal current_assistant_msg
            if current_assistant_msg is None:
                current_assistant_msg = ChatCompletionAssistantMessageParam(role="assistant")
                current_assistant_msg["tool_calls"] = []
            return current_assistant_msg

        for item in items:
            # 1) Check easy input message
            if easy_msg := cls.maybe_easy_input_message(item):
                role = easy_msg["role"]
                content = easy_msg["content"]

                if role == "user":
                    flush_assistant_message()
                    msg_user: ChatCompletionUserMessageParam = {
                        "role": "user",
                        "content": cls.extract_all_content(content),
                    }
                    result.append(msg_user)
                elif role == "system":
                    flush_assistant_message()
                    msg_system: ChatCompletionSystemMessageParam = {
                        "role": "system",
                        "content": cls.extract_text_content(content),
                    }
                    result.append(msg_system)
                elif role == "developer":
                    flush_assistant_message()
                    msg_developer: ChatCompletionDeveloperMessageParam = {
                        "role": "developer",
                        "content": cls.extract_text_content(content),
                    }
                    result.append(msg_developer)
                elif role == "assistant":
                    flush_assistant_message()
                    msg_assistant: ChatCompletionAssistantMessageParam = {
                        "role": "assistant",
                        "content": cls.extract_text_content(content),
                    }
                    result.append(msg_assistant)
                else:
                    raise UserError(f"Unexpected role in easy_input_message: {role}")

            # 2) Check input message
            elif in_msg := cls.maybe_input_message(item):
                role = in_msg["role"]
                content = in_msg["content"]
                flush_assistant_message()

                if role == "user":
                    msg_user = {
                        "role": "user",
                        "content": cls.extract_all_content(content),
                    }
                    result.append(msg_user)
                elif role == "system":
                    msg_system = {
                        "role": "system",
                        "content": cls.extract_text_content(content),
                    }
                    result.append(msg_system)
                elif role == "developer":
                    msg_developer = {
                        "role": "developer",
                        "content": cls.extract_text_content(content),
                    }
                    result.append(msg_developer)
                else:
                    raise UserError(f"Unexpected role in input_message: {role}")

            # 3) response output message => assistant
            elif resp_msg := cls.maybe_response_output_message(item):
                flush_assistant_message()
                new_asst = ChatCompletionAssistantMessageParam(role="assistant")
                contents = resp_msg["content"]
                text_segments = []
                for c in contents:
                    if c["type"] == "output_text":
                        text_segments.append(c["text"])
                    elif c["type"] == "refusal":
                        new_asst["refusal"] = c["refusal"]
                    elif c["type"] == "output_audio":
                        # Can't handle this, b/c chat completions expects an ID which we dont have
                        raise UserError(
                            f"Only audio IDs are supported for chat completions, but got: {c}"
                        )
                    elif c["type"] == "reasoning_content":
                        new_asst["reasoning_content"] = c["reasoning_content"]
                    else:
                        raise UserError(f"Unknown content type in ExtendedResponseOutputMessage: {c}")

                if text_segments:
                    combined = "\n".join(text_segments)
                    new_asst["content"] = combined

                new_asst["tool_calls"] = []
                current_assistant_msg = new_asst

            # 4) function/file-search calls => attach to assistant
            elif file_search := cls.maybe_file_search_call(item):
                asst = ensure_assistant_message()
                tool_calls = list(asst.get("tool_calls", []))
                new_tool_call = ChatCompletionMessageToolCallParam(
                    id=file_search["id"],
                    type="function",
                    function={
                        "name": "file_search_call",
                        "arguments": json.dumps(
                            {
                                "queries": file_search.get("queries", []),
                                "status": file_search.get("status"),
                            }
                        ),
                    },
                )
                tool_calls.append(new_tool_call)
                asst["tool_calls"] = tool_calls

            elif func_call := cls.maybe_function_tool_call(item):
                asst = ensure_assistant_message()
                tool_calls = list(asst.get("tool_calls", []))
                arguments = func_call["arguments"] if func_call["arguments"] else "{}"
                new_tool_call = ChatCompletionMessageToolCallParam(
                    id=func_call["call_id"],
                    type="function",
                    function={
                        "name": func_call["name"],
                        "arguments": arguments,
                    },
                )
                tool_calls.append(new_tool_call)
                asst["tool_calls"] = tool_calls
            # 5) function call output => tool message
            elif func_output := cls.maybe_function_tool_call_output(item):
                flush_assistant_message()
                msg: ChatCompletionToolMessageParam = {
                    "role": "tool",
                    "tool_call_id": func_output["call_id"],
                    "content": func_output["output"],
                }
                result.append(msg)

            # 6) item reference => handle or raise
            elif item_ref := cls.maybe_item_reference(item):
                raise UserError(
                    f"Encountered an item_reference, which is not supported: {item_ref}"
                )

            # 7) If we haven't recognized it => fail or ignore
            else:
                raise UserError(f"Unhandled item type or structure: {item}")

        flush_assistant_message()
        return result



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
        Add cache_control breakpoints to messages every 20 blocks from the front.
        No more than 4 breakpoints total. If message count is < 20, add at the last position only.
        Additional logic is removed, only every 20th (and last if needed) gets cache_control.
        """
        if not messages:
            return messages

        total = len(messages)
        indices = []

        # Compute target indices for cache_control
        if total <= 20:
            indices = [total - 1]
        else:
            segs = [i for i in range(19, total, 20)]
            indices.extend(segs)
            # Always add the last message if it's not already in segs and we haven't hit four
            if (total - 1) not in indices and len(indices) < 4:
                indices.append(total - 1)
            # Cap to at most 4
            indices = indices[:4]

        modified_messages = []
        for i, message in enumerate(messages):
            new_message = message.copy()
            if i in indices and isinstance(message.get('content'), str):
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
                    # print(f"🔄 PROMPT CACHING: Added cache_control to message index {i}")
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
        elif 'o4' in self.model or 'o3' in self.model or 'gemini' in self.model: # for gemini it will raise an error stating it does not support parallel tool calls, but if I remove this parameter, it can still do so, not sure if it has a different parameter name ...
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
        converted_messages = ConverterWithExplicitReasoningContent.items_to_messages(input)

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
        tool_choice = ConverterWithExplicitReasoningContent.convert_tool_choice(model_settings.tool_choice)
        response_format = ConverterWithExplicitReasoningContent.convert_response_format(output_schema)

        converted_tools = [ConverterWithExplicitReasoningContent.tool_to_openai(tool) for tool in tools] if tools else []

        for handoff in handoffs:
            converted_tools.append(ConverterWithExplicitReasoningContent.convert_handoff_tool(handoff))

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
        if "claude" in self.model and any(version in self.model for version in ["4.5", "4-5"]):
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

    async def raw_get_response(
        self,
        system_instructions: str | None,
        input: str | list[TResponseInputItem],
        model_settings: ModelSettings,
        tools: list[Tool],
        output_schema: AgentOutputSchemaBase | None,
        handoffs: list[Handoff],
        tracing: ModelTracing,
        previous_response_id: str | None,
    ) -> ModelResponse:
        with generation_span(
            model=str(self.model),
            model_config=model_settings.to_json_dict() | {"base_url": str(self._client.base_url)},
            disabled=tracing.is_disabled(),
        ) as span_generation:
            response = await self._fetch_response(
                system_instructions,
                input,
                model_settings,
                tools,
                output_schema,
                handoffs,
                span_generation,
                tracing,
                stream=False,
            )

            if _debug.DONT_LOG_MODEL_DATA:
                logger.debug("Received model response")
            else:
                logger.debug(
                    f"LLM resp:\n{json.dumps(response.choices[0].message.model_dump(), indent=2)}\n"
                )

            usage = (
                Usage(
                    requests=1,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                )
                if response.usage
                else Usage()
            )
            if tracing.include_data():
                span_generation.span_data.output = [response.choices[0].message.model_dump()]
            span_generation.span_data.usage = {
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
            }

            items = ConverterWithExplicitReasoningContent.message_to_output_items(response.choices[0].message)

            return ModelResponse(
                output=items,
                usage=usage,
                response_id=None,
            )

    async def get_response(self, *args, **kwargs):
        for i in range(self.retry_times):
            try:
                model_response = await self.raw_get_response(*args, **kwargs)
                output_items = model_response.output
                if self.debug:
                    for item in output_items:
                        if isinstance(item, ExtendedResponseOutputMessage):
                            reasoning_content = None
                            for content in item.content:
                                if isinstance(content, ResponseOutputReasoningContent):
                                    reasoning_content = content.reasoning_content
                                    break
                            if reasoning_content:
                                print("\033[90mTHINKING: ", reasoning_content, "\033[0m")
                            # find text content in the output items
                            text_content = None
                            for content in item.content:
                                if isinstance(content, ResponseOutputText):
                                    text_content = content.text
                                    break
                            if text_content:
                                import re
                                match = re.search(r'<think>(.*?)</think>', text_content, re.DOTALL)
                                display_text = text_content
                                if match:
                                    thinking = match.group(1).strip()
                                    print("\033[90mTHINKING: ", thinking, "\033[0m")
                                    # Remove only the first <think>...</think> for the assistant answer
                                    display_text = text_content[:match.start()] + text_content[match.end():]
                                stripped_text = display_text.strip()
                                if stripped_text:
                                    print("ASSISTANT: ", stripped_text)
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
                        'maximum prompt length is', # for xAI model
                        'request exceeded model token limit' # for kimi
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
                        match = re.search(r'maximum prompt length is (\d+).*request contains (\d+)', error_str)
                        if match:
                            max_tokens, current_tokens = int(match.group(1)), int(match.group(2))
                        
                        # Pattern 5: kimi
                        match = re.search(r'request exceeded model token limit: (\d+)', error_str)
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
                    # import traceback
                    # traceback.print_exc()
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

class CustomModelProviderGoogle(ModelProvider):
    def get_model(self, model_name: str | None, debug: bool = True, short_model_name: str | None = None) -> Model:
        client = AsyncOpenAI(
            api_key=global_configs.google_official_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
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

class CustomModelProviderXAI(ModelProvider):
    def get_model(self, model_name: str | None, debug: bool = True, short_model_name: str | None = None) -> Model:
        client = AsyncOpenAI(
            api_key=global_configs.xai_official_key,
            base_url="https://api.x.ai/v1",
        )
        return OpenAIChatCompletionsModelWithRetry(model=model_name, 
                                                   openai_client=client,
                                                   debug=debug,
                                                   short_model_name=short_model_name)

class CustomModelProviderUnified(ModelProvider):
    def get_model(self, model_name: str | None, debug: bool = True, short_model_name: str | None = None) -> Model:
        import os
        base_url = os.getenv('TOOLATHLON_OPENAI_BASE_URL', None)
        if base_url is None:
            raise ValueError("TOOLATHLON_OPENAI_BASE_URL is not set! You must set it in the environment variables when using unified model provider!")
        api_key = os.getenv('TOOLATHLON_OPENAI_API_KEY', "fake-key")
        if api_key == "fake-key":
            print("[Warning] TOOLATHLON_OPENAI_API_KEY is not set! Usually this is only expected when you are running some self-deployed models like via vllm or sglang!")
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
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
    "google": CustomModelProviderGoogle,
    "xai": CustomModelProviderXAI,
    "unified": CustomModelProviderUnified,
}

API_MAPPINGS = {
    'deepseek-v3.2-exp': Dict(
        api_model={"deepseek_official": "deepseek-chat"}, # 2025/9/29, this model may become other model later
        price=[0.28/1000, 0.42/1000], # an estimated price, no cache considered
        concurrency=32,
        context_window=128000,
    ),
    'gpt-5': Dict(
        api_model={"aihubmix": "gpt-5",
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
        openrouter_config={"provider": {"only": ["openai/default"]}}
    ),
    'gpt-5-medium': Dict(
        api_model={"openrouter": "openai/gpt-5"},
        price=[1.25/1000, 10/1000.0],
        concurrency=32,
        context_window=400000,
        openrouter_config={"provider": {"only": ["openai/default"]}}
    ),
    'gpt-5-high': Dict(
        api_model={"openrouter": "openai/gpt-5"},
        price=[1.25/1000, 10/1000.0],
        concurrency=32,
        context_window=400000,
        openrouter_config={"provider": {"only": ["openai/default"]}}
    ),
    'gpt-5-mini': Dict(
        api_model={"aihubmix": "gpt-5-mini",
                   "openrouter": "openai/gpt-5-mini"},
        price=[0.25/1000,2/1000.0],
        concurrency=32,
        context_window=400000,
        openrouter_config={"provider": {"only": ["openai"]}}
    ),
    'o4-mini': Dict(
        api_model={"aihubmix": "o4-mini",
                   "openrouter": "openai/o4-mini"},
        price=[0.0011, 0.0044],
        concurrency=32,
        context_window=200000,
        openrouter_config={"provider": {"only": ["openai"]}}
    ),
    'o3': Dict(
        api_model={"aihubmix": "o3",
                   "openrouter": "openai/o3"},
        price=[0.010, 0.040],
        concurrency=32,
        context_window=200000,
        openrouter_config={"provider": {"only": ["openai"]}}
    ),
    'o3-pro': Dict(
        api_model={"aihubmix": "o3-pro"}, # no o3-pro in aihubmix
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
        price=[0.001, 0.005],
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
        api_model={"aihubmix": "claude-opus-4-1-20250805",
                   "openrouter": "anthropic/claude-opus-4.1",
                   "anthropic": "claude-opus-4-1-20250805"},
        price=[16.5/1000, 82.5/1000],
        concurrency=32,
        context_window=200000,
        openrouter_config={"provider": {"only": ["anthropic"]}}
    ),
    'gemini-2.5-pro': Dict(
        api_model={"aihubmix": "gemini-2.5-pro",
                   "openrouter": "google/gemini-2.5-pro",
                   "google": "gemini-2.5-pro"},
        price=[0.00125, 0.010],
        concurrency=32,
        context_window=1000000,
        openrouter_config={"provider": {"only": ["google-vertex"]}}
    ),
    'gemini-2.5-flash': Dict(
        api_model={"aihubmix": "gemini-2.5-flash",
                   "openrouter": "google/gemini-2.5-flash",
                   "google": "gemini-2.5-flash"},
        price=[0.00015, 0.0035],
        concurrency=32,
        context_window=1000000,
        openrouter_config={"provider": {"only": ["google-vertex"]}}
    ),
    'grok-4': Dict(
        api_model={"openrouter": "x-ai/grok-4",
                    "xai":"grok-4-0709"},
        price=[3/1000, 15/1000],
        concurrency=32,
        context_window=256000,
        openrouter_config={"provider": {"only": ["xai"]}}
    ),
    'grok-code-fast-1': Dict(
        api_model={"aihubmix": "grok-code-fast-1",
                   "openrouter": "x-ai/grok-code-fast-1",
                   "xai":"grok-code-fast-1"},
        price=[0.2/1000, 1.5/1000],
        concurrency=32,
        context_window=256000,
        openrouter_config={"provider": {"only": ["xai"]}}
    ),    
    'grok-4-fast': Dict(
        api_model={"openrouter": "x-ai/grok-4-fast",
                   "xai":"grok-4-fast"},
        price=[0.2/1000, 0.5/1000],
        concurrency=32,
        context_window=2000000,
        openrouter_config={"provider": {"only": ["xai"]}}
    ),
    'kimi-k2-0905': Dict(
        api_model={"aihubmix": "Kimi-K2-0905",
                   "openrouter": "moonshotai/kimi-k2-0905",
                   "kimi_official": "kimi-k2-0905-preview"},
        price=[0.548/1000, 2.192/1000],
        concurrency=32,
        context_window=256000,
        openrouter_config={"provider": {"only": ["moonshotai"]}}
    ),

    'glm-4.6': Dict(
        api_model={"openrouter": "z-ai/glm-4.6"},
        price=[0.6/1000, 2.2/1000],
        concurrency=32,
        context_window=128000,
        openrouter_config={"provider": {"only": ["z-ai"]}}
    ),
    "qwen-3-coder-0722": Dict(
        api_model={"qwen_official": "qwen3-coder-plus-2025-07-22"},
        price=[0.54/1000, 2.16/1000],
        concurrency=32,
        context_window=256000,
    ),
    "qwen-3-coder-0923": Dict(
        api_model={"qwen_official": "qwen3-coder-plus-2025-09-23"},
        price=[0.54/1000, 2.16/1000],
        concurrency=32,
        context_window=256000,
    ),
    "qwen-3-coder": Dict(
        api_model={"qwen_official": "qwen3-coder-plus"},
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
    "minimax-m2": Dict(
        api_model={
            "openrouter": "minimax/minimax-m2:free"},
        price=[0.3/1000, 1.2/1000],
        concurrency=32,
        context_window=200000,
        openrouter_config={"provider": {"only": ["minimax"]}}
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