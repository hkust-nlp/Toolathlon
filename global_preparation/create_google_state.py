import asyncio
import json
from playwright.async_api import async_playwright
import os
 
browser_path="C:\Program Files\Google\Chrome\Application\chrome.exe"
# if no such file, raise a error
if not os.path.exists(browser_path):
    raise ValueError(f"No such file: {browser_path}, please find your own chrome executable path!")

target_page="https://docs.google.com/forms/d/e/1FAIpQLSdVCWBNzMaa4a5E0IGDjpkW6KkFi_9BAaHJwj_9N4WkZYlT5Q/viewform?pli=1"

async def save_storage(context, path):
    storage = await context.storage_state()
    with open(path, 'w', encoding='utf-8') as file:
        json.dump(storage, file, indent=2, ensure_ascii=False)
    print(f"Storage state saved to {path}")
 
async def load_storage(context, path):
    with open(path, 'r', encoding='utf-8') as file:
        storage = json.load(file)
    await context.set_storage_state(storage)
    print(f"Storage state loaded from {path}")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=browser_path,
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-extensions',
                '--no-sandbox',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-infobars',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding'
            ])

        # 初次使用浏览器上下文并保存数据
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            extra_http_headers={
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )
        page = await context.new_page()
        
        # 隐藏自动化特征
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // 删除自动化控制的痕迹
            delete window.navigator.__proto__.webdriver;
            
            // 伪造插件信息
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // 伪造语言信息
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en'],
            });
            
            // 伪造权限API
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        await page.goto(target_page)
        
        # 等待用户完成登录操作
        # 英文输出
        print("Please login in the browser, then press Enter to continue...")
        input()  # 等待用户按回车

        # 保存上下文数据
        await save_storage(context, 'google_auth_state.json')
        await browser.close()
 
        # 重新启动浏览器并加载上下文数据
        browser = await p.chromium.launch(
            executable_path=browser_path,
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-extensions',
                '--no-sandbox',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-infobars',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding'
            ])
        context = await browser.new_context(
            storage_state='google_auth_state.json',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            extra_http_headers={
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )
        page = await context.new_page()
        
        # 隐藏自动化特征
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // 删除自动化控制的痕迹
            delete window.navigator.__proto__.webdriver;
            
            // 伪造插件信息
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // 伪造语言信息
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en'],
            });
            
            // 伪造权限API
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        await page.goto(target_page)

        # 验证会话是否保持
        print("Checking session status, please check if you have already logged in in 5 seconds...")
        await page.wait_for_timeout(5000)
        
        print("Validation completed! Press Enter to exit...")
        input()  # 等待用户按回车退出

        await browser.close()
 
asyncio.run(main())