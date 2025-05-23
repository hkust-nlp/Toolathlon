
#### link
// modelscope
https://modelscope.cn/mcp/servers/@variflight-ai/variflight-mcp

// github
https://github.com/variflight/variflight-mcp

#### Get variflight api key
1. visit https://mcp.variflight.com/
2. register an account - enter account name+password+email, it will send you an email for activation
3. go to your email and click activation, then log in
4. go to "api key"
5. click "+create api key"
6. enter the name of this api key
7. copy the key

#### Configuration
##### modelscope sse
1. copy the api key to https://modelscope.cn/mcp/servers/@variflight-ai/variflight-mcp, on the right you will see a blank for you to fill in the api key of variflight-mcp
2. get the sse url
3. set params as
    ```
    variflight_mcp_server = MCPServerSse(
        name='variflight',
        params={
            "url": "<the url>",
        },
        cache_tools_list=True,
    )
    ```

##### local stdio
1. install
    ```
    npm install @variflight-ai/variflight-mcp
    ```
2. set params as 
    ```
    variflight_mcp_server = MCPServerStdio(
        name='variflight',
        params={
            "command": "npx",
            "args": ["-y", "@variflight-ai/variflight-mcp"],
            "env" : {
                "VARIFLIGHT_API_KEY": "<your_api_key_here>"
            }
        },
        cache_tools_list=True,
    )
    ```