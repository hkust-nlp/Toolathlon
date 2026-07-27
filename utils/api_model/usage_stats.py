from collections.abc import Mapping
from typing import Any


_MISSING = object()
_DETAIL_FIELD_NAMES = ("prompt_tokens_details", "input_tokens_details")
_CACHED_TOKEN_FIELD_NAMES = (
    "cached_tokens",
    "cached_input_tokens",
    "cached_content_token_count",
    "cachedContentTokenCount",
    "prompt_cache_hit_tokens",
)


def _get_field(value: Any, field_name: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(field_name, _MISSING)

    if hasattr(value, field_name):
        return getattr(value, field_name)

    model_extra = getattr(value, "model_extra", None)
    if isinstance(model_extra, Mapping):
        return model_extra.get(field_name, _MISSING)

    return _MISSING


def _as_token_count(value: Any) -> int | None:
    if value is _MISSING or value is None or isinstance(value, bool):
        return None

    try:
        token_count = int(value)
    except (TypeError, ValueError):
        return None

    return token_count if token_count >= 0 else None


def extract_cached_input_tokens(provider_usage: Any) -> int | None:
    """Return the provider-reported cached input count, or None if unavailable."""
    if provider_usage is None:
        return None

    for details_field in _DETAIL_FIELD_NAMES:
        details = _get_field(provider_usage, details_field)
        if details is _MISSING or details is None:
            continue
        for cached_field in _CACHED_TOKEN_FIELD_NAMES:
            cached_tokens = _as_token_count(_get_field(details, cached_field))
            if cached_tokens is not None:
                return cached_tokens

    for cached_field in _CACHED_TOKEN_FIELD_NAMES:
        cached_tokens = _as_token_count(_get_field(provider_usage, cached_field))
        if cached_tokens is not None:
            return cached_tokens

    return None


def split_cached_input_tokens(
    input_tokens: int,
    cached_input_tokens: int | None,
) -> tuple[int | None, int | None]:
    """Normalize cached input and derive the non-cached portion of the input."""
    if cached_input_tokens is None:
        return None, None

    normalized_input = max(0, int(input_tokens or 0))
    normalized_cached = max(0, int(cached_input_tokens))
    if normalized_cached > normalized_input:
        return None, None
    return normalized_cached, normalized_input - normalized_cached


def add_cached_token_details(usage: Any, provider_usage: Any) -> Any:
    """Attach optional cached/non-cached counts to an agents Usage instance."""
    cached_tokens, non_cached_tokens = split_cached_input_tokens(
        getattr(usage, "input_tokens", 0),
        extract_cached_input_tokens(provider_usage),
    )
    setattr(usage, "cached_input_tokens", cached_tokens)
    setattr(usage, "non_cached_input_tokens", non_cached_tokens)
    return usage
