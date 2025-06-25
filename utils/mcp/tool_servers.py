from typing import List, Dict, Optional, Union, Any
import asyncio
import os
import yaml
from pathlib import Path

from agents.mcp import MCPServerStdio, MCPServerSse
from configs.global_configs import global_configs
from configs.token_key_session import all_token_key_session

class MCPServerManager:
    """MCP 服务器管理器，用于初始化和管理多个 MCP 服务器"""

    def __init__(self, 
                 agent_workspace: str, 
                 config_dir: str = "configs/mcp_servers",
                 debug: bool = False):
        """
        初始化 MCP 服务器管理器
        
        Args:
            agent_workspace: 代理工作空间路径
            config_dir: 配置文件目录路径
        """
        self.local_servers_paths = os.path.abspath("./local_servers")
        self.agent_workspace = os.path.abspath(agent_workspace)
        self.servers: Dict[str, Union[MCPServerStdio, MCPServerSse]] = {}
        self.connected_servers: Dict[str, Union[MCPServerStdio, MCPServerSse]] = {}
        self.debug = debug
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
        }
        
        # 动态添加 global_configs 中的所有属性
        for key, value in global_configs.items():
            if isinstance(value, (str, int, float, bool)):  # 只处理基本类型
                template_vars[f'config.{key}'] = str(value)
        
        # 动态添加 all_token_key_session 中的所有属性
        for key, value in all_token_key_session.items():
            if isinstance(value, (str, int, float, bool)):  # 只处理基本类型
                template_vars[f'token.{key}'] = str(value)
        
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

    async def _manage_server_lifecycle(self, name: str, server: Union[MCPServerStdio, MCPServerSse]):
        """在单个任务中管理服务器的完整生命周期"""
        event = self._connection_events.get(name)
        try:
            async with server:  # 使用服务器的上下文管理器，这会自动调用 connect()
                # 连接成功后，添加到已连接列表
                self.connected_servers[name] = server
                
                # 设置连接完成事件
                if event:
                    event.set()
                
                if self.debug:
                    print(f"  - 服务器 {name} 已连接")
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
                    
        except asyncio.CancelledError:
            # 预期的取消，不记录为错误
            pass
        except Exception as e:
            print(f"服务器 {name} 生命周期管理出错: {e}")
            if event and not event.is_set():
                event.set()  # 确保事件被设置，避免死等
        finally:
            # 清理
            self.connected_servers.pop(name, None)
            self._server_tasks.pop(name, None)
            self._connection_events.pop(name, None)
            if self.debug:
                print(f"  - 服务器 {name} 已完全断开")

    async def connect_servers(self, server_names: Optional[List[str]] = None):
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
                    self._manage_server_lifecycle(name, server),
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

    async def disconnect_servers(self, server_names: Optional[List[str]] = None):
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
            
            # 取消任务，这会触发服务器的清理
            tasks_to_cancel = []
            for name in servers_to_disconnect:
                if task := self._server_tasks.get(name):
                    task.cancel()
                    tasks_to_cancel.append(task)
            
            # 等待所有任务完成清理
            if tasks_to_cancel:
                await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
            
            if self.debug:
                disconnected_count = sum(
                    1 for name in servers_to_disconnect 
                    if name not in self.connected_servers
                )
                print(f">>已断开 {disconnected_count}/{len(servers_to_disconnect)} 个 MCP 服务器")

    async def ensure_all_disconnected(self):
        """确保所有服务器都已断开（用于清理）"""
        # 先尝试正常断开
        await self.disconnect_servers()
        
        # 强制取消所有剩余的任务
        remaining_tasks = list(self._server_tasks.values())
        if remaining_tasks:
            for task in remaining_tasks:
                if not task.done():
                    task.cancel()
            
            # 等待所有任务完成
            await asyncio.gather(*remaining_tasks, return_exceptions=True)
        
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
        """异步上下文管理器出口，自动断开所有连接"""
        await self.ensure_all_disconnected()