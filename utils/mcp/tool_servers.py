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

    def __init__(self, agent_workspace: str, config_dir: str = "configs/mcp_servers"):
        """
        初始化 MCP 服务器管理器
        
        Args:
            agent_workspace: 代理工作空间路径
            config_dir: 配置文件目录路径
        """
        self.local_servers_paths = os.path.abspath("./local_servers")
        self.agent_workspace = os.path.abspath(agent_workspace)
        self.servers: Dict[str, Union[MCPServerStdio, MCPServerSse]] = {}
        self.connected_servers = []
        
        # 从配置文件加载服务器
        self._load_servers_from_configs(config_dir)

    def _load_servers_from_configs(self, config_dir: str):
        """从配置文件目录加载服务器配置"""
        config_path = Path(config_dir)
        if not config_path.exists():
            raise ValueError(f"配置目录不存在: {config_dir}")
        
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

    async def connect_servers(self, server_names: Optional[List[str]] = None):
        """连接指定的服务器"""
        if server_names is None:
            server_names = list(self.servers.keys())

        connect_tasks = []
        for name in server_names:
            if name in self.servers:
                try:
                    connect_tasks.append(self.servers[name].connect())
                    self.connected_servers.append(self.servers[name])
                except Exception as e:
                    print(f"服务器 {name} 连接失败: {e}")
            else:
                print(f"警告: 未找到名为 '{name}' 的服务器")

        if connect_tasks:
            await asyncio.gather(*connect_tasks)
            print(f">>已成功连接 {len(connect_tasks)} 个 MCP 服务器")

    async def disconnect_servers(self):
        """断开所有服务器连接"""
        disconnect_tasks = []
        for server in self.connected_servers:
            disconnect_tasks.append(server.cleanup())

        if disconnect_tasks:
            await asyncio.gather(*disconnect_tasks)
            print(f">>已断开 {len(disconnect_tasks)} 个 MCP 服务器连接")

    def get_all_connected_servers(self):
        return self.connected_servers

    def get_available_servers(self) -> List[str]:
        return list(self.servers.keys())
    
    def list_available_template_variables(self):
        """列出所有可用的模板变量（调试用）"""
        vars = self._get_template_variables()
        print("可用的模板变量:")
        for key, value in sorted(vars.items()):
            print(f"  ${{{key}}} = {value}")