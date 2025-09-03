#!/usr/bin/env python3
# mcp_sse_proxy.py

import subprocess
import asyncio
import json
import uuid
import logging
from aiohttp import web
from aiohttp_sse import sse_response
import argparse
from configs.token_key_session import all_token_key_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPSSEProxy:
    def __init__(self, github_token: str):
        self.container_process = None
        self.pending_requests = {}  # request_id -> response callback
        self.github_token = github_token
        self._lock = asyncio.Lock()  # 防止竞态条件
        self.sse_connections = {}  # session_id -> sse_response
        
    async def start_container(self):
        """启动并独占容器"""
        logger.info("Starting MCP container...")
        self.container_process = subprocess.Popen(
            # TODO: 这里其实可以换成任意stdio命令，从而实现stdio->sse的转换，从而实现任意mcp server的sse化
            [
                'podman', 'run', '-i', '--rm',
                '-e', f'GITHUB_PERSONAL_ACCESS_TOKEN={self.github_token}',
                'ghcr.io/github/github-mcp-server:v0.4.0',
                './github-mcp-server', 'stdio'
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # 启动响应读取器
        asyncio.create_task(self._read_responses())
        asyncio.create_task(self._read_errors())
        logger.info("MCP container started")

    async def startup(self, app):
        """应用启动时初始化"""
        await self.start_container()

    async def _read_errors(self):
        """读取容器错误输出"""
        loop = asyncio.get_event_loop()
        while True:
            try:
                line = await loop.run_in_executor(
                    None, self.container_process.stderr.readline
                )
                if not line:
                    break
                
                line = line.strip()
                if line:
                    logger.info(f"Container log: {line}")
            except Exception as e:
                logger.error(f"Error reading stderr: {e}")
                break
    
    async def _read_responses(self):
        """持续读取容器输出并调用响应回调"""
        loop = asyncio.get_event_loop()
        while True:
            try:
                line = await loop.run_in_executor(
                    None, self.container_process.stdout.readline
                )
                if not line:
                    logger.warning("Container stdout closed")
                    break
                
                # 解析JSON-RPC响应
                response = json.loads(line.strip())
                request_id = response.get('id')
                print(f"Received response with ID: {request_id} (type: {type(request_id)})")
                
                # 使用锁来防止竞态条件
                async with self._lock:
                    print(f"Pending requests: {list(self.pending_requests.keys())}")
                    
                    if request_id is not None and request_id in self.pending_requests:
                        print(f"Found matching request ID, sending via SSE...")
                        sse_response = self.pending_requests.pop(request_id)
                        try:
                            # 通过SSE发送message事件
                            await sse_response.send(json.dumps(response), event="message")
                            print(f"Response sent via SSE for ID: {request_id}")
                        except Exception as e:
                            logger.error(f"Failed to send SSE response: {e}")
                            print(f"SSE error: {e}")
                    else:
                        print(f"No matching request found for ID: {request_id}")
                        
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from container: {e}")
            except Exception as e:
                logger.error(f"Error processing response: {e}")

    async def handle_sse_connection(self, request):
        """处理SSE连接建立"""
        session_id = str(uuid.uuid4())
        async with sse_response(request) as resp:
            try:
                # 存储SSE连接
                self.sse_connections[session_id] = resp
                
                # 发送endpoint事件，告知客户端POST端点，包含session_id
                await resp.send(f"/messages?session_id={session_id}", event="endpoint")
                logger.info(f"Sent endpoint event to SSE client with session_id: {session_id}")
                
                # 保持连接，不发送心跳以避免解析错误
                while True:
                    await asyncio.sleep(30)
                    
            except asyncio.CancelledError:
                logger.info(f"SSE connection cancelled for session: {session_id}")
                raise
            except Exception as e:
                logger.error(f"SSE connection error: {e}")
            finally:
                # 清理连接
                self.sse_connections.pop(session_id, None)
                
        return resp

    async def handle_json_rpc(self, request):
        """处理JSON-RPC POST请求"""
        try:
            # 从query参数获取session_id
            session_id = request.query.get('session_id')
            if not session_id or session_id not in self.sse_connections:
                return web.json_response({
                    "error": "Invalid or missing session_id"
                }, status=400)
                
            sse_resp = self.sse_connections[session_id]
            
            # 从POST body获取JSON-RPC请求
            data = await request.json()

            print(data)
            
            # 确保有请求ID，保持原始类型
            if 'id' not in data:
                data['id'] = str(uuid.uuid4())
            
            request_id = data['id']
            print(f"Processing request with ID: {request_id} (type: {type(request_id)})")

            # 注册SSE响应器BEFORE发送请求，避免竞态条件
            async with self._lock:
                self.pending_requests[request_id] = sse_resp
                print(f"Registered SSE responder for ID: {request_id}")
                print(f"Pending requests after registration: {list(self.pending_requests.keys())}")
            
            # 发送请求到容器
            print(f"Sending request to container: {json.dumps(data)}")
            self.container_process.stdin.write(json.dumps(data) + '\n')
            self.container_process.stdin.flush()
            print(f"Request sent to container")
            logger.debug(f"Sent JSON-RPC request: {data}")
            
            # 立即返回202 Accepted，表示请求已接收，响应将通过SSE发送
            return web.Response(status=202)
            
        except Exception as e:
            logger.error(f"JSON-RPC handling error: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)},
                "id": None
            }
            return web.json_response(error_response)
    
    def create_app(self):
        """创建 aiohttp 应用"""
        app = web.Application()
        
        # 标准MCP SSE端点
        app.router.add_get('/sse', self.handle_sse_connection)
        app.router.add_post('/messages', self.handle_json_rpc)
        
        # 添加 CORS 支持
        async def cors_middleware(app, handler):
            async def middleware_handler(request):
                if request.method == 'OPTIONS':
                    return web.Response(headers={
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                        'Access-Control-Allow-Headers': 'Content-Type'
                    })
                    
                response = await handler(request)
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
                return response
            return middleware_handler
        
        app.middlewares.append(cors_middleware)
        
        # 添加启动和清理钩子
        app.on_startup.append(self.startup)
        app.on_cleanup.append(self.cleanup)

        return app
    
    async def cleanup(self, app):
        """清理资源"""
        if self.container_process:
            logger.info("Terminating container...")
            self.container_process.terminate()
            try:
                self.container_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.container_process.kill()
                self.container_process.wait()

def main():
    parser = argparse.ArgumentParser(description='MCP SSE Proxy')
    parser.add_argument("--port", type=int, default=10006, help="Port to listen on")
    args = parser.parse_args()
    
    github_token = all_token_key_session.github_token
    proxy = MCPSSEProxy(github_token)
    app = proxy.create_app()
    
    # 启动服务器
    logger.info(f"Starting SSE proxy on port {args.port}")
    web.run_app(app, host='0.0.0.0', port=args.port)

if __name__ == '__main__':
    main()