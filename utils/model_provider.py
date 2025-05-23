import asyncio
import os
import shutil

from agents import Agent, Runner, gen_trace_id, trace
from agents.mcp import MCPServer, MCPServerStdio

from agents import ModelProvider, OpenAIChatCompletionsModel, Model, set_tracing_disabled, RunConfig
from openai import AsyncOpenAI
import httpx

from configs.global_configs import global_configs

### IMPORTED
class CustomModelProvider(ModelProvider):
    def get_model(self, model_name: str | None) -> Model:
        client = AsyncOpenAI(
            api_key=global_configs['ds_key'],
            base_url=global_configs['base_url_ds']
        ) if model_name == 'deepseek-chat' or model_name == 'deepseek-reasoner' else AsyncOpenAI(
            api_key=global_configs['non_ds_key'],
            base_url=global_configs['base_url_non_ds'],
            http_client=httpx.AsyncClient(proxies=proxy)
        )
        return OpenAIChatCompletionsModel(model=model_name, openai_client=client)

model_provider = CustomModelProvider()

proxy = {
     'http://': global_configs['proxy'],
     'https://': global_configs['proxy']
}

models = {
        'V3': 'deepseek-chat',
        'R1': 'deepseek-reasoner',
        'gpt-4o': 'azure-gpt-4o-2024-11-20',
        'gpt-4.1': 'azure-gpt-4.1-2025-04-14',
        'gpt-4.1-mini': 'azure-gpt-4.1-mini-2025-04-14',
        'gpt-4.1-nano': 'azure-gpt-4.1-nano-2025-04-14',
        'claude-3.7': 'cloudsway-claude-3-7-sonnet-20250219',
        'qwen-max': 'qwen-max-2025-01-25',
        'qwen-72b': 'qwen2.5-72b-instruct',
        'qwen-32b': 'qwen2.5-32b-instruct',
        'qwen-7b': 'qwen2.5-7b-instruct',
    }


set_tracing_disabled(disabled=True)
### IMPORTED