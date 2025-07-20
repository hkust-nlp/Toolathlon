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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SearchError(Exception):
    pass

def get_realistic_headers(mobile=False):
    """Get realistic browser headers to avoid detection"""
    if mobile:
        return {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    else:
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }

def extract_text_fallback(html_content: str) -> str:
    """Extract pure text from HTML as fallback when parsing fails"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'noscript']):
            element.decompose()
        
        # Get pure text
        text = soup.get_text()
        
        # Clean up text
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Truncate if too long
        if len(text) > 500:
            text = text[:500] + "..."
        
        return text if text else "No description available"
        
    except Exception as e:
        logger.warning(f"Text extraction fallback failed: {e}")
        return "Description extraction failed"


async def search_duckduckgo(query: str, num_results: int = 10, page: int = 0) -> List[Dict[str, str]]:
    """DuckDuckGo search implementation with HTML parsing"""
    try:
        # DuckDuckGo doesn't have traditional pagination, we get more results and slice
        params = {
            'q': query,
            'kl': 'us-en',  # US English
            'safe': 'moderate'
        }
        
        url = f"https://html.duckduckgo.com/html/?{urlencode(params)}"
        
        headers = get_realistic_headers()
        headers.update({
            'Referer': 'https://duckduckgo.com/',
        })
        
        # Send request
        session = requests.Session()
        session.headers.update(headers)
        response = session.get(url, timeout=30)
        response.raise_for_status()
        
        # Parse search results
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # DuckDuckGo HTML version uses .result class
        search_results = soup.find_all('div', class_='result')
        
        for result in search_results[:num_results]:
            try:
                # Extract title and link
                title_elem = result.find('a', class_='result__a')
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                link = title_elem.get('href', '')
                
                # DuckDuckGo uses redirect links, extract the actual URL
                if link.startswith('//duckduckgo.com/l/?uddg='):
                    try:
                        # Extract the URL from the redirect
                        from urllib.parse import unquote, parse_qs, urlparse
                        # Remove the leading //
                        if link.startswith('//'):
                            link = 'https:' + link
                        parsed = urlparse(link)
                        query_params = parse_qs(parsed.query)
                        if 'uddg' in query_params:
                            link = unquote(query_params['uddg'][0])
                    except:
                        continue
                
                if not link.startswith('http'):
                    continue
                
                # Extract description
                description = ""
                
                # Look for snippet in result__snippet class
                desc_elem = result.find('a', class_='result__snippet')
                if desc_elem:
                    description = desc_elem.get_text(strip=True)
                
                # If no snippet found, try other common description elements
                if not description:
                    desc_candidates = result.find_all(['div', 'span'], class_=lambda x: x and 'snippet' in x.lower())
                    for elem in desc_candidates:
                        text = elem.get_text(strip=True)
                        if len(text) > 20 and text != title:
                            description = text
                            break
                
                # Fallback: look for any substantial text in the result
                if not description:
                    all_text = result.get_text(strip=True)
                    # Remove title and URL from text
                    clean_text = all_text.replace(title, '').replace(link.replace('https://', '').replace('http://', ''), '')
                    # Clean up whitespace
                    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                    if len(clean_text) > 30:
                        description = clean_text
                
                if not description:
                    description = "No description available"
                
                # Truncate long descriptions
                if len(description) > 500:
                    description = description[:500] + "..."
                
                if title and link:
                    results.append({
                        'title': title,
                        'link': link,
                        'description': description
                    })
                    
            except Exception as e:
                logger.warning(f"Error parsing DuckDuckGo search result: {e}")
                continue
        
        return results
        
    except requests.exceptions.RequestException as e:
        raise SearchError(f"DuckDuckGo search request failed: {e}")
    except Exception as e:
        raise SearchError(f"DuckDuckGo search parsing failed: {e}")

async def search_google(query: str, num_results: int = 10, page: int = 0) -> List[Dict[str, str]]:
    """Google search implementation with mobile fallback"""
    try:
        # Try desktop first, then mobile
        for is_mobile in [False, True]:
            try:
                if is_mobile:
                    logger.info("Trying mobile Google search...")
                    # Use mobile Google search
                    start = page * num_results
                    params = {
                        'q': query,
                        'num': min(num_results, 100),
                        'start': start,
                        'hl': 'en',
                    }
                    url = f"https://www.google.com/search?{urlencode(params)}"
                    headers = get_realistic_headers(mobile=True)
                else:
                    # Build desktop search URL
                    start = page * num_results
                    params = {
                        'q': query,
                        'num': min(num_results, 100),
                        'start': start,
                        'hl': 'en',
                        'lr': 'lang_en',
                    }
                    url = f"https://www.google.com/search?{urlencode(params)}"
                    headers = get_realistic_headers(mobile=False)
                
                # Add delay to avoid detection
                if page > 0:
                    await asyncio.sleep(1 + (page * 0.5))
                
                headers.update({
                    'Referer': 'https://www.google.com/',
                })
                
                # Send request
                session = requests.Session()
                session.headers.update(headers)
                response = session.get(url, timeout=30)
                response.raise_for_status()
                
                if "Our systems have detected unusual traffic" in response.text:
                    if is_mobile:
                        raise SearchError("Google detected unusual traffic from both desktop and mobile")
                    continue  # Try mobile
                
                # Parse search results
                soup = BeautifulSoup(response.text, 'html.parser')
                results = []
                
                # Try multiple selectors for different Google layouts
                search_containers = (
                    soup.find_all('div', class_='g') or  # Standard results
                    soup.find_all('div', class_='MjjYud') or  # New layout
                    soup.find_all('div', attrs={'data-ved': True}) or  # Results with data-ved
                    []
                )
                
                # If no standard containers, try broader search
                if not search_containers:
                    # Look for any div containing both h3 and clickable links
                    all_divs = soup.find_all('div')
                    potential_results = []
                    
                    for div in all_divs:
                        # Must have h3 and a link
                        h3 = div.find('h3')
                        link = div.find('a', href=True)
                        if h3 and link:
                            # Link should point to external site
                            href = link.get('href', '')
                            if href.startswith('http') and 'google.com' not in href:
                                potential_results.append(div)
                            elif href.startswith('/url?q='):
                                potential_results.append(div)
                    
                    search_containers = potential_results[:num_results * 2]
                
                for container in search_containers[:num_results]:
                    try:
                        title = ""
                        link = ""
                        description = ""
                        
                        # Extract title
                        h3_elem = container.find('h3')
                        if h3_elem:
                            # Get parent link of h3
                            title_link = h3_elem.find_parent('a') or h3_elem.find('a')
                            if title_link:
                                title = h3_elem.get_text(strip=True)
                                link = title_link.get('href', '')
                        
                        # If no title from h3, try other methods
                        if not title:
                            # Look for any prominent link
                            links = container.find_all('a', href=True)
                            for a_elem in links:
                                text = a_elem.get_text(strip=True)
                                if len(text) > 10 and not text.lower().startswith('http'):
                                    title = text
                                    link = a_elem.get('href', '')
                                    break
                        
                        if not title or not link:
                            continue
                        
                        # Clean Google redirect links
                        if link.startswith('/url?q='):
                            try:
                                link = link.split('/url?q=')[1].split('&')[0]
                                from urllib.parse import unquote
                                link = unquote(link)
                            except:
                                continue
                        elif link.startswith('/search?') or link.startswith('#'):
                            continue  # Skip internal Google links
                        
                        if not link.startswith('http'):
                            continue
                        
                        # Extract description
                        # Try multiple description selectors
                        desc_selectors = ['span', 'div']
                        for tag in desc_selectors:
                            desc_elems = container.find_all(tag)
                            for elem in desc_elems:
                                text = elem.get_text(strip=True)
                                # Good description criteria
                                if (len(text) > 30 and 
                                    text != title and 
                                    ' ' in text and 
                                    not text.startswith('http') and
                                    not text.startswith('Translate this page')):
                                    description = text
                                    break
                            if description:
                                break
                        
                        # Fallback description
                        if not description:
                            all_text = container.get_text(strip=True)
                            if title in all_text:
                                description = all_text.replace(title, '').strip()
                            else:
                                description = all_text
                            
                            # Clean and truncate
                            description = re.sub(r'\s+', ' ', description)
                            if len(description) > 500:
                                description = description[:500] + "..."
                        
                        if not description:
                            description = "No description available"
                        
                        results.append({
                            'title': title,
                            'link': link,
                            'description': description
                        })
                        
                    except Exception as e:
                        logger.warning(f"Error parsing Google search result: {e}")
                        continue
                
                if results:
                    return results
                elif not is_mobile:
                    logger.info("No results from desktop Google, trying mobile...")
                    continue
                else:
                    return []
                    
            except requests.exceptions.RequestException as e:
                if is_mobile:
                    raise SearchError(f"Google search request failed on both desktop and mobile: {e}")
                continue
        
        return []
        
    except SearchError:
        raise
    except Exception as e:
        raise SearchError(f"Google search parsing failed: {e}")

async def search_bing(query: str, num_results: int = 10, page: int = 0) -> List[Dict[str, str]]:
    """Bing search implementation with text fallback"""
    try:
        # Build search URL
        offset = page * num_results
        params = {
            'q': query,
            'count': min(num_results, 50),  # Bing limit
            'first': offset + 1,
            'FORM': 'PERE',
        }
        
        url = f"https://www.bing.com/search?{urlencode(params)}"
        
        # Add delay
        if page > 0:
            await asyncio.sleep(1 + (page * 0.5))
        
        headers = get_realistic_headers()
        headers.update({
            'Referer': 'https://www.bing.com/',
            'Origin': 'https://www.bing.com',
        })
        
        # Send request
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Parse search results
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # Find search results - try multiple selectors
        search_results = (
            soup.find_all('li', class_='b_algo') or
            soup.find_all('div', class_='b_algo') or
            soup.find_all('li', class_='b_ans')
        )
        
        for result in search_results:
            try:
                # Extract title and link
                title_link = None
                if result.find('h2'):
                    title_link = result.find('h2').find('a')
                elif result.find('h3'):
                    title_link = result.find('h3').find('a')
                elif result.find('a', href=True):
                    title_link = result.find('a', href=True)
                
                if not title_link:
                    continue
                
                title = title_link.get_text(strip=True)
                link = title_link.get('href', '')
                
                if not link.startswith('http'):
                    continue
                
                # Extract description with fallback strategies
                description = ""
                
                # Strategy 1: Look for common Bing description elements
                desc_selectors = [
                    'p',
                    '.b_caption p',
                    '.b_snippet',
                    'div.b_caption',
                    '.b_dsc'
                ]
                
                for selector in desc_selectors:
                    if '.' in selector or '#' in selector:
                        desc_elem = result.select_one(selector)
                    else:
                        desc_elem = result.find(selector)
                    
                    if desc_elem:
                        description = desc_elem.get_text(strip=True)
                        if len(description) > 20:
                            break
                
                # Strategy 2: Text fallback
                if not description:
                    description = extract_text_fallback(str(result))
                
                if title and link:
                    results.append({
                        'title': title,
                        'link': link,
                        'description': description or "No description available"
                    })
                    
            except Exception as e:
                logger.warning(f"Error parsing Bing search result item: {e}")
                continue
        
        return results
        
    except requests.exceptions.RequestException as e:
        raise SearchError(f"Bing search request failed: {e}")
    except Exception as e:
        raise SearchError(f"Bing search parsing failed: {e}")

def format_search_results(results: List[Dict[str, str]]) -> str:
    """Format search results as: title\nlink\ndescription\n\n..."""
    if not results:
        return "No search results found"
    
    formatted_results = []
    for result in results:
        formatted_result = f"{result['title']}\n{result['link']}\n{result['description']}"
        formatted_results.append(formatted_result)
    
    return "\n\n".join(formatted_results)

async def on_web_search_tool_invoke(context: RunContextWrapper, params_str: str) -> Any:
    """Web search tool main function"""
    try:
        params = json.loads(params_str)
        query = params.get("query", "").strip()
        num_results = params.get("num_results", 10)
        page = params.get("page", 0)
        
        if not query:
            return "Error: Search query cannot be empty"
        
        # Limit parameters
        num_results = max(1, min(num_results, 50))
        page = max(0, min(page, 10))  # Limit pagination
        
        logger.info(f"Executing web search: {query}, results: {num_results}, page: {page}")
        
        # Try engines in order: Google -> Bing -> DuckDuckGo
        results = []
        engine_used = ""
        
        # Try Google first
        try:
            logger.info("Trying Google search...")
            results = await search_google(query, num_results, page)
            if results:
                engine_used = "GOOGLE"
        except Exception as e:
            logger.warning(f"Google search failed: {e}")
        
        # If Google failed, try Bing
        if not results:
            try:
                logger.info("Google failed, trying Bing search...")
                results = await search_bing(query, num_results, page)
                if results:
                    engine_used = "BING (Google fallback)"
                    # Mark results to show they came from Bing
                    for result in results:
                        result['title'] = f"[Bing] {result['title']}"
            except Exception as e:
                logger.warning(f"Bing search failed: {e}")
        
        # If both Google and Bing failed, try DuckDuckGo
        if not results:
            try:
                logger.info("Google and Bing failed, trying DuckDuckGo search...")
                results = await search_duckduckgo(query, num_results, page)
                if results:
                    engine_used = "DUCKDUCKGO (Google & Bing fallback)"
                    # Mark results to show they came from DuckDuckGo
                    for result in results:
                        result['title'] = f"[DDG] {result['title']}"
            except Exception as e:
                logger.warning(f"DuckDuckGo search failed: {e}")
        
        if not results:
            return f"No search results found for '{query}' (all search engines failed - Google has bot detection issues, Bing and DuckDuckGo may be temporarily unavailable)"
        
        # Format and return results
        formatted_output = format_search_results(results)
        
        # Add search info
        search_info = f"Search Engine: {engine_used}\nQuery: {query}\nResults: {len(results)}\nPage: {page + 1}\n\n"
        
        return search_info + formatted_output
        
    except SearchError as e:
        return f"Error: {e}"
    except json.JSONDecodeError:
        return "Error: Invalid JSON format in parameters"
    except Exception as e:
        logger.error(f"Error during web search: {e}")
        return f"Error: Unknown error occurred during search: {e}"

# Define search tool
tool_web_search = FunctionTool(
    name='local-web_search',
    description='Search the web using Google, Bing, and DuckDuckGo without API keys. Automatically tries Google first, then Bing, then DuckDuckGo until results are found. Returns results in format: title\\nlink\\ndescription\\n\\n...',
    params_json_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query or keywords",
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results to return, default 10, max 50",
                "default": 10,
                "minimum": 1,
                "maximum": 50
            },
            "page": {
                "type": "integer", 
                "description": "Page number starting from 0, default 0 (first page), max 10",
                "default": 0,
                "minimum": 0,
                "maximum": 10
            }
        },
        "required": ["query"]
    },
    on_invoke_tool=on_web_search_tool_invoke
)