import json
import os
import time
import re
from typing import Any, List, Dict, Optional, Tuple
from agents.tool import FunctionTool, RunContextWrapper

OVERLONG_DIR_NAME = '.overlong_tool_outputs'
PAGE_SIZE = 10
CONTEXT_SIZE = 1000  # Characters of context around each match

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
    """Search within overlong tool output content using regex pattern."""
    params = json.loads(params_str)
    shortuuid = params.get("shortuuid", "").strip()
    pattern = params.get("pattern", "").strip()
    page = params.get("page", 1)
    page_size = params.get("page_size", PAGE_SIZE)
    context_size = params.get("context_size", CONTEXT_SIZE)
    
    if not shortuuid:
        return "Error: shortuuid parameter is required"
    
    if not pattern:
        return "Error: pattern parameter is required"
    
    if page < 1:
        return "Error: page must be >= 1"
    
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
        
        # Paginate results
        total_matches = len(matches)
        total_pages = (total_matches + page_size - 1) // page_size if total_matches > 0 else 1
        
        if page > total_pages:
            return f"Error: page {page} exceeds total pages {total_pages}"
        
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total_matches)
        page_matches = matches[start_idx:end_idx]
        
        # Format results
        result = f"Search Results in {shortuuid} (Page {page}/{total_pages})\n"
        result += f"Pattern: '{pattern}' | Total matches: {total_matches} | File size: {len(content)} chars\n"
        result += "=" * 80 + "\n\n"
        
        for i, match in enumerate(page_matches):
            match_num = start_idx + i + 1
            result += f"Match {match_num} (Line ~{match['line_num']}, Pos {match['start_pos']}-{match['end_pos']}):\n"
            result += "-" * 60 + "\n"
            
            # Show context with match highlighted
            context_text = match['before_context'] + f">>>{match['match_text']}<<<" + match['after_context']
            
            # Truncate very long contexts for readability
            if len(context_text) > context_size * 2:
                context_text = context_text[:context_size * 2] + "...[truncated]"
            
            result += context_text + "\n\n"
        
        result += f"Navigation: Use page parameter (1-{total_pages}) to view more results\n"
        result += f"Use jump_to_match to view specific match with more context"
        
        return result
        
    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error processing file for shortuuid {shortuuid}: {str(e)}"

async def on_browse_overlong_tools_invoke(context: RunContextWrapper, params_str: str) -> str:
    """Browse overlong tool outputs with pagination."""
    params = json.loads(params_str)
    page = params.get("page", 1)
    page_size = params.get("page_size", PAGE_SIZE)
    
    if page < 1:
        return "Error: page must be >= 1"
    
    if page_size < 1 or page_size > 100:
        return "Error: page_size must be between 1 and 100"
    
    overlong_dir = get_overlong_dir(context)
    
    # Cleanup old files first
    removed_files = cleanup_old_files(overlong_dir)
    
    files = get_file_list(overlong_dir)
    total_files = len(files)
    total_pages = (total_files + page_size - 1) // page_size if total_files > 0 else 1
    
    if page > total_pages and total_files > 0:
        return f"Error: page {page} exceeds total pages {total_pages}"
    
    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total_files)
    page_files = files[start_idx:end_idx]
    
    result = f"Overlong Tool Outputs (Page {page}/{total_pages}, Total: {total_files})\n"
    result += "=" * 60 + "\n"
    
    if removed_files:
        result += f"Cleaned up {len(removed_files)} old files (>1 hour)\n\n"
    
    if not page_files:
        result += "No overlong tool outputs found.\n"
    else:
        result += f"{'Index':<5} {'ShortUUID':<12} {'Age (hrs)':<10} {'Size (MB)':<10} {'Last Accessed':<20}\n"
        result += "-" * 60 + "\n"
        
        for i, file_info in enumerate(page_files):
            idx = start_idx + i + 1
            result += f"{idx:<5} {file_info['shortuuid']:<12} {file_info['age_hours']:<10} {file_info['size_mb']:<10} {file_info['last_accessed']:<20}\n"
    
    result += f"\nNavigation: Use page parameter to jump to different pages (1-{total_pages})\n"
    result += "Use search_overlong_tool with shortuuid to view specific content"
    
    return result

async def on_cleanup_overlong_tools_invoke(context: RunContextWrapper, params_str: str) -> str:
    """Manually cleanup overlong tool outputs older than specified hours."""
    params = json.loads(params_str)
    max_age_hours = params.get("max_age_hours", 1.0)
    
    if max_age_hours <= 0:
        return "Error: max_age_hours must be > 0"
    
    overlong_dir = get_overlong_dir(context)
    
    if not os.path.exists(overlong_dir):
        return "No overlong tool outputs directory found"
    
    current_time = time.time()
    cutoff_time = current_time - (max_age_hours * 3600)
    removed_files = []
    
    for filename in os.listdir(overlong_dir):
        if filename.endswith('.json'):
            file_path = os.path.join(overlong_dir, filename)
            try:
                stat = os.stat(file_path)
                if stat.st_atime < cutoff_time:
                    os.remove(file_path)
                    removed_files.append(filename)
            except OSError:
                continue
    
    if removed_files:
        return f"Cleaned up {len(removed_files)} files older than {max_age_hours} hours:\n" + "\n".join(removed_files)
    else:
        return f"No files found older than {max_age_hours} hours"

async def on_jump_to_match_invoke(context: RunContextWrapper, params_str: str) -> str:
    """Jump to a specific match with extended context."""
    params = json.loads(params_str)
    shortuuid = params.get("shortuuid", "").strip()
    pattern = params.get("pattern", "").strip()
    match_number = params.get("match_number", 1)
    context_size = params.get("context_size", CONTEXT_SIZE * 2)  # Double context for jump
    
    if not shortuuid:
        return "Error: shortuuid parameter is required"
    
    if not pattern:
        return "Error: pattern parameter is required"
    
    if match_number < 1:
        return "Error: match_number must be >= 1"
    
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
            return f"No matches found for pattern '{pattern}' in shortuuid: {shortuuid}"
        
        if match_number > len(matches):
            return f"Error: match_number {match_number} exceeds total matches {len(matches)}"
        
        match = matches[match_number - 1]
        
        # Format detailed result
        result = f"Match {match_number} of {len(matches)} in {shortuuid}\n"
        result += f"Pattern: '{pattern}' | Line ~{match['line_num']} | Position {match['start_pos']}-{match['end_pos']}\n"
        result += "=" * 80 + "\n\n"
        
        # Show extended context with match highlighted
        context_text = match['before_context'] + f">>>{match['match_text']}<<<" + match['after_context']
        
        result += f"Context ({len(context_text)} characters):\n"
        result += "-" * 60 + "\n"
        result += context_text + "\n\n"
        
        # Show surrounding matches info
        if len(matches) > 1:
            result += "Other matches in this file:\n"
            for i, other_match in enumerate(matches):
                if i != match_number - 1:
                    result += f"  Match {i+1}: Line ~{other_match['line_num']}, Pos {other_match['start_pos']}\n"
        
        return result
        
    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error processing file for shortuuid {shortuuid}: {str(e)}"

async def on_view_overlong_tool_invoke(context: RunContextWrapper, params_str: str) -> str:
    """View overlong tool output content by shortuuid (without search)."""
    params = json.loads(params_str)
    shortuuid = params.get("shortuuid", "").strip()
    start_pos = params.get("start_pos", 0)
    length = params.get("length", 5000)  # Default 5000 characters
    
    if not shortuuid:
        return "Error: shortuuid parameter is required"
    
    if start_pos < 0:
        return "Error: start_pos must be >= 0"
    
    if length < 1 or length > 20000:
        return "Error: length must be between 1 and 20000"
    
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
        
        if start_pos >= total_length:
            return f"Error: start_pos {start_pos} exceeds file length {total_length}"
        
        end_pos = min(start_pos + length, total_length)
        excerpt = content[start_pos:end_pos]
        
        # Calculate line numbers
        start_line = content[:start_pos].count('\n') + 1
        end_line = content[:end_pos].count('\n') + 1
        
        result = f"Viewing {shortuuid} (Characters {start_pos}-{end_pos} of {total_length})\n"
        result += f"Lines ~{start_line}-{end_line}\n"
        result += "=" * 80 + "\n\n"
        result += excerpt
        
        if end_pos < total_length:
            result += f"\n\n[Truncated - {total_length - end_pos} more characters available]"
            result += f"\nUse start_pos={end_pos} to continue reading"
        
        return result
        
    except Exception as e:
        return f"Error reading file for shortuuid {shortuuid}: {str(e)}"

# Tool definitions
tool_search_overlong = FunctionTool(
    name='local-search_overlong_tool',
    description='Search within overlong tool output content using regex patterns with pagination',
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
            "page": {
                "type": "integer",
                "description": "Page number for search results (default: 1)",
                "minimum": 1
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

tool_view_overlong = FunctionTool(
    name='local-view_overlong_tool',
    description='View overlong tool output content by shortuuid without search (for browsing)',
    params_json_schema={
        "type": "object",
        "properties": {
            "shortuuid": {
                "type": "string",
                "description": "The shortuuid identifier for the overlong tool output"
            },
            "start_pos": {
                "type": "integer",
                "description": "Starting character position in the file (default: 0)",
                "minimum": 0
            },
            "length": {
                "type": "integer",
                "description": "Number of characters to read (default: 5000, max: 20000)",
                "minimum": 1,
                "maximum": 20000
            }
        },
        "required": ["shortuuid"]
    },
    on_invoke_tool=on_view_overlong_tool_invoke
)

tool_jump_to_match = FunctionTool(
    name='local-jump_to_match',
    description='Jump to a specific search match with extended context',
    params_json_schema={
        "type": "object",
        "properties": {
            "shortuuid": {
                "type": "string",
                "description": "The shortuuid identifier for the overlong tool output"
            },
            "pattern": {
                "type": "string",
                "description": "The regex pattern that was used in the search"
            },
            "match_number": {
                "type": "integer",
                "description": "The match number to jump to (1-based index)",
                "minimum": 1
            },
            "context_size": {
                "type": "integer",
                "description": "Characters of context around the match (default: 2000)",
                "minimum": 200,
                "maximum": 10000,
                "default": 5000
            }
        },
        "required": ["shortuuid", "pattern", "match_number"]
    },
    on_invoke_tool=on_jump_to_match_invoke
)

tool_browse_overlong = FunctionTool(
    name='local-browse_overlong_tools',
    description='Browse overlong tool outputs with pagination and cleanup',
    params_json_schema={
        "type": "object",
        "properties": {
            "page": {
                "type": "integer",
                "description": "Page number (default: 1)",
                "minimum": 1
            },
            "page_size": {
                "type": "integer",
                "description": "Number of items per page (default: 10, max: 100)",
                "minimum": 1,
                "maximum": 100
            }
        }
    },
    on_invoke_tool=on_browse_overlong_tools_invoke
)

tool_cleanup_overlong = FunctionTool(
    name='local-cleanup_overlong_tools',
    description='Manually cleanup overlong tool outputs older than specified hours',
    params_json_schema={
        "type": "object",
        "properties": {
            "max_age_hours": {
                "type": "number",
                "description": "Maximum age in hours for files to keep (default: 1.0)",
                "minimum": 0.01
            }
        }
    },
    on_invoke_tool=on_cleanup_overlong_tools_invoke
)

if __name__ == "__main__":
    # Test the functions
    pass