#!/usr/bin/env python3
"""
Standalone MCP Tool Tester

This script allows you to test individual MCP tools without running the entire task framework.
You can list available servers, list tools for a server, and call specific tools with arguments.

IMPORTANT: This script must be run with uv to ensure proper dependencies are available.

Usage:
    uv run --active python test_mcp_tool.py list-servers
    uv run --active python test_mcp_tool.py list-tools --server terminal
    uv run --active python test_mcp_tool.py call-tool --server terminal --tool run_command --args '{"command": "ls -la"}'
    uv run --active python test_mcp_tool.py call-tool --server filesystem --tool read_file --args '{"path": "./README.md"}'
    uv run --active python test_mcp_tool.py call-tool --server googlesearch --tool search --args '{"query": "artificial intelligence latest news"}'
"""

import asyncio
import argparse
import json
import sys
import os
from pathlib import Path
from typing import Dict, Any

# Add the project root to the path so we can import utils
sys.path.append(str(Path(__file__).parent))

from utils.mcp.tool_servers import MCPServerManager, call_tool_with_retry, ToolCallError


class MCPToolTester:
    def __init__(self, workspace: str = "./", config_dir: str = "configs/mcp_servers", debug: bool = False):
        self.workspace = os.path.abspath(workspace)
        self.config_dir = config_dir
        self.debug = debug
        self.manager = None

    async def initialize_manager(self):
        """Initialize the MCP server manager"""
        try:
            self.manager = MCPServerManager(
                agent_workspace=self.workspace,
                config_dir=self.config_dir,
                debug=self.debug
            )
            print(f"✅ Initialized MCP Manager with workspace: {self.workspace}")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize MCP manager: {e}")
            return False

    async def list_servers(self):
        """List all available MCP servers"""
        if not await self.initialize_manager():
            return

        available_servers = self.manager.get_available_servers()
        connected_servers = self.manager.get_connected_server_names()
        
        print("\n📋 Available MCP Servers:")
        print("-" * 50)
        
        for server_name in available_servers:
            status = "🟢 Connected" if server_name in connected_servers else "⚪ Available"
            print(f"  {status} {server_name}")
        
        if not available_servers:
            print("  No servers found in configuration directory")
        
        print(f"\nTotal: {len(available_servers)} servers configured")

    async def list_tools(self, server_name: str):
        """List all tools available for a specific server"""
        if not await self.initialize_manager():
            return

        if server_name not in self.manager.get_available_servers():
            print(f"❌ Server '{server_name}' not found")
            await self.list_servers()
            return

        print(f"🔌 Connecting to server: {server_name}")
        
        try:
            # Connect to the specific server
            await self.manager.connect_servers([server_name])
            
            if not self.manager.is_server_connected(server_name):
                print(f"❌ Failed to connect to server '{server_name}'")
                return

            # Get the server instance
            server = self.manager.connected_servers[server_name]
            
            # List tools
            tools = await server.list_tools()
            
            print(f"\n🛠️  Tools available in '{server_name}':")
            print("-" * 60)
            
            for i, tool in enumerate(tools, 1):
                print(f"\n{i}. {tool.name}")
                if tool.description:
                    print(f"   Description: {tool.description}")
                
                if hasattr(tool, 'inputSchema') and tool.inputSchema:
                    print(f"   Parameters: {json.dumps(tool.inputSchema, indent=6)}")
            
            if not tools:
                print("  No tools found for this server")
            
            print(f"\nTotal: {len(tools)} tools available")
            
        except Exception as e:
            print(f"❌ Error listing tools: {e}")
        finally:
            if self.manager:
                await self.manager.disconnect_servers([server_name])

    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]):
        """Call a specific tool with given arguments"""
        if not await self.initialize_manager():
            return

        if server_name not in self.manager.get_available_servers():
            print(f"❌ Server '{server_name}' not found")
            await self.list_servers()
            return

        print(f"🔌 Connecting to server: {server_name}")
        
        try:
            # Connect to the specific server
            await self.manager.connect_servers([server_name])
            
            if not self.manager.is_server_connected(server_name):
                print(f"❌ Failed to connect to server '{server_name}'")
                return

            # Get the server instance
            server = self.manager.connected_servers[server_name]
            
            # Check if tool exists
            tools = await server.list_tools()
            tool_names = [tool.name for tool in tools]
            
            if tool_name not in tool_names:
                print(f"❌ Tool '{tool_name}' not found in server '{server_name}'")
                print(f"Available tools: {', '.join(tool_names)}")
                return

            print(f"🛠️  Calling tool: {tool_name}")
            print(f"📝 Arguments: {json.dumps(arguments, indent=2)}")
            print("-" * 60)
            
            # Call the tool
            result = await call_tool_with_retry(
                server=server,
                tool_name=tool_name,
                arguments=arguments,
                retry_time=3,
                delay=1.0
            )
            
            print("✅ Tool call successful!")
            print("\n📤 Result:")
            print("-" * 40)
            
            # Display result based on type
            if hasattr(result, 'content') and result.content:
                for i, content in enumerate(result.content):
                    if hasattr(content, 'text'):
                        print(f"Content {i+1} (text):")
                        print(content.text)
                    elif hasattr(content, 'type'):
                        print(f"Content {i+1} ({content.type}):")
                        print(str(content))
                    else:
                        print(f"Content {i+1}:")
                        print(str(content))
                    print()
            else:
                print("Result:", str(result))
            
        except ToolCallError as e:
            print(f"❌ Tool call failed: {e.message}")
            if e.original_exception:
                print(f"Original error: {e.original_exception}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
        finally:
            if self.manager:
                await self.manager.disconnect_servers([server_name])

    async def cleanup(self):
        """Clean up resources"""
        if self.manager:
            try:
                await self.manager.ensure_all_disconnected()
            except Exception:
                # Ignore cleanup errors, including abort errors
                pass


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Test individual MCP tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run --active python %(prog)s list-servers
  uv run --active python %(prog)s list-tools --server terminal
  uv run --active python %(prog)s call-tool --server terminal --tool run_command --args '{"command": "ls -la"}'
  uv run --active python %(prog)s call-tool --server filesystem --tool read_file --args '{"path": "./README.md"}'
        """
    )
    
    parser.add_argument(
        '--workspace', '-w',
        default="./temp_workspace",
        help='Agent workspace directory (default: ./temp_workspace)'
    )
    
    parser.add_argument(
        '--config-dir', '-c',
        default="configs/mcp_servers",
        help='MCP server configuration directory (default: configs/mcp_servers)'
    )
    
    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='Enable debug output'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List servers command
    subparsers.add_parser('list-servers', help='List all available MCP servers')
    
    # List tools command
    list_tools_parser = subparsers.add_parser('list-tools', help='List tools for a specific server')
    list_tools_parser.add_argument('--server', '-s', required=True, help='Server name')
    
    # Call tool command
    call_tool_parser = subparsers.add_parser('call-tool', help='Call a specific tool')
    call_tool_parser.add_argument('--server', '-s', required=True, help='Server name')
    call_tool_parser.add_argument('--tool', '-t', required=True, help='Tool name')
    call_tool_parser.add_argument('--args', '-a', required=True, help='Tool arguments as JSON string')
    
    return parser.parse_args()


async def main():
    """Main function"""
    args = parse_arguments()
    
    if not args.command:
        print("❌ No command specified. Use --help for usage information.")
        return 1
    
    # Ensure workspace exists
    os.makedirs(args.workspace, exist_ok=True)
    
    tester = MCPToolTester(
        workspace=args.workspace,
        config_dir=args.config_dir,
        debug=args.debug
    )
    
    try:
        if args.command == 'list-servers':
            await tester.list_servers()
        
        elif args.command == 'list-tools':
            await tester.list_tools(args.server)
        
        elif args.command == 'call-tool':
            try:
                arguments = json.loads(args.args)
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON in arguments: {e}")
                print(f"Provided: {args.args}")
                return 1
            
            await tester.call_tool(args.server, args.tool, arguments)
        
        return 0
    
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 