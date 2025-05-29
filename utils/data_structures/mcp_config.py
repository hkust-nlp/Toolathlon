from dataclasses import dataclass

@dataclass
class MCPConfig:
    """MCP配置"""
    server_config_path: str = None

    @classmethod
    def from_dict(cls, data: dict) -> 'MCPConfig':
        """从字典创建MCPConfig实例"""
        return cls(
            server_config_path=data['server_config_path'],
        )