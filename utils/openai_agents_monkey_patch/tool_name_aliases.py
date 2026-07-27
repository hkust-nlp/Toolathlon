"""Model-facing tool-name aliases for the OpenAI Agents harness.

Backend MCP and local tool names are intentionally left unchanged.  The model
only sees aliases in which hyphens are replaced with underscores, while the
original callback (or MCP tool object) remains responsible for dispatch.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import replace
from typing import Any, Iterable, Mapping

from agents.tool import FunctionTool


_BUILTIN_TOOL_CHOICES = {"auto", "none", "required"}


def to_model_tool_name(name: str) -> str:
    """Return the canonical tool name exposed to the model."""
    return name.replace("-", "_")


def to_model_mcp_tool_name(server_name: str, tool_name: str) -> str:
    """Build a model-facing MCP alias without changing either backend name."""
    return to_model_tool_name(f"{server_name}-{tool_name}")


def to_model_tool_choice(tool_choice: str | None) -> str | None:
    """Normalize a named tool choice while preserving built-in choices."""
    if tool_choice is None or tool_choice in _BUILTIN_TOOL_CHOICES:
        return tool_choice
    return to_model_tool_name(tool_choice)


def build_tool_name_aliases(tools: Iterable[Any]) -> dict[str, str]:
    """Return raw-name to model-name aliases for FunctionTools."""
    return {
        tool.name: to_model_tool_name(tool.name)
        for tool in tools
        if isinstance(tool, FunctionTool)
    }


def alias_function_tools(
    tools: Iterable[Any],
) -> tuple[list[Any], dict[str, str]]:
    """Clone FunctionTools with model-facing names and preserve callbacks."""
    tools = list(tools)
    aliased_tools: list[Any] = []
    aliases = build_tool_name_aliases(tools)

    for tool in tools:
        if not isinstance(tool, FunctionTool):
            aliased_tools.append(tool)
            continue

        model_name = aliases[tool.name]
        aliased_tools.append(
            tool if model_name == tool.name else replace(tool, name=model_name)
        )

    return aliased_tools, aliases


def rewrite_tool_name_references(
    text: Any,
    aliases: Mapping[str, str],
) -> Any:
    """Rewrite exact tool-name strings in an OpenAI-harness prompt."""
    if not isinstance(text, str):
        return text

    rewritten = text
    for raw_name, model_name in sorted(
        aliases.items(), key=lambda item: len(item[0]), reverse=True
    ):
        pattern = rf"(?<![A-Za-z0-9_-]){re.escape(raw_name)}(?![A-Za-z0-9_-])"
        rewritten = re.sub(pattern, lambda _: model_name, rewritten)
    return rewritten


def validate_model_tool_names(tools: Iterable[Any]) -> None:
    """Fail fast when model-visible FunctionTool names are invalid or collide."""
    names = [tool.name for tool in tools if isinstance(tool, FunctionTool)]
    hyphenated = sorted({name for name in names if "-" in name})
    duplicates = sorted(
        name for name, count in Counter(names).items() if count > 1
    )

    errors = []
    if hyphenated:
        errors.append(f"names still containing '-': {hyphenated}")
    if duplicates:
        errors.append(f"duplicate model-facing names: {duplicates}")
    if errors:
        raise ValueError("Invalid model-facing tool names: " + "; ".join(errors))
