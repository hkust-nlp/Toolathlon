from utils.mcp.tool_servers import MCPServerManager, call_tool_with_retry
import asyncio
import os
import json
import yaml
from utils.general.helper import print_color
from configs.global_configs import global_configs

async def main():

    to_check_servers = []

    for server_file_path in os.listdir("configs/mcp_servers"):
        with open(os.path.join("configs/mcp_servers", server_file_path), "r") as f:
            server_config = yaml.safe_load(f)
        server_name = server_config["name"]
        # print(server_name)
        to_check_servers.append(server_name)
    
    
    # create a ./dumps/mcp_servers_check directory
    os.makedirs("dumps_for_mcp_check/mcp_servers_check", exist_ok=True)

    xx_MCPServerManager = MCPServerManager(agent_workspace="./dumps_for_mcp_check/mcp_servers_check") # a pseudo server manager
    
    for server_name in to_check_servers:
        if server_name == "huggingface":
            # we do not verify this server
            continue
        server_x = xx_MCPServerManager.servers[server_name]
        
        max_retries = 4
        for attempt in range(1, max_retries + 1):
            try:
                print_color(f"Server {server_name} is checking (attempt {attempt}) ... ", "yellow")
                async with server_x as server:
                    tools = await server.list_tools()
                    # with open("./mcptools_count.jsonl", "a") as f:
                        # f.write(json.dumps({"server_name": server_name, "tools_count": len(tools)}) + "\n")
                    pass
                # if server_name == "github" and global_configs.podman_or_docker == "podman":
                    # print_color("If you see `2025-08-30T11:10:04.982268: process not running: No such process` somthing like in checking github MCP server with podman, do not worry, this is just a expected behavior :)", "cyan")
                print_color(f"Server {server_name} is checked", "green")
                break
            except Exception as e:
                if attempt < max_retries:
                    print_color(f"Server {server_name} check failed (attempt {attempt}): {e}", "red")
                    await asyncio.sleep(0.8)
                    continue
                else:
                    print_color(f"Server {server_name} is checked with error after {max_retries} attempts: {e}", "red")
                    break
        
    
    

    # print_color("All servers are checked", "green")
if __name__ == "__main__":
    asyncio.run(main())