# history_tools.py
import json
import re
from typing import Any, List, Tuple, Optional
from agents.tool import FunctionTool, RunContextWrapper
from utils.aux_tools.history_manager import HistoryManager
from datetime import datetime
from pathlib import Path


# 搜索会话缓存
search_sessions = {}

# 轮内搜索缓存
turn_search_sessions = {}

def truncate_content(content: str, max_length: int = 1000, head_tail_length: int = 500) -> str:
    """截断过长的内容，保留头尾"""
    if len(content) <= max_length:
        return content
    
    if len(content) <= head_tail_length * 2:
        # 如果内容不够长，直接返回
        return content
    
    head = content[:head_tail_length]
    tail = content[-head_tail_length:]
    return f"{head}\n... [{len(content) - head_tail_length * 2} characters omitted] ...\n{tail}"

def search_in_text(text: str, pattern: str, is_regex: bool = True) -> List[Tuple[int, int]]:
    """在文本中搜索模式，返回匹配位置列表"""
    matches = []
    
    try:
        if is_regex:
            # 正则表达式搜索
            for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                matches.append((match.start(), match.end()))
        else:
            # 普通文本搜索
            pattern_lower = pattern.lower()
            text_lower = text.lower()
            start = 0
            while True:
                pos = text_lower.find(pattern_lower, start)
                if pos == -1:
                    break
                matches.append((pos, pos + len(pattern)))
                start = pos + 1
    except re.error as e:
        # 如果正则表达式无效，回退到普通搜索
        return search_in_text(text, pattern, is_regex=False)
    
    return matches

def get_match_context(text: str, start: int, end: int, context_size: int = 500) -> str:
    """获取匹配位置的上下文"""
    # 计算上下文边界
    context_start = max(0, start - context_size // 2)
    context_end = min(len(text), end + context_size // 2)
    
    # 调整到词边界
    if context_start > 0:
        # 找到前面最近的空格或换行
        while context_start > 0 and text[context_start] not in ' \n\t':
            context_start -= 1
    
    if context_end < len(text):
        # 找到后面最近的空格或换行
        while context_end < len(text) and text[context_end] not in ' \n\t':
            context_end += 1
    
    # 提取上下文
    prefix = "..." if context_start > 0 else ""
    suffix = "..." if context_end < len(text) else ""
    
    context = text[context_start:context_end].strip()
    
    # 高亮匹配部分（调整偏移量）
    highlight_start = start - context_start
    highlight_end = end - context_start
    
    if 0 <= highlight_start < len(context) and 0 < highlight_end <= len(context):
        context = (
            context[:highlight_start] + 
            "**" + context[highlight_start:highlight_end] + "**" + 
            context[highlight_end:]
        )
    
    return prefix + context + suffix

async def on_search_history_invoke(context: RunContextWrapper, params_str: str) -> Any:
    """搜索历史记录，支持正则表达式"""
    params = json.loads(params_str)
    
    ctx = context.context if hasattr(context, 'context') else {}

    # 获取参数
    keywords = params.get("keywords", [])
    page = params.get("page", 1)
    per_page = params.get("per_page", 10)
    search_id = params.get("search_id")
    use_regex = params.get("use_regex", False)  # 是否使用正则表达式
    
    # 获取历史管理器
    session_id = ctx.get("_session_id", "unknown")
    history_dir = ctx.get("_history_dir", "conversation_histories")
    manager = HistoryManager(history_dir, session_id)
    
    # 如果提供了search_id，从缓存获取之前的搜索策略
    if search_id and search_id in search_sessions:
        cached_search = search_sessions[search_id]
        
        # 检查是否同时提供了搜索参数
        warning = None
        if keywords and keywords != cached_search["keywords"]:
            warning = f"Provided keywords '{keywords}' ignored, using cached search conditions '{cached_search['keywords']}'"
        elif "use_regex" in params and params["use_regex"] != cached_search.get("use_regex", False):
            warning = f"Provided use_regex setting ignored, using cached setting"
        
        keywords = cached_search["keywords"]
        use_regex = cached_search.get("use_regex", False)
        per_page = cached_search.get("per_page", per_page)
    else:
        # 新搜索，生成search_id
        import uuid
        search_id = f"search_{uuid.uuid4().hex[:8]}"
        warning = None
        
        if not keywords:
            return {
                "status": "error",
                "message": "Please provide keywords for search"
            }
    
    # 执行搜索
    skip = (page - 1) * per_page
    
    # 如果使用正则表达式，需要自定义搜索逻辑
    if use_regex:
        # 加载所有历史
        history = manager._load_history()
        matches = []
        
        # 编译正则表达式
        patterns = []
        for keyword in keywords:
            try:
                patterns.append(re.compile(keyword, re.IGNORECASE | re.MULTILINE))
            except re.error:
                return {
                    "status": "error",
                    "message": f"Invalid regex pattern: {keyword}"
                }
        
        # 搜索匹配
        for record in history:
            content = manager._extract_searchable_content(record)
            if content:
                # 检查是否所有模式都匹配
                if all(pattern.search(content) for pattern in patterns):
                    # 获取第一个匹配的上下文
                    match = patterns[0].search(content)
                    if match:
                        match_context = get_match_context(
                            content, 
                            match.start(), 
                            match.end(),
                            250  # 搜索结果使用较小的上下文
                        )
                        matches.append({
                            **record,
                            "match_context": match_context[:500] + "..." if len(match_context) > 500 else match_context
                        })
        
        # 分页
        total_matches = len(matches)
        matches = matches[skip:skip + per_page]
    else:
        # 使用原有的关键词搜索
        matches, total_matches = manager.search_by_keywords(keywords, per_page, skip)
    
    # 缓存搜索会话
    search_sessions[search_id] = {
        "keywords": keywords,
        "use_regex": use_regex,
        "per_page": per_page,
        "total_matches": total_matches,
        "created_at": json.dumps(datetime.now().isoformat()),
        "last_updated": datetime.now().isoformat()
    }
    
    # 清理过期的搜索会话（保留最近10个）
    if len(search_sessions) > 10:
        oldest_ids = sorted(search_sessions.keys())[:len(search_sessions) - 10]
        for old_id in oldest_ids:
            del search_sessions[old_id]
    
    # 格式化结果
    results = []
    for match in matches:
        # 从 raw_content 中提取角色信息
        role = "unknown"
        if match.get("item_type") == "message_output_item":
            raw_content = match.get("raw_content", {})
            if isinstance(raw_content, dict):
                role = raw_content.get("role", "unknown")
        elif match.get("item_type") in ["initial_input", "user_input"]:
            role = "user"
        elif match.get("item_type") == "tool_call_item":
            role = "assistant"
        elif match.get("item_type") == "tool_call_output_item":
            role = "tool"
        
        results.append({
            "turn": match.get("turn", -1),
            "timestamp": match.get("timestamp", "unknown"),
            "role": role,
            "preview": match.get("match_context", ""),
            "item_type": match.get("item_type", match.get("type", "unknown"))
        })
    
    total_pages = (total_matches + per_page - 1) // per_page
    
    return {
        "search_id": search_id,
        "keywords": keywords,
        "use_regex": use_regex,
        "total_matches": total_matches,
        "total_pages": total_pages,
        "current_page": page,
        "per_page": per_page,
        "has_more": page < total_pages,
        "results": results,
        "warning": warning,  # 添加这一行
        "search_info": {
            "is_cached_search": search_id in search_sessions,
            "last_updated": search_sessions[search_id]["last_updated"] if search_id in search_sessions else None,
            "search_type": "regex" if use_regex else "keyword"
        }
    }

async def on_view_history_turn_invoke(context: RunContextWrapper, params_str: str) -> Any:
    """查看特定轮次的详细内容"""
    params = json.loads(params_str)
    
    turn = params.get("turn")
    context_turns = params.get("context_turns", 2)
    truncate = params.get("truncate", True)  # 默认开启截断
    
    if turn is None:
        return {
            "status": "error",
            "message": "Please provide the turn number"
        }
    
    # 获取历史管理器
    ctx = context.context if hasattr(context, 'context') else {}
    session_id = ctx.get("_session_id", "unknown")
    history_dir = ctx.get("_history_dir", "conversation_histories")
    manager = HistoryManager(history_dir, session_id)
    
    # 获取轮次详情
    records = manager.get_turn_details(turn, context_turns)
    
    if not records:
        return {
            "status": "not_found",
            "message": f"No records found for turn {turn}"
        }
    
    # 格式化输出
    formatted_records = []
    for record in records:
        formatted = {
            "turn": record.get("turn", -1),
            "timestamp": record.get("timestamp", "unknown"),
            "is_target": record.get("is_target_turn", False)
        }
        
        # 根据类型格式化内容
        if record.get("type") == "initial_input":
            formatted["type"] = "Initial Input"
            content = record.get("content", "")
            formatted["content"] = truncate_content(content) if truncate else content
            formatted["original_length"] = len(content)
        elif record.get("item_type") == "message_output_item":
            formatted["type"] = "Message"
            raw_content = record.get("raw_content", {})
            if isinstance(raw_content, dict):
                formatted["role"] = raw_content.get("role", "unknown")
                # 提取文本内容
                content_parts = []
                for content_item in raw_content.get("content", []):
                    if isinstance(content_item, dict) and content_item.get("type") == "output_text":
                        content_parts.append(content_item.get("text", ""))
                content = " ".join(content_parts)
                formatted["content"] = truncate_content(content) if truncate else content
                formatted["original_length"] = len(content)
            else:
                formatted["role"] = "unknown"
                formatted["content"] = ""
                formatted["original_length"] = 0
        elif record.get("item_type") == "tool_call_item":
            formatted["type"] = "Tool Call"
            raw_content = record.get("raw_content", {})
            if isinstance(raw_content, dict):
                formatted["tool_name"] = raw_content.get("name", "unknown")
                # 如果有参数，也可以显示
                args = raw_content.get("arguments", {})
                if args:
                    args_str = json.dumps(args, ensure_ascii=False, indent=2)
                    formatted["arguments"] = truncate_content(args_str) if truncate else args_str
                    formatted["original_length"] = len(args_str)
            else:
                formatted["tool_name"] = "unknown"
        elif record.get("item_type") == "tool_call_output_item":
            formatted["type"] = "Tool Output"
            raw_content = record.get("raw_content", {})
            if isinstance(raw_content, dict):
                output = str(raw_content.get("output", ""))
                formatted["output"] = truncate_content(output) if truncate else output
                formatted["original_length"] = len(output)
            else:
                formatted["output"] = ""
                formatted["original_length"] = 0
        
        formatted_records.append(formatted)
    
    return {
        "status": "success",
        "target_turn": turn,
        "context_range": f"Displaying turn {turn - context_turns} to {turn + context_turns}",
        "truncated": truncate,
        "records": formatted_records
    }

async def on_search_in_turn_invoke(context: RunContextWrapper, params_str: str) -> Any:
    """在特定轮次内搜索内容"""
    params = json.loads(params_str)
    
    turn = params.get("turn")
    pattern = params.get("pattern")
    page = params.get("page", 1)
    per_page = params.get("per_page", 10)
    search_id = params.get("search_id")
    jump_to = params.get("jump_to")  # "first", "last", "next", "prev" 或具体页码
    
    if turn is None:
        return {
            "status": "error",
            "message": "Please provide the turn number"
        }
    
    # 处理搜索缓存
    if search_id and search_id in turn_search_sessions:
        cached = turn_search_sessions[search_id]
        
        # 检查是否同时提供了搜索参数
        warning = None
        if params.get("turn") is not None and params["turn"] != cached["turn"]:
            warning = f"Provided turn '{params['turn']}' ignored, using cached turn '{cached['turn']}'"
        elif params.get("pattern") and params["pattern"] != cached["pattern"]:
            warning = f"Provided pattern '{params['pattern']}' ignored, using cached search pattern '{cached['pattern']}'"
        
        turn = cached["turn"]
        pattern = cached["pattern"]
        matches = cached["matches"]
        total_matches = len(matches)
        
        # 处理页面跳转
        if jump_to:
            if jump_to == "first":
                page = 1
            elif jump_to == "last":
                page = (total_matches + per_page - 1) // per_page
            elif jump_to == "next":
                page = cached.get("current_page", 1) + 1
            elif jump_to == "prev":
                page = max(1, cached.get("current_page", 1) - 1)
            elif isinstance(jump_to, int):
                page = max(1, min(jump_to, (total_matches + per_page - 1) // per_page))
        
        # 更新当前页
        cached["current_page"] = page
    else:
        if not pattern:
            return {
                "status": "error",
                "message": "Please provide the search pattern"
            }
        
        warning = None  # 新搜索没有警告
        
        # 获取历史管理器
        ctx = context.context if hasattr(context, 'context') else {}
        session_id = ctx.get("_session_id", "unknown")
        history_dir = ctx.get("_history_dir", "conversation_histories")
        manager = HistoryManager(history_dir, session_id)
        
        # 获取轮次的所有记录
        records = manager.get_turn_details(turn, 0)  # 只获取目标轮次
        
        if not records:
            return {
                "status": "not_found",
                "message": f"No records found for turn {turn}"
            }
        
        # 搜索所有匹配
        all_matches = []
        
        for record in records:
            # 提取可搜索的内容
            content = ""
            record_type = ""
            
            if record.get("type") == "initial_input":
                content = record.get("content", "")
                record_type = "Initial Input"
            elif record.get("item_type") == "message_output_item":
                raw_content = record.get("raw_content", {})
                if isinstance(raw_content, dict):
                    content_parts = []
                    for content_item in raw_content.get("content", []):
                        if isinstance(content_item, dict) and content_item.get("type") == "output_text":
                            content_parts.append(content_item.get("text", ""))
                    content = " ".join(content_parts)
                record_type = f"Message ({raw_content.get('role', 'unknown')})"
            elif record.get("item_type") == "tool_call_item":
                raw_content = record.get("raw_content", {})
                if isinstance(raw_content, dict):
                    # 包括工具名称和参数
                    content = f"Tool: {raw_content.get('name', 'unknown')}\n"
                    args = raw_content.get("arguments", {})
                    if args:
                        content += f"Arguments: {json.dumps(args, ensure_ascii=False)}"
                record_type = "Tool Call"
            elif record.get("item_type") == "tool_call_output_item":
                raw_content = record.get("raw_content", {})
                if isinstance(raw_content, dict):
                    content = str(raw_content.get("output", ""))
                record_type = "Tool Output"
            
            if content:
                # 在内容中搜索
                matches = search_in_text(content, pattern, is_regex=True)
                
                for start, end in matches:
                    match_context = get_match_context(content, start, end, 500)
                    all_matches.append({
                        "record_type": record_type,
                        "position": f"Character {start}-{end}",
                        "match_text": content[start:end],
                        "context": match_context,
                        "item_type": record.get("item_type", record.get("type", "unknown"))
                    })
        
        # 生成搜索ID并缓存
        import uuid
        search_id = f"turn_search_{uuid.uuid4().hex[:8]}"
        
        matches = all_matches
        total_matches = len(matches)
        
        # 缓存搜索结果
        turn_search_sessions[search_id] = {
            "turn": turn,
            "pattern": pattern,
            "matches": matches,
            "current_page": page,
            "created_at": datetime.now().isoformat()
        }
        
        # 清理过期缓存
        if len(turn_search_sessions) > 20:
            oldest_ids = sorted(turn_search_sessions.keys(), 
                              key=lambda x: turn_search_sessions[x].get("created_at", ""))[:10]
            for old_id in oldest_ids:
                del turn_search_sessions[old_id]
    
    # 分页处理
    per_page = min(per_page, 20)  # 限制最大每页20条
    total_pages = max(1, (total_matches + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total_matches)
    page_matches = matches[start_idx:end_idx] if matches else []
    
    return {
        "status": "success",
        "search_id": search_id,
        "turn": turn,
        "pattern": pattern,
        "total_matches": total_matches,
        "warning": warning,  # 添加这一行
        "pagination": {
            "current_page": page,
            "total_pages": total_pages,
            "per_page": per_page,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "showing": f"{start_idx + 1}-{end_idx}" if page_matches else "0-0"
        },
        "matches": page_matches,
        "navigation_hint": "Use jump_to parameter to navigate: 'first', 'last', 'next', 'prev' or specific page number"
    }

async def on_history_stats_invoke(context: RunContextWrapper, params_str: str) -> Any:
    """获取历史统计信息"""
    # 获取历史管理器
    ctx = context.context if hasattr(context, 'context') else {}
    session_id = ctx.get("_session_id", "unknown")
    history_dir = ctx.get("_history_dir", "conversation_histories") 
    manager = HistoryManager(history_dir, session_id)
    
    stats = manager.get_statistics()
    
    # 添加当前会话信息
    meta = ctx.get("_context_meta", {})
    stats["current_session"] = {
        "active_turns": meta.get("turns_in_current_sequence", 0),
        "truncated_turns": meta.get("truncated_turns", 0),
        "started_at": meta.get("started_at", "unknown")
    }
    
    return stats

async def on_browse_history_invoke(context: RunContextWrapper, params_str: str) -> Any:
    """按顺序浏览历史"""
    params = json.loads(params_str)
    
    start_turn = params.get("start_turn", 0)
    end_turn = params.get("end_turn")
    limit = params.get("limit", 20)
    direction = params.get("direction", "forward")
    truncate = params.get("truncate", True)  # 默认开启截断
    
    # 获取历史管理器
    ctx = context.context if hasattr(context, 'context') else {}
    session_id = ctx.get("_session_id", "unknown")
    history_dir = ctx.get("_history_dir", "conversation_histories")
    manager = HistoryManager(history_dir, session_id)
    
    # 加载历史并按轮次分组
    history = manager._load_history()
    
    # 按轮次分组
    turns_map = {}
    for record in history:
        turn = record.get("turn", -1)
        if turn not in turns_map:
            turns_map[turn] = []
        turns_map[turn].append(record)
    
    # 获取所有轮次并排序
    all_turns = sorted([t for t in turns_map.keys() if t >= 0])
    
    if not all_turns:
        return {
            "status": "empty",
            "message": "No history records"
        }
    
    # 确定实际的结束轮次
    if end_turn is None:
        end_turn = all_turns[-1]
    
    # 过滤轮次范围
    selected_turns = [t for t in all_turns if start_turn <= t <= end_turn]
    
    # 根据方向排序
    if direction == "backward":
        selected_turns.reverse()
    
    # 应用限制
    if len(selected_turns) > limit:
        selected_turns = selected_turns[:limit]
    
    # 收集结果
    results = []
    for turn in selected_turns:
        turn_records = turns_map[turn]
        
        # 整理每轮的信息
        turn_summary = {
            "turn": turn,
            "timestamp": turn_records[0].get("timestamp", "unknown") if turn_records else "unknown",
            "messages": []
        }
        
        for record in turn_records:
            if record.get("item_type") == "message_output_item":
                raw_content = record.get("raw_content", {})
                role = "unknown"
                content = ""
                if isinstance(raw_content, dict):
                    role = raw_content.get("role", "unknown")
                    # 提取文本内容
                    content_parts = []
                    for content_item in raw_content.get("content", []):
                        if isinstance(content_item, dict) and content_item.get("type") == "output_text":
                            content_parts.append(content_item.get("text", ""))
                    content = " ".join(content_parts)
                
                # 应用截断
                display_content = truncate_content(content, 1000, 500) if truncate else content
                
                turn_summary["messages"].append({
                    "role": role,
                    "content": display_content[:200] + "..." if len(display_content) > 200 else display_content,
                    "original_length": len(content),
                    "truncated": truncate and len(content) > 1000
                })
            elif record.get("item_type") == "tool_call_item":
                raw_content = record.get("raw_content", {})
                tool_name = "unknown"
                if isinstance(raw_content, dict):
                    tool_name = raw_content.get("name", "unknown")
                
                turn_summary["messages"].append({
                    "type": "tool_call",
                    "tool": tool_name
                })
            elif record.get("item_type") == "tool_call_output_item":
                raw_content = record.get("raw_content", {})
                if isinstance(raw_content, dict):
                    output = str(raw_content.get("output", ""))
                    # 对工具输出也应用截断
                    display_output = truncate_content(output, 500, 250) if truncate else output
                    
                    turn_summary["messages"].append({
                        "type": "tool_output",
                        "preview": display_output[:100] + "..." if len(display_output) > 100 else display_output,
                        "original_length": len(output),
                        "truncated": truncate and len(output) > 500
                    })
        
        results.append(turn_summary)
    
    # 导航信息
    has_more_forward = end_turn < all_turns[-1] if direction == "forward" else start_turn > all_turns[0]
    has_more_backward = start_turn > all_turns[0] if direction == "forward" else end_turn < all_turns[-1]
    
    return {
        "status": "success",
        "direction": direction,
        "truncated": truncate,
        "turn_range": {
            "start": selected_turns[0] if selected_turns else start_turn,
            "end": selected_turns[-1] if selected_turns else end_turn,
            "total_returned": len(selected_turns)
        },
        "navigation": {
            "has_more_forward": has_more_forward,
            "has_more_backward": has_more_backward,
            "total_turns_available": len(all_turns),
            "first_turn": all_turns[0],
            "last_turn": all_turns[-1]
        },
        "results": results
    }

# 定义工具
tool_search_history = FunctionTool(
    name='local-search_history',
    description='Search history conversation records. Support multiple keyword search or regular expression search, return records containing all keywords. Support paging to browse all results.',
    params_json_schema={
        "type": "object",
        "properties": {
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Search keyword list or regular expression list, will find records matching all patterns"
            },
            "use_regex": {
                "type": "boolean",
                "description": "Whether to treat keywords as regular expressions",
                "default": False
            },
            "page": {
                "type": "integer",
                "description": "Page number, starting from 1",
                "default": 1,
                "minimum": 1
            },
            "per_page": {
                "type": "integer",
                "description": "Number of results per page",
                "default": 10,
                "minimum": 1,
                "maximum": 50
            },
            "search_id": {
                "type": "string",
                "description": "Continue previous search (for paging)"
            }
        },
        "required": []
    },
    on_invoke_tool=on_search_history_invoke
)

tool_view_history_turn = FunctionTool(
    name='local-view_history_turn',
    description='View the complete conversation content of a specific turn, including the context of previous and subsequent turns. Support content truncation to view long content.',
    params_json_schema={
        "type": "object",
        "properties": {
            "turn": {
                "type": "integer",
                "description": "Turn number to view",
                "minimum": 0
            },
            "context_turns": {
                "type": "integer",
                "description": "Display the context of previous and subsequent turns",
                "default": 2,
                "minimum": 0,
                "maximum": 10
            },
            "truncate": {
                "type": "boolean",
                "description": "Whether to truncate long content (keep the first 500 and last 500 characters)",
                "default": True
            }
        },
        "required": ["turn"]
    },
    on_invoke_tool=on_view_history_turn_invoke
)

tool_search_in_turn = FunctionTool(
    name='local-search_in_turn',
    description='Search content within a specific turn, support regular expressions. Used to find specific information in long content (such as tool output).',
    params_json_schema={
        "type": "object",
        "properties": {
            "turn": {
                "type": "integer",
                "description": "Turn number to search",
                "minimum": 0
            },
            "pattern": {
                "type": "string",
                "description": "Search pattern (support regular expressions)"
            },
            "page": {
                "type": "integer",
                "description": "Page number, starting from 1",
                "default": 1,
                "minimum": 1
            },
            "per_page": {
                "type": "integer",
                "description": "Number of results per page",
                "default": 10,
                "minimum": 1,
                "maximum": 20
            },
            "search_id": {
                "type": "string",
                "description": "Search session ID (for paging)"
            },
            "jump_to": {
                "oneOf": [
                    {
                        "type": "string",
                        "enum": ["first", "last", "next", "prev"]
                    },
                    {
                        "type": "integer",
                        "minimum": 1
                    }
                ],
                "description": "Jump to: 'first'(first page), 'last'(last page), 'next'(next page), 'prev'(previous page), or specific page number"
            }
        },
        "required": ["turn"]
    },
    on_invoke_tool=on_search_in_turn_invoke
)

tool_browse_history = FunctionTool(
    name='local-browse_history',
    description='Browse history records in chronological order, support forward or backward browsing. Can choose whether to truncate long content.',
    params_json_schema={
        "type": "object",
        "properties": {
            "start_turn": {
                "type": "integer",
                "description": "Start turn (inclusive), default from earliest",
                "minimum": 0
            },
            "end_turn": {
                "type": "integer",
                "description": "End turn (inclusive), default to latest",
                "minimum": 0
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of turns returned",
                "default": 20,
                "minimum": 1,
                "maximum": 100
            },
            "direction": {
                "type": "string",
                "enum": ["forward", "backward"],
                "description": "Browse direction: forward from early to late, backward from late to early",
                "default": "forward"
            },
            "truncate": {
                "type": "boolean",
                "description": "Whether to truncate long content display",
                "default": True
            }
        },
        "required": []
    },
    on_invoke_tool=on_browse_history_invoke
)

tool_history_stats = FunctionTool(
    name='local-history_stats',
    description='Get statistics of history records, including total turns, time range, message type distribution, etc.',
    params_json_schema={
        "type": "object",
        "properties": {},
        "required": []
    },
    on_invoke_tool=on_history_stats_invoke
)

# 导出所有历史工具
history_tools = [
    tool_search_history,
    tool_view_history_turn,
    tool_browse_history,
    tool_history_stats,
    tool_search_in_turn  # 新增的工具
]