# stdio_servers/bash_server.py
# -*- coding: utf-8 -*-
import json
import asyncio
import aiohttp
import time
from typing import Any, Optional
from agents.tool import FunctionTool, RunContextWrapper
from time import sleep
from utils.api_model.openai_client import AsyncOpenAIClientWithRetry
from configs.global_configs import global_configs

# 网页抓取相关导入
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# launch a AsyncOpenAIClientWithRetry instance
client = AsyncOpenAIClientWithRetry( # FIXME: hardcoded now, should be dynamic
    api_key=global_configs.non_ds_key,
    base_url=global_configs.base_url_non_ds,
    provider="aihubmix",  
)

class FetchUrlContentError(Exception):
    pass

def clean_text(text: str) -> str:
    """清理文本内容，移除多余的空白字符"""
    if not text:
        return ""
    
    # 移除多余的空白字符
    text = re.sub(r'\s+', ' ', text)
    # 移除换行符
    text = text.replace('\n', ' ').replace('\r', ' ')
    # 移除多余的空白
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

async def extract_text_from_html(html_content: str, url: str) -> str:
    """从HTML内容中提取可读文本"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 移除不需要的元素
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'noscript']):
            element.decompose()
        
        # 移除注释
        for comment in soup.find_all(string=lambda text: isinstance(text, str) and text.strip().startswith('<!--')):
            comment.extract()
        
        # 提取文本内容
        text_parts = []
        
        # 提取标题
        for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            for element in soup.find_all(tag):
                text = clean_text(element.get_text())
                if text:
                    text_parts.append(f"{tag.upper()}: {text}")
        
        # 提取段落和其他文本内容
        for element in soup.find_all(['p', 'div', 'span', 'li', 'td', 'th']):
            text = clean_text(element.get_text())
            if text and len(text) > 10:  # 只保留有意义的文本
                text_parts.append(text)
        
        # 提取链接文本
        for link in soup.find_all('a', href=True):
            link_text = clean_text(link.get_text())
            if link_text and len(link_text) > 3:
                href = link.get('href')
                if href:
                    # 处理相对链接
                    if not href.startswith(('http://', 'https://')):
                        href = urljoin(url, href)
                    text_parts.append(f"链接: {link_text} ({href})")
        
        # 合并所有文本
        full_text = '\n\n'.join(text_parts)
        
        # 如果文本太短，尝试提取所有文本
        if len(full_text) < 100:
            full_text = clean_text(soup.get_text())
        
        return full_text
        
    except Exception as e:
        logger.error(f"解析HTML时出错: {e}")
        raise FetchUrlContentError(f"解析HTML内容失败: {e}")

async def fetch_with_requests(url: str, timeout: int = 30) -> str:
    """使用requests获取网页内容"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        
        # 检查内容类型
        content_type = response.headers.get('content-type', '').lower()
        if 'text/html' not in content_type:
            raise FetchUrlContentError(f"不支持的内容类型: {content_type}")
        
        return response.text
        
    except requests.exceptions.RequestException as e:
        raise FetchUrlContentError(f"请求失败: {e}")

async def fetch_with_playwright(url: str, timeout: int = 30) -> str:
    """使用Playwright获取动态网页内容"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise FetchUrlContentError("Playwright未安装，无法处理动态内容。请运行: pip install playwright && playwright install")
    
    try:
        async with async_playwright() as p:
            # 启动浏览器（使用Chromium，性能更好）
            browser = await p.chromium.launch(
                headless=True,  # 无头模式
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            # 创建上下文
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                extra_http_headers={
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
            )
            
            # 创建页面
            page = await context.new_page()
            
            # 设置超时
            page.set_default_timeout(timeout * 1000)  # Playwright使用毫秒
            
            # 访问页面
            await page.goto(url, wait_until='domcontentloaded')
            
            # 等待页面稳定（等待网络空闲）
            try:
                await page.wait_for_load_state('networkidle', timeout=10000)
            except Exception:
                logger.warning("等待网络空闲超时，继续处理")
            
            # 等待JavaScript执行完成
            await page.wait_for_timeout(2000)
            
            # 尝试滚动页面以触发懒加载内容
            try:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1000)
                await page.evaluate("window.scrollTo(0, 0)")
                await page.wait_for_timeout(500)
            except Exception:
                logger.warning("页面滚动失败，继续处理")
            
            # 获取页面源码
            html_content = await page.content()
            
            # 关闭浏览器
            await browser.close()
            
            return html_content
            
    except Exception as e:
        raise FetchUrlContentError(f"Playwright执行失败: {e}")

async def fetch_url_content(url: str) -> str:
    """获取页面上的所有可视文本内容，自动处理js等动态内容，包含重试机制"""
    if not url:
        raise FetchUrlContentError("URL不能为空")
    
    # 验证URL格式
    try:
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise FetchUrlContentError("无效的URL格式")
    except Exception as e:
        raise FetchUrlContentError(f"URL解析失败: {e}")
    
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            logger.info(f"尝试获取URL内容 (第{attempt + 1}次): {url}")
            
            # 首先尝试使用requests获取静态内容
            try:
                html_content = await fetch_with_requests(url)
                text_content = await extract_text_from_html(html_content, url)
                
                # 如果内容足够丰富，直接返回
                if len(text_content) > 100:
                    logger.info(f"成功获取静态内容，长度: {len(text_content)}")
                    return text_content
                else:
                    logger.info("静态内容较少，尝试使用Playwright获取动态内容")
                    raise FetchUrlContentError("内容不足，需要动态加载")
                    
            except FetchUrlContentError as e:
                if "内容不足" in str(e):
                    # 尝试使用Playwright获取动态内容
                    html_content = await fetch_with_playwright(url)
                    text_content = await extract_text_from_html(html_content, url)
                    
                    if len(text_content) > 50:
                        logger.info(f"成功获取动态内容，长度: {len(text_content)}")
                        return text_content
                    else:
                        raise FetchUrlContentError("无法获取有效内容")
                else:
                    raise
            
        except FetchUrlContentError as e:
            if attempt == max_retries - 1:
                raise FetchUrlContentError(f"获取内容失败 (重试{max_retries}次): {e}")
            else:
                logger.warning(f"第{attempt + 1}次尝试失败: {e}")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # 指数退避
    
    raise FetchUrlContentError("未知错误")

# 自建AI总结网页工具
async def on_ai_webpage_summary_tool_invoke(context: RunContextWrapper, params_str: str) -> Any:
    """获取URL内容并请求AI模型进行总结"""
    params = json.loads(params_str)
    url = params.get("url")
    max_tokens = params.get("max_tokens", 1000)
    
    if not url:
        return "Error: URL参数不能为空"
    
    try:
        # 获取网页内容
        url_content = await fetch_url_content(url)
        
        if not url_content or len(url_content.strip()) < 10:
            return "Error: 无法获取有效的网页内容"
        
        # 限制内容长度，避免超出模型限制
        if len(url_content) > 180000:
            url_content = url_content[:180000] + "\n\n[内容已截断...]"
        
        # 调用AI模型进行总结
        response = await client.chat_completion(
            model="gpt-4.1-nano-0414",
            messages=[
                {"role": "user", "content": f"请总结以下网页内容，总结长度不超过{max_tokens}个token。只返回总结内容，不要包含其他文字，总结的语种应当与网页主要内容保持一致。\n\n网页内容：\n{url_content}"}
            ],
            max_tokens=max_tokens
        )
        
        return response
        
    except FetchUrlContentError as e:
        return f"Error: {e}"
    except Exception as e:
        logger.error(f"AI总结过程中出错: {e}")
        return f"Error: 处理过程中出现未知错误: {e}"

tool_ai_webpage_summary = FunctionTool(
    name='local-ai_webpage_summary',
    description='use this tool to get a summary of a webpage, powered by GPT-4.1-nano',
    params_json_schema={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "url of the webpage to be summarized",
            },
            "max_tokens": {
                "type": "number",
                "description": "max tokens of the summary, default is 1000, max is 8000",
                "default": 1000,
                "maximum": 8000,
            },
        },
        "required": ["url"]
    },
    on_invoke_tool=on_ai_webpage_summary_tool_invoke
)