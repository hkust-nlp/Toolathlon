from __future__ import annotations

import asyncio
from typing import List, Dict, Any

from functools import partial
import threading

from utils.model_provider import API_MAPPINGS

from utils.utils import *

async def to_thread(func, /, *args, **kwargs):
    loop = asyncio.get_event_loop()
    func_call = partial(func, *args, **kwargs)
    return await loop.run_in_executor(None, func_call)

class SmartAsyncSemaphore:
    """
    智能异步信号量：
    - 在事件循环创建线程中调用：使用 asyncio.Semaphore（非阻塞，推荐）。
    - 在其他线程中调用：使用 threading.Semaphore + asyncio.to_thread（可跨线程）。 
    本版本在每种模式下只打印一次日志。
    """

    def __init__(self, value: int):
        self._value = value

        self._loop = asyncio.get_event_loop()
        self._loop_thread = threading.current_thread()

        self._asyncio_semaphore = asyncio.Semaphore(value)
        self._threading_semaphore = threading.Semaphore(value)

        # 打印控制标志：默认未打印
        self._asyncio_warned = False
        self._threading_warned = False

        # 用锁保护标志位设置（线程安全）
        self._print_lock = threading.Lock()

    def _use_threadsafe(self) -> bool:
        return threading.current_thread() != self._loop_thread

    async def __aenter__(self):
        if self._use_threadsafe():
            with self._print_lock:
                if not self._threading_warned:
                    print(f"[SmartAsyncSemaphore] ⚠️ 跨线程访问：将使用 threading.Semaphore (来自线程：{threading.current_thread().name})")
                    self._threading_warned = True
            # await asyncio.to_thread(self._threading_semaphore.acquire)
            await to_thread(self._threading_semaphore.acquire) # py3.8 OK
            return self
        else:
            with self._print_lock:
                if not self._asyncio_warned:
                    print(f"[SmartAsyncSemaphore] ✅ 当前线程为事件循环创建线程：使用 asyncio.Semaphore (线程：{threading.current_thread().name})")
                    self._asyncio_warned = True
            return await self._asyncio_semaphore.__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._use_threadsafe():
            self._threading_semaphore.release()
        else:
            return await self._asyncio_semaphore.__aexit__(exc_type, exc_val, exc_tb)

class APILLMProvider:
    def __init__(self, model: str, **kwargs):
        super().__init__()
        assert model in API_MAPPINGS, f"Invalid model: {model}"
        self.api_meta = API_MAPPINGS[model]
        self.api_key = kwargs.get("api_key", None)
        
        # a thread safe version compatibale to api_eval
        self.semaphore = SmartAsyncSemaphore(kwargs.get("max_concurrent_limit", self.api_meta.concurrency))

        if kwargs.get("log_path", None):
            self.logger = setup_logger(f'llm_api', kwargs.get("log_path"))
        else:
            self.logger = None

        self.max_retries = kwargs.get("max_retries", 3)

    async def complete(self, request: LLMChatCompletion) -> LLMChatResponse:
        messages = [x.dict() for x in request.messages]
        kwargs = {}

        if request.max_tokens:
            kwargs['max_tokens'] = request.max_tokens
        if request.temperature:
            kwargs['temperature'] = request.temperature
        if request.top_p:
            kwargs['top_p'] = request.top_p
        if request.tools:
            kwargs['tools'] = [x.dict() for x in request.tools]
        
        if self.logger:
            self.logger.info(f">>> {self.api_meta.api_model} request ({request.id}): {request.dict()}")

        async with self.semaphore:
            for try_idx in range(self.max_retries):
                try:
                    resp = await self._complete(
                        messages, 
                        **kwargs
                    )
                    resp.id = request.id

                    if self.logger:
                        self.logger.info(
                            f"<<< {self.api_meta.api_model} response ({request.id}): {resp.dict()}"
                        )

                    return resp

                except Exception as e:
                    if self.logger:
                        import traceback
                        self.logger.error(
                            f"Error during API call attempt {try_idx+1}: {e}\n{traceback.format_exc()}"
                        )

                    if "invalid_request_error" in str(e):
                        break  # 不再重试

                    await asyncio.sleep(2 * (try_idx + 1))  # backoff

            # finally:
            #     await http_client.aclose()

            # 👇 如果执行到这里，说明重试失败或异常都无法成功，构造 fallback 响应 👇
            a_msg = ChatMessage.assistant(content="")
            a_msg.update_meta(
                {"error": f"retry failed after {self.max_retries} retries"}
            )
            return LLMChatResponse(
                id=request.id,
                message=a_msg,
                finish_reason="error",
                usage=LLMUsage(),
            )
        
    async def _complete(self, messages: List[Dict[str, Any]], 
                        # http_client: httpx.AsyncClient, 
                        **kwargs) -> LLMChatResponse:
        from openai import OpenAI, AsyncOpenAI
        client = AsyncOpenAI(
            api_key="sk-e976a05cbd9b45129bd90a71e26ee34d",
            base_url="https://api-internal.deepseek.com",
        )
            
        else:
            raise NotImplementedError
        
        try:
            resp = await client.chat.completions.create(
                    model=self.api_meta.api_model,
                    messages=messages,
                    stream=False,
                    **kwargs
                )
        finally:
            await client.close()
            # if isinstance(client, AsyncOpenAI):
            #     await client.close()
            # elif isinstance(client, AsyncAzureOpenAI):
            #     await client.close()
        

        
        resp = resp.model_dump(exclude_unset=True)
        output_msg = resp['choices'][0]['message']
        output_msg = ChatMessage.parse_obj(output_msg)
        # print(resp)
        finish_reason = resp["choices"][0]["finish_reason"]
        usage = resp['usage']

        if 'prompt_tokens' in usage and 'completion_tokens' in usage:
            usage['cost'] = self.api_meta.price[0] * usage['prompt_tokens'] / 1000 + self.api_meta.price[1] * usage['completion_tokens'] / 1000
            usage = LLMUsage(
                input_tokens=usage['prompt_tokens'],
                output_tokens=usage['completion_tokens'],
                cost=usage['cost']
            )
        else:
            usage = None

        return LLMChatResponse(
            id="",
            message=output_msg,
            finish_reason=finish_reason,
            usage=usage,
        )

