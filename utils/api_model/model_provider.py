from agents import ModelProvider, OpenAIChatCompletionsModel, Model, set_tracing_disabled
from openai import AsyncOpenAI
import httpx
from configs.global_configs import global_configs
from addict import Dict

class CustomModelProvider(ModelProvider):
    def get_model(self, model_name: str | None) -> Model:
        client = AsyncOpenAI(
            api_key=global_configs.ds_key,
            base_url=global_configs.base_url_ds
        ) if model_name == 'deepseek-chat' or model_name == 'deepseek-reasoner' else AsyncOpenAI(
            api_key=global_configs.non_ds_key,
            base_url=global_configs.base_url_non_ds,
        )
        return OpenAIChatCompletionsModel(model=model_name, openai_client=client)

class CustomModelProviderAiHubMix(ModelProvider):
    def get_model(self, model_name: str | None) -> Model:
        client = AsyncOpenAI(
            api_key=global_configs.non_ds_key,
            base_url=global_configs.base_url_non_ds,
        )
        return OpenAIChatCompletionsModel(model=model_name, openai_client=client)

model_provider_mapping = {
    "ds_internal": CustomModelProvider,
    "aihubmix": CustomModelProviderAiHubMix,
}

API_MAPPINGS = {
    'deepseek-v3-0324': Dict(
        api_model={"ds_internal": "deepseek-chat",
                   "aihubmix": "DeepSeek-V3"},
        price=[0.272/1000, 1.088/1000],
        concurrency=32
    ),
    'deepseek-r1-0528': Dict(
        api_model={"ds_internal": "deepseek-reasoner",
                   "aihubmix": "DeepSeek-R1"},
        price=[0.546/1000, 2.184/1000],
        concurrency=32
    ),
    'gpt-4o': Dict(
        api_model={"ds_internal": "azure-gpt-4o-2024-11-20",
                   "aihubmix": "gpt-4o-2024-11-20"},
        price=[0.005, 0.015],
        concurrency=32
    ),
    'gpt-4o-mini': Dict(
        api_model={"ds_internal": "azure-gpt-4o-mini-2024-07-18",
                   "aihubmix": "gpt-4o-mini"},
        price=[0.00015, 0.0006],
        concurrency=32
    ),
    'gpt-4.1-0414': Dict(
        api_model={"ds_internal": "azure-gpt-4.1-2025-04-14",
                   "aihubmix": "gpt-4.1"},
        price=[0.002, 0.008],
        concurrency=32
    ),
    'gpt-4.1-mini-0414': Dict(
        api_model={"ds_internal": "azure-gpt-4.1-mini-2025-04-14",
                   "aihubmix": "gpt-4.1-mini"},
        price=[0.0004, 0.0016],
        concurrency=32
    ),
    'gpt-4.1-nano-0414': Dict(
        api_model={"ds_internal": "azure-gpt-4.1-nano-2025-04-14",
                   "aihubmix": "gpt-4.1-nano"},
        price=[0.0001, 0.0004],
        concurrency=32
    ),
    'o4-mini': Dict(
        api_model={"ds_internal": "azure-o4-mini-2025-04-16",
                   "aihubmix": "o4-mini"},
        price=[0.0011, 0.0044],
        concurrency=32
    ),
    'o3': Dict(
        api_model={"ds_internal": "?????", # no o3 in ds internal
                   "aihubmix": "o3"},
        price=[0.010, 0.040],
        concurrency=32
    ),
    'o3-pro': Dict(
        api_model={"ds_internal": "?????", # no o3-pro in ds internal
                   "aihubmix": "o3-pro"}, # no o3-pro in aihubmix
        price=[0.022, 0.088],
        concurrency=32
    ),
    'claude-3.7-sonnet': Dict(
        api_model={"ds_internal": "cloudsway-claude-3-7-sonnet-20250219",
                   "aihubmix": "cloudsway-claude-3-7-sonnet-20250219"},
        price=[0.003, 0.015],
        concurrency=32
    ),
    'claude-4-sonnet-0514': Dict(
        api_model={"ds_internal": "oai-api-claude-sonnet-4-20250514",
                   "aihubmix": "claude-sonnet-4-20250514"},
        price=[0.003, 0.015],
        concurrency=32
    ),
    'claude-4-opus-0514': Dict(
        api_model={"ds_internal": "oai-api-claude-opus-4-20250514",
                   "aihubmix": "claude-opus-4-20250514"},
        price=[0.015, 0.075],
        concurrency=32
    ),
    'qwen3-235b-a22b': Dict(
        api_model={"ds_internal": "qwen3-235b-a22b",
                   "aihubmix": "Qwen/Qwen3-235B-A22B"},
        price=[0.004, 0.04],
        concurrency=32
    ),
    'qwen3-32b': Dict(
        api_model={"ds_internal": "qwen3-32b",
                   "aihubmix": "Qwen/Qwen3-32B"},
        price=[0.002, 0.02],
        concurrency=32
    ),
    'qwen3-30b-a3b': Dict(
        api_model={"ds_internal": "qwen3-30b-a3b",
                   "aihubmix": "Qwen/Qwen3-30B-A3B"},
        price=[0.0015, 0.015],
        concurrency=32
    ),
    'qwq-plus': Dict(
        api_model={"ds_internal": "qwq-plus-2025-03-05",
                   "aihubmix": None},  # No qwq plus on aihubmix
        price=[0, 0],
        concurrency=32
    ),
    'qwq-32b': Dict(
        api_model={"ds_internal": "qwq-32b",
                   "aihubmix": "Qwen/QwQ-32B"},
        price=[0.14/1000, 0.56/1000],
        concurrency=32
    ),
    'gemini-2.5-flash-0520': Dict(
        api_model={"ds_internal": "gemini-2.5-flash-preview-05-20",
                   "aihubmix": "gemini-2.5-flash-preview-05-20"},
        price=[0.00015, 0.0035],
        concurrency=32
    ),
    'gemini-2.5-pro-0506': Dict(
        api_model={"ds_internal": "cloudsway-gemini-2.5-pro-preview-05-06",
                   "aihubmix": "gemini-2.5-pro-preview-05-06"},
        price=[0.00125, 0.010],
        concurrency=32
    ),
    'gemini-2.5-pro-0605': Dict(
        api_model={"ds_internal": "cloudsway-gemini-2.5-pro-preview-06-05",
                   "aihubmix": "gemini-2.5-pro-preview-06-05"},
        price=[0.00125, 0.010],
        concurrency=32
    ),
    'grok-3-beta': Dict(
        api_model={"ds_internal": "grok-3-beta",
                   "aihubmix": "grok-3-beta"},
        price=[0.003, 0.015],
        concurrency=32
    ),
    'grok-3-mini-beta': Dict(
        api_model={"ds_internal": "grok-3-mini-beta",
                   "aihubmix": "grok-3-mini-beta"},
        price=[0.0003, 0.0005],
        concurrency=32
    )
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