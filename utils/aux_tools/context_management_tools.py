# context_management_tools.py
import json
from typing import Any, Dict, List
from agents.tool import FunctionTool, RunContextWrapper

async def on_check_context_status_invoke(context: RunContextWrapper, params_str: str) -> Any:
    """查询当前上下文状态"""
    try:
        # 从 context.context 中获取数据
        ctx = context.context if hasattr(context, 'context') and context.context is not None else {}
        
        meta = ctx.get("_context_meta", {})
        session_id = ctx.get("_session_id", "unknown")
        context_limit = ctx.get("_context_limit", 128000)
        
        # 直接使用当前的 usage（已经是累积的）
        total_tokens = 0
        input_tokens = 0
        output_tokens = 0
        
        if hasattr(context, 'usage') and context.usage:
            total_tokens = context.usage.total_tokens or 0
            input_tokens = context.usage.input_tokens or 0
            output_tokens = context.usage.output_tokens or 0
        
        # 确保所有值都不是 None
        total_tokens = total_tokens or 0
        context_limit = context_limit or 128000
        
        # 计算使用率
        usage_percentage = round(total_tokens / context_limit * 100, 2) if context_limit > 0 else 0.0
        
        return {
            "session_info": {
                "session_id": session_id,
                "started_at": meta.get("started_at", "unknown"),
                "history_dir": ctx.get("_history_dir", "unknown")
            },
            "turn_statistics (turns before invoking this tool)": {
                "current_turn": meta.get("current_turn", 0),
                "turns_in_current_sequence": meta.get("turns_in_current_sequence", 0),
                "total_turns_ever": meta.get("total_turns_ever", 0),
                "truncated_turns": meta.get("truncated_turns", 0)
            },
            "token_usage": {
                "total_tokens": total_tokens,
                # "input_tokens": input_tokens,
                # "output_tokens": output_tokens,
                "context_limit": context_limit,
                "usage_percentage": usage_percentage,
                "remaining_tokens": max(0, context_limit - total_tokens)
            },
            "truncation_history": meta.get("truncation_history", []),
            "status": _get_status_recommendation(usage_percentage)
        }
    
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "message": "无法获取上下文状态"
        }

def _get_status_recommendation(usage_pct: float) -> Dict[str, Any]:
    """根据使用率给出建议"""
    if usage_pct >= 90:
        return {
            "level": "critical",
            "message": "上下文即将耗尽！强烈建议立即清理历史对话。",
            "recommended_action": "manage_context"
        }
    elif usage_pct >= 80:
        return {
            "level": "warning", 
            "message": "上下文使用率较高，建议清理部分历史对话。",
            "recommended_action": "manage_context"
        }
    elif usage_pct >= 70:
        return {
            "level": "info",
            "message": "上下文使用率适中，可以考虑预防性清理。",
            "recommended_action": "monitor"
        }
    else:
        return {
            "level": "good",
            "message": "上下文使用率健康。",
            "recommended_action": "none"
        }

tool_check_context = FunctionTool(
    name='local-check_context_status',
    description='查询当前对话的上下文状态，包括轮数统计、token使用情况、截断历史等信息',
    params_json_schema={
        "type": "object",
        "properties": {},
        "required": []
    },
    on_invoke_tool=on_check_context_status_invoke
)

async def on_manage_context_invoke(context: RunContextWrapper, params_str: str) -> Any:
    """管理上下文，执行截断操作"""
    params = json.loads(params_str)
    action = params.get("action", "truncate")
    ctx = context.context if hasattr(context, 'context') else {}
    if action != "truncate":
        return {
            "status": "error",
            "message": f"不支持的操作: {action}"
        }
    
    method = params.get("method")
    value = params.get("value")
    preserve_system = params.get("preserve_system", True)
    
    # 验证参数
    valid_methods = ["keep_recent_turns", "keep_recent_percent", "delete_first_turns", "delete_first_percent"]
    if method not in valid_methods:
        return {
            "status": "error",
            "message": f"无效的方法: {method}. 支持的方法: {valid_methods}"
        }
    
    if not isinstance(value, (int, float)) or value <= 0:
        return {
            "status": "error",
            "message": f"无效的值: {value}. 必须是正数。"
        }
    
    # 百分比方法需要检查范围
    if "percent" in method and (value <= 0 or value >= 100):
        return {
            "status": "error",
            "message": f"百分比必须在 0-100 之间，当前值: {value}"
        }
    
    # 获取当前统计
    meta = ctx.get("_context_meta", {})
    current_turns = meta.get("turns_in_current_sequence", 0)
    
    # 预计算会保留多少轮
    if method == "keep_recent_turns":
        keep_turns = int(value)
    elif method == "keep_recent_percent":
        keep_turns = max(1, int(current_turns * value / 100))
    elif method == "delete_first_turns":
        keep_turns = max(1, current_turns - int(value))
    elif method == "delete_first_percent":
        delete_turns = int(current_turns * value / 100)
        keep_turns = max(1, current_turns - delete_turns)
    
    if keep_turns >= current_turns:
        return {
            "status": "no_action",
            "message": f"当前只有 {current_turns} 轮对话，无需截断。",
            "current_turns": current_turns,
            "requested_keep": keep_turns
        }
    
    # 设置截断标记
    ctx["_pending_truncate"] = {
        "method": method,
        "value": value,
        "preserve_system": preserve_system,
        "requested_at_turn": meta.get("current_turn", 0),
        "expected_keep_turns": keep_turns,
        "expected_delete_turns": current_turns - keep_turns
    }
    
    return {
        "status": "scheduled", # 虽然返回的时候还没截断,但下次回复会基于截断后的上下文,所以就直接说已完成了
        "message": "已完成截断操作。",
        "details": {
            "method": method,
            "value": value,
            "current_turns": current_turns,
            "will_keep": keep_turns,
            "will_delete": current_turns - keep_turns,
            "preserve_system_messages": preserve_system
        },
        # "note": "截断将在本轮完成后执行，下一轮回复将基于截断后的上下文。"
    }

tool_manage_context = FunctionTool(
    name='local-manage_context',
    description='''管理对话上下文，通过删除历史消息来释放空间。支持多种策略：
- keep_recent_turns: 保留最近N轮对话
- keep_recent_percent: 保留最近X%的对话  
- delete_first_turns: 删除最早的N轮对话
- delete_first_percent: 删除最早X%的对话''',
    params_json_schema={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["truncate"],
                "description": "要执行的操作，目前只支持truncate",
                "default": "truncate"
            },
            "method": {
                "type": "string",
                "enum": ["keep_recent_turns", "keep_recent_percent", "delete_first_turns", "delete_first_percent"],
                "description": "截断策略"
            },
            "value": {
                "type": "number",
                "description": "数值参数，对于turns方法是轮数，对于percent方法是百分比(0-100)",
                "minimum": 0
            },
            "preserve_system": {
                "type": "boolean",
                "description": "是否保留系统消息",
                "default": True
            }
        },
        "required": ["method", "value"]
    },
    on_invoke_tool=on_manage_context_invoke
)

async def on_smart_context_truncate_invoke(context: RunContextWrapper, params_str: str) -> Any:
    """智能上下文截取，通过指定区间来精确控制保留内容"""
    try:
        params = json.loads(params_str)
        ranges = params.get("ranges", [])
        preserve_system = params.get("preserve_system", True)
        
        ctx = context.context if hasattr(context, 'context') else {}
        meta = ctx.get("_context_meta", {})
        current_turns = meta.get("turns_in_current_sequence", 0)
        
        # 参数验证
        if not isinstance(ranges, list):
            return {
                "status": "error",
                "message": "ranges参数必须是一个二维列表"
            }
        
        if not ranges:
            return {
                "status": "error", 
                "message": "ranges不能为空，必须指定至少一个保留区间"
            }
        
        # 验证每个区间格式
        validated_ranges = []
        for i, range_item in enumerate(ranges):
            if not isinstance(range_item, list) or len(range_item) != 2:
                return {
                    "status": "error",
                    "message": f"ranges[{i}]必须是包含两个元素的列表[start, end]"
                }
            
            start, end = range_item
            if not isinstance(start, int) or not isinstance(end, int):
                return {
                    "status": "error",
                    "message": f"ranges[{i}]中的start和end必须是整数"
                }
            
            if start < 0 or end < 0:
                return {
                    "status": "error",
                    "message": f"ranges[{i}]中的索引不能为负数"
                }
            
            if start > end:
                return {
                    "status": "error",
                    "message": f"ranges[{i}]中start({start})不能大于end({end})"
                }
            
            if end >= current_turns:
                return {
                    "status": "error",
                    "message": f"ranges[{i}]中end({end})超出了当前轮数范围(0-{current_turns-1})"
                }
            
            validated_ranges.append((start, end))
        
        # 检查区间重叠
        validated_ranges.sort()
        for i in range(1, len(validated_ranges)):
            if validated_ranges[i][0] <= validated_ranges[i-1][1]:
                return {
                    "status": "error",
                    "message": f"区间重叠：[{validated_ranges[i-1][0]}, {validated_ranges[i-1][1]}]与[{validated_ranges[i][0]}, {validated_ranges[i][1]}]"
                }
        
        # 计算保留的轮数
        keep_turns = sum(end - start + 1 for start, end in validated_ranges)
        delete_turns = current_turns - keep_turns
        
        if delete_turns <= 0:
            return {
                "status": "no_action",
                "message": f"指定的区间已涵盖所有轮次，无需截断。",
                "current_turns": current_turns,
                "keep_turns": keep_turns
            }
        
        # 设置智能截断标记
        ctx["_pending_truncate"] = {
            "method": "smart_ranges",
            "ranges": validated_ranges,
            "preserve_system": preserve_system,
            "requested_at_turn": meta.get("current_turn", 0),
            "expected_keep_turns": keep_turns,
            "expected_delete_turns": delete_turns
        }
        
        return {
            "status": "scheduled",
            "message": "已完成智能截断操作。",
            "details": {
                "method": "smart_ranges",
                "ranges": validated_ranges,
                "current_turns": current_turns,
                "will_keep": keep_turns,
                "will_delete": delete_turns,
                "preserve_system_messages": preserve_system
            }
        }
        
    except json.JSONDecodeError:
        return {
            "status": "error",
            "message": "参数格式错误，无法解析JSON"
        }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "message": f"执行智能截断时发生错误: {str(e)}",
            "traceback": traceback.format_exc()
        }

tool_smart_context_truncate = FunctionTool(
    name='local-smart_context_truncate',
    description='''智能上下文截取工具，通过指定区间精确控制保留内容。
接受二维列表[[start1,end1],[start2,end2],...,[startN,endN]]，每个子列表代表一个要保留的闭区间（两端都保留）。
索引从0开始，区间不能重叠，必须按顺序排列。''',
    params_json_schema={
        "type": "object",
        "properties": {
            "ranges": {
                "type": "array",
                "description": "要保留的区间列表，格式：[[start1,end1],[start2,end2],...]，索引从0开始",
                "items": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 2,
                    "items": {
                        "type": "integer",
                        "minimum": 0
                    }
                },
                "minItems": 1
            },
            "preserve_system": {
                "type": "boolean",
                "description": "是否保留系统消息",
                "default": True
            }
        },
        "required": ["ranges"]
    },
    on_invoke_tool=on_smart_context_truncate_invoke
)

# 导出工具列表
context_management_tools = [tool_check_context, tool_manage_context, tool_smart_context_truncate]