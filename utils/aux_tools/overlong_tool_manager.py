import json
import os
import time
import re
import uuid
from typing import Any, List, Dict, Optional, Tuple
from agents.tool import FunctionTool, RunContextWrapper

OVERLONG_DIR_NAME = '.overlong_tool_outputs'
SEARCH_PAGE_SIZE = 10
VIEW_PAGE_SIZE = 10000
MAX_VIEW_PAGE_SIZE = 100000
CONTEXT_SIZE = 1000  # Characters of context around each match

# Global storage for search sessions
search_sessions = {}
# Global storage for view sessions
view_sessions = {}

def get_overlong_dir(context: RunContextWrapper) -> str:
    """Get the overlong tool outputs directory path."""
    agent_workspace = context.context.get('_agent_workspace', '.')
    agent_workspace = os.path.abspath(agent_workspace)
    return os.path.join(agent_workspace, OVERLONG_DIR_NAME)

def touch_file(file_path: str) -> None:
    """Touch a file to update its access time."""
    current_time = time.time()
    os.utime(file_path, (current_time, current_time))

def cleanup_old_files(overlong_dir: str) -> List[str]:
    """Remove files older than 1 hour. Returns list of removed files."""
    if not os.path.exists(overlong_dir):
        return []
    
    current_time = time.time()
    one_hour_ago = current_time - 3600  # 1 hour = 3600 seconds
    removed_files = []
    
    for filename in os.listdir(overlong_dir):
        if filename.endswith('.json'):
            file_path = os.path.join(overlong_dir, filename)
            try:
                # Check last access time
                stat = os.stat(file_path)
                if stat.st_atime < one_hour_ago:
                    os.remove(file_path)
                    removed_files.append(filename)
            except OSError:
                continue
    
    return removed_files

def get_file_list(overlong_dir: str) -> List[Dict[str, Any]]:
    """Get list of all overlong tool output files with metadata."""
    if not os.path.exists(overlong_dir):
        return []
    
    files = []
    current_time = time.time()
    
    for filename in os.listdir(overlong_dir):
        if filename.endswith('.json'):
            file_path = os.path.join(overlong_dir, filename)
            try:
                stat = os.stat(file_path)
                shortuuid = filename[:-5]  # Remove .json extension
                age_hours = (current_time - stat.st_atime) / 3600
                
                # Get file size
                size_mb = stat.st_size / (1024 * 1024)
                
                files.append({
                    'shortuuid': shortuuid,
                    'filename': filename,
                    'age_hours': round(age_hours, 2),
                    'size_mb': round(size_mb, 2),
                    'last_accessed': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_atime))
                })
            except OSError:
                continue
    
    # Sort by last accessed time (newest first)
    files.sort(key=lambda x: x['age_hours'])
    return files

def search_in_content(content: str, pattern: str, context_size: int = CONTEXT_SIZE) -> List[Dict[str, Any]]:
    """Search for regex pattern in content and return matches with context."""
    try:
        regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    except re.error as e:
        raise ValueError(f"Invalid regex pattern: {e}")
    
    matches = []
    for match in regex.finditer(content):
        start_pos = match.start()
        end_pos = match.end()
        
        # Calculate context boundaries
        context_start = max(0, start_pos - context_size // 2)
        context_end = min(len(content), end_pos + context_size // 2)
        
        # Get context with match highlighted
        before_context = content[context_start:start_pos]
        match_text = content[start_pos:end_pos]
        after_context = content[end_pos:context_end]
        
        # Calculate line number (approximate)
        line_num = content[:start_pos].count('\n') + 1
        
        matches.append({
            'match_text': match_text,
            'start_pos': start_pos,
            'end_pos': end_pos,
            'line_num': line_num,
            'before_context': before_context,
            'after_context': after_context,
            'context_start': context_start,
            'context_end': context_end
        })
    
    return matches

async def on_search_overlong_tool_invoke(context: RunContextWrapper, params_str: str) -> str:
    """Search within overlong tool output content using regex pattern and return first page with session ID."""
    params = json.loads(params_str)
    shortuuid = params.get("shortuuid", "").strip()
    pattern = params.get("pattern", "").strip()
    page_size = params.get("page_size", SEARCH_PAGE_SIZE)
    context_size = params.get("context_size", CONTEXT_SIZE)
    
    if not shortuuid:
        return "Error: shortuuid parameter is required"
    
    if not pattern:
        return "Error: pattern parameter is required"
    
    if page_size < 1 or page_size > 50:
        return "Error: page_size must be between 1 and 50"
    
    overlong_dir = get_overlong_dir(context)
    file_path = os.path.join(overlong_dir, f"{shortuuid}.json")
    
    if not os.path.exists(file_path):
        return f"Error: No overlong tool output found for shortuuid: {shortuuid}"
    
    try:
        # Touch the file to update access time
        touch_file(file_path)
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Search for pattern
        matches = search_in_content(content, pattern, context_size)
        
        if not matches:
            return f"No matches found for pattern '{pattern}' in shortuuid: {shortuuid}\nFile size: {len(content)} characters"
        
        # Create search session
        search_session_id = str(uuid.uuid4())[:8]
        search_sessions[search_session_id] = {
            'shortuuid': shortuuid,
            'pattern': pattern,
            'matches': matches,
            'page_size': page_size,
            'context_size': context_size,
            'content_length': len(content),
            'current_page': 1,
            'created_time': time.time()
        }
        
        # Return first page
        total_matches = len(matches)
        total_pages = (total_matches + page_size - 1) // page_size if total_matches > 0 else 1
        
        page_matches = matches[:page_size]
        
        # Format results
        result = f"Search Results in {shortuuid} (Page 1/{total_pages})\n"
        result += f"Pattern: '{pattern}' | Total matches: {total_matches} | File size: {len(content)} chars\n"
        result += f"Search Session ID: {search_session_id}\n"
        result += "=" * 80 + "\n\n"
        
        for i, match in enumerate(page_matches):
            match_num = i + 1
            result += f"Match {match_num} (Line ~{match['line_num']}, Pos {match['start_pos']}-{match['end_pos']}):\n"
            result += "-" * 60 + "\n"
            
            # Show context with match highlighted
            context_text = match['before_context'] + f">>>{match['match_text']}<<<" + match['after_context']
            
            # Truncate very long contexts for readability
            if len(context_text) > context_size * 2:
                context_text = context_text[:context_size * 2] + "...[truncated]"
            
            result += context_text + "\n\n"
        
        result += f"Use search_session_id '{search_session_id}' with search_navigate tool for pagination\n"
        result += f"Available commands: next_page, prev_page, jump_to_page, first_page, last_page"
        
        return result
        
    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error processing file for shortuuid {shortuuid}: {str(e)}"

async def on_search_navigate_invoke(context: RunContextWrapper, params_str: str) -> str:
    """Navigate through search results using session ID."""
    params = json.loads(params_str)
    search_session_id = params.get("search_session_id", "").strip()
    action = params.get("action", "next_page").strip().lower()
    target_page = params.get("target_page")
    
    if not search_session_id:
        return "Error: search_session_id parameter is required"
    
    if search_session_id not in search_sessions:
        return f"Error: Invalid or expired search session ID: {search_session_id}"
    
    session = search_sessions[search_session_id]
    matches = session['matches']
    page_size = session['page_size']
    total_matches = len(matches)
    total_pages = (total_matches + page_size - 1) // page_size if total_matches > 0 else 1
    
    # Determine current page from session state
    current_page = session.get('current_page', 1)
    
    # Handle different actions
    if action == "next_page":
        target_page = min(current_page + 1, total_pages)
    elif action == "prev_page":
        target_page = max(current_page - 1, 1)
    elif action == "first_page":
        target_page = 1
    elif action == "last_page":
        target_page = total_pages
    elif action == "jump_to_page":
        if target_page is None:
            return "Error: target_page parameter is required for jump_to_page action"
        if target_page < 1 or target_page > total_pages:
            return f"Error: target_page {target_page} must be between 1 and {total_pages}"
    else:
        return f"Error: Invalid action '{action}'. Valid actions: next_page, prev_page, jump_to_page, first_page, last_page"
    
    # Update session current page
    session['current_page'] = target_page
    
    # Get page results
    start_idx = (target_page - 1) * page_size
    end_idx = min(start_idx + page_size, total_matches)
    page_matches = matches[start_idx:end_idx]
    
    # Format results
    result = f"Search Results in {session['shortuuid']} (Page {target_page}/{total_pages})\n"
    result += f"Pattern: '{session['pattern']}' | Total matches: {total_matches} | File size: {session['content_length']} chars\n"
    result += f"Search Session ID: {search_session_id}\n"
    result += "=" * 80 + "\n\n"
    
    for i, match in enumerate(page_matches):
        match_num = start_idx + i + 1
        result += f"Match {match_num} (Line ~{match['line_num']}, Pos {match['start_pos']}-{match['end_pos']}):\n"
        result += "-" * 60 + "\n"
        
        # Show context with match highlighted
        context_text = match['before_context'] + f">>>{match['match_text']}<<<" + match['after_context']
        
        # Truncate very long contexts for readability
        if len(context_text) > session['context_size'] * 2:
            context_text = context_text[:session['context_size'] * 2] + "...[truncated]"
        
        result += context_text + "\n\n"
    
    # Navigation info
    nav_info = []
    if target_page > 1:
        nav_info.append("prev_page")
    if target_page < total_pages:
        nav_info.append("next_page")
    nav_info.extend(["first_page", "last_page", "jump_to_page"])
    
    result += f"Available navigation: {', '.join(nav_info)}\n"
    result += f"Use search_session_id '{search_session_id}' to continue navigation"
    
    return result

async def on_view_overlong_tool_invoke(context: RunContextWrapper, params_str: str) -> str:
    """View overlong tool output content with pagination and return first page with session ID."""
    params = json.loads(params_str)
    shortuuid = params.get("shortuuid", "").strip()
    page_size = params.get("page_size", VIEW_PAGE_SIZE)
    
    if not shortuuid:
        return "Error: shortuuid parameter is required"
    
    if page_size < 1 or page_size > MAX_VIEW_PAGE_SIZE:
        return f"Error: page_size must be between 1 and {MAX_VIEW_PAGE_SIZE}"
    
    overlong_dir = get_overlong_dir(context)
    file_path = os.path.join(overlong_dir, f"{shortuuid}.json")
    
    if not os.path.exists(file_path):
        return f"Error: No overlong tool output found for shortuuid: {shortuuid}"
    
    try:
        # Touch the file to update access time
        touch_file(file_path)
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        total_length = len(content)
        total_pages = (total_length + page_size - 1) // page_size if total_length > 0 else 1
        
        # Create view session
        view_session_id = str(uuid.uuid4())[:8]
        view_sessions[view_session_id] = {
            'shortuuid': shortuuid,
            'content_length': total_length,
            'page_size': page_size,
            'current_page': 1,
            'created_time': time.time()
        }
        
        # Get first page content
        end_pos = min(page_size, total_length)
        excerpt = content[:end_pos]
        
        # Calculate line numbers
        start_line = 1
        end_line = content[:end_pos].count('\n') + 1
        
        result = f"Viewing {shortuuid} (Page 1/{total_pages})\n"
        result += f"Characters 0-{end_pos} of {total_length} | Lines ~{start_line}-{end_line}\n"
        result += f"View Session ID: {view_session_id}\n"
        result += "=" * 80 + "\n\n"
        result += excerpt
        
        if end_pos < total_length:
            result += f"\n\n[Page 1 of {total_pages} - {total_length - end_pos} more characters available]\n"
            result += f"Use view_session_id '{view_session_id}' with view_navigate tool for pagination\n"
            result += f"Available commands: next_page, prev_page, jump_to_page, first_page, last_page"
        else:
            result += f"\n\n[End of file - {total_length} characters total]"
        
        return result
        
    except Exception as e:
        return f"Error reading file for shortuuid {shortuuid}: {str(e)}"

async def on_view_navigate_invoke(context: RunContextWrapper, params_str: str) -> str:
    """Navigate through view content using session ID."""
    params = json.loads(params_str)
    view_session_id = params.get("view_session_id", "").strip()
    action = params.get("action", "next_page").strip().lower()
    target_page = params.get("target_page")
    
    if not view_session_id:
        return "Error: view_session_id parameter is required"
    
    if view_session_id not in view_sessions:
        return f"Error: Invalid or expired view session ID: {view_session_id}"
    
    session = view_sessions[view_session_id]
    shortuuid = session['shortuuid']
    page_size = session['page_size']
    total_length = session['content_length']
    total_pages = (total_length + page_size - 1) // page_size if total_length > 0 else 1
    
    # Determine current page from session state
    current_page = session.get('current_page', 1)
    
    # Handle different actions
    if action == "next_page":
        target_page = min(current_page + 1, total_pages)
    elif action == "prev_page":
        target_page = max(current_page - 1, 1)
    elif action == "first_page":
        target_page = 1
    elif action == "last_page":
        target_page = total_pages
    elif action == "jump_to_page":
        if target_page is None:
            return "Error: target_page parameter is required for jump_to_page action"
        if target_page < 1 or target_page > total_pages:
            return f"Error: target_page {target_page} must be between 1 and {total_pages}"
    else:
        return f"Error: Invalid action '{action}'. Valid actions: next_page, prev_page, jump_to_page, first_page, last_page"
    
    # Update session current page
    session['current_page'] = target_page
    
    # Read file content
    overlong_dir = get_overlong_dir(context)
    file_path = os.path.join(overlong_dir, f"{shortuuid}.json")
    
    try:
        # Touch the file to update access time
        touch_file(file_path)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Calculate page boundaries
        start_pos = (target_page - 1) * page_size
        end_pos = min(start_pos + page_size, total_length)
        excerpt = content[start_pos:end_pos]
        
        # Calculate line numbers
        start_line = content[:start_pos].count('\n') + 1
        end_line = content[:end_pos].count('\n') + 1
        
        result = f"Viewing {shortuuid} (Page {target_page}/{total_pages})\n"
        result += f"Characters {start_pos}-{end_pos} of {total_length} | Lines ~{start_line}-{end_line}\n"
        result += f"View Session ID: {view_session_id}\n"
        result += "=" * 80 + "\n\n"
        result += excerpt
        
        if end_pos < total_length:
            result += f"\n\n[Page {target_page} of {total_pages} - {total_length - end_pos} more characters available]\n"
        else:
            result += f"\n\n[End of file reached - {total_length} characters total]\n"
        
        # Navigation info
        nav_info = []
        if target_page > 1:
            nav_info.append("prev_page")
        if target_page < total_pages:
            nav_info.append("next_page")
        nav_info.extend(["first_page", "last_page", "jump_to_page"])
        
        result += f"Available navigation: {', '.join(nav_info)}\n"
        result += f"Use view_session_id '{view_session_id}' to continue navigation"
        
        return result
        
    except Exception as e:
        return f"Error reading file for shortuuid {shortuuid}: {str(e)}"
# Tool definitions
tool_search_overlong = FunctionTool(
    name='local-search_overlong_tooloutput',
    description='Search within overlong tool output content using regex patterns and return first page with session ID',
    params_json_schema={
        "type": "object",
        "properties": {
            "shortuuid": {
                "type": "string",
                "description": "The shortuuid identifier for the overlong tool output"
            },
            "pattern": {
                "type": "string",
                "description": "The regex pattern to search for in the content"
            },
            "page_size": {
                "type": "integer",
                "description": "Number of matches per page (default: 10, max: 50)",
                "minimum": 1,
                "maximum": 50
            },
            "context_size": {
                "type": "integer",
                "description": "Characters of context around each match (default: 1000)",
                "minimum": 100,
                "maximum": 5000
            }
        },
        "required": ["shortuuid", "pattern"]
    },
    on_invoke_tool=on_search_overlong_tool_invoke
)

tool_search_navigate = FunctionTool(
    name='local-search_overlong_tooloutput_navigate',
    description='Navigate through search results using search session ID',
    params_json_schema={
        "type": "object",
        "properties": {
            "search_session_id": {
                "type": "string",
                "description": "The search session ID returned from search_overlong_tool"
            },
            "action": {
                "type": "string",
                "description": "Navigation action to perform",
                "enum": ["next_page", "prev_page", "jump_to_page", "first_page", "last_page"]
            },
            "target_page": {
                "type": "integer",
                "description": "Target page number (required for jump_to_page action)",
                "minimum": 1
            }
        },
        "required": ["search_session_id"]
    },
    on_invoke_tool=on_search_navigate_invoke
)

tool_view_overlong = FunctionTool(
    name='local-view_overlong_tooloutput',
    description='View overlong tool output content with pagination and return first page with session ID',
    params_json_schema={
        "type": "object",
        "properties": {
            "shortuuid": {
                "type": "string",
                "description": "The shortuuid identifier for the overlong tool output"
            },
            "page_size": {
                "type": "integer",
                "description": f"Number of characters per page (default: {VIEW_PAGE_SIZE}, max: {MAX_VIEW_PAGE_SIZE})",
                "minimum": 1,
                "maximum": MAX_VIEW_PAGE_SIZE
            }
        },
        "required": ["shortuuid"]
    },
    on_invoke_tool=on_view_overlong_tool_invoke
)

tool_view_navigate = FunctionTool(
    name='local-view_overlong_tooloutput_navigate',
    description='Navigate through view content using view session ID',
    params_json_schema={
        "type": "object",
        "properties": {
            "view_session_id": {
                "type": "string",
                "description": "The view session ID returned from view_overlong_tool"
            },
            "action": {
                "type": "string",
                "description": "Navigation action to perform",
                "enum": ["next_page", "prev_page", "jump_to_page", "first_page", "last_page"]
            },
            "target_page": {
                "type": "integer",
                "description": "Target page number (required for jump_to_page action)",
                "minimum": 1
            }
        },
        "required": ["view_session_id"]
    },
    on_invoke_tool=on_view_navigate_invoke
)

overlong_tool_tools = [
    tool_search_overlong,
    tool_search_navigate,
    tool_view_overlong,
    tool_view_navigate
]