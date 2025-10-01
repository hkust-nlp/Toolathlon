"""
OpenHands MCP Configuration Converter

This module provides utilities to convert mcpbench_dev's YAML-based MCP server
configurations to OpenHands SDK's expected Dict format.

Key Features:
- Load YAML configs from configs/mcp_servers/
- Process template variables (${agent_workspace}, ${token.*}, etc.)
- Convert to OpenHands mcpServers format
- Maintain compatibility with existing YAML configuration system

Usage:
    from utils.mcp.openhands_mcp_config import create_openhands_mcp_config

    mcp_config = create_openhands_mcp_config(
        agent_workspace="/path/to/workspace",
        config_dir="configs/mcp_servers",
        server_names=["filesystem", "github", "playwright_with_chunk"],
        local_token_key_session={...}
    )

    # Use with OpenHands Agent
    agent = Agent(llm=llm, tools=[], mcp_config=mcp_config)
"""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any

from configs.global_configs import global_configs
from configs.token_key_session import all_token_key_session


def _get_template_variables(
    agent_workspace: str,
    local_token_key_session: Optional[Dict] = None
) -> Dict[str, str]:
    """
    Get all available template variables for YAML config processing

    This replicates MCPServerManager._get_template_variables() logic
    to maintain compatibility with existing YAML configs.

    Args:
        agent_workspace: Path to agent workspace directory
        local_token_key_session: Task-specific tokens (overrides global tokens)

    Returns:
        Dict mapping template variable names to values
    """
    local_servers_paths = os.path.abspath("./local_servers")
    local_binary_paths = os.path.abspath("./local_binary")

    template_vars = {
        # Basic path variables
        'agent_workspace': os.path.abspath(agent_workspace),
        'local_servers_paths': local_servers_paths,
        'local_binary_paths': local_binary_paths,
        'podman_or_docker': global_configs.podman_or_docker,
    }

    # Dynamically add all attributes in global_configs
    for key, value in global_configs.items():
        if isinstance(value, (str, int, float, bool)):
            template_vars[f'config.{key}'] = str(value)

    # Dynamically add all attributes in all_token_key_session
    for key, value in all_token_key_session.items():
        if isinstance(value, (str, int, float, bool)):
            template_vars[f'token.{key}'] = str(value)

    # Override with local_token_key_session
    if local_token_key_session is not None:
        for key, value in local_token_key_session.items():
            if isinstance(value, (str, int, float, bool)):
                template_vars[f'token.{key}'] = str(value)

    return template_vars


def _process_template_variables(
    obj: Any,
    template_vars: Dict[str, str]
) -> Any:
    """
    Recursively replace template variables in configuration

    Replaces ${var_name} patterns with values from template_vars.

    Args:
        obj: Configuration object (str, list, dict, or primitive)
        template_vars: Mapping of variable names to values

    Returns:
        Object with template variables replaced
    """
    if isinstance(obj, str):
        # Replace all ${var_name} patterns
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
        return [_process_template_variables(item, template_vars) for item in obj]

    elif isinstance(obj, dict):
        return {k: _process_template_variables(v, template_vars) for k, v in obj.items()}

    else:
        return obj


def _load_yaml_config(
    config_file: Path,
    template_vars: Dict[str, str]
) -> Optional[Dict[str, Any]]:
    """
    Load and process a single YAML config file

    Args:
        config_file: Path to YAML config file
        template_vars: Template variables for substitution

    Returns:
        Processed config dict or None if loading fails
    """
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if not config:
                return None

            # Process template variables in params
            if 'params' in config:
                config['params'] = _process_template_variables(
                    config['params'],
                    template_vars
                )

            return config

    except Exception as e:
        print(f"Warning: Failed to load config file {config_file}: {e}")
        return None


def _convert_to_openhands_format(
    yaml_config: Dict[str, Any],
    server_name: str
) -> Dict[str, Any]:
    """
    Convert a single YAML config to OpenHands mcpServers format

    YAML format:
        type: stdio
        name: filesystem
        params:
          command: npx
          args: ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]
          env:
            GITHUB_TOKEN: "ghp_xxx"

    OpenHands format:
        {
          "command": "npx",
          "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"],
          "env": {"GITHUB_TOKEN": "ghp_xxx"}
        }

    Args:
        yaml_config: Loaded YAML configuration
        server_name: Name of the server

    Returns:
        OpenHands-compatible server configuration
    """
    server_type = yaml_config.get('type', 'stdio').lower()
    params = yaml_config.get('params', {})

    # Specialized preprocessing for playwright_with_chunk
    if server_name == 'playwright_with_chunk':
        # If current user is root, add --no-sandbox
        if os.geteuid() == 0:
            if 'args' in params:
                params['args'].append('--no-sandbox')

    if server_type == 'stdio':
        # Stdio server: use command + args format
        openhands_config = {}

        if 'command' in params:
            openhands_config['command'] = params['command']

        if 'args' in params:
            openhands_config['args'] = params['args']

        if 'env' in params:
            openhands_config['env'] = params['env']

        return openhands_config

    elif server_type == 'sse':
        # SSE server: use url format
        openhands_config = {}

        if 'url' in params:
            openhands_config['url'] = params['url']

        if 'auth' in params:
            openhands_config['auth'] = params['auth']

        return openhands_config

    else:
        raise ValueError(f"Unsupported server type: {server_type}")


def create_openhands_mcp_config(
    agent_workspace: str,
    config_dir: str = "configs/mcp_servers",
    server_names: Optional[List[str]] = None,
    local_token_key_session: Optional[Dict] = None,
    debug: bool = False
) -> Dict[str, Any]:
    """
    Create OpenHands-compatible MCP configuration from YAML files

    This function:
    1. Loads YAML configs from config_dir
    2. Processes template variables (${agent_workspace}, ${token.*}, etc.)
    3. Converts to OpenHands mcpServers Dict format
    4. Returns ready-to-use config for OpenHands Agent

    Args:
        agent_workspace: Path to agent workspace directory
        config_dir: Directory containing YAML config files
        server_names: List of server names to include (None = all)
        local_token_key_session: Task-specific tokens (overrides global)
        debug: Enable debug output

    Returns:
        OpenHands MCP configuration in format:
        {
            "mcpServers": {
                "filesystem": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]
                },
                "github": {
                    "command": "/path/to/github-mcp-server",
                    "args": ["stdio"],
                    "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxx"}
                },
                ...
            }
        }

    Example:
        >>> mcp_config = create_openhands_mcp_config(
        ...     agent_workspace="/tasks/task001/workspace",
        ...     server_names=["filesystem", "github"]
        ... )
        >>> agent = Agent(llm=llm, tools=[], mcp_config=mcp_config)
    """
    config_path = Path(config_dir)
    if not config_path.exists():
        raise ValueError(f"Configuration directory does not exist: {config_dir}")

    # Get template variables
    template_vars = _get_template_variables(agent_workspace, local_token_key_session)

    if debug:
        print(f"Loading MCP configs from: {config_dir}")
        print(f"Agent workspace: {agent_workspace}")

    # Load all YAML configs
    yaml_configs: Dict[str, Dict[str, Any]] = {}

    for config_file in config_path.glob("*.yaml"):
        config = _load_yaml_config(config_file, template_vars)
        if config:
            name = config.get('name', config_file.stem)
            yaml_configs[name] = config

    if debug:
        print(f"Loaded {len(yaml_configs)} YAML configs")

    # Filter by server_names if specified
    if server_names is not None:
        yaml_configs = {
            name: config for name, config in yaml_configs.items()
            if name in server_names
        }

        if debug:
            print(f"Filtered to {len(yaml_configs)} servers: {list(yaml_configs.keys())}")

    # Convert to OpenHands format
    mcp_servers = {}

    for name, yaml_config in yaml_configs.items():
        try:
            openhands_config = _convert_to_openhands_format(yaml_config, name)
            mcp_servers[name] = openhands_config

            if debug:
                print(f"Converted server '{name}': {openhands_config}")

        except Exception as e:
            print(f"Warning: Failed to convert config for '{name}': {e}")
            continue

    if debug:
        print(f"Successfully converted {len(mcp_servers)} servers to OpenHands format")

    return {
        "mcpServers": mcp_servers
    }


def create_openhands_mcp_tools(
    agent_workspace: str,
    config_dir: str = "configs/mcp_servers",
    server_names: Optional[List[str]] = None,
    local_token_key_session: Optional[Dict] = None,
    timeout: float = 30.0,
    debug: bool = False
):
    """
    Create OpenHands MCP tools from YAML configs (convenience wrapper)

    This is a high-level wrapper that:
    1. Creates OpenHands MCP config from YAML files
    2. Calls OpenHands SDK's create_mcp_tools()
    3. Returns ready-to-use tool list

    Args:
        agent_workspace: Path to agent workspace directory
        config_dir: Directory containing YAML config files
        server_names: List of server names to include (None = all)
        local_token_key_session: Task-specific tokens
        timeout: Timeout for MCP server connections (seconds)
        debug: Enable debug output

    Returns:
        List[MCPTool] ready for use with OpenHands Agent

    Example:
        >>> tools = create_openhands_mcp_tools(
        ...     agent_workspace="/tasks/task001/workspace",
        ...     server_names=["filesystem", "github"]
        ... )
        >>> agent = Agent(llm=llm, tools=tools)
    """
    # Import OpenHands SDK
    try:
        from openhands.sdk.mcp.utils import create_mcp_tools
    except ImportError:
        # Try fallback path
        import sys
        from pathlib import Path
        agent_sdk_path = Path(__file__).parent.parent.parent.parent / 'agent-sdk'
        if agent_sdk_path.exists():
            sys.path.insert(0, str(agent_sdk_path))
        from openhands.sdk.mcp.utils import create_mcp_tools

    # Create config
    mcp_config = create_openhands_mcp_config(
        agent_workspace=agent_workspace,
        config_dir=config_dir,
        server_names=server_names,
        local_token_key_session=local_token_key_session,
        debug=debug
    )

    # Create tools using OpenHands SDK
    if debug:
        print(f"Creating MCP tools with timeout={timeout}s...")

    tools = create_mcp_tools(mcp_config, timeout=timeout)

    if debug:
        print(f"Created {len(tools)} MCP tools: {[t.name for t in tools]}")

    return tools
