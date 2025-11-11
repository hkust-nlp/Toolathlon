from typing import List, Dict, Optional, Union, Any
import asyncio
import os
import yaml
from pathlib import Path

from agents.mcp import MCPServerStdio, MCPServerSse
from configs.global_configs import global_configs
from configs.token_key_session import all_token_key_session


class ToolCallError(Exception):
    """Custom exception type for tool call errors"""
    def __init__(self, message: str, original_exception: Exception = None):
        self.message = message
        self.original_exception = original_exception
        super().__init__(self.message)

class MCPServerManager:
    """MCP server manager, for initializing and managing multiple MCP servers"""

    def __init__(self, 
                 agent_workspace: str, 
                 config_dir: str = "configs/mcp_servers",
                 debug: bool = False,
                 local_token_key_session: Dict = None):
        """
        Initialize MCP server manager
        
        Args:
            agent_workspace: Agent workspace path
            config_dir: Configuration file directory path
        """
        self.local_servers_paths = os.path.abspath("./local_servers")
        self.local_binary_paths = os.path.abspath("./local_binary")
        self.agent_workspace = os.path.abspath(agent_workspace)
        self.servers: Dict[str, Union[MCPServerStdio, MCPServerSse]] = {}
        self.connected_servers: Dict[str, Union[MCPServerStdio, MCPServerSse]] = {}
        self.debug = debug
        self.local_token_key_session = local_token_key_session
        self._lock = asyncio.Lock()
        # Save each server's task, ensure the lifecycle is managed in the same task
        self._server_tasks: Dict[str, asyncio.Task] = {}
        # Save the event of connection completion
        self._connection_events: Dict[str, asyncio.Event] = {}
        
        # Load servers from configuration files
        self._load_servers_from_configs(config_dir)

    def _load_servers_from_configs(self, config_dir: str):
        """Load servers from configuration file directory"""
        config_path = Path(config_dir)
        if not config_path.exists():
            raise ValueError(f"Configuration directory does not exist: {config_dir}")
        
        if self.debug:
            print(f">>Loading servers from config directory: {config_dir}")
            print(f">>Agent workspace: {self.agent_workspace}")
        
        # Read all yaml configuration files
        for config_file in config_path.glob("*.yaml"):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    if config:
                        self._initialize_server_from_config(config, config_file.stem)
            except Exception as e:
                print(f"Failed to load config file {config_file}: {e}")

    def _initialize_server_from_config(self, config: Dict[str, Any], default_name: str):
        """Initialize a single server from a configuration dictionary"""
        server_type = config.get('type', 'stdio').lower()
        server_name = config.get('name', default_name)
        
        # Process template variables in parameters
        params = self._process_config_params(config.get('params', {}))
        
        # specialized preprocessing for playwright_with_chunk
        if server_name == 'playwright_with_chunk':
            # if the current user is root, then add --no-sandbox to the params
            if os.geteuid() == 0:
                params['args'].append('--no-sandbox')

        # Create server instance
        kwargs = {
            'name': server_name,
            'params': params,
            'cache_tools_list': config.get('cache_tools_list', True)
        }
        
        if timeout := config.get('client_session_timeout_seconds'):
            kwargs['client_session_timeout_seconds'] = timeout
        
        if server_type == 'stdio':
            server = MCPServerStdio(**kwargs)
        elif server_type == 'sse':
            server = MCPServerSse(**kwargs)
        else:
            raise ValueError(f"Unsupported server type: {server_type}")
        
        self.servers[server_name] = server
        # if self.debug:
            # print(f"  - Preloaded server: {server_name} (type: {server_type})")

    def _get_template_variables(self) -> Dict[str, str]:
        """Dynamically get all available template variables"""
        template_vars = {
            # Basic path variables
            'agent_workspace': self.agent_workspace,
            'local_servers_paths': self.local_servers_paths,
            'local_binary_paths': self.local_binary_paths,
            'podman_or_docker': global_configs.podman_or_docker,
        }
        
        # Dynamically add all attributes in global_configs
        for key, value in global_configs.items():
            if isinstance(value, (str, int, float, bool)):  # Only process basic types
                template_vars[f'config.{key}'] = str(value)
        
        # Dynamically add all attributes in all_token_key_session
        for key, value in all_token_key_session.items():
            if isinstance(value, (str, int, float, bool)):  # Only process basic types
                template_vars[f'token.{key}'] = str(value)
        
        # Use local_token_key_session to override all_token_key_session
        # And add prompt information
        if self.local_token_key_session is not None:
            for key, value in self.local_token_key_session.items():
                if isinstance(value, (str, int, float, bool)):  # Only process basic types
                    template_vars[f'token.{key}'] = str(value)
        
        return template_vars

    def _process_config_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Process template variables in configuration parameters"""
        template_vars = self._get_template_variables()
        
        def replace_templates(obj):
            if isinstance(obj, str):
                # Use regular expression to replace all template variables
                import re
                pattern = r'\$\{([^}]+)\}'
                
                def replacer(match):
                    var_name = match.group(1)
                    if var_name in template_vars:
                        return template_vars[var_name]
                    else:
                        print(f"Warning: Template variable '{var_name}' not found")
                        return match.group(0)  # Keep original
                
                return re.sub(pattern, replacer, obj)
                
            elif isinstance(obj, list):
                return [replace_templates(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: replace_templates(v) for k, v in obj.items()}
            else:
                return obj
        
        return replace_templates(params)

    async def _manage_server_lifecycle(self, name: str, server: Union[MCPServerStdio, MCPServerSse], 
                                       max_connect_retries: int = 3, connect_retry_delay: float = 2.0):
        """Manage the full lifecycle of a server in a single task"""
        event = self._connection_events.get(name)
        last_connect_exception = None
        
        # Connection retry logic
        for connect_attempt in range(max_connect_retries + 1):
            try:
                async with server:  # Use server's context manager, which will automatically call connect()
                    # After connection success, add to connected list
                    self.connected_servers[name] = server
                    
                    # Set connection completion event
                    if event:
                        event.set()
                    
                    if self.debug:
                        print(f"  - Server {name} connected (attempt {connect_attempt + 1}/{max_connect_retries + 1})")
                        # Try to get tool list to verify connection
                        try:
                            tools = await server.list_tools()
                            print(f"    Available tools: {len(tools)}")
                        except Exception as e:
                            print(f"    Failed to get tools list: {e}")
                    
                    # Keep connection until task is cancelled
                    try:
                        await asyncio.sleep(float('inf'))  # Infinite wait
                    except asyncio.CancelledError:
                        # Normal cancellation, perform cleanup
                        if self.debug:
                            print(f"  - Disconnecting server {name}")
                        raise  # Re-throw to trigger __aexit__
                    
                    # If connection successful, break retry loop
                    break
                    
            except asyncio.CancelledError:
                # Expected cancellation, not recorded as error
                raise
            except Exception as e:
                last_connect_exception = e
                if connect_attempt < max_connect_retries:
                    if self.debug:
                        print(f"Server {name} connection failed (attempt {connect_attempt + 1}/{max_connect_retries + 1}): {e}")
                        print(f"Waiting {connect_retry_delay} seconds to retry connection...")
                    await asyncio.sleep(connect_retry_delay)
                else:
                    print(f"Server {name} connection failed (attempt {max_connect_retries + 1} times): {e}")
                    if event and not event.is_set():
                        event.set()  # Ensure event is set, avoid dead wait
                    break
        
        # Cleanup - use try-finally to ensure cleanup always executes
        try:
            # Cleanup logic
            self.connected_servers.pop(name, None)
            self._server_tasks.pop(name, None)
            self._connection_events.pop(name, None)
            if self.debug:
                print(f"  - Server {name} fully disconnected")
        except Exception as e:
            if self.debug:
                print(f"  - Server {name} error during cleanup: {e}")
            # Even if cleanup fails, continue, ensure state is cleaned up
            self.connected_servers.pop(name, None)
            self._server_tasks.pop(name, None)
            self._connection_events.pop(name, None)

    async def connect_servers(self, server_names: Optional[List[str]] = None, 
                             max_connect_retries: int = 3, connect_retry_delay: float = 2.0):
        """Connect specified servers"""
        if server_names is None:
            server_names = list(self.servers.keys())

        async with self._lock:
            tasks_to_wait = []
            
            for name in server_names:
                if name not in self.servers:
                    print(f"Warning: Server '{name}' not found")
                    continue
                    
                if name in self._server_tasks:
                    if self.debug:
                        print(f"Server '{name}' is already running, skipping")
                    continue
                
                server = self.servers[name]
                
                # Create connection completion event
                event = asyncio.Event()
                self._connection_events[name] = event
                
                # Create task to manage server lifecycle
                task = asyncio.create_task(
                    self._manage_server_lifecycle(name, server, max_connect_retries, connect_retry_delay),
                    name=f"mcp_server_{name}"
                )
                self._server_tasks[name] = task
                tasks_to_wait.append((name, event))
            
            # Wait for all servers to connect
            if tasks_to_wait:
                if self.debug:
                    print(f">>Connecting {len(tasks_to_wait)} servers...")
                
                # Wait for all connection events
                wait_tasks = [event.wait() for name, event in tasks_to_wait]
                await asyncio.gather(*wait_tasks)
                
                # Verify connection
                connected_count = sum(1 for name, _ in tasks_to_wait if name in self.connected_servers)
                if self.debug:
                    print(f">>Successfully connected {connected_count}/{len(tasks_to_wait)} MCP servers")
                if connected_count != len(tasks_to_wait):
                    print(f"Warning: Only {connected_count} servers connected, expected {len(tasks_to_wait)}")
                    raise ValueError(f"Only {connected_count} servers connected, expected {len(tasks_to_wait)}")

    async def disconnect_servers(self, server_names: Optional[List[str]] = None, 
                                max_disconnect_retries: int = 3, disconnect_retry_delay: float = 1.0):
        """Disconnect specified servers"""
        async with self._lock:
            if server_names is None:
                servers_to_disconnect = list(self._server_tasks.keys())
            else:
                servers_to_disconnect = [
                    name for name in server_names 
                    if name in self._server_tasks
                ]
            
            if not servers_to_disconnect:
                if self.debug:
                    print("No servers to disconnect")
                return
            
            if self.debug:
                print(f">>Disconnecting {len(servers_to_disconnect)} servers...")
            
            # Record tasks to disconnect, for later statistics
            tasks_to_cancel = []
            for name in servers_to_disconnect:
                if task := self._server_tasks.get(name):
                    task.cancel()
                    tasks_to_cancel.append((name, task))
            
            # Immediately remove servers from connected list, avoid inconsistent state
            for name in servers_to_disconnect:
                self.connected_servers.pop(name, None)
            
            # Wait for all tasks to complete cleanup, with retry mechanism
            if tasks_to_cancel:
                last_disconnect_exception = None
                for disconnect_attempt in range(max_disconnect_retries + 1):
                    try:
                        # Use timeout to avoid infinite wait
                        try:
                            # Extract task objects to wait
                            tasks_only = [task for name, task in tasks_to_cancel]
                            await asyncio.wait_for(
                                asyncio.gather(*tasks_only, return_exceptions=True),
                                timeout=10.0  # 10 seconds timeout
                            )
                        except asyncio.TimeoutError:
                            if self.debug:
                                print(f"Waiting for tasks to complete timeout (attempt {disconnect_attempt + 1}/{max_disconnect_retries + 1})")
                        
                        # Verify if all tasks are completed
                        still_running = [
                            name for name, task in tasks_to_cancel 
                            if not task.done()
                        ]
                        if not still_running:
                            if self.debug:
                                print(f"All servers disconnected successfully (attempt {disconnect_attempt + 1}/{max_disconnect_retries + 1})")
                            break
                        else:
                            if disconnect_attempt < max_disconnect_retries:
                                if self.debug:
                                    print(f"Some servers disconnected failed, still have {len(still_running)} tasks running")
                                    print(f"Waiting {disconnect_retry_delay} seconds to retry disconnect...")
                                await asyncio.sleep(disconnect_retry_delay)
                            else:
                                print(f"Disconnect operation failed, still have {len(still_running)} tasks running")
                                # Force cleanup remaining tasks
                                for name in still_running:
                                    if task := self._server_tasks.get(name):
                                        if not task.done():
                                            task.cancel()
                    except Exception as e:
                        last_disconnect_exception = e
                        if disconnect_attempt < max_disconnect_retries:
                            if self.debug:
                                print(f"Disconnect operation failed (attempt {disconnect_attempt + 1}/{max_disconnect_retries + 1}): {e}")
                                print(f"Waiting {disconnect_retry_delay} seconds to retry disconnect...")
                            await asyncio.sleep(disconnect_retry_delay)
                        else:
                            print(f"Disconnect operation failed (attempt {max_disconnect_retries + 1} times): {e}")
            
            if self.debug:
                # Count actual disconnected servers
                disconnected_count = 0
                for name, task in tasks_to_cancel:
                    if task.done():
                        disconnected_count += 1
                
                print(f">>Disconnected {disconnected_count}/{len(servers_to_disconnect)} MCP servers")

    async def ensure_all_disconnected(self, max_cleanup_retries: int = 3, cleanup_retry_delay: float = 1.0):
        """Ensure all servers are disconnected (for cleanup)"""
        # Try to disconnect normally first
        await self.disconnect_servers(max_disconnect_retries=max_cleanup_retries, 
                                     disconnect_retry_delay=cleanup_retry_delay)
        
        # Force cancel all remaining tasks
        remaining_tasks = list(self._server_tasks.values())
        if remaining_tasks:
            for task in remaining_tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for all tasks to complete, with retry mechanism
            for cleanup_attempt in range(max_cleanup_retries + 1):
                try:
                    # Use timeout to avoid infinite wait
                    try:
                        await asyncio.wait_for(
                            asyncio.gather(*remaining_tasks, return_exceptions=True),
                            timeout=10.0  # 10 seconds timeout
                        )
                    except asyncio.TimeoutError:
                        if self.debug:
                            print(f"Waiting for cleanup tasks to complete timeout (attempt {cleanup_attempt + 1}/{max_cleanup_retries + 1})")
                    
                    if not self._server_tasks:  # If all tasks are cleaned up
                        break
                    elif cleanup_attempt < max_cleanup_retries:
                        if self.debug:
                            print(f"Cleanup tasks failed (attempt {cleanup_attempt + 1}/{max_cleanup_retries + 1})")
                            print(f"Waiting {cleanup_retry_delay} seconds to retry cleanup...")
                        await asyncio.sleep(cleanup_retry_delay)
                    else:
                        print(f"Cleanup tasks failed (attempt {max_cleanup_retries + 1} times)")
                except Exception as e:
                    if cleanup_attempt < max_cleanup_retries:
                        if self.debug:
                            print(f"Cleanup tasks failed (attempt {cleanup_attempt + 1}/{max_cleanup_retries + 1}): {e}")
                            print(f"Waiting {cleanup_retry_delay} seconds to retry cleanup...")
                        await asyncio.sleep(cleanup_retry_delay)
                    else:
                        print(f"Cleanup tasks failed (attempt {max_cleanup_retries + 1} times): {e}")
        
        # Force cleanup all states
        self._server_tasks.clear()
        self.connected_servers.clear()
        self._connection_events.clear()

    def get_all_connected_servers(self) -> List[Union[MCPServerStdio, MCPServerSse]]:
        """Get all connected server instances"""
        return list(self.connected_servers.values())

    def get_connected_server_names(self) -> List[str]:
        """Get all connected server names"""
        return list(self.connected_servers.keys())

    def get_available_servers(self) -> List[str]:
        """Get all available server names (including not connected ones)"""
        return list(self.servers.keys())
    
    def is_server_connected(self, server_name: str) -> bool:
        """Check if specified server is connected"""
        return server_name in self.connected_servers

    def list_available_template_variables(self):
        """List all available template variables (for debugging)"""
        vars = self._get_template_variables()
        print("Available template variables:")
        for key, value in sorted(vars.items()):
            print(f"  ${{{key}}} = {value}")

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.ensure_all_disconnected(max_cleanup_retries=3, cleanup_retry_delay=1.0)


async def call_tool_with_retry(server, tool_name: str, arguments: dict, retry_time: int = 5, delay: float = 1.0):
    """
    Tool call function with retry mechanism
    
    Args:
        server: MCP server instance
        tool_name: Tool name
        arguments: Tool arguments
        retry_time: Retry times, default 5 times
        delay: Retry interval (seconds), default 1 second
    
    Returns:
        Tool call result
    
    Raises:
        ToolCallError: All retries failed and throw tool call error
    """
    last_exception = None
    
    for attempt in range(retry_time + 1):  # +1 because the first attempt is not a retry
        try:
            result = await server.call_tool(tool_name=tool_name, arguments=arguments)
            return result
        except Exception as e:
            last_exception = e
            if attempt < retry_time:  # If not the last attempt
                print(f"Tool call failed (attempt {attempt + 1}/{retry_time + 1}): {e}")
                print(f"Waiting {delay} seconds to retry...")
                await asyncio.sleep(delay)
            else:
                print(f"Tool call failed (attempt {retry_time + 1} times): {e}")
    
    # All retries failed, throw ToolCallError
    raise ToolCallError(f"Tool call failed: {tool_name}", last_exception)