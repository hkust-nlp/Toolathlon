import argparse
import asyncio
import datetime
import json
import os
import traceback
from functools import partial
from pathlib import Path
from typing import Any, Dict, List

import yaml
from agents.items import MessageOutputItem, ToolCallItem, ToolCallOutputItem

from utils.data_structures.task_config import SystemPrompts, TaskConfig
from utils.general.helper import (
    build_agent_model_provider,
    build_user_client,
    setup_proxy,
)
from utils.roles.task_agent import TaskAgent, TaskStatus
from utils.task_runner.runner import TaskRunner
from utils.task_runner.termination_checkers import default_termination_checker

from utils.openai_agents_monkey_patch.custom_run_impl import *
from utils.openai_agents_monkey_patch.custom_mcp_util import *


IGNORED_LOCAL_TOOLS = {"manage_context", "history", "handle_overlong_tool_outputs", "claim_done"}
ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_DIM = "\033[2m"
ANSI_RED = "\033[31m"
ANSI_GREEN = "\033[32m"
ANSI_YELLOW = "\033[33m"
ANSI_BLUE = "\033[34m"
ANSI_MAGENTA = "\033[35m"
ANSI_CYAN = "\033[36m"

MAX_INLINE_ARGS_CHARS = 240
MAX_INLINE_OUTPUT_CHARS = 600


def read_json_file(path: str) -> dict:
    import json

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def filter_local_tools(tools: List[str]) -> List[str]:
    return [tool for tool in tools if tool not in IGNORED_LOCAL_TOOLS]


def preview_text(text: str, limit: int = MAX_INLINE_OUTPUT_CHARS) -> str:
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


def short_id(value: str | None) -> str:
    if not value:
        return "-"
    return value[-8:] if len(value) > 8 else value


def stringify_console_payload(payload: Any) -> str:
    if payload is None:
        return ""
    if isinstance(payload, str):
        return payload
    if hasattr(payload, "model_dump"):
        return json.dumps(payload.model_dump(), ensure_ascii=False, separators=(",", ":"))
    try:
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    except TypeError:
        return str(payload)


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


def extract_assistant_console_entries(raw_message: Any) -> List[tuple[str, str, str]]:
    entries: List[tuple[str, str, str]] = []
    for content in getattr(raw_message, "content", []) or []:
        content_type = getattr(content, "type", None)
        if content_type == "output_text":
            text = getattr(content, "text", "")
            if text and text.strip():
                entries.append(("ASSIST", preview_text(text.strip()), ANSI_GREEN))
        elif content_type == "refusal":
            text = getattr(content, "refusal", "")
            if text and text.strip():
                entries.append(("ASSIST", preview_text(text.strip()), ANSI_RED))
        elif content_type == "reasoning_content":
            pure_thinking = getattr(content, "pure_thinking_str", None)
            if pure_thinking and pure_thinking.strip():
                entries.append(("THINK", preview_text(pure_thinking.strip()), ANSI_DIM))
            else:
                extra_contents = getattr(content, "extra_contents_in_tool_calls", None)
                if extra_contents:
                    try:
                        parsed = json.loads(extra_contents)
                    except Exception:
                        parsed = None
                    if isinstance(parsed, list) and any(parsed):
                        entries.append(("THINK", "(implicit reasoning in tool calls)", ANSI_DIM))
    return entries


def render_run_items_to_console_events(new_items: List[Any]) -> List[tuple[str, str, str]]:
    events: List[tuple[str, str, str]] = []
    tool_name_by_call_id: Dict[str, str] = {}

    for item in new_items:
        if isinstance(item, MessageOutputItem):
            events.extend(extract_assistant_console_entries(item.raw_item))
            continue

        if isinstance(item, ToolCallItem):
            raw_item = item.raw_item
            tool_name = getattr(raw_item, "name", "unknown_tool")
            call_id = getattr(raw_item, "call_id", None) or getattr(raw_item, "id", None)
            if call_id:
                tool_name_by_call_id[call_id] = tool_name
            arguments = stringify_console_payload(getattr(raw_item, "arguments", ""))
            if arguments:
                arguments = preview_text(arguments, MAX_INLINE_ARGS_CHARS)
                message = f"{tool_name}#{short_id(call_id)} {arguments}"
            else:
                message = f"{tool_name}#{short_id(call_id)}"
            events.append(("TOOL CALL", message, ANSI_CYAN))
            continue

        if isinstance(item, ToolCallOutputItem):
            input_item = item.to_input_item()
            call_id = input_item.get("call_id") if isinstance(input_item, dict) else None
            tool_name = tool_name_by_call_id.get(call_id or "", "unknown_tool")
            output_text = preview_text(stringify_console_payload(item.output).strip())
            tag = "TOOL ERR" if is_tool_error_text(output_text) else "TOOL OUT"
            color = ANSI_RED if tag == "TOOL ERR" else ANSI_YELLOW
            events.append((tag, f"{tool_name}#{short_id(call_id)} {output_text}".strip(), color))

    return events


def print_session_header(model_name: str, gateway_url: str, workspace: str) -> None:
    print("")
    print(colorize("=" * 88, ANSI_DIM))
    print_log_line("SESSION", f"framework=toolathlon_default model={model_name}", ANSI_MAGENTA)
    print_log_line("GATEWAY", gateway_url, ANSI_MAGENTA)
    print_log_line("WORKDIR", workspace, ANSI_MAGENTA)
    print(colorize("=" * 88, ANSI_DIM))


class PrettyDecoupledTaskAgent(TaskAgent):
    async def process_agent_response(self, result) -> List[Dict]:
        recent_tool_calls = await super().process_agent_response(result)
        events = render_run_items_to_console_events(result.new_items)

        print_log_line(
            "TURN",
            f"user_turn={self.stats['interaction_turns']} tool_calls={len(recent_tool_calls)}",
            ANSI_BLUE,
        )
        for tag, message, color in events:
            print_log_line(tag, message, color)
        if result.final_output:
            summary_text = str(result.final_output).strip()
            assistant_messages = [message for tag, message, _ in events if tag == "ASSIST"]
            if summary_text and summary_text not in assistant_messages:
                print_log_line("SUMMARY", preview_text(summary_text), ANSI_GREEN)

        return recent_tool_calls


def expand_stop_tool_names(stop_tools: List[str], gateway_server_name: str) -> List[str]:
    expanded = set(stop_tools)
    for tool in stop_tools:
        expanded.add(f"{gateway_server_name}-{tool}")
    return sorted(expanded)


def decoupled_termination_checker(
    content: str,
    recent_tools: List[Dict],
    check_target: str = "user",
    user_stop_phrases: List[str] = [],
    agent_stop_tools: List[str] = [],
) -> bool:
    if default_termination_checker(
        content=content,
        recent_tools=recent_tools,
        check_target=check_target,
        user_stop_phrases=user_stop_phrases,
        agent_stop_tools=agent_stop_tools,
    ):
        return True

    # Decoupled hard requirement: stop when the agent makes no tool call in this round.
    if check_target == "agent" and len(recent_tools) == 0:
        return True

    return False


def build_gateway_runtime_mcp_config(
    runtime_dir: str,
    gateway_server_name: str,
    gateway_url: str,
) -> str:
    os.makedirs(runtime_dir, exist_ok=True)
    config_path = os.path.join(runtime_dir, "gateway_sse.yaml")
    config = {
        "type": "sse",
        "name": gateway_server_name,
        "params": {
            "url": gateway_url,
        },
        "cache_tools_list": False,
    }
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, sort_keys=False)
    return runtime_dir


def build_host_task_config(bundle: Dict[str, Any], agent_short_name: str) -> TaskConfig:
    eval_config_dict = bundle["eval_config"]
    global_task_config = dict(eval_config_dict["global_task_config"])
    global_task_config["dump_path"] = bundle["host_paths"]["task_root"]
    global_task_config["direct_to_dumps"] = True

    task_config = TaskConfig.build(
        task_dir=bundle["task_dir"],
        agent_short_name=agent_short_name,
        global_task_config=global_task_config,
        single_turn_mode=bundle["single_turn_mode"],
        cn_mode=bundle["cn_mode"],
    )

    task_config.task_root = os.path.abspath(bundle["host_paths"]["task_root"])
    task_config.agent_workspace = os.path.abspath(bundle["host_paths"]["agent_workspace"])
    task_config.log_file = os.path.abspath(bundle["host_paths"]["log_file"])
    task_config.task_str = bundle["task_str"]
    task_config.launch_time = bundle["launch_time"]

    # Rebuild prompts with host workspace path and the original launch_time.
    task_config.system_prompts = SystemPrompts.build(task_config.task_dir, task_config.cn_mode)
    task_config.system_prompts.apply(
        task_config.agent_workspace,
        task_config.task_str,
        task_config.launch_time,
        task_config.single_turn_mode,
        task_config.cn_mode,
    )

    task_config.needed_local_tools = filter_local_tools(task_config.needed_local_tools or [])
    return task_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Host-side decoupled agent loop runner")
    parser.add_argument("--bundle_file", required=True)
    parser.add_argument("--gateway_url", required=True, help="SSE endpoint, e.g. http://127.0.0.1:10086/sse")
    parser.add_argument("--gateway_server_name", default="gw")
    parser.add_argument("--with_proxy", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--allow_resume", action="store_true")
    parser.add_argument("--programmatic_tool_calling", action="store_true",
                       help=("Enable programmatic tool calling on the host side: "
                             "wraps the gateway in a PTC layer that exposes "
                             "ptc-programmatic_tool_call. Inside the sandbox, code "
                             "calls gateway tools via tools[\"<gw>-<tool>\"](...)."))
    parser.add_argument("--ptc_timeout", type=int, default=None,
                       help="Per-call timeout (seconds) for programmatic_tool_call. Default 60.")
    return parser.parse_args()


def _apply_ptc_overrides(eval_config_dict: Dict[str, Any], args: argparse.Namespace) -> None:
    """Mirror main.py: env var > CLI flag > eval-config default."""
    tool_cfg = eval_config_dict.setdefault("agent", {}).setdefault("tool", {})
    env_ptc = os.getenv("TOOLATHLON_PROGRAMMATIC_TOOL_CALLING")
    if env_ptc is not None:
        tool_cfg["programmatic_tool_calling"] = env_ptc.strip().lower() in ("1", "true", "yes", "on")
    elif args.programmatic_tool_calling:
        tool_cfg["programmatic_tool_calling"] = True

    env_ptc_timeout = os.getenv("TOOLATHLON_PTC_TIMEOUT")
    if env_ptc_timeout is not None:
        try:
            tool_cfg["ptc_timeout_seconds"] = int(env_ptc_timeout)
        except ValueError:
            print(f"Invalid TOOLATHLON_PTC_TIMEOUT={env_ptc_timeout!r}, ignoring.")
    elif args.ptc_timeout is not None:
        tool_cfg["ptc_timeout_seconds"] = args.ptc_timeout


async def run_host_loop(args: argparse.Namespace) -> int:
    bundle = read_json_file(args.bundle_file)
    setup_proxy(args.with_proxy)

    eval_config_dict = bundle["eval_config"]
    _apply_ptc_overrides(eval_config_dict, args)
    mcp_config, agent_config, user_config = TaskRunner.load_configs(eval_config_dict)
    task_config = build_host_task_config(bundle, agent_short_name=agent_config.model.short_name)

    # Only keep one MCP server from container gateway on host side.
    runtime_dir = os.path.join(task_config.task_root, ".decoupled_runtime")
    mcp_config.server_config_path = build_gateway_runtime_mcp_config(
        runtime_dir=runtime_dir,
        gateway_server_name=args.gateway_server_name,
        gateway_url=args.gateway_url,
    )
    task_config.needed_mcp_servers = [args.gateway_server_name]

    # Stop on both local name and MCP-prefixed name.
    task_config.stop.tool_names = expand_stop_tool_names(
        stop_tools=task_config.stop.tool_names or ["local-claim_done"],
        gateway_server_name=args.gateway_server_name,
    )

    agent_model_provider = build_agent_model_provider(agent_config)
    user_client = build_user_client(user_config)

    print_session_header(
        model_name=agent_config.model.short_name,
        gateway_url=args.gateway_url,
        workspace=task_config.agent_workspace,
    )
    print_log_line("USER", preview_text(task_config.task_str), ANSI_MAGENTA)

    task_agent = PrettyDecoupledTaskAgent(
        task_config=task_config,
        agent_config=agent_config,
        agent_model_provider=agent_model_provider,
        user_config=user_config,
        user_client=user_client,
        mcp_config=mcp_config,
        termination_checker=partial(
            decoupled_termination_checker,
            user_stop_phrases=task_config.stop.user_phrases,
            agent_stop_tools=task_config.stop.tool_names,
        ),
        debug=False,
        allow_resume=args.allow_resume,
        manual=False,
        single_turn_mode=task_config.single_turn_mode,
    )

    current_dir = os.path.abspath(os.getcwd())
    task_status = TaskStatus.FAILED

    try:
        # Preprocess is completed in container already.
        task_agent.status_manager.update_preprocess("done")

        await task_agent.setup_mcp_servers(local_token_key_session=bundle.get("local_token_key_session"))
        await task_agent.setup_agent()
        await task_agent.setup_user_simulator()

        os.chdir(task_config.agent_workspace)
        task_agent.status_manager.update_running("running")
        await task_agent.run_interaction_loop(abs_original_task_root=os.path.abspath(task_config.task_root))

        if task_agent.task_status not in [TaskStatus.MAX_TURNS_REACHED, TaskStatus.INTERRUPTED]:
            task_status = TaskStatus.SUCCESS
            task_agent.status_manager.update_running("done")
        else:
            task_status = task_agent.task_status
            if task_status == TaskStatus.MAX_TURNS_REACHED:
                task_agent.status_manager.update_running("max_turn_exceeded")

    except Exception as e:
        if args.debug:
            traceback.print_exc()
        task_status = TaskStatus.FAILED
        task_agent.status_manager.update_running("fail")
        print(f"Host loop failed: {e}")
    finally:
        os.chdir(current_dir)
        task_agent.task_status = task_status
        user_cost, agent_cost = task_agent.get_cost_summary()
        task_agent.user_cost = user_cost
        task_agent.agent_cost = agent_cost
        await task_agent.save_results()
        await task_agent.cleanup()

    color = ANSI_GREEN if task_status == TaskStatus.SUCCESS else ANSI_RED
    print_log_line(
        "RESULT",
        (
            f"status={task_status.value} "
            f"user_turns={task_agent.stats['interaction_turns']} "
            f"tool_calls={task_agent.stats['tool_calls']} "
            f"agent_requests={task_agent.stats['agent_llm_requests']}"
        ),
        color,
    )
    print(f"Host loop completed with status: {task_status.value}")
    return 0 if task_status == TaskStatus.SUCCESS else 1


def main() -> None:
    args = parse_args()
    raise SystemExit(asyncio.run(run_host_loop(args)))


if __name__ == "__main__":
    main()
