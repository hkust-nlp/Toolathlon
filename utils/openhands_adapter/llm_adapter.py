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

    # For custom OpenAI-compatible endpoints, use "openai/" prefix
    # This tells LiteLLM to route to OpenAI-compatible API format
    # Example: openai/mistral, openai/claude-sonnet-4-20250514
    final_model_name = f"openai/{model_name}"

    llm_config: Dict[str, Any] = {
        "model": final_model_name,
        "temperature": temperature,
        "max_output_tokens": max_tokens,  # OpenHands uses max_output_tokens
        "top_p": top_p,
    }

    if debug:
        print(f"[LLM Adapter] Creating LLM with model: {final_model_name}")
        print(f"  Original model name: {model_name}")

    # Try to extract API key and base URL from model_provider
    # model_provider.get_model() returns a Model instance with openai_client
    try:
        # Get a dummy model to access the client configuration
        dummy_model = model_provider.get_model(model_name, debug=debug)

        if debug:
            print(f"[LLM Adapter] dummy_model type: {type(dummy_model)}")
            if hasattr(dummy_model, 'model'):
                print(f"[LLM Adapter] dummy_model.model: {dummy_model.model}")

        # The OpenAI client is stored as _client (private attribute)
        if hasattr(dummy_model, '_client'):
            client = dummy_model._client

            if debug:
                print(f"[LLM Adapter] client type: {type(client)}")
                print(f"[LLM Adapter] client has api_key attr: {hasattr(client, 'api_key')}")
                print(f"[LLM Adapter] client has base_url attr: {hasattr(client, 'base_url')}")

            # Extract API key
            if hasattr(client, 'api_key') and client.api_key:
                if debug:
                    print(f"[LLM Adapter] Raw api_key type: {type(client.api_key)}")
                    print(f"[LLM Adapter] Raw api_key value: {str(client.api_key)[:20]}...")

                # Convert to SecretStr
                llm_config["api_key"] = SecretStr(str(client.api_key))

                if debug:
                    print(f"[LLM Adapter] Converted api_key to SecretStr")
            else:
                if debug:
                    print(f"[LLM Adapter] WARNING: No api_key found in client!")

            # Extract base URL (api_base for custom endpoints)
            if hasattr(client, 'base_url') and client.base_url:
                base_url_str = str(client.base_url)
                if debug:
                    print(f"[LLM Adapter] Raw base_url: {base_url_str}")

                # Remove trailing slash for consistency
                if base_url_str.endswith('/'):
                    base_url_str = base_url_str[:-1]
                llm_config["base_url"] = base_url_str

            if debug:
                print(f"[LLM Adapter] Final llm_config:")
                print(f"  - Model: {llm_config['model']}")
                print(f"  - Base URL: {llm_config.get('base_url', 'NOT SET')}")
                print(f"  - API Key present: {('api_key' in llm_config)}")
                if 'api_key' in llm_config:
                    print(f"  - API Key type: {type(llm_config['api_key'])}")
                    print(f"  - API Key value (first 20 chars): {llm_config['api_key'].get_secret_value()[:20]}...")
        else:
            if debug:
                print(f"[LLM Adapter] WARNING: dummy_model has no _client attribute!")

    except Exception as e:
        import traceback
        if debug:
            print(f"[LLM Adapter] ERROR extracting client config: {e}")
            print(f"[LLM Adapter] Traceback: {traceback.format_exc()}")
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
