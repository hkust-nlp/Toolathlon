# history_tools.py
import json
from typing import Any
from agents.tool import FunctionTool, RunContextWrapper
from utils.aux_tools.history_manager import HistoryManager
from datetime import datetime
from pathlib import Path

# 搜索会话缓存
search_sessions = {}

async def on_search_history_invoke(context: RunContextWrapper, params_str: str) -> Any:
    """搜索历史记录"""
    params = json.loads(params_str)
    
    ctx = context.context if hasattr(context, 'context') else {}

    # 获取参数
    keywords = params.get("keywords", [])
    page = params.get("page", 1)
    per_page = params.get("per_page", 10)
    search_id = params.get("search_id")
    
    # 获取历史管理器
    session_id = ctx.get("_session_id", "unknown")
    history_dir = ctx.get("_history_dir", "conversation_histories")
    manager = HistoryManager(history_dir, session_id)
    
    # 如果提供了search_id，从缓存获取之前的搜索策略
    if search_id and search_id in search_sessions:
        cached_search = search_sessions[search_id]
        keywords = cached_search["keywords"]
        # 使用缓存的每页展示数，确保搜索策略一致
        per_page = cached_search.get("per_page", per_page)
        # 不更新缓存，让搜索重新执行以获取最新的结果
    else:
        # 新搜索，生成search_id
        import uuid
        search_id = f"search_{uuid.uuid4().hex[:8]}"
        
        if not keywords:
            return {
                "status": "error",
                "message": "请提供搜索关键词"
            }
    
    # 执行搜索
    skip = (page - 1) * per_page
    matches, total_matches = manager.search_by_keywords(keywords, per_page, skip)
    
    # 缓存搜索会话（每次搜索都更新，确保数据最新）
    search_sessions[search_id] = {
        "keywords": keywords,
        "per_page": per_page,  # 缓存每页展示数
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
        "total_matches": total_matches,
        "total_pages": total_pages,
        "current_page": page,
        "per_page": per_page,
        "has_more": page < total_pages,
        "results": results,
        "search_info": {
            "is_cached_search": search_id in search_sessions,
            "last_updated": search_sessions[search_id]["last_updated"] if search_id in search_sessions else None,
            "cached_per_page": search_sessions[search_id].get("per_page") if search_id in search_sessions else None,
            "note": "搜索结果会动态更新，页数可能因新内容而变化。使用search_id时，关键词和每页展示数保持一致。"
        }
    }

async def on_view_history_turn_invoke(context: RunContextWrapper, params_str: str) -> Any:
    """查看特定轮次的详细内容"""
    params = json.loads(params_str)
    
    turn = params.get("turn")
    context_turns = params.get("context_turns", 2)
    
    if turn is None:
        return {
            "status": "error",
            "message": "请提供轮次号"
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
            "message": f"未找到第 {turn} 轮的记录"
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
            formatted["type"] = "初始输入"
            formatted["content"] = record.get("content", "")
        elif record.get("item_type") == "message_output_item":
            formatted["type"] = "消息"
            raw_content = record.get("raw_content", {})
            if isinstance(raw_content, dict):
                formatted["role"] = raw_content.get("role", "unknown")
                # 提取文本内容
                content_parts = []
                for content_item in raw_content.get("content", []):
                    if isinstance(content_item, dict) and content_item.get("type") == "output_text":
                        content_parts.append(content_item.get("text", ""))
                formatted["content"] = " ".join(content_parts)
            else:
                formatted["role"] = "unknown"
                formatted["content"] = ""
        elif record.get("item_type") == "tool_call_item":
            formatted["type"] = "工具调用"
            raw_content = record.get("raw_content", {})
            if isinstance(raw_content, dict):
                formatted["tool_name"] = raw_content.get("name", "unknown")
            else:
                formatted["tool_name"] = "unknown"
        elif record.get("item_type") == "tool_call_output_item":
            formatted["type"] = "工具输出"
            raw_content = record.get("raw_content", {})
            if isinstance(raw_content, dict):
                formatted["output"] = raw_content.get("output", "")
            else:
                formatted["output"] = ""
        
        formatted_records.append(formatted)
    
    return {
        "status": "success",
        "target_turn": turn,
        "context_range": f"显示第 {turn - context_turns} 到 {turn + context_turns} 轮",
        "records": formatted_records
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


# 浏览历史的实现
async def on_browse_history_invoke(context: RunContextWrapper, params_str: str) -> Any:
    """按顺序浏览历史"""
    params = json.loads(params_str)
    
    start_turn = params.get("start_turn", 0)
    end_turn = params.get("end_turn")
    limit = params.get("limit", 20)
    direction = params.get("direction", "forward")
    
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
            "message": "没有历史记录"
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
                
                turn_summary["messages"].append({
                    "role": role,
                    "content": content[:200] + "..." if len(content) > 200 else content
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
        
        results.append(turn_summary)
    
    # 导航信息
    has_more_forward = end_turn < all_turns[-1] if direction == "forward" else start_turn > all_turns[0]
    has_more_backward = start_turn > all_turns[0] if direction == "forward" else end_turn < all_turns[-1]
    
    return {
        "status": "success",
        "direction": direction,
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
    description='搜索历史对话记录。支持多个关键词搜索，返回包含所有关键词的记录。支持分页浏览所有结果。',
    params_json_schema={
        "type": "object",
        "properties": {
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "搜索关键词列表，将查找包含所有关键词的记录"
            },
            "page": {
                "type": "integer",
                "description": "页码，从1开始",
                "default": 1,
                "minimum": 1
            },
            "per_page": {
                "type": "integer",
                "description": "每页显示的结果数",
                "default": 10,
                "minimum": 1,
                "maximum": 50
            },
            "search_id": {
                "type": "string",
                "description": "继续之前的搜索（用于翻页）"
            }
        },
        "required": []
    },
    on_invoke_tool=on_search_history_invoke
)

tool_view_history_turn = FunctionTool(
    name='local-view_history_turn',
    description='查看特定轮次的完整对话内容，包括前后几轮的上下文。',
    params_json_schema={
        "type": "object",
        "properties": {
            "turn": {
                "type": "integer",
                "description": "要查看的轮次号",
                "minimum": 0
            },
            "context_turns": {
                "type": "integer",
                "description": "同时显示前后几轮的上下文",
                "default": 2,
                "minimum": 0,
                "maximum": 10
            }
        },
        "required": ["turn"]
    },
    on_invoke_tool=on_view_history_turn_invoke
)

tool_browse_history = FunctionTool(
    name='local-browse_history',
    description='按时间顺序浏览历史记录，支持正向或反向浏览。',
    params_json_schema={
        "type": "object",
        "properties": {
            "start_turn": {
                "type": "integer",
                "description": "起始轮次（包含），默认从最早开始",
                "minimum": 0
            },
            "end_turn": {
                "type": "integer",
                "description": "结束轮次（包含），默认到最新",
                "minimum": 0
            },
            "limit": {
                "type": "integer",
                "description": "最多返回的轮数",
                "default": 20,
                "minimum": 1,
                "maximum": 100
            },
            "direction": {
                "type": "string",
                "enum": ["forward", "backward"],
                "description": "浏览方向：forward从早到晚，backward从晚到早",
                "default": "forward"
            }
        },
        "required": []
    },
    on_invoke_tool=on_browse_history_invoke
)

tool_history_stats = FunctionTool(
    name='local-history_stats',
    description='获取历史记录的统计信息，包括总轮数、时间范围、消息类型分布等。',
    params_json_schema={  # 这里之前拼错了，是 params_json_schema 不是 params_json_scheme
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
    tool_history_stats
]