#!/usr/bin/env python3
# mcp_sse_proxy.py

### NOTE: WE DO NOT ACTUALLY USE THIS FILE, IT IS JUST FOR REFERENCE

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
        self._lock = asyncio.Lock()  # prevent race conditions
        self.sse_connections = {}  # session_id -> sse_response
        
    async def start_container(self):
        """Start and exclusively occupy the container"""
        logger.info("Starting MCP container...")
        self.container_process = subprocess.Popen(
            # TODO: Here we can actually replace it with any stdio command, thus implementing the conversion from stdio to sse, and thus implementing the sse of any mcp server
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
        
        # Start response reader
        asyncio.create_task(self._read_responses())
        asyncio.create_task(self._read_errors())
        logger.info("MCP container started")

    async def startup(self, app):
        """Initialize when the application starts"""
        await self.start_container()

    async def _read_errors(self):
        """Read container error output"""
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
        """Continuously read container output and call response callback"""
        loop = asyncio.get_event_loop()
        while True:
            try:
                line = await loop.run_in_executor(
                    None, self.container_process.stdout.readline
                )
                if not line:
                    logger.warning("Container stdout closed")
                    break
                
                # Parse JSON-RPC response
                response = json.loads(line.strip())
                request_id = response.get('id')
                print(f"Received response with ID: {request_id} (type: {type(request_id)})")
                
                # Use lock to prevent race conditions
                async with self._lock:
                    print(f"Pending requests: {list(self.pending_requests.keys())}")
                    
                    if request_id is not None and request_id in self.pending_requests:
                        print(f"Found matching request ID, sending via SSE...")
                        sse_response = self.pending_requests.pop(request_id)
                        try:
                            # Send message event via SSE
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
        """Handle SSE connection establishment"""
        session_id = str(uuid.uuid4())
        async with sse_response(request) as resp:
            try:
                # Store SSE connection
                self.sse_connections[session_id] = resp
                
                # Send endpoint event, inform the client that the POST endpoint contains session_id
                await resp.send(f"/messages?session_id={session_id}", event="endpoint")
                logger.info(f"Sent endpoint event to SSE client with session_id: {session_id}")
                
                # Keep connection, do not send heartbeat to avoid parsing errors
                while True:
                    await asyncio.sleep(30)
                    
            except asyncio.CancelledError:
                logger.info(f"SSE connection cancelled for session: {session_id}")
                raise
            except Exception as e:
                logger.error(f"SSE connection error: {e}")
            finally:
                # Clean up connection
                self.sse_connections.pop(session_id, None)
                
        return resp

    async def handle_json_rpc(self, request):
        """Handle JSON-RPC POST request"""
        try:
            # Get session_id from query parameters
            session_id = request.query.get('session_id')
            if not session_id or session_id not in self.sse_connections:
                return web.json_response({
                    "error": "Invalid or missing session_id"
                }, status=400)
                
            sse_resp = self.sse_connections[session_id]
            
            # Get JSON-RPC request from POST body
            data = await request.json()

            print(data)
            
            # Ensure there is a request ID, keep the original type
            if 'id' not in data:
                data['id'] = str(uuid.uuid4())
            
            request_id = data['id']
            print(f"Processing request with ID: {request_id} (type: {type(request_id)})")

            # Register SSE responder BEFORE sending request, avoid race conditions
            async with self._lock:
                self.pending_requests[request_id] = sse_resp
                print(f"Registered SSE responder for ID: {request_id}")
                print(f"Pending requests after registration: {list(self.pending_requests.keys())}")
            
            # Send request to container
            print(f"Sending request to container: {json.dumps(data)}")
            self.container_process.stdin.write(json.dumps(data) + '\n')
            self.container_process.stdin.flush()
            print(f"Request sent to container")
            logger.debug(f"Sent JSON-RPC request: {data}")
            
            # Immediately return 202 Accepted, indicating that the request has been received, and the response will be sent via SSE
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
        """Create aiohttp application"""
        app = web.Application()
        
        # Standard MCP SSE endpoints
        app.router.add_get('/sse', self.handle_sse_connection)
        app.router.add_post('/messages', self.handle_json_rpc)
        
        # Add CORS support
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
        
        # Add startup and cleanup hooks
        app.on_startup.append(self.startup)
        app.on_cleanup.append(self.cleanup)

        return app
    
    async def cleanup(self, app):
        """Clean up resources"""
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
    
    # Start server
    logger.info(f"Starting SSE proxy on port {args.port}")
    web.run_app(app, host='0.0.0.0', port=args.port)

if __name__ == '__main__':
    main()