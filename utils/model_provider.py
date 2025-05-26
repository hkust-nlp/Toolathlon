from agents import ModelProvider, OpenAIChatCompletionsModel, Model, set_tracing_disabled
from openai import AsyncOpenAI
import httpx
from configs.global_configs import global_configs

class CustomModelProvider(ModelProvider):
    def get_model(self, model_name: str | None) -> Model:
        proxy = { 'http://': global_configs['proxy'], 'https://': global_configs['proxy']}
        client = AsyncOpenAI(
            api_key=global_configs['ds_key'],
            base_url=global_configs['base_url_ds']
        ) if model_name == 'deepseek-chat' or model_name == 'deepseek-reasoner' else AsyncOpenAI(
            api_key=global_configs['non_ds_key'],
            base_url=global_configs['base_url_non_ds'],
            http_client=httpx.AsyncClient(proxies=proxy)
        )
        return OpenAIChatCompletionsModel(model=model_name, openai_client=client)

class CustomModelProviderAiHubMix(ModelProvider):
    def get_model(self, model_name: str | None) -> Model:
        client = AsyncOpenAI(
            api_key=global_configs['non_ds_key'],
            base_url=global_configs['base_url_non_ds'],
        )
        return OpenAIChatCompletionsModel(model=model_name, openai_client=client)

model_provider_mapping = {
    "ds_internal": CustomModelProvider,
    "aihubmix": CustomModelProviderAiHubMix,
}

model_shortname2fullname_ds_internal = {
        'deekseek-v3': 'deepseek-chat',
        'deepseek-r1': 'deepseek-reasoner',

        'gpt-4o': 'azure-gpt-4o-2024-11-20',
        'gpt-4.1': 'azure-gpt-4.1-2025-04-14',
        'gpt-4.1-mini': 'azure-gpt-4.1-mini-2025-04-14',
        'gpt-4.1-nano': 'azure-gpt-4.1-nano-2025-04-14',
        'o4-mini': 'azure-o4-mini-2025-04-16',
        
        'claude-3.7-sonnet': 'cloudsway-claude-3-7-sonnet-20250219',
        'claude-4-sonnet': 'claude-sonnet-4-20250514',
        'claude-4-opus': 'claude-opus-4-20250514',

        'qwen3-235b-a22b': 'qwen3-235b-a22b',
        'qwen3-32b': 'qwen3-32b',
        'qwen3-30b-a3b': 'qwen3-30b-a3b',
        'qwq-plus': 'qwq-plus-2025-03-05',
        'qwq-32b': 'qwq-32b',

        'gemini-2.5-flash' : 'gemini-2.5-flash-preview-05-20',
        'gemini-2.5-pro': 'cloudsway-gemini-2.5-pro-preview-05-06',
    }

model_shortname2fullname_aihubmix = {
        'deekseek-v3': 'DeepSeek-V3',
        'deepseek-r1': 'DeepSeek-R1',

        'gpt-4o': 'gpt-4o-2024-11-20',
        'gpt-4.1': 'gpt-4.1',
        'gpt-4.1-mini': 'gpt-4.1-mini',
        'gpt-4.1-nano': 'gpt-4.1-nano',
        'o4-mini': 'o4-mini',
        
        'claude-3.7-sonnet': 'cloudsway-claude-3-7-sonnet-20250219',
        'claude-4-sonnet': 'claude-sonnet-4-20250514',
        'claude-4-opus': 'claude-opus-4-20250514',

        'qwen3-235b-a22b': 'Qwen/Qwen3-235B-A22B',
        'qwen3-32b': 'Qwen/Qwen3-32B',
        'qwen3-30b-a3b': 'Qwen/Qwen3-30B-A3B',
        # 'qwq-plus': 'qwq-plus-2025-03-05', # [REMINDER] no qwq plus on aihubmix
        'qwq-32b': 'Qwen/QwQ-32B',

        'gemini-2.5-flash' : 'gemini-2.5-flash-preview-05-20',
        'gemini-2.5-pro': 'gemini-2.5-pro-preview-05-06',
    }

model_shortname2fullname_mapping = {
    "ds_internal": model_shortname2fullname_ds_internal,
    "aihubmix": model_shortname2fullname_aihubmix
}

set_tracing_disabled(disabled=True)