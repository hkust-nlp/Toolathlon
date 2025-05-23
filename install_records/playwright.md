
#### link
// modelscope
https://modelscope.cn/mcp/servers/@microsoft/playwright-mcp

// github
https://github.com/microsoft/playwright-mcp

#### Configuration
##### modelscope sse
pass

##### local stdio
1. install
    ```
    npm install @playwright/mcp@latest
    ```

2. install playwright&chromium (optional if you have already installed in your machine)
    ```
    npm install playwright
    npx playwright install chromium
    ```

3. set params
    ```
    playwright_mcp_server = MCPServerStdio(
        name='playwright',
        params={
            "command": "npx",
            "args": [
                "-y", 
                "@playwright/mcp@latest",
                "--headless" ,
                "--browser", "chromium"
            ]
        },
        cache_tools_list=True,
    )
    ```