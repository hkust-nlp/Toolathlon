"""
OpenHands LLM Adapter

This module provides adapters to convert mcpbench_dev's model_provider
to OpenHands SDK's LLM format.

The adapter bridges:
- mcpbench_dev: Uses OpenAI SDK with custom ModelProvider
- OpenHands SDK: Uses litellm-based LLM class

Usage:
    from utils.openhands_adapter.llm_adapter import create_openhands_llm

    llm = create_openhands_llm(
        model_provider=agent_model_provider,
        model_name="gpt-4",
        temperature=0.7,
        max_tokens=4096,
    )
"""

from typing import Optional, Dict, Any
from openhands.sdk.llm import LLM
from pydantic import SecretStr


def create_openhands_llm(
    model_provider,
    model_name: str,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    top_p: float = 1.0,
    debug: bool = False,
) -> LLM:
    """
    Create an OpenHands LLM from mcpbench_dev's model_provider

    Args:
        model_provider: mcpbench_dev's ModelProvider instance
        model_name: Model name (e.g., "gpt-4", "claude-sonnet-4")
        temperature: Temperature for generation
        max_tokens: Maximum tokens for generation (will be mapped to max_output_tokens)
        top_p: Top-p sampling parameter
        debug: Enable debug mode

    Returns:
        OpenHands LLM instance

    Example:
        >>> from utils.api_model.model_provider import ModelProviderClass
        >>> model_provider = ModelProviderClass(...)
        >>> llm = create_openhands_llm(
        ...     model_provider=model_provider,
        ...     model_name="gpt-4",
        ...     temperature=0.7,
        ... )
    """

    # Extract configuration from model_provider
    # mcpbench_dev's model_provider wraps an AsyncOpenAI client
    # Note: OpenHands LLM uses max_output_tokens instead of max_tokens
    llm_config: Dict[str, Any] = {
        "model": model_name,
        "temperature": temperature,
        "max_output_tokens": max_tokens,  # OpenHands uses max_output_tokens
        "top_p": top_p,
    }

    # Try to extract API key and base URL from model_provider
    # model_provider.get_model() returns a Model instance with openai_client
    try:
        # Get a dummy model to access the client configuration
        dummy_model = model_provider.get_model(model_name, debug=debug)

        if hasattr(dummy_model, 'openai_client'):
            client = dummy_model.openai_client

            # Extract API key
            if hasattr(client, 'api_key') and client.api_key:
                llm_config["api_key"] = SecretStr(client.api_key)

            # Extract base URL
            if hasattr(client, 'base_url') and client.base_url:
                base_url_str = str(client.base_url)
                # Remove trailing slash for consistency
                if base_url_str.endswith('/'):
                    base_url_str = base_url_str[:-1]
                llm_config["base_url"] = base_url_str

            if debug:
                print(f"[LLM Adapter] Extracted config from model_provider:")
                print(f"  - Model: {model_name}")
                print(f"  - Base URL: {llm_config.get('base_url', 'default')}")
                print(f"  - API Key: {'***' if llm_config.get('api_key') else 'none'}")

    except Exception as e:
        if debug:
            print(f"[LLM Adapter] Warning: Could not extract client config: {e}")
            print(f"[LLM Adapter] Using default litellm configuration")

    # Create OpenHands LLM
    llm = LLM(**llm_config)

    if debug:
        print(f"[LLM Adapter] Created OpenHands LLM: {llm.model}")

    return llm


def create_openhands_llm_from_config(
    agent_config,
    agent_model_provider,
    debug: bool = False,
) -> LLM:
    """
    Create OpenHands LLM from TaskAgent configuration

    This is a convenience wrapper that extracts parameters from
    AgentConfig and creates an OpenHands LLM.

    Args:
        agent_config: AgentConfig instance
        agent_model_provider: ModelProvider instance
        debug: Enable debug mode

    Returns:
        OpenHands LLM instance

    Example:
        >>> llm = create_openhands_llm_from_config(
        ...     agent_config=self.agent_config,
        ...     agent_model_provider=self.agent_model_provider,
        ...     debug=self.debug,
        ... )
    """
    return create_openhands_llm(
        model_provider=agent_model_provider,
        model_name=agent_config.model.real_name,
        temperature=agent_config.generation.temperature,
        max_tokens=agent_config.generation.max_tokens,
        top_p=agent_config.generation.top_p,
        debug=debug,
    )
