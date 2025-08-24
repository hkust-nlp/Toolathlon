# context_management_tools.py
import json
from typing import Any, Dict, List
from agents.tool import FunctionTool, RunContextWrapper

async def on_check_context_status_invoke(context: RunContextWrapper, params_str: str) -> Any:
    """Query current context status"""
    try:
        # Get data from context.context
        ctx = context.context if hasattr(context, 'context') and context.context is not None else {}
        
        meta = ctx.get("_context_meta", {})
        session_id = ctx.get("_session_id", "unknown")
        context_limit = ctx.get("_context_limit", 128000)
        
        # Directly use current usage (already cumulative)
        total_tokens = 0
        input_tokens = 0
        output_tokens = 0
        
        if hasattr(context, 'usage') and context.usage:
            total_tokens = context.usage.total_tokens or 0
            input_tokens = context.usage.input_tokens or 0
            output_tokens = context.usage.output_tokens or 0
        
        # Ensure all values are not None
        total_tokens = total_tokens or 0
        context_limit = context_limit or 128000
        
        # Calculate usage percentage
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
            "message": "Unable to get context status"
        }

def _get_status_recommendation(usage_pct: float) -> Dict[str, Any]:
    """Provide recommendations based on usage percentage"""
    if usage_pct >= 90:
        return {
            "level": "critical",
            "message": "Context is about to be exhausted! Strongly recommend cleaning up conversation history immediately.",
            "recommended_action": "manage_context"
        }
    elif usage_pct >= 80:
        return {
            "level": "warning", 
            "message": "Context usage is high, recommend cleaning up some conversation history.",
            "recommended_action": "manage_context"
        }
    elif usage_pct >= 70:
        return {
            "level": "info",
            "message": "Context usage is moderate, consider preventive cleanup.",
            "recommended_action": "monitor"
        }
    else:
        return {
            "level": "good",
            "message": "Context usage is healthy.",
            "recommended_action": "none"
        }

tool_check_context = FunctionTool(
    name='local-check_context_status',
    description='Query current conversation context status, including turn statistics, token usage, truncation history and other information',
    params_json_schema={
        "type": "object",
        "properties": {},
        "required": []
    },
    on_invoke_tool=on_check_context_status_invoke
)

async def on_manage_context_invoke(context: RunContextWrapper, params_str: str) -> Any:
    """Manage context, execute truncation operations"""
    params = json.loads(params_str)
    action = params.get("action", "truncate")
    ctx = context.context if hasattr(context, 'context') else {}
    if action != "truncate":
        return {
            "status": "error",
            "message": f"Unsupported operation: {action}"
        }
    
    method = params.get("method")
    value = params.get("value")
    preserve_system = params.get("preserve_system", True)
    
    # Validate parameters
    valid_methods = ["keep_recent_turns", "keep_recent_percent", "delete_first_turns", "delete_first_percent"]
    if method not in valid_methods:
        return {
            "status": "error",
            "message": f"Invalid method: {method}. Supported methods: {valid_methods}"
        }
    
    if not isinstance(value, (int, float)) or value <= 0:
        return {
            "status": "error",
            "message": f"Invalid value: {value}. Must be a positive number."
        }
    
    # Percentage methods need range checking
    if "percent" in method and (value <= 0 or value >= 100):
        return {
            "status": "error",
            "message": f"Percentage must be between 0-100, current value: {value}"
        }
    
    # Get current statistics
    meta = ctx.get("_context_meta", {})
    current_turns = meta.get("turns_in_current_sequence", 0)
    
    # Pre-calculate how many turns will be kept
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
            "message": f"Currently only {current_turns} turns of conversation, no truncation needed.",
            "current_turns": current_turns,
            "requested_keep": keep_turns
        }
    
    # Set truncation flag
    ctx["_pending_truncate"] = {
        "method": method,
        "value": value,
        "preserve_system": preserve_system,
        "requested_at_turn": meta.get("current_turn", 0),
        "expected_keep_turns": keep_turns,
        "expected_delete_turns": current_turns - keep_turns
    }
    
    return {
        "status": "scheduled", # Although truncation hasn't happened when returning, the next reply will be based on truncated context, so we say it's completed
        "message": "Truncation operation completed.",
        "details": {
            "method": method,
            "value": value,
            "current_turns": current_turns,
            "will_keep": keep_turns,
            "will_delete": current_turns - keep_turns,
            "preserve_system_messages": preserve_system
        },
        # "note": "Truncation will be executed after this turn completes, next reply will be based on truncated context."
    }

tool_manage_context = FunctionTool(
    name='local-manage_context',
    description='''Manage conversation context by deleting historical messages to free up space. Supports multiple strategies:
- keep_recent_turns: Keep the most recent N turns of conversation
- keep_recent_percent: Keep the most recent X% of conversation  
- delete_first_turns: Delete the earliest N turns of conversation
- delete_first_percent: Delete the earliest X% of conversation''',
    params_json_schema={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["truncate"],
                "description": "Operation to execute, currently only supports truncate",
                "default": "truncate"
            },
            "method": {
                "type": "string",
                "enum": ["keep_recent_turns", "keep_recent_percent", "delete_first_turns", "delete_first_percent"],
                "description": "Truncation strategy"
            },
            "value": {
                "type": "number",
                "description": "Numeric parameter, for turns methods it's number of turns, for percent methods it's percentage (0-100)",
                "minimum": 0
            },
            "preserve_system": {
                "type": "boolean",
                "description": "Whether to preserve system messages",
                "default": True
            }
        },
        "required": ["method", "value"]
    },
    on_invoke_tool=on_manage_context_invoke
)

async def on_smart_context_truncate_invoke(context: RunContextWrapper, params_str: str) -> Any:
    """Smart context truncation, precisely control retained content by specifying ranges"""
    try:
        params = json.loads(params_str)
        ranges = params.get("ranges", [])
        preserve_system = params.get("preserve_system", True)
        
        ctx = context.context if hasattr(context, 'context') else {}
        meta = ctx.get("_context_meta", {})
        current_turns = meta.get("turns_in_current_sequence", 0)
        
        # Parameter validation
        if not isinstance(ranges, list):
            return {
                "status": "error",
                "message": "ranges parameter must be a 2D list"
            }
        
        if not ranges:
            return {
                "status": "error", 
                "message": "ranges cannot be empty, must specify at least one retention range"
            }
        
        # Validate each range format
        validated_ranges = []
        for i, range_item in enumerate(ranges):
            if not isinstance(range_item, list) or len(range_item) != 2:
                return {
                    "status": "error",
                    "message": f"ranges[{i}] must be a list containing two elements [start, end]"
                }
            
            start, end = range_item
            if not isinstance(start, int) or not isinstance(end, int):
                return {
                    "status": "error",
                    "message": f"start and end in ranges[{i}] must be integers"
                }
            
            if start < 0 or end < 0:
                return {
                    "status": "error",
                    "message": f"Indexes in ranges[{i}] cannot be negative"
                }
            
            if start > end:
                return {
                    "status": "error",
                    "message": f"start({start}) in ranges[{i}] cannot be greater than end({end})"
                }
            
            if end >= current_turns:
                return {
                    "status": "error",
                    "message": f"end({end}) in ranges[{i}] exceeds current turn range (0-{current_turns-1})"
                }
            
            validated_ranges.append((start, end))
        
        # Check for range overlap
        validated_ranges.sort()
        for i in range(1, len(validated_ranges)):
            if validated_ranges[i][0] <= validated_ranges[i-1][1]:
                return {
                    "status": "error",
                    "message": f"Range overlap: [{validated_ranges[i-1][0]}, {validated_ranges[i-1][1]}] with [{validated_ranges[i][0]}, {validated_ranges[i][1]}]"
                }
        
        # Calculate retained turns
        keep_turns = sum(end - start + 1 for start, end in validated_ranges)
        delete_turns = current_turns - keep_turns
        
        if delete_turns <= 0:
            return {
                "status": "no_action",
                "message": f"Specified ranges already cover all turns, no truncation needed.",
                "current_turns": current_turns,
                "keep_turns": keep_turns
            }
        
        # Set smart truncation flag
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
            "message": "Smart truncation operation completed.",
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
            "message": "Parameter format error, unable to parse JSON"
        }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "message": f"Error occurred while executing smart truncation: {str(e)}",
            "traceback": traceback.format_exc()
        }

tool_smart_context_truncate = FunctionTool(
    name='local-smart_context_truncate',
    description='''Smart context truncation tool that precisely controls retained content by specifying ranges.
Accepts 2D list [[start1,end1],[start2,end2],...,[startN,endN]], each sublist represents a closed range to retain (both ends included).
Indexing starts from 0, ranges cannot overlap, must be arranged in order.''',
    params_json_schema={
        "type": "object",
        "properties": {
            "ranges": {
                "type": "array",
                "description": "List of ranges to retain, format: [[start1,end1],[start2,end2],...], indexing starts from 0",
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
                "description": "Whether to preserve system messages",
                "default": True
            }
        },
        "required": ["ranges"]
    },
    on_invoke_tool=on_smart_context_truncate_invoke
)

# Export tool list
context_management_tools = [tool_check_context, tool_manage_context, tool_smart_context_truncate]