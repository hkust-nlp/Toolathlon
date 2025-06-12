
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
    you can skip this as we have already installed via `npm install`

2. install playwright & chromium, this will install the corresponding chromium for the playwright used in the mcp
    ```
    cd node_modules/@playwright/mcp
    npx playwright install chromium
    ```

3. you may see warnings if you are not using Ubuntu 20.04, for example, we use AlmaLinux 9, then you can just set `export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1` to ignore these warning