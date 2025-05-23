from agents.mcp import MCPServerStdio, MCPServerSse
from typing import List, Dict, Optional, Union, Literal
import asyncio
import os

from configs.global_configs import global_configs

ServerNameLiteral = Literal[
    'filesystem',
    'variflight',
    'amap',
    'playwright',
    'puppeteer',
    'fetch',
    'time',
    'arxiv_local',
    'edgeone',
    'shadcn_ui',
    'leetcode',
    'codesavant',
    'scholarly_search',
    'antv_chart',
    'code_runner',
    'slack',
    'github',
    '12306'
]


class MCPServerManager:
    """MCP 服务器管理器，用于初始化和管理多个 MCP 服务器"""

    def __init__(self, agent_workspace):
        """初始化 MCP 服务器管理器"""
        
        self.local_servers_paths = os.path.abspath("./local_servers") # 所有eval的共有运行路径，安装一些包
        self.agent_workspace = os.path.abspath(agent_workspace)
        self.servers: Dict[str, Union[MCPServerStdio, MCPServerSse]] = {}
        self._initialize_servers()
        self.connected_servers = []

        # TODO: 需要对MCP进行个性化初始化？

    def _initialize_servers(self):
        """初始化所有 MCP 服务器"""
        print(f">>servers工作区: {self.agent_workspace}")
        
        # 文件系统
        # https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem
        self.servers['filesystem'] = MCPServerStdio(
            name='filesystem',
            params={
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", 
                         self.agent_workspace], # 仅允许对该目录下的文件进行读写
            },
            cache_tools_list=True,
        )

        # 飞常准航空
        # sk-vd4XzwcgukiXynPveHE6GYgzoL1aVLKxb9QMmHAZnSQ
        self.servers['variflight'] = MCPServerSse(
            name='variflight',
            params={
                "url": "https://mcp.api-inference.modelscope.cn/sse/03e18b661de74f",
            },
            cache_tools_list=True,
        )

        # 高德地图位置服务
        # https://modelscope.cn/mcp/servers/@amap/amap-maps
        self.servers['amap'] = MCPServerSse(
            name='高德地图',
            params={
                "url": "https://mcp.api-inference.modelscope.cn/sse/af7d9dedc84e4b",
            },
            cache_tools_list=True,
        )

        # 一个使用 Playwright 提供浏览器自动化功能的 Model Context Protocol (MCP) 服务器。
        # https://github.com/microsoft/playwright-mcp
        self.servers['playwright'] = MCPServerStdio(
            name='playwright',
            params={
                "command": "npx",
                "args": [
                    "-y", 
                    "@playwright/mcp@latest",
                    "--headless", # no visual elements
                    "--isolated", # every time, initialize a new session, and no cache is stored
                    "--no-sandbox", # this may brings danger, if your machine support sandbox, please delete this
                    "--browser", "chromium", # please use chromium, others may need sudo to install
                    ],
                "env": { # this is necessary
                    "HTTPS_PROXY": global_configs['proxy'],
                    "HTTP_PROXY": global_configs['proxy'],
                }
            },
            client_session_timeout_seconds=10,
            cache_tools_list=True,
        )

        # 一个使用 Puppeteer 提供浏览器自动化功能的 Model Context Protocol 服务器。该服务器使 LLMs 能够与网页交互、截屏以及在真实的浏览器环境中执行 JavaScript。
        # https://github.com/modelcontextprotocol/servers/tree/main/src/puppeteer
        self.servers['puppeteer'] = MCPServerStdio(
            name='puppeteer',
            params={
                "command": "npx",
                "args": [
                    "-y", "@modelcontextprotocol/server-puppeteer",
                    "--no-sandbox", # switch on this on container
                    ],
                # "env": { # this is necessary
                    # "HTTPS_PROXY": global_configs['proxy'],
                    # "HTTP_PROXY": global_configs['proxy'],
                # }
            },
            cache_tools_list=True,
        )

        # Fetch 抓取网页并获得 raw HTML 或者转化后的markdown
        # https://modelscope.cn/mcp/servers/@modelcontextprotocol/fetch
        self.servers['fetch'] = MCPServerSse(
            name='fetch',
            params={
                "url": "https://mcp.api-inference.modelscope.cn/sse/01e5d883e78449",
            },
            client_session_timeout_seconds=10,
            cache_tools_list=True,
        )

        # Time
        self.servers['time'] = MCPServerStdio(
            name='time',
            params={
                "command": "python",
                "args": ["-m", "mcp_server_time", "--local-timezone=Asia/Hong_Kong"]
            },
            cache_tools_list=True,
        )
        
        # arxiv论文搜索、下载至本地、阅读
        # https://modelscope.cn/mcp/servers/@blazickjp/arxiv-mcp-server
        self.servers['arxiv_local'] = MCPServerStdio(
            name='ArXiv 搜索服务(本地)',
            params={
                "command": "uv",
                "args": [
                    "--directory",
                    f"{self.local_servers_paths}/arxiv-mcp-server",
                    "run",
                    "arxiv-mcp-server",
                    "--storage-path", f"{self.agent_workspace}/arxiv_local_storage"
                ],
                "env": { # this is necessary
                    "HTTPS_PROXY": global_configs['proxy'],
                    "HTTP_PROXY": global_configs['proxy'],
                }
            },
            client_session_timeout_seconds=10,
            cache_tools_list=True,
        )
        

        # edgeone-pages（一个用于将 HTML 内容部署到 EdgeOne Pages 并获取公开可访问 URL 的 MCP 服务。）
        # https://modelscope.cn/mcp/servers/@TencentEdgeOne/edgeone-pages-mcp
        self.servers['edgeone'] = MCPServerSse(
            name='edgeone',
            params={
                "url": "https://mcp.api-inference.modelscope.cn/sse/d92929d50e834a",
            },
            cache_tools_list=True,
        )


        # 访问 shadcn/ui 组件文档和示例
        # https://modelscope.cn/mcp/servers/@ymadd/shadcn-ui-mcp-server
        self.servers['shadcn_ui'] = MCPServerSse(
            name='shadcn-ui',
            params={
                "url": "https://mcp.api-inference.modelscope.cn/sse/83df379713b24c"
            },
            cache_tools_list=True,
        )

        # LeetCode 数据库检索
        # https://modelscope.cn/mcp/servers/@jinzcdev/leetcode-mcp-server
        self.servers['leetcode'] = MCPServerSse(
            name='leetcode',
            params={
                "url": "https://mcp.api-inference.modelscope.cn/sse/30f7d9b277ec4f"
            },
            cache_tools_list=True,
        )

        # 代码读写与沙箱执行
        # https://modelscope.cn/mcp/servers/@twolven/mcp-codesavant
        self.servers['codesavant'] = MCPServerStdio(
            name='codesavant',
            params={
                "command": "uv",
                "args": ["run", f"{self.local_servers_paths}/mcp-codesavant-main/codesavant.py"]
            },
            cache_tools_list=True,
        )

        # 学术搜索，通过关键词搜索 arxiv 和 谷歌学术上的文章（但无法下载全文）
        # https://modelscope.cn/mcp/servers/@adityak74/mcp-scholarly
        self.servers['scholarly_search'] = MCPServerStdio(
            name='scholarly',
            params={
                "command": "uvx",
                "args": ["mcp-scholarly"],
                "env": {
                    "HTTPS_PROXY": global_configs['proxy'],
                    "HTTP_PROXY": global_configs['proxy'],
                }
            },
            # client_session_timeout_seconds=20,
            cache_tools_list=True,
        )

        # antv mcp绘制可视化图表，返回图表图片的url
        # https://modelscope.cn/mcp/servers/@antvis/mcp-server-chart
        self.servers['antv_chart'] = MCPServerSse(
            name='antv_chart',
            params={
                "url": "https://mcp.api-inference.modelscope.cn/sse/55c878ff004641",
            },
            cache_tools_list=True,
        )

        # 代码执行器（远程临时下载包，可运行几乎所有的常见语言，目前环境中只装了python和node）
        # https://modelscope.cn/mcp/servers/@formulahendry/mcp-server-code-runner
        self.servers['code_runner'] = MCPServerStdio(
            name='code_runner',
            params={
                "command": "npx",
                "args": [
                    "-y",
                    "mcp-server-code-runner@latest"
                ],
            },
            cache_tools_list=True,
        )

        # Slack
        # https://github.com/modelcontextprotocol/servers/tree/main/src/slack
        self.servers['slack'] = MCPServerSse(
            name='Slack',
            params={
                "url": "https://mcp.api-inference.modelscope.cn/sse/ce2c0b9ef05442",
            },
            cache_tools_list=True,
        )

        # Github
        # https://github.com/modelcontextprotocol/servers/tree/main/src/github
        self.servers['github'] = MCPServerStdio(
            name='github',
            params={
                "command": "npx",
                "args": [
                    "-y", "@modelcontextprotocol/server-github"],
                "env": {
                    "GITHUB_PERSONAL_ACCESS_TOKEN": "<YOUR_TOKEN>"
                }
            },
            cache_tools_list=True,
        )

        # 12306 CN train tickets
        # https://modelscope.cn/mcp/servers/@Joooook/12306-mcp
        self.servers['12306'] = MCPServerSse(
            name='12306',
            params={
                "url": "https://mcp.api-inference.modelscope.cn/sse/e8b10afe5d864c",
            },
            cache_tools_list=True,
        )
        

    async def connect_servers(self, server_names: Optional[List[ServerNameLiteral]] = None):
        """
        连接指定的服务器

        Args:
            server_names: 要连接的服务器名称列表，如果为 None，则连接所有服务器
        """
        if server_names is None:
            # 默认连接的服务器列表
            server_names = []

        connect_tasks = []
        for name in server_names:
            if name in self.servers:
                try:
                    connect_tasks.append(self.servers[name].connect())
                    self.connected_servers.append(self.servers[name])
                except Exception as e:
                    print(e)
                    print(f"server {name} 连接失败")
            else:
                print(f"警告: 未找到名为 '{name}' 的服务器")

        if connect_tasks:
            await asyncio.gather(*connect_tasks)
            print(f">>已成功连接 {len(connect_tasks)} 个 MCP 服务器")

    async def disconnect_servers(self):
        """
        断开所有服务器连接
        """
        disconnect_tasks = []
        for server in self.connected_servers:
            disconnect_tasks.append(server.cleanup())

        if disconnect_tasks:
            await asyncio.gather(*disconnect_tasks)
            print(f">>已断开 {len(disconnect_tasks)} 个 MCP 服务器连接")

    def get_all_connected_servers(self):
        return self.connected_servers       
