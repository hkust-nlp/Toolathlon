# -*- coding: utf-8 -*-
import json
import asyncio
import re
import time
from typing import Any, List, Dict, Optional
from agents.tool import FunctionTool, RunContextWrapper
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode, quote
import logging
import random
import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from configs.token_key_session import all_token_key_session

SERPER_API_KEY = all_token_key_session.serper_api_key

# Global instance, reusable
_global_concurrency_manager = None
_global_retry_manager = None

def get_global_concurrency_manager() -> "ConcurrencyManager":
    """Get global concurrency manager instance"""
    global _global_concurrency_manager
    if _global_concurrency_manager is None:
        _global_concurrency_manager = ConcurrencyManager(
            max_concurrent=5, 
            rate_limit=100, 
            time_window=60
        )
    return _global_concurrency_manager

def get_global_retry_manager() -> "RetryManager":
    """Get global retry manager instance"""
    global _global_retry_manager
    if _global_retry_manager is None:
        _global_retry_manager = RetryManager(
            max_retries=3, 
            base_delay=1.0, 
            max_delay=60.0
        )
    return _global_retry_manager

class SearchError(Exception):
    pass

def get_random_key(api_key):
    """Get a random key from a comma-separated list of keys"""
    if api_key and ',' in api_key:
        keys = api_key.split(',')
        return random.choice(keys)
    return api_key

class ConcurrencyManager:
    def __init__(self, max_concurrent: int = 5, rate_limit: int = 100, time_window: int = 60):
        """
        Concurrency manager, controlling both semaphore and rate limit
        
        Args:
            max_concurrent: Maximum concurrent requests
            rate_limit: Maximum requests allowed within time window
            time_window: Time window size (seconds)
        """
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.rate_limiter = RateLimiter(rate_limit, time_window)
        
    async def acquire(self):
        """Acquire concurrency permission and rate limit permission"""
        await self.semaphore.acquire()
        await self.rate_limiter.acquire()
        
    def release(self):
        """Release semaphore"""
        self.semaphore.release()

class RetryManager:
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        """
        Retry manager
        
        Args:
            max_retries: Maximum retry times
            base_delay: Base delay time (seconds)
            max_delay: Maximum delay time (seconds)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        
    async def retry_with_backoff(self, func, *args, **kwargs):
        """Use exponential backoff retry mechanism"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt == self.max_retries:
                    break
                    
                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                jitter = random.uniform(0.1, 0.3) * delay
                await asyncio.sleep(delay + jitter)
                
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay + jitter:.2f}s...")
        
        raise last_exception

class RateLimiter:
    def __init__(self, rate_limit: int, time_window: int = 60):
        """
        Initialize rate limiter
        
        Args:
            rate_limit: Maximum requests allowed within time window
            time_window: Time window size (seconds), default 60 seconds
        """
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.tokens = rate_limit
        self.last_update = time.time()
        self.lock = asyncio.Lock()

    async def acquire(self):
        """Acquire a token, if no available token, wait"""
        async with self.lock:
            while self.tokens <= 0:
                now = time.time()
                time_passed = now - self.last_update
                self.tokens = min(
                    self.rate_limit,
                    self.tokens + (time_passed * self.rate_limit / self.time_window)
                )
                self.last_update = now
                if self.tokens <= 0:
                    await asyncio.sleep(random.randint(5, 30))  # Wait xxx seconds and retry
            
            self.tokens -= 1
            return True

def search_google(query_list: list, 
                  num_results: int = 10) -> List[Dict[str, Any]]:
        '''Use Google search engine to search information for the given query. Google is usually a good choice. Translate your query into English for better results unless the query is Chinese localized.

        Args:
            query_list (list): The list of queries to be searched(List[str]). Search a list of queries at a time is highly recommended. Each query should be distinctive and specific. e.g. ['xx xxxx xx', 'xxxx', ...].
            num_results (int): The number of result pages to retrieve for EACH query. default is 4.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries where each dictionary represents a website.
                Each dictionary contains the following keys:
                - 'title': The title of the website.
                - 'link': The URL of the website.
                - 'snippet': A brief description of the website.
                - 'position': A number in order.
                - 'sitelinks': Useful links within the website.

                Example:
                {
                    'title': 'OpenAI',
                    'link': 'https://www.openai.com'
                    'snippet': 'An organization focused on ensuring that
                    'position': 1,
                    'sitelinks': [...],
                }
            title, description, url of a website.
        '''
        if isinstance(query_list, str):
            query_list = [query_list]
        all_results=[]
        for query in query_list:
            url = "https://google.serper.dev/search"
            headers = {
                'X-API-KEY': get_random_key(SERPER_API_KEY),
                'Content-Type': 'application/json'
            }
            payload = json.dumps({
                "q": query,
                "num": num_results
            })
            try:
                response = requests.request("POST", url, headers=headers, data=payload)
                response.raise_for_status()
                responses = json.loads(response.text)['organic']
            except Exception as e:
                logger.error(f"Google search failed with error: {repr(e)}")
                responses=[{"error": f"google serper search failed for {query=}. The error is: {repr(e)}"}]
            
            all_results.extend(responses)
        
        return all_results

async def search_google_async(session: aiohttp.ClientSession, query_list: list, 
                             num_results: int = 10, 
                             concurrency_manager: ConcurrencyManager = None,
                             retry_manager: RetryManager = None) -> List[Dict[str, Any]]:
    """Async version of Google search"""
    if isinstance(query_list, str):
        query_list = [query_list]
    
    if concurrency_manager is None:
        concurrency_manager = ConcurrencyManager()
    if retry_manager is None:
        retry_manager = RetryManager()
    
    async def search_single_query(query: str) -> List[Dict[str, Any]]:
        """Search single query"""
        await concurrency_manager.acquire()
        try:
            async def _do_search():
                url = "https://google.serper.dev/search"
                headers = {
                    'X-API-KEY': get_random_key(SERPER_API_KEY),
                    'Content-Type': 'application/json'
                }
                payload = {
                    "q": query,
                    "num": num_results
                }
                
                async with session.post(url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data.get('organic', [])
            
            return await retry_manager.retry_with_backoff(_do_search)
            
        except Exception as e:
            logger.error(f"Google search failed for query '{query}': {repr(e)}")
            return [{"error": f"google serper search failed for {query=}. The error is: {repr(e)}"}]
        finally:
            concurrency_manager.release()
    
    # Concurrent execution of all queries
    tasks = [search_single_query(query) for query in query_list]
    results_list = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Merge results
    all_results = []
    for result in results_list:
        if isinstance(result, Exception):
            logger.error(f"Task failed: {repr(result)}")
            all_results.append({"error": f"Search task failed: {repr(result)}"})
        else:
            all_results.extend(result)
    
    return all_results

async def on_web_search_tool_invoke(context: RunContextWrapper, params_str: str) -> Any:
    """Web search tool main function"""
    try:
        # Parse parameters
        params = json.loads(params_str)
        query = params.get('query', '').strip()
        num_results = min(max(params.get('num_results', 10), 1), 50)
        
        if not query:
            raise SearchError("Query parameter is required and cannot be empty")
        
        logger.info(f"Starting web search for query: '{query}' with {num_results} results")
        
        # Use global concurrency and retry manager
        concurrency_manager = get_global_concurrency_manager()
        retry_manager = get_global_retry_manager()
        
        # Use async search
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            results = await search_google_async(
                session=session,
                query_list=[query], 
                num_results=num_results,
                concurrency_manager=concurrency_manager,
                retry_manager=retry_manager
            )
        
        # Format output
        if not results:
            return "No search results found."
        
        formatted_results = []
        for i, result in enumerate(results, 1):
            if 'error' in result:
                formatted_results.append(f"Error: {result['error']}")
            else:
                title = result.get('title', 'No title')
                link = result.get('link', 'No link')
                snippet = result.get('snippet', 'No description')
                sitelinks = result.get('sitelinks', 'No sitelinks')
                
                formatted_results.append(f"Title: {title}\nLink: {link}\nSnippet: {snippet}\nSitelinks: {sitelinks}\n")
        
        output = "\n".join(formatted_results)
        logger.info(f"Web search completed successfully, returned {len(results)} results")
        return output
        
    except SearchError as e:
        logger.error(f"Search error: {e}")
        return f"Error: {e}"
    except json.JSONDecodeError:
        logger.error("Invalid JSON format in parameters")
        return "Error: Invalid JSON format in parameters"
    except Exception as e:
        logger.error(f"Unexpected error during web search: {e}")
        return f"Error: Unexpected error occurred during search: {e}"

# Define tools
tool_web_search = FunctionTool(
    name='local-web_search',
    description='Search the web using Google Serper API with concurrency control and retry mechanisms. Supports various Google search operators.',
    params_json_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query with optional Google search operators.",
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results to return, default 10, max 50",
                "default": 10,
                "minimum": 1,
                "maximum": 50
            }
        },
        "required": ["query"]
    },
    on_invoke_tool=on_web_search_tool_invoke
)