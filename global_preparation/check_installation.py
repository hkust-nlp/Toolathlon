from utils.mcp.tool_servers import MCPServerManager, call_tool_with_retry
import asyncio
import os
import yaml
from utils.general.helper import print_color

async def main():

    to_check_servers = []

    for server_file_path in os.listdir("configs/mcp_servers"):
        with open(os.path.join("configs/mcp_servers", server_file_path), "r") as f:
            server_config = yaml.safe_load(f)
        server_name = server_config["name"]
        # print(server_name)
        to_check_servers.append(server_name)
    
    # create a ./dump/mcp_servers_check directory
    os.makedirs("dump/mcp_servers_check", exist_ok=True)

    xx_MCPServerManager = MCPServerManager(agent_workspace="./dump/mcp_servers_check") # a pseudo server manager
    
    for server_name in to_check_servers:
        server_x = xx_MCPServerManager.servers[server_name]
        
        try:
            print_color(f"Server {server_name} is checking ... ", "yellow")
            async with server_x as server:
                pass
        except Exception as e:
            print_color(f"Server {server_name} is checked with error: {e}", "red")
            continue
        print_color(f"Server {server_name} is checked", "green")

if __name__ == "__main__":
    asyncio.run(main())