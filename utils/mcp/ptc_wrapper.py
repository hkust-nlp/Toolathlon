"""
Programmatic Tool Calling (PTC) wrapper for Toolathlon.

The model is given one extra tool, ``programmatic_tool_call``, that runs Python
code in a persistent subprocess sandbox. From inside the sandbox, the code
calls the task's underlying MCP tools through a ``tools`` proxy, e.g.::

    tools["canvas-list_courses"]()
    tools["arxiv-search"](query="LLM agents", max_results=5)

The proxy forwards tool calls back to the parent over a JSON-line protocol on
stdin/stdout; the parent looks the name up in an aggregated index built from
all connected ``MCPServerManager`` servers and dispatches to the right one.
Index keys are ``f"{server.name}-{tool.name}"``, matching the prefixed names
the model already sees through ``custom_mcp_util.my_to_function_tool``.

Design points worth knowing:
  * Tool failures raise exceptions inside the sandbox, so ``try/except``
    around a tool call works and error text never flows onward as data.
  * Values cross the pipe as JSON; anything without a JSON equivalent is
    reduced to a string (see ``_jsonify``).
  * Tool results are recovered from the ``CallToolResult`` text payload
    deterministically, so a given tool always yields the same Python type.
  * Unknown tool names return ranked "Did you mean: ..." suggestions.
  * Oversized sandbox output is middle-truncated (env-configurable).

The wrapper ships as a synthetic ``MCPServer`` (``PTCSyntheticServer``) so the
existing OpenAI-Agents-SDK plumbing picks it up with no further changes.
"""

from __future__ import annotations

import ast
import asyncio
import datetime as _datetime
import difflib
import json
import logging
import os
import re
import shutil
import sys
import tempfile
import time
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from agents.mcp import MCPServer
from mcp.types import CallToolResult, TextContent, Tool as MCPTool

logger = logging.getLogger(__name__)


# Cap on the output a single programmatic_tool_call may return (chars). Agents
# occasionally print entire fetched datasets (hundreds of KB), which poisons
# the context. 0 disables.
_MAX_OUTPUT_CHARS = int(os.getenv("TOOLATHLON_PTC_MAX_OUTPUT_CHARS", "10000"))


# Persistent worker source. Stays alive across calls; talks JSON-line on
# stdin/stdout. Kept as a string so we can drop it onto disk lazily.
_PERSISTENT_WORKER = r'''
import os, sys, json, csv, traceback, uuid
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

_proto_out = sys.stdout
_proto_in = sys.stdin


def _read_msg():
    line = _proto_in.readline()
    if not line:
        sys.exit(0)
    return json.loads(line)


def _write_msg(msg):
    # default=str: a tool argument the user's code built out of a non-JSON
    # type (a Decimal, a datetime) is sent as its string form rather than
    # raising here — the tool call still goes out, and the receiving tool
    # reports the type problem if it cares.
    _proto_out.write(json.dumps(msg, default=str) + "\n")
    _proto_out.flush()


def _rpc_tool_call(tool_name, args, kwargs):
    req_id = uuid.uuid4().hex
    _write_msg({"type": "tool_call", "id": req_id,
                "tool_name": tool_name,
                "args": list(args),
                "kwargs": dict(kwargs)})
    while True:
        msg = _read_msg()
        if msg.get("type") == "tool_result" and msg.get("id") == req_id:
            if msg.get("ok"):
                return msg.get("value")
            # Raise (rather than return an error string) so failures surface
            # as exceptions — try/except around tool calls works and errors
            # never flow onward disguised as data.
            raise RuntimeError(msg.get("error", "unknown error"))


class _ToolProxy:
    __slots__ = ("_name",)

    def __init__(self, name):
        object.__setattr__(self, "_name", name)

    def __call__(self, *args, **kwargs):
        return _rpc_tool_call(self._name, args, kwargs)


class ToolCaller:
    def __getitem__(self, key):
        return _ToolProxy(str(key))

    def __getattr__(self, name):
        return _ToolProxy(str(name))


def main():
    init = _read_msg()
    workspace = init.get("workspace") or os.getcwd()
    try:
        os.chdir(workspace)
    except Exception:
        pass

    g = {
        "__name__": "__main__",
        "tools": ToolCaller(),
        "WORKSPACE": workspace,
        "workspace_path": workspace,
        # Pre-imports, as promised in the tool description.
        "os": os,
        "sys": sys,
        "json": json,
        "csv": csv,
    }

    _write_msg({"type": "ready"})

    while True:
        try:
            msg = _read_msg()
        except Exception as exc:
            _write_msg({"type": "done", "stdout": None, "stderr": None,
                        "error": f"Protocol error: {exc}"})
            continue

        if msg.get("type") != "exec":
            continue

        code = msg.get("code", "")
        file_path = msg.get("file_path", "<code>")
        g["__file__"] = file_path

        out_buf, err_buf, tb = StringIO(), StringIO(), None
        try:
            with redirect_stdout(out_buf), redirect_stderr(err_buf):
                exec(compile(code, file_path, "exec"), g)
        except Exception:
            tb = traceback.format_exc()

        _write_msg({"type": "done",
                    "stdout": out_buf.getvalue() or None,
                    "stderr": err_buf.getvalue() or None,
                    "error": tb})


if __name__ == "__main__":
    main()
'''


# Tool names are prefixed `<server>-<tool>` (hyphens), so only bracket access
# works — the examples below use it throughout.
_CODE_EXECUTION_DESCRIPTION = (
    'Run Python that calls the tools listed above as `tools["tool_name"](*args, **kwargs)`. State (variables, imports) persists across calls. Use print() to see output.\n'
    "USE WHEN: loops, conditionals, error handling, or chaining multiple tool calls with intermediate processing.\n\n"
    "Notes:\n"
    "- Code runs in the workspace directory and file writes are restricted to it, don't write to `/tmp`; always use absolute paths for file writes; os, json, csv, sys are pre-imported.\n"
    "- Tools return native Python values; the type and structure vary by tool (e.g. dict, list, or str). Always print and inspect the first result before processing many items; do not assume a result is a list and loop over it.\n"
    "- Very large printed output is truncated; print summaries rather than large raw data.\n"
    "- Tools may raise an exception; wrap calls in try/except to handle failures.\n"
    "Usage examples:\n\n"
    "Batch + conditional workflow:\n"
    "```python\n"
    "print(type(tools[\"get_info\"](id='A001')))  # inspect return type first, then loop\n"
    "results = []\n"
    "for item in ['A001', 'A002', 'A003']:\n"
    "    info = tools[\"get_info\"](id=item)\n"
    "    if info.get('status') == 'active': # info is a dict, confirmed above\n"
    "        results.append(tools[\"get_details\"](id=item))\n"
    "    else:\n"
    "        print(f'Skipping {item}')\n"
    "    print(f'Processed {item}')\n"
    "print('Collected', len(results))\n"
    "```\n\n"
    "Error handling:\n"
    "```python\n"
    "ok, failed = [], []\n"
    "for item_id in ['A001', 'A002', 'A003']:\n"
    "    try:\n"
    "        r = tools[\"get_info\"](id=item_id)\n"
    "        ok.append(r)\n"
    "    except Exception as e:\n"
    "        failed.append((item_id, str(e)))\n"
    "    print(f'{len(ok)} ok, {len(failed)} failed')\n"
    "print('Failed:', failed[:3] if failed else 'none')\n"
    "```"
)


def _coerce_block(text: str) -> tuple:
    """Recover a Python value from one text block; ``(value, ok)``.

    Structured payloads become native objects, plain text stays ``str``:

      1. strict JSON (canonical structured channel for well-behaved servers);
      2. a Python ``repr`` container via ``ast.literal_eval`` — only attempted
         when the text looks like a top-level ``[``/``{``/``(`` collection, so
         genuine prose (file contents, error strings) is never mis-parsed;
      3. otherwise ``(text, False)`` — caller keeps it as a string.
    """
    try:
        return json.loads(text), True
    except (json.JSONDecodeError, TypeError):
        pass
    if text.lstrip()[:1] not in ("[", "{", "("):
        return text, False
    try:
        return ast.literal_eval(text), True
    except (ValueError, SyntaxError, MemoryError, RecursionError):
        return text, False


def _stringify_result(result: Any) -> Any:
    """Recover a *native* Python value from an MCP ``CallToolResult``.

    The tool's payload crossed the MCP boundary boxed into text content
    blocks, so we always parse it back into a native ``dict``/``list``/scalar
    and do so *deterministically* — the same tool yields the same type on
    every call. That predictability matters: a value that is "sometimes a
    parsed list, sometimes its raw string" makes generated code guess wrong
    (``json.loads`` on an already-parsed list, or ``row['x']`` on an unparsed
    string), which is exactly the failure loop native returns avoid.

      1. coerce the joined text content *once* — JSON, then a Python ``repr``
         container;
      2. only genuinely unparseable prose (file contents, error strings) stays
         ``str`` — itself consistent, since such a tool always returns prose.
    """
    try:
        if isinstance(result, dict):
            content = result.get("content")
        else:
            content = getattr(result, "content", None)
        texts: List[str] = []
        for item in content or ():
            if isinstance(item, dict):
                text = item.get("text")
            else:
                text = getattr(item, "text", None)
            if text is not None:
                texts.append(text)
        joined = "\n".join(texts) if texts else None

        if not texts:
            if hasattr(result, "model_dump"):
                try:
                    return result.model_dump(mode="json")
                except Exception:
                    pass
            if isinstance(result, (str, int, float, bool, list, dict)) or result is None:
                return result
            return str(result)

        # Coerce the joined payload exactly once, so a given tool's result — and
        # therefore its type — is deterministic across calls.
        value, _ = _coerce_block(joined)
        return value
    except Exception:
        return str(result)


def _result_error_text(result: Any) -> Optional[str]:
    """Return the error message when an MCP ``CallToolResult`` signals failure.

    Tool failures arrive as ``isError: True`` on an *otherwise normal* result —
    the MCP convention. ``server.call_tool`` does **not** raise for them, so
    this check is what turns a failure into an exception inside the sandbox;
    without it the error text flows onward disguised as data, generated code
    subscripts the error string as if it were a row, and its ``try/except``
    never fires.

    Returns the extracted error text on failure, otherwise ``None``.
    """
    if isinstance(result, dict):
        is_err = result.get("isError")
    else:
        is_err = getattr(result, "isError", None)
    if is_err:
        text = _stringify_result(result)
        if not isinstance(text, str):
            text = repr(text)
        return text or "tool reported an error (isError) with no message"

    return None


def _jsonify(value: Any) -> Any:
    """Reduce a recovered value to JSON-clean types.

    Used at the MCP argument boundary: str/int/float/bool/None inside plain
    list/dict containers — Decimal→float, datetime/date/time→ISO string,
    tuple/set→list; anything else degrades to str(). Total function, so the
    result always survives json.dumps.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonify(v) for v in value]
    if isinstance(value, dict):
        return {
            (k if isinstance(k, str) else str(k)): _jsonify(v)
            for k, v in value.items()
        }
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (_datetime.datetime, _datetime.date, _datetime.time)):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", errors="replace")
    return str(value)


def _truncate_output(text: str, limit: int) -> str:
    """Middle-truncate `text` to ~`limit` chars, keeping head and tail."""
    if limit <= 0 or len(text) <= limit:
        return text
    head = int(limit * 0.7)
    tail = limit - head
    omitted = len(text) - head - tail
    return (
        f"{text[:head]}\n...[output truncated: {omitted} chars omitted; "
        f"print concise summaries instead of large raw data]...\n{text[-tail:]}"
    )


# Appended whenever the worker dies. A killed worker is respawned lazily by
# _ensure_worker() on the next call, so the model's next step is simply to
# retry — but only if it is told, otherwise a bare crash message reads like a
# dead end and the following NameError (state was reset) looks unexplained.
_RESTART_NOTE = (
    " — a fresh Python session starts automatically on your next "
    "programmatic_tool_call, but all variables, imports and function "
    "definitions are lost, so re-create any state you still need"
)


def _ptc_text_result(text: str, is_error: bool = True) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=text)],
        isError=is_error,
    )


def _format_exec_result(msg: Dict[str, Any]) -> CallToolResult:
    parts: List[str] = []
    if msg.get("stdout"):
        parts.append(str(msg["stdout"]))
    if msg.get("stderr"):
        parts.append("STDERR:\n" + str(msg["stderr"]))
    if msg.get("error"):
        parts.append("ERROR:\n" + str(msg["error"]))
    text = _truncate_output("\n".join(parts) if parts else "", _MAX_OUTPUT_CHARS)
    return CallToolResult(
        content=[TextContent(type="text", text=text)],
        isError=bool(msg.get("error")),
    )


class PTCWrapper:
    """Aggregates underlying MCP servers behind a single ``programmatic_tool_call`` tool."""

    CODE_EXECUTION_TOOL = "programmatic_tool_call"

    def __init__(
        self,
        servers: List[MCPServer],
        workspace: Optional[str] = None,
        default_code_timeout: int = 60,
    ):
        self._servers: List[MCPServer] = list(servers)
        self._workspace = os.path.abspath(workspace) if workspace else os.getcwd()
        self._default_code_timeout = int(default_code_timeout)

        # exposed_name -> (server, original_tool_name)
        self._tool_index: Dict[str, Tuple[MCPServer, str]] = {}
        # exposed_name -> ordered parameter list (for positional-arg binding)
        self._tool_param_order: Dict[str, List[str]] = {}
        # exposed_name -> tool description (for unknown-name suggestions)
        self._tool_descriptions: Dict[str, str] = {}
        self._index_built = False
        self._index_lock = asyncio.Lock()

        self._proc: Optional[asyncio.subprocess.Process] = None
        self._proc_lock = asyncio.Lock()
        self._tmp_dir: Optional[str] = None
        self._script_path: Optional[str] = None

    async def setup(self) -> None:
        await self._ensure_index()

    async def aclose(self) -> None:
        await self._kill_worker()
        if self._tmp_dir and os.path.isdir(self._tmp_dir):
            shutil.rmtree(self._tmp_dir, ignore_errors=True)
            self._tmp_dir = None

    def code_execution_tool(self) -> MCPTool:
        return MCPTool(
            name=self.CODE_EXECUTION_TOOL,
            description=_CODE_EXECUTION_DESCRIPTION,
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": (
                            "Python code. Use tools[\"func_name\"](*args, "
                            "**kwargs) to call env tools."
                        ),
                    },
                },
                "required": ["code"],
            },
        )

    @property
    def known_tools(self) -> List[str]:
        return sorted(self._tool_index.keys())

    async def _ensure_index(self) -> None:
        if self._index_built:
            return
        async with self._index_lock:
            if self._index_built:
                return
            for server in self._servers:
                server_name = getattr(server, "name", "") or ""
                try:
                    tools = await server.list_tools()
                except Exception as exc:
                    logger.warning(
                        "PTC: failed to list tools from server %r: %s",
                        server_name, exc,
                    )
                    continue
                for tool in tools:
                    tname = getattr(tool, "name", None)
                    if not tname:
                        continue
                    exposed = f"{server_name}-{tname}"
                    self._tool_index[exposed] = (server, tname)
                    schema = getattr(tool, "inputSchema", None) or {}
                    if not isinstance(schema, dict):
                        schema = {}
                    props = schema.get("properties") or {}
                    if not isinstance(props, dict):
                        props = {}
                    # JSON object key order is preserved in dict iteration.
                    self._tool_param_order[exposed] = list(props.keys())
                    self._tool_descriptions[exposed] = getattr(tool, "description", None) or ""
            self._index_built = True
            logger.info(
                "PTC index built: %d tools across %d server(s)",
                len(self._tool_index), len(self._servers),
            )

    async def call_programmatic(self, code: str) -> CallToolResult:
        await self._ensure_index()
        return await self._handle_code_execution({"code": code})

    async def _handle_code_execution(self, arguments: Dict[str, Any]) -> CallToolResult:
        code = arguments.get("code") or ""
        timeout = self._default_code_timeout

        filename = f"ptc_{uuid.uuid4().hex[:8]}.py"
        tmp_dir = self._ensure_tmp_dir()
        file_path = os.path.join(tmp_dir, filename)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)
        except Exception as exc:
            return _ptc_text_result(f"[ptc] failed to write code file: {exc}")

        async with self._proc_lock:
            try:
                await self._ensure_worker()
            except Exception as exc:
                return _ptc_text_result(
                    f"[ptc] worker failed to start: {exc}{_RESTART_NOTE}"
                )

            try:
                await self._send({"type": "exec", "code": code, "file_path": file_path})
            except (BrokenPipeError, ConnectionResetError, OSError) as exc:
                await self._kill_worker()
                return _ptc_text_result(
                    f"[ptc] worker crashed before exec: {exc}{_RESTART_NOTE}"
                )

            deadline = time.monotonic() + timeout
            timeout_msg = (
                f"[ptc] execution timed out after {timeout}s{_RESTART_NOTE}"
            )
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    await self._kill_worker()
                    return _ptc_text_result(timeout_msg)
                try:
                    msg = await self._readline(remaining)
                except asyncio.TimeoutError:
                    await self._kill_worker()
                    return _ptc_text_result(timeout_msg)
                if msg is None:
                    await self._kill_worker()
                    return _ptc_text_result(
                        "[ptc] the Python session crashed (the code likely "
                        "killed the interpreter, e.g. os._exit or a segfault)"
                        f"{_RESTART_NOTE}"
                    )

                mtype = msg.get("type")
                if mtype == "done":
                    return _format_exec_result(msg)
                if mtype == "tool_call":
                    await self._handle_tool_call(msg)
                    continue
                logger.warning("PTC worker sent unknown message: %s", mtype)

    async def _handle_tool_call(self, msg: Dict[str, Any]) -> None:
        req_id = msg.get("id")
        tool_name = msg.get("tool_name") or ""
        args = msg.get("args") or []
        kwargs = msg.get("kwargs") or {}

        # The agent sees the prefixed name ("ptc-programmatic_tool_call");
        # accept the bare name too in case a caller strips the prefix.
        prefixed = f"{PTCSyntheticServer.SERVER_NAME}-{self.CODE_EXECUTION_TOOL}"
        if tool_name == self.CODE_EXECUTION_TOOL or tool_name == prefixed:
            await self._send({
                "type": "tool_result", "id": req_id, "ok": False,
                "error": (
                    f"'{self.CODE_EXECUTION_TOOL}' must be invoked as a direct "
                    "tool call, not from inside programmatic_tool_call"
                ),
            })
            return

        # Self-correction for hallucinated tool names: surface valid candidates
        # instead of letting the inner server reply with an opaque
        # "Method <name> not found".
        target = self._tool_index.get(tool_name)
        if target is None:
            await self._send({
                "type": "tool_result", "id": req_id,
                "ok": False, "error": self._unknown_tool_message(tool_name),
            })
            return

        server, original_name = target
        try:
            bound_kwargs = self._bind_positional(tool_name, args, kwargs)
        except Exception as exc:
            await self._send({
                "type": "tool_result", "id": req_id, "ok": False,
                "error": f"argument binding failed: {exc}",
            })
            return

        try:
            # MCP arguments must be JSON-clean.
            raw = await server.call_tool(original_name, _jsonify(bound_kwargs))
            err = _result_error_text(raw)
            if err is not None:
                # An MCP-level failure (isError) — surface it as ok:False so the
                # worker raises, instead of returning the error text as a value.
                reply = {"type": "tool_result", "id": req_id, "ok": False, "error": err}
            else:
                value = _jsonify(_stringify_result(raw))
                reply = {"type": "tool_result", "id": req_id, "ok": True, "value": value}
        except Exception as exc:
            reply = {
                "type": "tool_result", "id": req_id,
                "ok": False, "error": f"{type(exc).__name__}: {exc}",
            }

        try:
            await self._send(reply)
        except (BrokenPipeError, ConnectionResetError, OSError):
            await self._kill_worker()
        except (TypeError, ValueError) as exc:
            # A value _jsonify missed. The worker is still blocked
            # on this req_id — answer with an error rather than leaving the
            # protocol desynced (which turns every later call into a timeout).
            try:
                await self._send({
                    "type": "tool_result", "id": req_id, "ok": False,
                    "error": f"tool result could not be serialized: {exc}",
                })
            except (BrokenPipeError, ConnectionResetError, OSError):
                await self._kill_worker()

    def _bind_positional(
        self, tool_name: str, args: List[Any], kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve positional args against the tool's declared parameter order."""
        if not args:
            return dict(kwargs)
        order = self._tool_param_order.get(tool_name)
        if order is None:
            raise ValueError(
                f"unknown tool '{tool_name}' (positional args require a known schema)"
            )
        out = dict(kwargs)
        idx = 0
        for pname in order:
            if idx >= len(args):
                break
            if pname in out:
                continue
            out[pname] = args[idx]
            idx += 1
        if idx < len(args):
            raise ValueError(
                f"too many positional arguments for '{tool_name}': "
                f"got {len(args)}, schema declares {len(order)} parameter(s)"
            )
        return out

    # ------------------------------------------------------------------
    # Self-correction for unknown tool names.
    # ------------------------------------------------------------------

    @staticmethod
    def _tokenize(text: str) -> set:
        return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if t}

    def _closest_tools(self, tool_name: str, n: int = 3) -> List[str]:
        """Rank known tool names by similarity to a (probably misremembered) name.

        Tool names often follow a REST-verb convention (``API-post-page`` to
        *create* a page), so a name-only fuzzy match misleads — the model's
        intent ("create a page") lives in the description. Score each candidate
        on token overlap against name + description, tie-broken by raw name
        similarity, so e.g. ``API-create-a-page`` surfaces ``API-post-page``
        ("Notion | Create a page").
        """
        wanted = self._tokenize(tool_name)
        scored = []
        for name in self._tool_index:
            tokens = self._tokenize(name) | self._tokenize(
                self._tool_descriptions.get(name, "")
            )
            overlap = len(wanted & tokens) / len(wanted) if wanted else 0.0
            name_ratio = difflib.SequenceMatcher(None, tool_name, name).ratio()
            score = overlap + 0.3 * name_ratio
            if score > 0:
                scored.append((score, name))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [name for _, name in scored[:n]]

    def _unknown_tool_message(self, tool_name: str) -> str:
        suggestions = self._closest_tools(tool_name)
        if suggestions:
            hint = "Did you mean: " + ", ".join(suggestions) + "?"
        else:
            hint = "See the available tools list for valid names."
        return (
            f"Unknown tool '{tool_name}'. {hint} "
            "Use exact prefixed names, e.g. 'serverName-toolName'."
        )

    # ------------------------------------------------------------------
    # Worker lifecycle.
    # ------------------------------------------------------------------

    def _ensure_tmp_dir(self) -> str:
        if self._tmp_dir and os.path.isdir(self._tmp_dir):
            return self._tmp_dir
        self._tmp_dir = tempfile.mkdtemp(prefix="toolathlon_ptc_")
        self._script_path = os.path.join(self._tmp_dir, "_ptc_worker.py")
        with open(self._script_path, "w", encoding="utf-8") as f:
            f.write(_PERSISTENT_WORKER)
        return self._tmp_dir

    async def _ensure_worker(self) -> None:
        if self._proc is not None and self._proc.returncode is None:
            return
        if self._proc is not None:
            logger.warning(
                "PTC worker exited (code %s) — restarting (state reset)",
                self._proc.returncode,
            )
            self._proc = None

        self._ensure_tmp_dir()
        self._proc = await asyncio.create_subprocess_exec(
            sys.executable, self._script_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self._workspace,
        )

        init = json.dumps({"workspace": self._workspace}) + "\n"
        self._proc.stdin.write(init.encode())
        await self._proc.stdin.drain()

        try:
            line = await asyncio.wait_for(self._proc.stdout.readline(), timeout=15)
            ready = json.loads(line) if line else {}
            if ready.get("type") != "ready":
                raise RuntimeError(f"unexpected init response: {ready}")
        except Exception as exc:
            await self._kill_worker()
            raise RuntimeError(f"worker failed to start: {exc}") from exc

        logger.info(
            "PTC worker started (pid %s, cwd=%s)",
            self._proc.pid, self._workspace,
        )

    async def _send(self, msg: Dict[str, Any]) -> None:
        if self._proc is None or self._proc.stdin is None:
            raise BrokenPipeError("PTC worker is not running")
        data = (json.dumps(msg) + "\n").encode()
        self._proc.stdin.write(data)
        await self._proc.stdin.drain()

    async def _readline(self, timeout: float) -> Optional[Dict[str, Any]]:
        if self._proc is None or self._proc.stdout is None:
            return None
        line = await asyncio.wait_for(self._proc.stdout.readline(), timeout=timeout)
        if not line:
            return None
        return json.loads(line)

    async def _kill_worker(self) -> None:
        proc = self._proc
        self._proc = None
        if proc is None:
            return
        try:
            proc.kill()
            await proc.wait()
        except (ProcessLookupError, OSError):
            pass


class PTCSyntheticServer(MCPServer):
    """Exposes a ``PTCWrapper`` as a single-tool MCP server.

    The Toolathlon agent loop iterates ``MCPServerManager.connected_servers``
    and converts each server's tools through ``my_to_function_tool``, which
    prefixes the tool name with the server name. Plugging this synthetic
    server in there means the model sees a regular tool named
    ``ptc-programmatic_tool_call`` with no other code changes.
    """

    SERVER_NAME = "ptc"

    def __init__(self, wrapper: PTCWrapper):
        self._wrapper = wrapper
        # Mirror the MCPServerStdio API so the agents framework can read it.
        self.cache_tools_list = True

    @property
    def name(self) -> str:
        return self.SERVER_NAME

    async def connect(self):
        # Real servers were already connected before this wrapper was built;
        # the worker is started lazily on the first programmatic_tool_call.
        return None

    async def cleanup(self):
        await self._wrapper.aclose()

    def invalidate_tools_cache(self):
        return None

    async def list_tools(self) -> List[MCPTool]:
        return [self._wrapper.code_execution_tool()]

    async def call_tool(
        self, tool_name: str, arguments: Optional[Dict[str, Any]]
    ) -> CallToolResult:
        if tool_name != PTCWrapper.CODE_EXECUTION_TOOL:
            return _ptc_text_result(
                f"[ptc] unknown tool '{tool_name}' — only "
                f"'{PTCWrapper.CODE_EXECUTION_TOOL}' is exposed."
            )
        return await self._wrapper.call_programmatic(
            (arguments or {}).get("code") or ""
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.cleanup()
        return False
