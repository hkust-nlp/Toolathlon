import argparse
import asyncio
import datetime
import json
import os
import traceback
import uuid
from urllib.parse import urlparse
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple, cast

import aiohttp

from claude_agent_sdk import query
from claude_agent_sdk.types import (
    AssistantMessage,
    ClaudeAgentOptions,
    ContentBlock,
    EffortLevel,
    ResultMessage,
    StreamEvent,
    SystemMessage,
    TextBlock,
    ThinkingConfigAdaptive,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from scripts.decoupled.host_agent_loop import (
    build_host_task_config,
    expand_stop_tool_names,
    read_json_file,
)
from utils.general.helper import setup_proxy
from utils.roles.task_agent import TaskStatus
from utils.status_manager import TaskStatusManager
from utils.task_runner.runner import TaskRunner

MAX_CONSOLE_PREVIEW_CHARS = 1200
MAX_INLINE_ARGS_CHARS = 420
MAX_INLINE_OUTPUT_CHARS = 500
GATEWAY_CONNECTIVITY_ERROR_TEXT = "Unable to connect. Is the computer able to access the url?"
MAX_CONSECUTIVE_GATEWAY_CONNECTIVITY_ERRORS = 2

ANSI_RESET = "\033[0m"
ANSI_DIM = "\033[2m"
ANSI_CYAN = "\033[36m"
ANSI_GREEN = "\033[32m"
ANSI_YELLOW = "\033[33m"
ANSI_RED = "\033[31m"
ANSI_MAGENTA = "\033[35m"
ANSI_BOLD = "\033[1m"

CLAUDE_CODE_MODEL_ALIASES = {"default", "sonnet", "opus", "haiku", "opusplan"}
CLAUDE_EFFORT_LEVELS = {"low", "medium", "high", "xhigh", "max"}


def get_env_optional_int(name: str) -> Optional[int]:
    value = os.getenv(name)
    if value is None or value == "":
        return None
    return int(value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Host-side decoupled Claude SDK agent loop runner")
    parser.add_argument("--bundle_file", required=True)
    parser.add_argument("--gateway_url", required=True, help="SSE endpoint, e.g. http://127.0.0.1:10086/sse")
    parser.add_argument("--gateway_server_name", default="gw")
    parser.add_argument("--model", default=None, help="Claude model id override")
    parser.add_argument("--base_url", default=None, help="API base URL override (unified-style)")
    parser.add_argument("--api_key", default=None, help="API key override (unified-style)")
    parser.add_argument(
        "--tool_call_mode",
        default="parallel",
        choices=["parallel", "serial"],
        help="Tool-calling style. 'serial' adds a prompt guard to avoid sibling parallel calls.",
    )
    parser.add_argument(
        "--permission_mode",
        default="default",
        choices=["default", "acceptEdits", "dontAsk", "plan", "bypassPermissions"],
        help="Claude permission mode.",
    )
    parser.add_argument("--max_turns", type=int, default=get_env_optional_int("TOOLATHLON_MAX_TURNS_PER_TASK"))
    parser.add_argument("--with_proxy", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--allow_resume", action="store_true")
    return parser.parse_args()


def resolve_claude_sdk_env(
    source_env: Optional[Dict[str, str]] = None,
    base_url_override: Optional[str] = None,
    api_key_override: Optional[str] = None,
) -> Dict[str, str]:
    env = source_env if source_env is not None else os.environ
    resolved: Dict[str, str] = {}

    # Claude SDK backend intentionally does not read TOOLATHLON_OPENAI_*.
    base_url = base_url_override or env.get("ANTHROPIC_BASE_URL")
    if base_url:
        resolved["ANTHROPIC_BASE_URL"] = base_url

    # Preserve OpenRouter-style auth envs as-is:
    # ANTHROPIC_AUTH_TOKEN carries the real token, while ANTHROPIC_API_KEY may be an empty string.
    if api_key_override is not None:
        resolved["ANTHROPIC_API_KEY"] = api_key_override
    elif "ANTHROPIC_API_KEY" in env:
        resolved["ANTHROPIC_API_KEY"] = env.get("ANTHROPIC_API_KEY", "")

    auth_token = env.get("ANTHROPIC_AUTH_TOKEN")
    if auth_token:
        resolved["ANTHROPIC_AUTH_TOKEN"] = auth_token

    return resolved


def is_claude_code_builtin_model_name(model_name: str) -> bool:
    normalized = model_name.strip().lower()
    if not normalized:
        return False
    if normalized.endswith("[1m]"):
        normalized = normalized[:-4]
    return (
        normalized in CLAUDE_CODE_MODEL_ALIASES
        or normalized.startswith("claude-")
        or normalized.startswith("anthropic.")
        or normalized.startswith("us.anthropic.")
        or normalized.startswith("eu.anthropic.")
        or normalized.startswith("apac.anthropic.")
    )


def resolve_claude_sdk_model(
    requested_model: str,
) -> Tuple[str, Dict[str, str], Optional[str]]:
    normalized = requested_model.strip()

    if is_claude_code_builtin_model_name(normalized):
        return normalized, {}, None

    if "opus" in normalized.lower():
        return "opus", {"ANTHROPIC_DEFAULT_OPUS_MODEL": normalized}, normalized

    return "sonnet", {"ANTHROPIC_DEFAULT_SONNET_MODEL": normalized}, normalized


def resolve_claude_sdk_reasoning(
    reasoning: Any,
) -> Tuple[Optional[ThinkingConfigAdaptive], Optional[EffortLevel]]:
    if reasoning is None:
        return None, None
    if not isinstance(reasoning, dict):
        raise ValueError("agent.generation.reasoning must be an object")

    effort = reasoning.get("effort")
    if effort is None:
        return None, None
    if not isinstance(effort, str) or effort not in CLAUDE_EFFORT_LEVELS:
        supported = ", ".join(sorted(CLAUDE_EFFORT_LEVELS))
        raise ValueError(f"Unsupported Claude effort {effort!r}; expected one of: {supported}")

    return {
        "type": "adaptive",
        "display": "summarized",
    }, cast(EffortLevel, effort)


def has_claude_sdk_auth(env: Dict[str, str]) -> bool:
    if env.get("ANTHROPIC_AUTH_TOKEN"):
        return True
    return bool(env.get("ANTHROPIC_API_KEY"))


def format_session_model_label(cli_model_name: str, requested_model_name: Optional[str]) -> str:
    if requested_model_name and requested_model_name != cli_model_name:
        return f"{cli_model_name} (requested: {requested_model_name})"
    return cli_model_name


def maybe_print_model_mapping(cli_model_name: str, requested_model_name: Optional[str]) -> None:
    if requested_model_name and requested_model_name != cli_model_name:
        mapping_env_name = (
            "ANTHROPIC_DEFAULT_OPUS_MODEL"
            if cli_model_name == "opus"
            else "ANTHROPIC_DEFAULT_SONNET_MODEL"
        )
        print_log_line(
            "MODEL MAP",
            f"{requested_model_name} -> {cli_model_name} via {mapping_env_name}",
            ANSI_MAGENTA,
        )


def merge_env_vars(base_env: Dict[str, str], extra_env: Dict[str, str]) -> Dict[str, str]:
    merged = dict(base_env)
    merged.update(extra_env)
    return merged


def serialize_content_block(block: ContentBlock) -> Dict[str, Any]:
    if isinstance(block, TextBlock):
        return {"type": "text", "text": block.text}
    if isinstance(block, ThinkingBlock):
        return {
            "type": "thinking",
            "thinking": block.thinking,
            "signature": block.signature,
        }
    if isinstance(block, ToolUseBlock):
        return {
            "type": "tool_use",
            "id": block.id,
            "name": block.name,
            "input": block.input,
        }
    if isinstance(block, ToolResultBlock):
        return {
            "type": "tool_result",
            "tool_use_id": block.tool_use_id,
            "content": block.content,
            "is_error": block.is_error,
        }
    return {"type": block.__class__.__name__}


def content_blocks_to_text(blocks: List[ContentBlock]) -> str:
    text_parts: List[str] = []
    for block in blocks:
        if isinstance(block, TextBlock) and block.text:
            text_parts.append(block.text)
        elif isinstance(block, ToolResultBlock) and isinstance(block.content, str) and block.content:
            text_parts.append(block.content)
    return "\n".join(text_parts).strip()


def build_tool_call_record(block: ToolUseBlock) -> Dict[str, Any]:
    return {
        "id": block.id,
        "type": "function",
        "function": {
            "name": block.name,
            "arguments": json.dumps(block.input, ensure_ascii=False),
        },
    }


def parse_assistant_message(message: AssistantMessage) -> Tuple[Dict[str, Any], List[Dict[str, Any]], bool]:
    tool_calls = [build_tool_call_record(block) for block in message.content if isinstance(block, ToolUseBlock)]
    content_blocks = [serialize_content_block(block) for block in message.content]
    text = content_blocks_to_text(message.content)

    entry: Dict[str, Any] = {
        "role": "assistant",
        "content": text,
        "content_blocks": content_blocks,
        "tool_calls_count": len(tool_calls),
    }
    if tool_calls:
        entry["tool_calls"] = tool_calls
    return entry, tool_calls, len(tool_calls) == 0


def parse_user_message_content(content: str | List[ContentBlock]) -> Tuple[str, Optional[List[Dict[str, Any]]]]:
    if isinstance(content, str):
        return content, None

    serialized = [serialize_content_block(block) for block in content]
    text = content_blocks_to_text(content)
    return text, serialized


def is_gateway_connectivity_error_text(text: str) -> bool:
    return text.strip() == GATEWAY_CONNECTIVITY_ERROR_TEXT


def decide_task_status(
    result_message: Optional[ResultMessage],
    saw_stop_tool: bool,
    saw_no_tool_call_turn: bool,
) -> Tuple[TaskStatus, str]:
    if result_message is None:
        return TaskStatus.FAILED, "missing_result_message"

    if result_message.is_error:
        raw_result = (result_message.result or "").lower()
        if "max turn" in raw_result or "maximum turn" in raw_result:
            return TaskStatus.MAX_TURNS_REACHED, "max_turns_reached"
        return TaskStatus.FAILED, "sdk_result_error"

    # Decoupled hard requirement: no tool call is a termination condition.
    if saw_no_tool_call_turn:
        return TaskStatus.SUCCESS, "no_tool_call"
    if saw_stop_tool:
        return TaskStatus.SUCCESS, "stop_tool"

    return TaskStatus.FAILED, "termination_condition_not_met"


def build_agent_cost(result_message: Optional[ResultMessage]) -> Dict[str, Any]:
    if result_message is None:
        return {
            "total_cost": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_requests": 0,
        }

    usage = result_message.usage or {}
    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    return {
        "total_cost": round(float(result_message.total_cost_usd or 0.0), 6),
        "total_input_tokens": input_tokens,
        "total_output_tokens": output_tokens,
        "total_requests": int(result_message.num_turns or 0),
    }


def build_key_stats(
    result_message: Optional[ResultMessage],
    assistant_turns: int,
    tool_calls_count: int,
) -> Dict[str, Any]:
    usage = result_message.usage or {} if result_message is not None else {}
    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)

    return {
        "interaction_turns": 1,
        "tool_calls": tool_calls_count,
        "agent_llm_requests": assistant_turns,
        "total_tokens": input_tokens + output_tokens,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "sdk_num_turns": int(result_message.num_turns) if result_message is not None else 0,
    }


async def single_prompt_stream(prompt: str) -> AsyncIterator[Dict[str, Any]]:
    yield {
        "type": "user",
        "message": {
            "role": "user",
            "content": prompt,
        },
    }


def write_traj_log(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)


def build_allowed_mcp_tool_names(gateway_server_name: str, tool_names: List[str]) -> List[str]:
    names = [f"mcp__{gateway_server_name}__{name}" for name in tool_names if name]
    # keep order while removing duplicates
    return list(dict.fromkeys(names))


async def list_gateway_tools_via_sse(gateway_url: str, timeout_seconds: int = 20) -> List[str]:
    parsed = urlparse(gateway_url)
    if not parsed.scheme or not parsed.netloc:
        raise RuntimeError(f"Invalid gateway URL: {gateway_url}")
    origin = f"{parsed.scheme}://{parsed.netloc}"

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout_seconds)) as session:
        async with session.get(gateway_url) as sse_resp:
            if sse_resp.status != 200:
                raise RuntimeError(f"Gateway SSE connect failed: {sse_resp.status}")

            endpoint_path: Optional[str] = None
            event_name = "message"
            data_lines: List[str] = []

            async for raw_line in sse_resp.content:
                line = raw_line.decode("utf-8", errors="ignore").strip("\r\n")

                if line == "":
                    if data_lines:
                        payload = "\n".join(data_lines)
                        if event_name == "endpoint":
                            endpoint_path = payload.strip()
                            break
                    event_name = "message"
                    data_lines = []
                    continue

                if line.startswith("event:"):
                    event_name = line[len("event:") :].strip()
                elif line.startswith("data:"):
                    data_lines.append(line[len("data:") :].lstrip())

            if not endpoint_path:
                raise RuntimeError("Gateway SSE did not return endpoint path")

            if not endpoint_path.startswith("/"):
                endpoint_path = f"/{endpoint_path}"
            messages_url = f"{origin}{endpoint_path}"

            await session.post(
                messages_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {},
                },
            )
            await session.post(
                messages_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {},
                },
            )

            event_name = "message"
            data_lines = []
            async for raw_line in sse_resp.content:
                line = raw_line.decode("utf-8", errors="ignore").strip("\r\n")

                if line == "":
                    if data_lines:
                        payload = "\n".join(data_lines)
                        if event_name == "message":
                            parsed_payload = json.loads(payload)
                            if parsed_payload.get("id") == 2:
                                tools = parsed_payload.get("result", {}).get("tools", [])
                                return [str(tool.get("name")) for tool in tools if isinstance(tool, dict)]
                    event_name = "message"
                    data_lines = []
                    continue

                if line.startswith("event:"):
                    event_name = line[len("event:") :].strip()
                elif line.startswith("data:"):
                    data_lines.append(line[len("data:") :].lstrip())

    raise RuntimeError("Gateway tools/list response not received")


async def resolve_allowed_tools_for_gateway(
    gateway_url: str,
    gateway_server_name: str,
    debug: bool = False,
) -> List[str]:
    try:
        gateway_tools = await list_gateway_tools_via_sse(gateway_url)
    except Exception as e:
        if debug:
            print(f"[allowed_tools] list tools from gateway failed: {e}")
        return []

    allowed_tools = build_allowed_mcp_tool_names(
        gateway_server_name=gateway_server_name,
        tool_names=gateway_tools,
    )
    if debug:
        print(f"[allowed_tools] gateway tools: {gateway_tools}")
        print(f"[allowed_tools] sdk allowed tools: {allowed_tools}")
    return allowed_tools


def build_runtime_system_prompt(base_prompt: str, tool_call_mode: str) -> str:
    if tool_call_mode == "serial":
        guard = (
            "\n\nExecution constraints:\n"
            "1) At most one tool call per assistant turn.\n"
            "2) Wait for the tool result before issuing the next tool call.\n"
            "3) Do not dispatch parallel sibling tool calls in one response."
        )
        return f"{base_prompt}{guard}"
    return base_prompt


def preview_text(text: str, limit: int = MAX_CONSOLE_PREVIEW_CHARS) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]} ... [truncated {len(text) - limit} chars]"


def now_hms() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S")


def colorize(text: str, color: str) -> str:
    return f"{color}{text}{ANSI_RESET}"


def print_log_line(tag: str, message: str, color: str = ANSI_CYAN) -> None:
    ts = colorize(now_hms(), ANSI_DIM)
    tag_text = colorize(f"{tag:<10}", f"{ANSI_BOLD}{color}")
    print(f"{ts} {tag_text} {message}")


def short_id(value: Optional[str]) -> str:
    if not value:
        return "-"
    return value[-8:] if len(value) > 8 else value


def is_tool_error_text(text: str) -> bool:
    lowered = text.lower()
    hints = [
        "<tool_use_error>",
        "error:",
        "failed to",
        "permission to use ",
        "access denied",
    ]
    return any(hint in lowered for hint in hints)


def print_assistant_message_realtime(
    message: AssistantMessage,
    tool_name_by_call_id: Dict[str, str],
) -> None:
    for block in message.content:
        if isinstance(block, ThinkingBlock) and block.thinking.strip():
            thinking = preview_text(block.thinking.strip(), MAX_INLINE_OUTPUT_CHARS)
            print_log_line("THINK", thinking, ANSI_DIM)
        elif isinstance(block, TextBlock) and block.text.strip():
            text = preview_text(block.text.strip(), MAX_INLINE_OUTPUT_CHARS)
            print_log_line("ASSIST", text, ANSI_GREEN)
        elif isinstance(block, ToolUseBlock):
            tool_name_by_call_id[block.id] = block.name
            args = preview_text(
                json.dumps(block.input, ensure_ascii=False, separators=(",", ":")),
                MAX_INLINE_ARGS_CHARS,
            )
            print_log_line(
                "TOOL CALL",
                f"{block.name}#{short_id(block.id)} {args}",
                ANSI_CYAN,
            )
        elif isinstance(block, ToolResultBlock):
            content = block.content
            if isinstance(content, str):
                text = preview_text(content.strip(), MAX_INLINE_OUTPUT_CHARS)
            else:
                text = preview_text(
                    json.dumps(content, ensure_ascii=False, separators=(",", ":")),
                    MAX_INLINE_OUTPUT_CHARS,
                )
            tool_name = tool_name_by_call_id.get(block.tool_use_id, "unknown_tool")
            tag = "TOOL ERR" if bool(block.is_error) or is_tool_error_text(text) else "TOOL OUT"
            color = ANSI_RED if tag == "TOOL ERR" else ANSI_YELLOW
            print_log_line(
                tag,
                f"{tool_name}#{short_id(block.tool_use_id)} {text}",
                color,
            )


def print_user_message_realtime(
    content_text: str,
    parent_tool_use_id: Optional[str],
    tool_name_by_call_id: Dict[str, str],
) -> None:
    if not content_text.strip():
        return
    text = preview_text(content_text.strip(), MAX_INLINE_OUTPUT_CHARS)
    if parent_tool_use_id is None:
        print_log_line("USER", text, ANSI_MAGENTA)
        return

    tool_name = tool_name_by_call_id.get(parent_tool_use_id, "unknown_tool")
    tag = "TOOL ERR" if is_tool_error_text(text) else "TOOL OUT"
    color = ANSI_RED if tag == "TOOL ERR" else ANSI_YELLOW
    print_log_line(tag, f"{tool_name}#{short_id(parent_tool_use_id)} {text}", color)


def print_result_message_realtime(message: ResultMessage) -> None:
    color = ANSI_RED if message.is_error else ANSI_GREEN
    print_log_line(
        "RESULT",
        (
            f"subtype={message.subtype} "
            f"is_error={message.is_error} "
            f"turns={message.num_turns} "
            f"cost={message.total_cost_usd}"
        ),
        color,
    )
    if message.result:
        print_log_line("SUMMARY", preview_text(message.result, MAX_INLINE_OUTPUT_CHARS), color)


def print_session_header(
    model_name: str,
    gateway_url: str,
    permission_mode: str,
    tool_call_mode: str,
    allowed_tools: List[str],
    thinking_mode: Optional[str],
    thinking_display: Optional[str],
    effort: Optional[str],
) -> None:
    print("")
    print(colorize("=" * 88, ANSI_DIM))
    print_log_line(
        "SESSION",
        f"model={model_name} permission_mode={permission_mode} tool_call_mode={tool_call_mode}",
        ANSI_MAGENTA,
    )
    print_log_line(
        "REASONING",
        (
            f"thinking={thinking_mode or 'default'} "
            f"display={thinking_display or 'default'} "
            f"effort={effort or 'default'}"
        ),
        ANSI_MAGENTA,
    )
    print_log_line("GATEWAY", gateway_url, ANSI_MAGENTA)
    print_log_line("MCP TOOLS", f"pre-authorized={len(allowed_tools)}", ANSI_MAGENTA)
    print(colorize("=" * 88, ANSI_DIM))


async def run_host_loop(args: argparse.Namespace) -> int:
    bundle = read_json_file(args.bundle_file)
    setup_proxy(args.with_proxy)

    eval_config_dict = bundle["eval_config"]
    _, agent_config, _ = TaskRunner.load_configs(eval_config_dict)
    thinking_config, claude_effort = resolve_claude_sdk_reasoning(
        agent_config.generation.reasoning,
    )
    task_config = build_host_task_config(bundle, agent_short_name=agent_config.model.short_name)

    task_config.stop.tool_names = expand_stop_tool_names(
        stop_tools=task_config.stop.tool_names or ["local-claim_done"],
        gateway_server_name=args.gateway_server_name,
    )
    stop_tool_name_set = set(task_config.stop.tool_names)

    max_turns = args.max_turns
    if max_turns is None:
        max_turns = int(bundle.get("max_steps_under_single_turn_mode") or task_config.max_steps_under_single_turn_mode or 100)

    requested_model_name = args.model or agent_config.model.short_name
    sdk_env = resolve_claude_sdk_env(
        base_url_override=args.base_url,
        api_key_override=args.api_key,
    )
    model_name, model_env_updates, custom_model_name = resolve_claude_sdk_model(
        requested_model_name,
    )
    sdk_env = merge_env_vars(sdk_env, model_env_updates)
    if not has_claude_sdk_auth(sdk_env):
        raise RuntimeError("Missing ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN for Claude SDK host loop")

    status_manager = TaskStatusManager(task_config.task_root)
    status_manager.update_preprocess("done")
    status_manager.update_running("running")

    initial_run_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    completion_time = initial_run_time

    task_status = TaskStatus.FAILED
    termination_reason = "unknown"
    error_message: Optional[str] = None

    messages: List[Dict[str, Any]] = [{"role": "user", "content": task_config.task_str}]
    executed_tool_calls: List[Dict[str, Any]] = []
    assistant_turns = 0
    saw_stop_tool = False
    saw_no_tool_call_turn = False
    session_id: Optional[str] = None
    result_message: Optional[ResultMessage] = None
    tool_name_by_call_id: Dict[str, str] = {}
    consecutive_gateway_connectivity_errors = 0

    try:
        os.makedirs(task_config.agent_workspace, exist_ok=True)
        allowed_tools = await resolve_allowed_tools_for_gateway(
            gateway_url=args.gateway_url,
            gateway_server_name=args.gateway_server_name,
            debug=args.debug,
        )
        maybe_print_model_mapping(model_name, custom_model_name)
        print_session_header(
            model_name=format_session_model_label(model_name, custom_model_name),
            gateway_url=args.gateway_url,
            permission_mode=args.permission_mode,
            tool_call_mode=args.tool_call_mode,
            allowed_tools=allowed_tools,
            thinking_mode=thinking_config["type"] if thinking_config else None,
            thinking_display=thinking_config.get("display") if thinking_config else None,
            effort=claude_effort,
        )

        options = ClaudeAgentOptions(
            model=model_name,
            system_prompt=build_runtime_system_prompt(
                task_config.system_prompts.agent,
                args.tool_call_mode,
            ),
            # Disable Claude built-in tools (WebFetch/Bash/etc.) so decoupled runs
            # only use container gateway MCP tools.
            tools=[],
            mcp_servers={
                args.gateway_server_name: {
                    "type": "sse",
                    "url": args.gateway_url,
                }
            },
            allowed_tools=allowed_tools,
            permission_mode=args.permission_mode,
            max_turns=max_turns,
            cwd=task_config.agent_workspace,
            env=sdk_env,
            thinking=thinking_config,
            effort=claude_effort,
            extra_args={"strict-mcp-config": None},
        )

        async for message in query(prompt=single_prompt_stream(task_config.task_str), options=options):
            if isinstance(message, AssistantMessage):
                assistant_turns += 1
                print_assistant_message_realtime(message, tool_name_by_call_id)
                entry, recent_tool_calls, no_tool_call_turn = parse_assistant_message(message)
                messages.append(entry)
                executed_tool_calls.extend(recent_tool_calls)
                saw_no_tool_call_turn = saw_no_tool_call_turn or no_tool_call_turn
                if any(call["function"]["name"] in stop_tool_name_set for call in recent_tool_calls):
                    saw_stop_tool = True

            elif isinstance(message, UserMessage):
                content_text, content_blocks = parse_user_message_content(message.content)
                print_user_message_realtime(
                    content_text,
                    message.parent_tool_use_id,
                    tool_name_by_call_id,
                )
                entry: Dict[str, Any] = {"role": "user", "content": content_text}
                if content_blocks is not None:
                    entry["content_blocks"] = content_blocks
                if message.parent_tool_use_id is not None:
                    entry["parent_tool_use_id"] = message.parent_tool_use_id
                if message.tool_use_result is not None:
                    entry["tool_use_result"] = message.tool_use_result
                messages.append(entry)

                if is_gateway_connectivity_error_text(content_text):
                    consecutive_gateway_connectivity_errors += 1
                    if consecutive_gateway_connectivity_errors >= MAX_CONSECUTIVE_GATEWAY_CONNECTIVITY_ERRORS:
                        raise RuntimeError(
                            "Detected repeated gateway connectivity failures; aborting Claude SDK host loop"
                        )
                else:
                    consecutive_gateway_connectivity_errors = 0

            elif isinstance(message, SystemMessage):
                session_id = message.data.get("session_id") or session_id

            elif isinstance(message, ResultMessage):
                result_message = message
                session_id = message.session_id or session_id
                print_result_message_realtime(message)

            elif isinstance(message, StreamEvent):
                if args.debug and session_id is None:
                    session_id = message.session_id

        task_status, termination_reason = decide_task_status(
            result_message=result_message,
            saw_stop_tool=saw_stop_tool,
            saw_no_tool_call_turn=saw_no_tool_call_turn,
        )

        if task_status == TaskStatus.SUCCESS:
            status_manager.update_running("done")
        elif task_status == TaskStatus.MAX_TURNS_REACHED:
            status_manager.update_running("max_turn_exceeded")
        else:
            status_manager.update_running("fail")

    except Exception as e:
        if args.debug:
            traceback.print_exc()
        error_message = str(e)
        task_status = TaskStatus.FAILED
        termination_reason = "exception"
        status_manager.update_running("fail")
        print(f"Host Claude SDK loop failed: {e}")

    completion_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    result_payload: Dict[str, Any] = {
        "config": task_config.to_dict(),
        "request_id": str(uuid.uuid4()),
        "initial_run_time": initial_run_time,
        "completion_time": completion_time,
        "tool_calls": {
            "tools": executed_tool_calls,
            "tool_choice": agent_config.tool.tool_choice,
        },
        "status": task_status.value,
        "messages": messages,
        "key_stats": build_key_stats(
            result_message=result_message,
            assistant_turns=assistant_turns,
            tool_calls_count=len(executed_tool_calls),
        ),
        "agent_cost": build_agent_cost(result_message),
        "user_cost": {
            "total_cost": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_requests": 0,
        },
        "resumed": bool(args.allow_resume),
        "session_id": session_id,
        "history_file": None,
        "termination_reason": termination_reason,
        "sdk_model": model_name,
        "stop_tool_detected": saw_stop_tool,
        "no_tool_call_detected": saw_no_tool_call_turn,
    }

    if result_message is not None:
        result_payload["sdk_result"] = {
            "subtype": result_message.subtype,
            "is_error": result_message.is_error,
            "num_turns": result_message.num_turns,
            "result": result_message.result,
            "usage": result_message.usage,
            "total_cost_usd": result_message.total_cost_usd,
        }

    if error_message is not None:
        result_payload["failure"] = error_message

    write_traj_log(task_config.log_file, result_payload)

    print(f"Host Claude SDK loop completed with status: {task_status.value} ({termination_reason})")
    return 0 if task_status == TaskStatus.SUCCESS else 1


def main() -> None:
    args = parse_args()
    raise SystemExit(asyncio.run(run_host_loop(args)))


if __name__ == "__main__":
    main()
