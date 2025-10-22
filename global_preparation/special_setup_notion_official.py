from utils.mcp.tool_servers import MCPServerManager, call_tool_with_retry, ToolCallError
import asyncio
import json

xx_MCPServerManager = MCPServerManager(agent_workspace="./") # a pseudo server manager
notion_official_server = xx_MCPServerManager.servers['notion_official']

from configs.token_key_session import all_token_key_session

async def main():
    async with notion_official_server as server:
        print("We need to configure this notion official mcp server to the desires account, so that it can be used to duplicate and move pages!")
        print("Please follow the login guidances to do so ...")
        pass
    print(">>>> DONE!")

if __name__ == "__main__":
    asyncio.run(main())