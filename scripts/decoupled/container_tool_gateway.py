import argparse
import asyncio
import json
import random
import re
import uuid
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional

from aiohttp import web
from aiohttp_sse import sse_response

from utils.mcp.tool_servers import MCPServerManager, ToolCallError, call_tool_with_retry

JSONRPC_VERSION = "2.0"
MCP_PROTOCOL_VERSION = "2024-11-05"

# Transient upstream failures worth absorbing inside the gateway rather than
# surfacing to the agent (each surfaced failure costs a full LLM round-trip,
# and quota-style errors need a longer wait than any agent will give them).
# Matched against the tool result text as well as raised errors, because most
# MCP servers report HTTP failures as ordinary text results.
TRANSIENT_ERROR_RE = re.compile(
    r"HttpError 429|Too Many Requests|quota ?[Ee]xceeded|RESOURCE_EXHAUSTED"
    r"|rate limit|status of 50[0234]|50[0234] (Internal|Bad Gateway|Service|Gateway)"
    r"|Service Unavailable|ECONNRESET|ETIMEDOUT|Connection reset|timed? out",
)
# Only read-like tools are safe to re-run when the *result* looks transient: a
# 429 on a write does not prove the write never landed.
READ_ONLY_TOOL_RE = re.compile(
    r"(^|[-_])(get|list|read|search|fetch|query|download|describe|view)([-_]|$)",
    re.IGNORECASE,
)
# Long tail on purpose: Google-style quotas are per-minute windows, so the
# final waits must be able to cross into the next window.
TRANSIENT_RETRY_DELAYS = (2.0, 5.0, 15.0, 35.0)


def read_json_file(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _tool_to_dict(tool: Any) -> Dict[str, Any]:
    if isinstance(tool, dict):
        raw = dict(tool)
    elif hasattr(tool, "model_dump"):
        raw = tool.model_dump(mode="json", exclude_none=True)
    else:
        raw = {}

    name = raw.get("name", getattr(tool, "name", None))
    description = raw.get("description", getattr(tool, "description", "")) or ""
    input_schema = (
        raw.get("inputSchema")
        or raw.get("input_schema")
        or raw.get("parameters")
        or getattr(tool, "inputSchema", None)
        or getattr(tool, "input_schema", None)
        or {"type": "object", "properties": {}, "additionalProperties": True}
    )
    if not isinstance(input_schema, dict):
        input_schema = {"type": "object", "properties": {}, "additionalProperties": True}
    if "type" not in input_schema:
        input_schema = dict(input_schema)
        input_schema["type"] = "object"
    if input_schema.get("type") == "object" and "properties" not in input_schema:
        input_schema = dict(input_schema)
        input_schema["properties"] = {}

    if not isinstance(name, str) or not name:
        raise ValueError(f"Invalid MCP tool name: {name}")

    return {
        "name": name,
        "description": description,
        "inputSchema": input_schema,
    }


def _content_item_to_dict(item: Any) -> Dict[str, Any]:
    if isinstance(item, dict):
        result = dict(item)
    elif hasattr(item, "model_dump"):
        result = item.model_dump(mode="json", exclude_none=True)
    else:
        text = getattr(item, "text", None)
        if text is None:
            text = str(item)
        result = {"type": "text", "text": text}
    if "type" not in result:
        result["type"] = "text"
    return result


def _call_result_to_dict(result: Any) -> Dict[str, Any]:
    if isinstance(result, dict):
        out = dict(result)
    elif hasattr(result, "model_dump"):
        out = result.model_dump(mode="json", exclude_none=True)
    else:
        out = {}

    if isinstance(out, dict) and "content" in out and isinstance(out["content"], list):
        out["content"] = [_content_item_to_dict(item) for item in out["content"]]
        if "isError" not in out:
            out["isError"] = bool(out.get("is_error", False))
        return out

    content = getattr(result, "content", None)
    if isinstance(content, list):
        is_error = bool(getattr(result, "isError", getattr(result, "is_error", False)))
        return {
            "content": [_content_item_to_dict(item) for item in content],
            "isError": is_error,
        }

    return {
        "content": [_content_item_to_dict(result)],
        "isError": False,
    }


@dataclass
class ToolRecord:
    exposed_name: str
    backend_type: str  # remote | local
    backend_name: str
    description: str
    input_schema: Dict[str, Any]
    server_name: Optional[str] = None


class ToolRegistry:
    def __init__(self) -> None:
        self._records: Dict[str, ToolRecord] = {}

    def _allocate_name(
        self,
        base_name: str,
        server_name: Optional[str],
        always_prefix: bool = True,
    ) -> str:
        if not always_prefix and base_name not in self._records:
            return base_name

        prefix = server_name or "tool"
        candidate = f"{prefix}-{base_name}"
        suffix = 2
        while candidate in self._records:
            candidate = f"{prefix}-{base_name}-{suffix}"
            suffix += 1
        return candidate

    def add_remote_tools(self, server_name: str, tools: List[Any]) -> None:
        for tool in tools:
            normalized = _tool_to_dict(tool)
            exposed_name = self._allocate_name(normalized["name"], server_name)
            self._records[exposed_name] = ToolRecord(
                exposed_name=exposed_name,
                backend_type="remote",
                backend_name=normalized["name"],
                description=normalized["description"],
                input_schema=normalized["inputSchema"],
                server_name=server_name,
            )

    def add_claim_done(self) -> None:
        name = self._allocate_name("local-claim_done", "local", always_prefix=False)
        self._records[name] = ToolRecord(
            exposed_name=name,
            backend_type="local",
            backend_name="local-claim_done",
            description="claim the task is done",
            input_schema={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            server_name=None,
        )

    def list_tools(self) -> List[Dict[str, Any]]:
        tools = []
        for name in sorted(self._records.keys()):
            record = self._records[name]
            tools.append(
                {
                    "name": record.exposed_name,
                    "description": record.description,
                    "inputSchema": record.input_schema,
                }
            )
        return tools

    def get(self, tool_name: str) -> Optional[ToolRecord]:
        return self._records.get(tool_name)

    def __len__(self) -> int:
        return len(self._records)


class GatewayCore:
    def __init__(
        self,
        registry: ToolRegistry,
        remote_caller: Callable[[ToolRecord, Dict[str, Any]], Awaitable[Dict[str, Any]]],
    ) -> None:
        self.registry = registry
        self.remote_caller = remote_caller

    @staticmethod
    def _success(request_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": request_id,
            "result": result,
        }

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> Dict[str, Any]:
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": request_id,
            "error": {"code": code, "message": message},
        }

    async def handle_json_rpc(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(payload, dict):
            return self._error(None, -32600, "Invalid Request")

        request_id = payload.get("id")
        method = payload.get("method")

        if not isinstance(method, str):
            if request_id is None:
                return None
            return self._error(request_id, -32600, "Invalid Request")

        if method == "notifications/initialized":
            return None

        if method == "initialize":
            if request_id is None:
                return None
            return self._success(
                request_id,
                {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {
                        "name": "toolathlon-container-gateway",
                        "version": "0.1.0",
                    },
                },
            )

        if method == "ping":
            if request_id is None:
                return None
            return self._success(request_id, {})

        if method == "tools/list":
            if request_id is None:
                return None
            return self._success(request_id, {"tools": self.registry.list_tools()})

        if method == "tools/call":
            params = payload.get("params", {})
            if not isinstance(params, dict):
                if request_id is None:
                    return None
                return self._error(request_id, -32602, "Invalid params")

            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            if not isinstance(tool_name, str) or not tool_name:
                if request_id is None:
                    return None
                return self._error(request_id, -32602, "Tool name is required")
            if not isinstance(arguments, dict):
                if request_id is None:
                    return None
                return self._error(request_id, -32602, "Tool arguments must be an object")

            tool_record = self.registry.get(tool_name)
            if tool_record is None:
                if request_id is None:
                    return None
                return self._error(request_id, -32602, f"Tool not found: {tool_name}")

            try:
                if tool_record.backend_type == "local":
                    result = {
                        "content": [
                            {
                                "type": "text",
                                "text": "you have claimed the task is done!",
                            }
                        ],
                        "isError": False,
                    }
                else:
                    result = await self.remote_caller(tool_record, arguments)
            except Exception as e:
                if request_id is None:
                    return None
                return self._error(request_id, -32603, f"Tool call failed: {e}")

            if request_id is None:
                return None
            return self._success(request_id, result)

        if request_id is None:
            return None
        return self._error(request_id, -32601, f"Method not found: {method}")


class ContainerToolGateway:
    def __init__(self, bundle_file: str, debug: bool = False) -> None:
        self.bundle_file = bundle_file
        self.debug = debug

        self.bundle: Dict[str, Any] = {}
        self.registry = ToolRegistry()
        self.core = GatewayCore(self.registry, self._remote_call)

        self.mcp_manager: Optional[MCPServerManager] = None

        self._sse_connections: Dict[str, Any] = {}
        self._session_locks: Dict[str, asyncio.Lock] = {}
        self._request_tasks: set[asyncio.Task] = set()

    async def startup(self, app: web.Application) -> None:
        self.bundle = read_json_file(self.bundle_file)

        needed_servers = self.bundle.get("needed_mcp_servers", []) or []
        mcp_config = self.bundle["eval_config"]["mcp"]
        agent_workspace = self.bundle["container_paths"]["agent_workspace"]
        local_token_key_session = self.bundle.get("local_token_key_session")

        self.mcp_manager = MCPServerManager(
            agent_workspace=agent_workspace,
            config_dir=mcp_config["server_config_path"],
            debug=self.debug,
            local_token_key_session=local_token_key_session,
        )
        await self.mcp_manager.connect_servers(needed_servers)

        for server_name in self.mcp_manager.get_connected_server_names():
            server = self.mcp_manager.connected_servers[server_name]
            tools = await server.list_tools()
            self.registry.add_remote_tools(server_name, tools)

        self.registry.add_claim_done()

        if self.debug:
            print(f"[gateway] connected servers: {self.mcp_manager.get_connected_server_names()}")
            print(f"[gateway] exposed tools: {[tool['name'] for tool in self.registry.list_tools()]}")

    async def cleanup(self, app: web.Application) -> None:
        for task in list(self._request_tasks):
            task.cancel()
        if self._request_tasks:
            await asyncio.gather(*self._request_tasks, return_exceptions=True)
        self._request_tasks.clear()

        if self.mcp_manager is not None:
            await self.mcp_manager.ensure_all_disconnected()

    async def _remote_call(self, tool_record: ToolRecord, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if self.mcp_manager is None:
            raise RuntimeError("MCP manager is not initialized")
        if tool_record.server_name not in self.mcp_manager.connected_servers:
            raise RuntimeError(f"MCP server is not connected: {tool_record.server_name}")

        server = self.mcp_manager.connected_servers[tool_record.server_name]
        retryable = READ_ONLY_TOOL_RE.search(tool_record.backend_name) is not None

        for attempt, delay in enumerate(TRANSIENT_RETRY_DELAYS):
            try:
                result = await call_tool_with_retry(
                    server=server,
                    tool_name=tool_record.backend_name,
                    arguments=arguments,
                    retry_time=1,
                    delay=0.5,
                )
            except ToolCallError:
                # call_tool_with_retry already retried the raised error once;
                # give read-only tools the longer backoff ladder too.
                if not retryable:
                    raise
                await asyncio.sleep(delay * (1 + random.uniform(0, 0.25)))
                continue

            payload = _call_result_to_dict(result)
            if not retryable:
                return payload
            # Scan only the head: transient errors appear early, results can be huge.
            if not TRANSIENT_ERROR_RE.search(json.dumps(payload)[:20_000]):
                return payload
            print(
                f"[gateway] transient error from {tool_record.backend_name} "
                f"(attempt {attempt + 1}/{len(TRANSIENT_RETRY_DELAYS) + 1}); "
                f"retrying in {delay:.0f}s",
                flush=True,
            )
            await asyncio.sleep(delay * (1 + random.uniform(0, 0.25)))

        # Last attempt runs outside the loop: its result — success, a still-
        # transient payload, or a raised ToolCallError — goes to the caller as-is.
        result = await call_tool_with_retry(
            server=server,
            tool_name=tool_record.backend_name,
            arguments=arguments,
            retry_time=1,
            delay=0.5,
        )
        return _call_result_to_dict(result)

    async def handle_health(self, request: web.Request) -> web.Response:
        connected = []
        if self.mcp_manager is not None:
            connected = self.mcp_manager.get_connected_server_names()
        return web.json_response(
            {
                "ok": True,
                "connected_servers": connected,
                "tool_count": len(self.registry),
            }
        )

    async def handle_sse_connection(self, request: web.Request) -> web.StreamResponse:
        session_id = str(uuid.uuid4())
        async with sse_response(request) as resp:
            self._sse_connections[session_id] = resp
            self._session_locks[session_id] = asyncio.Lock()
            await resp.send(f"/messages/?session_id={session_id}", event="endpoint")

            try:
                while True:
                    await asyncio.sleep(30)
            except asyncio.CancelledError:
                raise
            finally:
                self._sse_connections.pop(session_id, None)
                self._session_locks.pop(session_id, None)

        return resp

    async def _send_to_session(self, session_id: str, payload: Dict[str, Any]) -> None:
        sse_conn = self._sse_connections.get(session_id)
        session_lock = self._session_locks.get(session_id)
        if sse_conn is None or session_lock is None:
            return

        async with session_lock:
            await sse_conn.send(json.dumps(payload, ensure_ascii=False), event="message")

    async def _process_rpc_request(self, session_id: str, payload: Dict[str, Any]) -> None:
        response = await self.core.handle_json_rpc(payload)
        if response is None:
            return
        await self._send_to_session(session_id, response)

    async def handle_json_rpc(self, request: web.Request) -> web.Response:
        session_id = request.query.get("session_id")
        if not session_id or session_id not in self._sse_connections:
            return web.json_response({"error": "Invalid or missing session_id"}, status=400)

        try:
            payload = await request.json()
        except Exception as e:
            parse_error = {
                "jsonrpc": JSONRPC_VERSION,
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {e}"},
            }
            await self._send_to_session(session_id, parse_error)
            return web.Response(status=202)

        task = asyncio.create_task(self._process_rpc_request(session_id, payload))
        self._request_tasks.add(task)
        task.add_done_callback(self._request_tasks.discard)
        return web.Response(status=202)

    def create_app(self) -> web.Application:
        app = web.Application()
        app.router.add_get("/health", self.handle_health)
        app.router.add_get("/sse", self.handle_sse_connection)
        app.router.add_post("/messages", self.handle_json_rpc)
        app.router.add_post("/messages/", self.handle_json_rpc)
        app.on_startup.append(self.startup)
        app.on_cleanup.append(self.cleanup)
        return app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Container-side aggregated MCP SSE gateway")
    parser.add_argument("--bundle_file", default="/workspace/dumps/task_bundle.json")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=10086)
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    gateway = ContainerToolGateway(bundle_file=args.bundle_file, debug=args.debug)
    app = gateway.create_app()
    web.run_app(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
