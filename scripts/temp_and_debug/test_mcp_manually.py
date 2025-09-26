from utils.mcp.tool_servers import MCPServerManager, call_tool_with_retry
import asyncio

async def main():
    xx_MCPServerManager = MCPServerManager(agent_workspace="./") # a pseudo server manager
    server_x = xx_MCPServerManager.servers['你想使用的服务器']
    async with server_x as server:
        res = call_tool_with_retry(server, 
                                   tool_name= "你想使用的工具",
                                   arguments= { # 对应的工具参数
                                        ...
                                    },
                                   )
        print(res.content[0].text)
        # or， 如果上面这个不行，则换成下面的
        # print(res.content[0].text)

if __name__ == "__main__":
    asyncio.run(main())