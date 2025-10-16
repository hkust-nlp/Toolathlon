# stdio_servers/bash_server.py
# -*- coding: utf-8 -*-

### THIS LOCAL TOOL IS DEPRECATED, DO NOT USE IT

import json
import asyncio
import aiohttp
import time
from typing import Any, Optional
from agents.tool import FunctionTool, RunContextWrapper
from time import sleep
from utils.api_model.openai_client import AsyncOpenAIClientWithRetry
from configs.global_configs import global_configs

# Webpage fetching related imports
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
import logging

# Set logging
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

# launch a AsyncOpenAIClientWithRetry instance
client = AsyncOpenAIClientWithRetry( # FIXME: hardcoded now, should be dynamic
    api_key=global_configs.aihubmix_key,
    base_url="https://aihubmix.com/v1",
    provider="aihubmix",  
)

class FetchUrlContentError(Exception):
    pass

def clean_text(text: str) -> str:
    """Clean text content, remove extra whitespace characters"""
    if not text:
        return ""
    
    # Remove extra whitespace characters
    text = re.sub(r'\s+', ' ', text)
    # Remove newline characters
    text = text.replace('\n', ' ').replace('\r', ' ')
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

async def extract_text_from_html(html_content: str, url: str) -> str:
    """Extract readable text from HTML content"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'noscript']):
            element.decompose()
        
        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, str) and text.strip().startswith('<!--')):
            comment.extract()
        
        # Extract text content
        text_parts = []
        
        # Extract titles
        for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            for element in soup.find_all(tag):
                text = clean_text(element.get_text())
                if text:
                    text_parts.append(f"{tag.upper()}: {text}")
        
        # Extract paragraphs and other text content
        for element in soup.find_all(['p', 'div', 'span', 'li', 'td', 'th']):
            text = clean_text(element.get_text())
            if text and len(text) > 10:  # Only keep meaningful text
                text_parts.append(text)
        
        # Extract link text
        for link in soup.find_all('a', href=True):
            link_text = clean_text(link.get_text())
            if link_text and len(link_text) > 3:
                href = link.get('href')
                if href:
                    # Handle relative links
                    if not href.startswith(('http://', 'https://')):
                        href = urljoin(url, href)
                    text_parts.append(f"Link: {link_text} ({href})")
        
        # Merge all text
        full_text = '\n\n'.join(text_parts)
        
        # If text is too short, try to extract all text
        if len(full_text) < 100:
            full_text = clean_text(soup.get_text())
        
        return full_text
        
    except Exception as e:
        logger.error(f"Error parsing HTML: {e}")
        raise FetchUrlContentError(f"Failed to parse HTML content: {e}")

async def fetch_with_requests(url: str, timeout: int = 30) -> str:
    """Use requests to fetch webpage content"""
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
        
        # Check content type
        content_type = response.headers.get('content-type', '').lower()
        if 'text/html' not in content_type:
            raise FetchUrlContentError(f"Unsupported content type: {content_type}")
        
        return response.text
        
    except requests.exceptions.RequestException as e:
        raise FetchUrlContentError(f"Request failed: {e}")

async def fetch_with_playwright(url: str, timeout: int = 30) -> str:
    """Use Playwright to fetch dynamic webpage content"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise FetchUrlContentError("Playwright is not installed, cannot handle dynamic content. Please run: pip install playwright && playwright install")
    
    try:
        async with async_playwright() as p:
            # Launch browser (using Chromium, better performance)
            browser = await p.chromium.launch(
                headless=True,  # Headless mode
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            # Create context
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
            
            # Create page
            page = await context.new_page()
            
            # Set timeout
            page.set_default_timeout(timeout * 1000)  # Playwright uses milliseconds
            
            # Visit page
            await page.goto(url, wait_until='domcontentloaded')
            
            # Wait for page to stabilize (wait for network idle)
            try:
                await page.wait_for_load_state('networkidle', timeout=10000)
            except Exception:
                logger.warning("Network idle timeout, continue processing")
            
            # Wait for JavaScript to complete
            await page.wait_for_timeout(2000)
            
            # Try scrolling page to trigger lazy loading content
            try:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1000)
                await page.evaluate("window.scrollTo(0, 0)")
                await page.wait_for_timeout(500)
            except Exception:
                logger.warning("Page scrolling failed, continue processing")
            
            # Get page source code
            html_content = await page.content()
            
            # Close browser
            await browser.close()
            
            return html_content
            
    except Exception as e:
        raise FetchUrlContentError(f"Playwright execution failed: {e}")

async def fetch_url_content(url: str) -> str:
    """Get all visible text content on the page, automatically handle js etc. dynamic content, including retry mechanism"""
    if not url:
        raise FetchUrlContentError("URL cannot be empty")
    
    # Validate URL format
    try:
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise FetchUrlContentError("Invalid URL format")
    except Exception as e:
        raise FetchUrlContentError(f"URL parsing failed: {e}")
    
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Trying to fetch URL content (attempt {attempt + 1}): {url}")
            
            # First try to use requests to fetch static content
            try:
                html_content = await fetch_with_requests(url)
                text_content = await extract_text_from_html(html_content, url)
                
                # If content is rich enough, return directly
                if len(text_content) > 100:
                    logger.info(f"Successfully fetched static content, length: {len(text_content)}")
                    return text_content
                else:
                    logger.info("Static content is less, try to use Playwright to fetch dynamic content")
                    raise FetchUrlContentError("Content is not enough, need to dynamically load")
                    
            except FetchUrlContentError as e:
                if "Content is not enough" in str(e):
                    # Try to use Playwright to fetch dynamic content
                    html_content = await fetch_with_playwright(url)
                    text_content = await extract_text_from_html(html_content, url)
                    
                    if len(text_content) > 50:
                        logger.info(f"Successfully fetched dynamic content, length: {len(text_content)}")
                        return text_content
                    else:
                        raise FetchUrlContentError("Cannot get valid content")
                else:
                    raise
            
        except FetchUrlContentError as e:
            if attempt == max_retries - 1:
                raise FetchUrlContentError(f"Failed to fetch content (attempt {max_retries} times): {e}")
            else:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
    
    raise FetchUrlContentError("Unknown error")

# Self-built AI summary webpage tool
async def on_ai_webpage_summary_tool_invoke(context: RunContextWrapper, params_str: str) -> Any:
    """Get URL content and request AI model to summarize"""
    params = json.loads(params_str)
    url = params.get("url")
    max_tokens = params.get("max_tokens", 1000)
    
    if not url:
        return "Error: URL parameter cannot be empty"
    
    try:
        # Get webpage content
        url_content = await fetch_url_content(url)
        
        if not url_content or len(url_content.strip()) < 10:
            return "Error: Cannot get valid webpage content"
        
        # Limit content length, avoid exceeding model limit
        if len(url_content) > 180000:
            url_content = url_content[:180000] + "\n\n[Content truncated...]"
        
        # Call AI model to summarize
        response = await client.chat_completion(
            model="gpt-4.1-nano-0414",
            messages=[
                {"role": "user", "content": f"Please summarize the following webpage content, the summary length should not exceed {max_tokens} tokens. Only return the summary content, do not include any other text, the language of the summary should be consistent with the main content of the webpage.\n\nWebpage content:\n{url_content}"}
            ],
            max_tokens=max_tokens
        )
        
        return response
        
    except FetchUrlContentError as e:
        return f"Error: {e}"
    except Exception as e:
        logger.error(f"Error occurred during AI summary: {e}")
        return f"Error: Error occurred during AI summary: {e}"

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