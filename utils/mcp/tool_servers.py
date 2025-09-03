from typing import List, Dict, Optional, Union, Any
import asyncio
import os
import yaml
from pathlib import Path

from agents.mcp import MCPServerStdio, MCPServerSse
from configs.global_configs import global_configs
from configs.token_key_session import all_token_key_session


class ToolCallError(Exception):
    """工具调用错误的自定义异常类型"""
    def __init__(self, message: str, original_exception: Exception = None):
        self.message = message
        self.original_exception = original_exception
        super().__init__(self.message)

class MCPServerManager:
    """MCP 服务器管理器，用于初始化和管理多个 MCP 服务器"""

    def __init__(self, 
                 agent_workspace: str, 
                 config_dir: str = "configs/mcp_servers",
                 debug: bool = False,
                 local_token_key_session: Dict = None):
        """
        初始化 MCP 服务器管理器
        
        Args:
            agent_workspace: 代理工作空间路径
            config_dir: 配置文件目录路径
        """
        self.local_servers_paths = os.path.abspath("./local_servers")
        self.local_binary_paths = os.path.abspath("./local_binary")
        self.agent_workspace = os.path.abspath(agent_workspace)
        self.servers: Dict[str, Union[MCPServerStdio, MCPServerSse]] = {}
        self.connected_servers: Dict[str, Union[MCPServerStdio, MCPServerSse]] = {}
        self.debug = debug
        self.local_token_key_session = local_token_key_session
        self._lock = asyncio.Lock()
        # 保存每个服务器的任务，确保在同一个任务中管理生命周期
        self._server_tasks: Dict[str, asyncio.Task] = {}
        # 保存连接完成的事件
        self._connection_events: Dict[str, asyncio.Event] = {}
        
        # 从配置文件加载服务器
        self._load_servers_from_configs(config_dir)

    def _load_servers_from_configs(self, config_dir: str):
        """从配置文件目录加载服务器配置"""
        config_path = Path(config_dir)
        if not config_path.exists():
            raise ValueError(f"配置目录不存在: {config_dir}")
        
        if self.debug:
            print(f">>从配置目录加载服务器: {config_dir}")
            print(f">>servers工作区: {self.agent_workspace}")
        
        # 读取所有 yaml 配置文件
        for config_file in config_path.glob("*.yaml"):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    if config:
                        self._initialize_server_from_config(config, config_file.stem)
            except Exception as e:
                print(f"加载配置文件 {config_file} 失败: {e}")

    def _initialize_server_from_config(self, config: Dict[str, Any], default_name: str):
        """从配置字典初始化单个服务器"""
        server_type = config.get('type', 'stdio').lower()
        server_name = config.get('name', default_name)
        
        # 处理参数中的模板变量
        params = self._process_config_params(config.get('params', {}))
        
        # 创建服务器实例
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
            raise ValueError(f"不支持的服务器类型: {server_type}")
        
        self.servers[server_name] = server
        if self.debug:
            print(f"  - 已预加载服务器: {server_name} (类型: {server_type})")

    def _get_template_variables(self) -> Dict[str, str]:
        """动态获取所有可用的模板变量"""
        template_vars = {
            # 基本路径变量
            'agent_workspace': self.agent_workspace,
            'local_servers_paths': self.local_servers_paths,
            'local_binary_paths': self.local_binary_paths,
            'podman_or_docker': global_configs.podman_or_docker,
        }
        
        # 动态添加 global_configs 中的所有属性
        for key, value in global_configs.items():
            if isinstance(value, (str, int, float, bool)):  # 只处理基本类型
                template_vars[f'config.{key}'] = str(value)
        
        # 动态添加 all_token_key_session 中的所有属性
        for key, value in all_token_key_session.items():
            if isinstance(value, (str, int, float, bool)):  # 只处理基本类型
                template_vars[f'token.{key}'] = str(value)
        
        # 用local_token_key_session 覆盖 all_token_key_session
        # 并加上提示信息
        if self.local_token_key_session is not None:
            for key, value in self.local_token_key_session.items():
                if isinstance(value, (str, int, float, bool)):  # 只处理基本类型
                    template_vars[f'token.{key}'] = str(value)
                    # print(f"  - 已覆盖 token.{key} = {value}")
        
        return template_vars

    def _process_config_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理配置参数中的模板变量"""
        template_vars = self._get_template_variables()
        
        def replace_templates(obj):
            if isinstance(obj, str):
                # 使用正则表达式替换所有的模板变量
                import re
                pattern = r'\$\{([^}]+)\}'
                
                def replacer(match):
                    var_name = match.group(1)
                    if var_name in template_vars:
                        return template_vars[var_name]
                    else:
                        print(f"警告: 未找到模板变量 '{var_name}'")
                        return match.group(0)  # 保持原样
                
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
        """在单个任务中管理服务器的完整生命周期"""
        event = self._connection_events.get(name)
        last_connect_exception = None
        
        # 连接重试逻辑
        for connect_attempt in range(max_connect_retries + 1):
            try:
                async with server:  # 使用服务器的上下文管理器，这会自动调用 connect()
                    # 连接成功后，添加到已连接列表
                    self.connected_servers[name] = server
                    
                    # 设置连接完成事件
                    if event:
                        event.set()
                    
                    if self.debug:
                        print(f"  - 服务器 {name} 已连接 (尝试 {connect_attempt + 1}/{max_connect_retries + 1})")
                        # 尝试获取工具列表以验证连接
                        try:
                            tools = await server.list_tools()
                            print(f"    可用工具数: {len(tools)}")
                        except Exception as e:
                            print(f"    获取工具列表失败: {e}")
                    
                    # 保持连接，直到任务被取消
                    try:
                        await asyncio.sleep(float('inf'))  # 无限等待
                    except asyncio.CancelledError:
                        # 正常取消，进行清理
                        if self.debug:
                            print(f"  - 正在断开服务器 {name}")
                        raise  # 重新抛出以触发 __aexit__
                    
                    # 如果连接成功，跳出重试循环
                    break
                    
            except asyncio.CancelledError:
                # 预期的取消，不记录为错误
                raise
            except Exception as e:
                last_connect_exception = e
                if connect_attempt < max_connect_retries:
                    if self.debug:
                        print(f"服务器 {name} 连接失败 (尝试 {connect_attempt + 1}/{max_connect_retries + 1}): {e}")
                        print(f"等待 {connect_retry_delay} 秒后重试连接...")
                    await asyncio.sleep(connect_retry_delay)
                else:
                    print(f"服务器 {name} 连接最终失败 (已尝试 {max_connect_retries + 1} 次): {e}")
                    if event and not event.is_set():
                        event.set()  # 确保事件被设置，避免死等
                    break
        
        # 清理 - 使用 try-finally 确保清理总是执行
        try:
            # 清理逻辑
            self.connected_servers.pop(name, None)
            self._server_tasks.pop(name, None)
            self._connection_events.pop(name, None)
            if self.debug:
                print(f"  - 服务器 {name} 已完全断开")
        except Exception as e:
            if self.debug:
                print(f"  - 服务器 {name} 清理时出错: {e}")
            # 即使清理出错也要继续，确保状态被清理
            self.connected_servers.pop(name, None)
            self._server_tasks.pop(name, None)
            self._connection_events.pop(name, None)

    async def connect_servers(self, server_names: Optional[List[str]] = None, 
                             max_connect_retries: int = 3, connect_retry_delay: float = 2.0):
        """连接指定的服务器"""
        if server_names is None:
            server_names = list(self.servers.keys())

        async with self._lock:
            tasks_to_wait = []
            
            for name in server_names:
                if name not in self.servers:
                    print(f"警告: 未找到名为 '{name}' 的服务器")
                    continue
                    
                if name in self._server_tasks:
                    if self.debug:
                        print(f"服务器 '{name}' 已在运行，跳过")
                    continue
                
                server = self.servers[name]
                
                # 创建连接完成事件
                event = asyncio.Event()
                self._connection_events[name] = event
                
                # 创建任务来管理服务器生命周期
                task = asyncio.create_task(
                    self._manage_server_lifecycle(name, server, max_connect_retries, connect_retry_delay),
                    name=f"mcp_server_{name}"
                )
                self._server_tasks[name] = task
                tasks_to_wait.append((name, event))
            
            # 等待所有服务器连接完成
            if tasks_to_wait:
                if self.debug:
                    print(f">>正在连接 {len(tasks_to_wait)} 个服务器...")
                
                # 等待所有连接事件
                wait_tasks = [event.wait() for name, event in tasks_to_wait]
                await asyncio.gather(*wait_tasks)
                
                # 验证连接
                connected_count = sum(1 for name, _ in tasks_to_wait if name in self.connected_servers)
                if self.debug:
                    print(f">>已成功连接 {connected_count}/{len(tasks_to_wait)} 个 MCP 服务器")

    async def disconnect_servers(self, server_names: Optional[List[str]] = None, 
                                max_disconnect_retries: int = 3, disconnect_retry_delay: float = 1.0):
        """断开指定服务器连接"""
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
                    print("没有需要断开的服务器")
                return
            
            if self.debug:
                print(f">>正在断开 {len(servers_to_disconnect)} 个服务器...")
            
            # 记录要断开的任务，用于后续统计
            tasks_to_cancel = []
            for name in servers_to_disconnect:
                if task := self._server_tasks.get(name):
                    task.cancel()
                    tasks_to_cancel.append((name, task))
            
            # 立即从连接列表中移除服务器，避免状态不一致
            for name in servers_to_disconnect:
                self.connected_servers.pop(name, None)
            
            # 等待所有任务完成清理，带重试机制
            if tasks_to_cancel:
                last_disconnect_exception = None
                for disconnect_attempt in range(max_disconnect_retries + 1):
                    try:
                        # 使用超时等待，避免无限等待
                        try:
                            # 提取任务对象进行等待
                            tasks_only = [task for name, task in tasks_to_cancel]
                            await asyncio.wait_for(
                                asyncio.gather(*tasks_only, return_exceptions=True),
                                timeout=10.0  # 10秒超时
                            )
                        except asyncio.TimeoutError:
                            if self.debug:
                                print(f"等待任务完成超时 (尝试 {disconnect_attempt + 1}/{max_disconnect_retries + 1})")
                        
                        # 验证任务是否都已完成
                        still_running = [
                            name for name, task in tasks_to_cancel 
                            if not task.done()
                        ]
                        if not still_running:
                            if self.debug:
                                print(f"所有服务器断开成功 (尝试 {disconnect_attempt + 1}/{max_disconnect_retries + 1})")
                            break
                        else:
                            if disconnect_attempt < max_disconnect_retries:
                                if self.debug:
                                    print(f"部分服务器断开失败，仍有 {len(still_running)} 个任务运行中")
                                    print(f"等待 {disconnect_retry_delay} 秒后重试断开...")
                                await asyncio.sleep(disconnect_retry_delay)
                            else:
                                print(f"断开操作最终失败，仍有 {len(still_running)} 个任务运行中")
                                # 强制清理剩余的任务
                                for name in still_running:
                                    if task := self._server_tasks.get(name):
                                        if not task.done():
                                            task.cancel()
                    except Exception as e:
                        last_disconnect_exception = e
                        if disconnect_attempt < max_disconnect_retries:
                            if self.debug:
                                print(f"断开操作失败 (尝试 {disconnect_attempt + 1}/{max_disconnect_retries + 1}): {e}")
                                print(f"等待 {disconnect_retry_delay} 秒后重试...")
                            await asyncio.sleep(disconnect_retry_delay)
                        else:
                            print(f"断开操作最终失败 (已尝试 {max_disconnect_retries + 1} 次): {e}")
            
            if self.debug:
                # 统计实际断开的服务器数量
                disconnected_count = 0
                for name, task in tasks_to_cancel:
                    if task.done():
                        disconnected_count += 1
                
                print(f">>已断开 {disconnected_count}/{len(servers_to_disconnect)} 个 MCP 服务器")

    async def ensure_all_disconnected(self, max_cleanup_retries: int = 3, cleanup_retry_delay: float = 1.0):
        """确保所有服务器都已断开（用于清理）"""
        # 先尝试正常断开
        await self.disconnect_servers(max_disconnect_retries=max_cleanup_retries, 
                                     disconnect_retry_delay=cleanup_retry_delay)
        
        # 强制取消所有剩余的任务
        remaining_tasks = list(self._server_tasks.values())
        if remaining_tasks:
            for task in remaining_tasks:
                if not task.done():
                    task.cancel()
            
            # 等待所有任务完成，带重试机制
            for cleanup_attempt in range(max_cleanup_retries + 1):
                try:
                    # 使用超时等待，避免无限等待
                    try:
                        await asyncio.wait_for(
                            asyncio.gather(*remaining_tasks, return_exceptions=True),
                            timeout=10.0  # 10秒超时
                        )
                    except asyncio.TimeoutError:
                        if self.debug:
                            print(f"等待清理任务完成超时 (尝试 {cleanup_attempt + 1}/{max_cleanup_retries + 1})")
                    
                    if not self._server_tasks:  # 如果所有任务都已清理
                        break
                    elif cleanup_attempt < max_cleanup_retries:
                        if self.debug:
                            print(f"清理任务失败 (尝试 {cleanup_attempt + 1}/{max_cleanup_retries + 1})")
                            print(f"等待 {cleanup_retry_delay} 秒后重试清理...")
                        await asyncio.sleep(cleanup_retry_delay)
                    else:
                        print(f"清理任务最终失败 (已尝试 {max_cleanup_retries + 1} 次)")
                except Exception as e:
                    if cleanup_attempt < max_cleanup_retries:
                        if self.debug:
                            print(f"清理任务异常 (尝试 {cleanup_attempt + 1}/{max_cleanup_retries + 1}): {e}")
                            print(f"等待 {cleanup_retry_delay} 秒后重试清理...")
                        await asyncio.sleep(cleanup_retry_delay)
                    else:
                        print(f"清理任务最终异常 (已尝试 {max_cleanup_retries + 1} 次): {e}")
        
        # 强制清理所有状态
        self._server_tasks.clear()
        self.connected_servers.clear()
        self._connection_events.clear()

    def get_all_connected_servers(self) -> List[Union[MCPServerStdio, MCPServerSse]]:
        """获取所有已连接的服务器实例"""
        return list(self.connected_servers.values())

    def get_connected_server_names(self) -> List[str]:
        """获取所有已连接的服务器名称"""
        return list(self.connected_servers.keys())

    def get_available_servers(self) -> List[str]:
        """获取所有可用的服务器名称（包括未连接的）"""
        return list(self.servers.keys())
    
    def is_server_connected(self, server_name: str) -> bool:
        """检查指定服务器是否已连接"""
        return server_name in self.connected_servers

    def list_available_template_variables(self):
        """列出所有可用的模板变量（调试用）"""
        vars = self._get_template_variables()
        print("可用的模板变量:")
        for key, value in sorted(vars.items()):
            print(f"  ${{{key}}} = {value}")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.ensure_all_disconnected(max_cleanup_retries=3, cleanup_retry_delay=1.0)


async def call_tool_with_retry(server, tool_name: str, arguments: dict, retry_time: int = 5, delay: float = 1.0):
    """
    带重试机制的工具调用函数
    
    Args:
        server: MCP服务器实例
        tool_name: 工具名称
        arguments: 工具参数
        retry_time: 重试次数，默认5次
        delay: 重试间隔（秒），默认1秒
    
    Returns:
        工具调用结果
    
    Raises:
        ToolCallError: 所有重试都失败后抛出工具调用错误
    """
    last_exception = None
    
    for attempt in range(retry_time + 1):  # +1 是因为第一次不算重试
        try:
            result = await server.call_tool(tool_name=tool_name, arguments=arguments)
            return result
        except Exception as e:
            last_exception = e
            if attempt < retry_time:  # 如果不是最后一次尝试
                print(f"工具调用失败 (尝试 {attempt + 1}/{retry_time + 1}): {e}")
                print(f"等待 {delay} 秒后重试...")
                await asyncio.sleep(delay)
            else:
                print(f"工具调用最终失败 (已尝试 {retry_time + 1} 次): {e}")
    
    # 所有重试都失败了，抛出ToolCallError
    raise ToolCallError(f"工具调用失败: {tool_name}", last_exception)