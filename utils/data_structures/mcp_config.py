from dataclasses import dataclass

@dataclass
class MCPConfig:
    """MCP configuration"""
    server_config_path: str = None

    @classmethod
    def from_dict(cls, data: dict) -> 'MCPConfig':
        """Create MCPConfig instance from dictionary"""
        return cls(
            server_config_path=data['server_config_path'],
        )