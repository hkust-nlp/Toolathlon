# context_managed_runner.py (English version)
import json
from typing import Dict, Any, List, Union, Optional
from datetime import datetime
from pathlib import Path

from agents import Runner, RunConfig, RunHooks, Agent, RunResult
from agents.run_context import RunContextWrapper
from agents.items import (
    RunItem, TResponseInputItem, MessageOutputItem, 
    ToolCallItem, ToolCallOutputItem, ItemHelpers
)
from openai.types.responses import ResponseOutputMessage, ResponseOutputText
from utils.api_model.model_provider import ContextTooLongError

class ContextManagedRunner(Runner):
    """A Runner that supports context management and history recording."""
    
    # Default directory for storing conversation history files
    DEFAULT_HISTORY_DIR = Path("conversation_histories")
    
    @classmethod
    async def run(
        cls,
        starting_agent: Agent,
        input: str | list[TResponseInputItem],
        *,
        context: Any = None,
        max_turns: int = 10,
        hooks: RunHooks | None = None,
        run_config: RunConfig | None = None,
        previous_response_id: str | None = None,
        history_dir: Union[str, Path, None] = None,  # newly added parameter
        session_id: Optional[str] = None,  # allow specifying session_id
    ) -> RunResult:
        """Override the run method to add context management functionality.
        
        Args:
            history_dir: Directory to store conversation history files. Use default if None.
            session_id: Specify the session ID. If None, one is generated automatically.
            ... other parameters as in the parent class.
        """
        
        # Handle history directory
        if history_dir is None:
            history_dir = cls.DEFAULT_HISTORY_DIR
        else:
            history_dir = Path(history_dir)
        
        # Make sure the directory exists
        history_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate or use provided session ID
        if session_id is None:
            session_id = cls._generate_session_id()
        
        # Create wrapped context
        if context is None:
            context = {}
        
        # Initialize context metadata, including history dir info
        wrapped_context = cls._init_context_metadata(context, session_id, history_dir)
        
        # Record initial input to history (already managed by user side, skip here)
        # cls._save_initial_input_to_history(session_id, input, history_dir)

        # Call the parent run method
        result = await super().run(
            starting_agent=starting_agent,
            input=input,
            context=wrapped_context,
            max_turns=max_turns,
            hooks=hooks,
            run_config=run_config,
            previous_response_id=previous_response_id,
        )
        
        return result

    @classmethod
    def run_sync(
        cls,
        starting_agent: Agent,
        input: str | list[TResponseInputItem],
        *,
        context: Any = None,
        max_turns: int = 10,
        hooks: RunHooks | None = None,
        run_config: RunConfig | None = None,
        previous_response_id: str | None = None,
        history_dir: Union[str, Path, None] = None,  # new parameter
        session_id: Optional[str] = None,  # allow specifying session_id
    ) -> RunResult:
        """Synchronous version of run, supporting history recording."""
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            cls.run(
                starting_agent=starting_agent,
                input=input,
                context=context,
                max_turns=max_turns,
                hooks=hooks,
                run_config=run_config,
                previous_response_id=previous_response_id,
                history_dir=history_dir,
                session_id=session_id,
            )
        )

    @classmethod
    def _init_context_metadata(cls, context: Any, session_id: str, history_dir: Path) -> Any:
        """Initialize or update context metadata."""
        # If context is None, create a new one
        if context is None:
            context = {}
        
        # Check if already initialized
        if "_context_meta" in context:
            # Already initialized, don't overwrite
            return context
        
        # First-time initialization
        metadata = {
            "session_id": session_id,
            "history_dir": str(history_dir),
            "started_at": datetime.now().isoformat(),
            "current_turn": 0,
            "total_turns_ever": 0,
            "turns_in_current_sequence": 0,
            "mini_turns_in_current_sequence": 0,
            "boundary_in_current_sequence": [],
            "truncated_turns": 0,
            "truncation_history": []
        }
        
        context["_session_id"] = session_id
        context["_history_dir"] = str(history_dir)
        context["_context_meta"] = metadata
        context["_context_limit"] = context.get("_context_limit", 128000)
        
        return context

    @classmethod
    async def _run_single_turn(cls, **kwargs):
        # print('----IN-----')
        """Override single step execution, add history saving and truncation checking."""
        
        # Get context_wrapper
        context_wrapper = kwargs.get('context_wrapper')
        original_input = kwargs.get('original_input')
        generated_items = kwargs.get('generated_items', [])
        agent = kwargs.get('agent')

        # context_wrapper.context is our data storage
        ctx = context_wrapper.context if context_wrapper and hasattr(context_wrapper, 'context') else {}

        # Set the model's context window info
        if ctx and ("_context_limit" not in ctx or ctx["_context_limit"] is None):
            model_name = agent.model.model
            from utils.api_model.model_provider import API_MAPPINGS
            
            context_limit_found = False
            for key, mapping in API_MAPPINGS.items():
                if model_name == key:
                    ctx["_context_limit"] = mapping.context_window
                    context_limit_found = True
                    break
                # Or check if in api_model mapping
                elif 'api_model' in mapping:
                    for provider, api_model_name in mapping.api_model.items():
                        if model_name == api_model_name:
                            ctx["_context_limit"] = mapping.context_window
                            context_limit_found = True
                            break
                    if context_limit_found:
                        break
            
            # # If not found, set to default
            # if not context_limit_found:
            #     ctx["_context_limit"] = 128000
        # print("Model:", model_name, "context window", ctx["_context_limit"])

        # Get history directory
        history_dir = Path(ctx.get("_history_dir", cls.DEFAULT_HISTORY_DIR))
        
        # Record number of generated items before execution, so we can identify new ones
        items_before = len(generated_items)

        # Update turn info
        # Get and update metadata
        meta = ctx.get("_context_meta", {})
        if "turns_in_current_sequence" not in meta:
            meta["turns_in_current_sequence"] = 0

        meta["current_turn"] = meta.get("current_turn", 0) + 1
        meta["total_turns_ever"] = meta.get("total_turns_ever", 0) + 1
        meta["turns_in_current_sequence"] = meta.get("turns_in_current_sequence", 0) + 1


        # Call parent method for actual execution
        try:
            result = await super()._run_single_turn(**kwargs)
        except ContextTooLongError as e:
            # Flag need for forced context reset, record steps executed
            ctx["_force_reset_context"] = {
                "reason": str(e),
                "token_count": getattr(e, 'token_count', None),
                "max_tokens": getattr(e, 'max_tokens', None),
                "timestamp": datetime.now().isoformat(),
                "executed_mini_turns": meta.get("mini_turns_in_current_sequence", 0),
                "executed_turns": meta.get("turns_in_current_sequence", 0)
            }
            # Raise to let upper logic handle
            raise


        meta["boundary_in_current_sequence"].append((meta["mini_turns_in_current_sequence"], 
                                                     meta["mini_turns_in_current_sequence"]+len(result.new_step_items)))
        # print("len(meta['boundary_in_current_sequence'])", len(meta["boundary_in_current_sequence"]))
        # print("meta['turns_in_current_sequence']", meta["turns_in_current_sequence"])
        
        assert len(meta["boundary_in_current_sequence"]) == meta["turns_in_current_sequence"], (
            f"Length of boundary_in_current_sequence does not match turns_in_current_sequence: "
            f"{len(meta['boundary_in_current_sequence'])} != {meta['turns_in_current_sequence']}, "
            f"boundary_in_current_sequence: {meta['boundary_in_current_sequence']}"
        )
        meta["mini_turns_in_current_sequence"] += len(result.new_step_items)

        # Update cumulative usage info into context
        if hasattr(context_wrapper, 'usage'):
            ctx["_cumulative_usage"] = {
                "total_tokens": context_wrapper.usage.total_tokens,
                "input_tokens": context_wrapper.usage.input_tokens,
                "output_tokens": context_wrapper.usage.output_tokens,
                "requests": context_wrapper.usage.requests
            }

        # Save new items to history
        session_id = ctx.get("_session_id")
        # print("session_id", session_id, "len(generated_items)", len(generated_items), "items_before", items_before)
        # if session_id and len(generated_items) > items_before:
            # new_items = generated_items[items_before:]
        cls._save_items_to_history(
            session_id=session_id,
            turn_number=meta.get("current_turn", 0),
            items=result.new_step_items,
            agent_name=agent.name if agent else "unknown",
            history_dir=history_dir
        )
        
        # Check for pending truncation request
        pending_truncate = ctx.get("_pending_truncate")
        # print("pending_truncate", pending_truncate)

        # Get all sequential items; type is list[TResponseInputItem]
        all_seq_items = ItemHelpers.input_to_new_input_list(original_input)
        all_seq_items.extend([generated_item.to_input_item() for generated_item in generated_items])

        # TODO: Currently we ignore pre_step_items and new_step_items, just use all_seq_items
        # But that makes it impossible to tell which are pre_step_items and which new
        # So a better solution is needed to handle this
        if pending_truncate:
            cls._handle_truncation(
                original_input=original_input,
                pre_step_items=result.pre_step_items,
                new_step_items=result.new_step_items,
                truncate_params=pending_truncate,
                context_wrapper=context_wrapper
            )
            # Clear flag
            ctx["_pending_truncate"] = None
            
            # # Optionally update turn_result
            # result.original_input = original_input
            # result.pre_step_items = []
            # result.new_step_items = ctx["_truncated_items"]
        # else:
        #     result.original_input = []
        #     result.pre_step_items = []
        #     result.new_step_items = all_seq_items.copy()
        
        # # Update context statistics (optional)
        # cls._update_context_stats(context_wrapper, generated_items)
        
        # print("result.next_step", result.next_step)
        # print('----OUT-----')
        
        return result
    
    @classmethod
    def _handle_truncation(
        cls,
        original_input: List[TResponseInputItem],
        pre_step_items: List[RunItem],
        new_step_items: List[RunItem],
        truncate_params: Dict[str, Any],
        context_wrapper: RunContextWrapper
    ):
        """Handle context truncation request."""
        method = truncate_params.get("method")
        value = truncate_params.get("value")
        preserve_system = truncate_params.get("preserve_system", True)
        
        ctx = context_wrapper.context if context_wrapper else {}
        meta = ctx.get("_context_meta", {})
        
        # Get all turn boundaries
        turn_boundaries = ctx["_context_meta"]["boundary_in_current_sequence"]
        total_turns = len(turn_boundaries)
        
        # Assert turn count consistency
        current_turns_in_sequence = meta.get("turns_in_current_sequence", 0)
        assert total_turns == current_turns_in_sequence, (
            f"Turn boundary count ({total_turns}) does not equal turns_in_current_sequence ({current_turns_in_sequence})"
        )
        
        if total_turns == 0:
            return  # Nothing to truncate
        
        # Apply truncation strategy
        keep_turns = total_turns  # Default keep all
        
        if method == "keep_recent_turns":
            keep_turns = min(int(value), total_turns)
        elif method == "keep_recent_percent":
            keep_turns = max(1, int(total_turns * value / 100))
        elif method == "delete_first_turns":
            keep_turns = max(1, total_turns - int(value))
        elif method == "delete_first_percent":
            delete_turns = int(total_turns * value / 100)
            keep_turns = max(1, total_turns - delete_turns)
        
        # Do the truncation
        if keep_turns < total_turns:
            print("keep_turns < total_turns, truncating history")
            
            # Calculate number of turns to delete
            delete_turns = total_turns - keep_turns
            
            # Remove items in order: original_input -> pre_step_items -> new_step_items
            deleted_items_count = cls._truncate_sequential_lists(
                original_input, pre_step_items, new_step_items, 
                turn_boundaries, delete_turns, preserve_system
            )
            
            if deleted_items_count > 0:
                meta["turns_in_current_sequence"] = keep_turns
                meta["truncated_turns"] = meta.get("truncated_turns", 0) + delete_turns
                meta["truncation_history"].append({
                    "at_turn": meta["current_turn"],
                    "method": method,
                    "value": value,
                    "deleted_items": deleted_items_count,
                    "deleted_turns": delete_turns,
                    "timestamp": datetime.now().isoformat()
                })
                ctx["_context_truncated"] = True
                
                # Update mini_turns_in_current_sequence
                meta["mini_turns_in_current_sequence"] = len(original_input) + len(pre_step_items) + len(new_step_items)
                
                # Update boundary info, subtract deleted item count
                meta["boundary_in_current_sequence"] = [
                    (start - deleted_items_count, end - deleted_items_count)
                    for start, end in turn_boundaries[-keep_turns:]
                ]
    
    @classmethod
    def _find_turn_boundaries(cls, items: List[TResponseInputItem]) -> List[tuple[int, int]]:
        """Find dialogue turn boundaries [(start_idx, end_idx), ...]
        
        Turn is defined as: a user or assistant message starts a new turn, tools are attached to their preceding assistant.
        """
        boundaries = []
        # TODO: implement this
        
        return boundaries
    
    @classmethod
    def _truncate_sequential_lists(
        cls,
        original_input: List[TResponseInputItem],
        pre_step_items: List[RunItem],
        new_step_items: List[RunItem],
        boundaries: List[tuple[int, int]],
        delete_turns: int,
        preserve_system: bool
    ) -> int:
        """Truncate three lists in order, deleting items of given count from the front."""
        if delete_turns <= 0:
            return 0
        
        # Compute where to start deleting
        delete_from_boundary = boundaries[delete_turns - 1]
        delete_from_idx = delete_from_boundary[1]
        
        # Delete sequentially
        deleted_count = 0
        
        # First remove from original_input
        if delete_from_idx <= len(original_input):
            original_input[:] = original_input[delete_from_idx:]
            deleted_count = delete_from_idx
        else:
            # Remove all from original_input
            deleted_count = len(original_input)
            original_input.clear()
            remaining_delete = delete_from_idx - deleted_count
            if remaining_delete <= len(pre_step_items):
                pre_step_items[:] = pre_step_items[remaining_delete:]
                deleted_count += remaining_delete
            else:
                # Remove all pre_step_items
                deleted_count += len(pre_step_items)
                pre_step_items.clear()
                # Remove rest from new_step_items
                remaining_delete = delete_from_idx - deleted_count
                if remaining_delete <= len(new_step_items):
                    new_step_items[:] = new_step_items[remaining_delete:]
                    deleted_count += remaining_delete
                else:
                    # Remove all new_step_items
                    new_step_items.clear()
                    deleted_count = delete_from_idx
        
        return deleted_count
    
    @classmethod
    def _create_truncation_notice(cls, method: str, value: Any, deleted_items: int, deleted_turns: int) -> MessageOutputItem:
        """Create a system truncation notice message."""
        content = (f"[Context Management] Due to token limit, used strategy {method}({value}) for truncation. "
                   f"{deleted_items} message(s) (about {deleted_turns} turns) were deleted.")
        
        # Create a system message
        raw_message = ResponseOutputMessage(
            id="system_truncation",
            content=[ResponseOutputText(
                text=content,
                type="output_text",
                annotations=[]
            )],
            role="system",
            type="message",
            status="completed"
        )
        
        # Use a placeholder agent for this system message.
        from agents import Agent
        placeholder_agent = Agent(name="system", model="gpt-4")
        
        return MessageOutputItem(
            agent=placeholder_agent,
            raw_item=raw_message
        )
    
    @classmethod
    def _save_items_to_history(
        cls,
        session_id: str,
        turn_number: int,
        items: List[RunItem],
        agent_name: str,
        history_dir: Path
    ):
        """Save items to the history file."""
        history_path = history_dir / f"{session_id}_history.jsonl"
        # Ensure directory exists
        history_path.parent.mkdir(parents=True, exist_ok=True)
        
        # print("Entering _save_items_to_history")
        with open(history_path, 'a', encoding='utf-8') as f:
            for step_idx, item in enumerate(items):
                # print("Saving item")
                record = {
                    "in_turn_steps": step_idx,  # Step index within the turn
                    "turn": turn_number,
                    "timestamp": datetime.now().isoformat(),
                    "agent": agent_name,
                    "item_type": item.type,
                    "raw_content": item.raw_item.model_dump() if hasattr(item.raw_item, 'model_dump') else item.raw_item
                }
                
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    @classmethod
    def _save_initial_input_to_history(cls, 
                                       session_id: str, 
                                       input: Union[str, List[TResponseInputItem]], 
                                       history_dir: Path,
                                       turn_number: int = 0):
        """Save the initial input to history."""
        history_path = history_dir / f"{session_id}_history.jsonl"
        # Ensure directory exists
        history_path.parent.mkdir(parents=True, exist_ok=True)

        # Check for existing initial input entry
        if history_path.exists():
            with open(history_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        if record.get("type") == "initial_input":
                            return  # Already exists
                    except json.JSONDecodeError:
                        continue

        with open(history_path, 'a', encoding='utf-8') as f:
            record = {
                "in_turn_steps": 0,  # Initial input is always the first step
                "turn": turn_number,
                "timestamp": datetime.now().isoformat(),
                "type": "initial_input",
                "content": input if isinstance(input, str) else [item.model_dump() for item in input]
            }
            f.write(json.dumps(record, ensure_ascii=False) + '\n')


    @classmethod
    def _save_user_input_to_history(cls, session_id: str, user_input: Union[str, TResponseInputItem], history_dir: Path, turn_number: int):
        """Save user input to history."""
        history_path = Path(history_dir) / f"{session_id}_history.jsonl"
        # Ensure directory exists
        history_path.parent.mkdir(parents=True, exist_ok=True)

        with open(history_path, 'a', encoding='utf-8') as f:
            record = {
                "in_turn_steps": 0,  # User input is the first step in its turn
                "turn": turn_number,
                "timestamp": datetime.now().isoformat(),
                "type": "user_input",
                "content": user_input if isinstance(user_input, str) else [item.model_dump() for item in user_input]
            }
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    @classmethod
    def _generate_session_id(cls) -> str:
        """Generate a unique session ID."""
        from uuid import uuid4
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"


    @classmethod
    def get_formatted_history(cls, history_dir: Union[str, Path], session_id: str) -> List[Dict[str, Any]]:
        """Get formatted conversation history suitable for logging.
        
        Returns:
            The formatted message list, suitable for logging.
        """
        history_file = Path(history_dir) / f"{session_id}_history.jsonl"
        
        if not history_file.exists():
            return []
        
        formatted_messages = []
        
        # Read all records, sorted by turn and step
        records = []
        with open(history_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line)
                    records.append(record)
                except json.JSONDecodeError:
                    continue
        
        records.sort(key=lambda x: (x.get("turn", 0), x.get("in_turn_steps", 0)))
        
        # Process each turn
        current_turn = -1
        current_turn_records = []
        
        for record in records:
            # Skip initial input record
            if record.get("type") == "initial_input":
                continue
                
            turn = record.get("turn", 0)
            
            # If turn changes, process previous turn's records
            if turn != current_turn and current_turn_records:
                formatted_messages.extend(cls._process_turn_records(current_turn_records))
                current_turn_records = []
            
            current_turn = turn
            current_turn_records.append(record)
        
        # Process last turn's records
        if current_turn_records:
            formatted_messages.extend(cls._process_turn_records(current_turn_records))
        
        return formatted_messages
    
    @classmethod
    def _process_turn_records(cls, records: List[Dict]) -> List[Dict]:
        """Process the records of a single turn, returns the formatted message list."""
        formatted_messages = []
        item_index = 0
        
        while item_index < len(records):
            current_record = records[item_index]
            
            if current_record.get("type") == "user_input":
                # User input
                content = current_record.get("content", "")
                if isinstance(content, list):
                    # If content is a list, extract text parts
                    content_parts = []
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            content_parts.append(item.get("text", ""))
                    content = " ".join(content_parts)
                
                formatted_messages.append({
                    "role": "user",
                    "content": content
                })
                item_index += 1
                
            elif current_record.get("item_type") == "message_output_item":
                raw_content = current_record.get("raw_content", {})
                role = "unknown"
                content = ""
                
                if isinstance(raw_content, dict):
                    role = raw_content.get("role", "unknown")
                    # Extract text content
                    content_parts = []
                    for content_item in raw_content.get("content", []):
                        if isinstance(content_item, dict) and content_item.get("type") == "output_text":
                            content_parts.append(content_item.get("text", ""))
                    content = " ".join(content_parts)
                
                if role == "system" and "Context Management" in content:
                    # Skip context management system messages
                    item_index += 1
                    continue
                
                # Check if this is the last message (no following tool call)
                if item_index == len(records) - 1:
                    # Last message, final assistant reply
                    formatted_messages.append({
                        "role": role,
                        "content": content
                    })
                    item_index += 1
                else:
                    # Not last; check if tools follow
                    tool_calls = []
                    next_index = item_index + 1
                    
                    # Collect subsequent tool calls
                    while next_index < len(records) and records[next_index].get("item_type") == "tool_call_item":
                        tool_record = records[next_index]
                        raw_content = tool_record.get("raw_content", {})
                        tool_call = {
                            "id": raw_content.get("call_id", "unknown") if isinstance(raw_content, dict) else "unknown",
                            "type": "function",
                            "function": {
                                "name": raw_content.get("name", "unknown") if isinstance(raw_content, dict) else "unknown",
                                "arguments": raw_content.get("arguments", "{}") if isinstance(raw_content, dict) else "{}"
                            }
                        }
                        tool_calls.append(tool_call)
                        next_index += 1
                    
                    if tool_calls:
                        # Assistant message with tool calls
                        formatted_messages.append({
                            "role": role,
                            "content": content,
                            "tool_calls": tool_calls
                        })
                        item_index = next_index
                    else:
                        # No tool call
                        formatted_messages.append({
                            "role": role,
                            "content": content
                        })
                        item_index += 1
                        
            elif current_record.get("item_type") == "tool_call_item":
                # Tool call with no content
                tool_calls = []
                next_index = item_index
                
                # Collect consecutive tool calls
                while next_index < len(records) and records[next_index].get("item_type") == "tool_call_item":
                    tool_record = records[next_index]
                    raw_content = tool_record.get("raw_content", {})
                    tool_call = {
                        "id": raw_content.get("call_id", "unknown") if isinstance(raw_content, dict) else "unknown",
                        "type": "function",
                        "function": {
                            "name": raw_content.get("name", "unknown") if isinstance(raw_content, dict) else "unknown",
                            "arguments": raw_content.get("arguments", "{}") if isinstance(raw_content, dict) else "{}"
                        }
                    }
                    tool_calls.append(tool_call)
                    next_index += 1
                
                # Create an assistant message without content
                formatted_messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": tool_calls
                })
                item_index = next_index
                
            elif current_record.get("item_type") == "tool_call_output_item":
                # Tool execution result
                raw_content = current_record.get("raw_content", {})
                formatted_messages.append({
                    "role": "tool",
                    "content": raw_content.get("output", "") if isinstance(raw_content, dict) else "",
                    "tool_call_id": raw_content.get("call_id", "unknown") if isinstance(raw_content, dict) else "unknown"
                })
                item_index += 1
                
            else:
                # Skip other types of records
                item_index += 1
        
        return formatted_messages

    @classmethod
    def get_recent_turns_summary(cls, history_dir: Union[str, Path], session_id: str, num_turns: int = 5) -> str:
        """Get simplified summary of last N rounds for memory on context reset.
        
        Args:
            history_dir: History file directory
            session_id: Session ID
            num_turns: Number of rounds to summarize
            
        Returns:
            Formatted summary as string
        """
        history_file = Path(history_dir) / f"{session_id}_history.jsonl"
        
        if not history_file.exists():
            return "No history"
        
        # Read all records, group by turn
        records = []
        with open(history_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line)
                    records.append(record)
                except json.JSONDecodeError:
                    continue
        
        # Sort by turn and step
        records.sort(key=lambda x: (x.get("turn", 0), x.get("in_turn_steps", 0)))
        
        # Group by turn number
        turns_data = {}
        for record in records:
            turn_num = record.get("turn", 0)
            if turn_num not in turns_data:
                turns_data[turn_num] = []
            turns_data[turn_num].append(record)
        
        # Select recent turn numbers
        recent_turn_nums = sorted(turns_data.keys())[-num_turns:] if len(turns_data) > num_turns else sorted(turns_data.keys())
        
        if not recent_turn_nums:
            return "No recent turns"
        
        summary_lines = []
        summary_lines.append(f"=== Overview of recent {len(recent_turn_nums)} turns of interaction history ===")
        
        for turn_num in recent_turn_nums:
            turn_records = turns_data[turn_num]
            summary_lines.append(f"\nTurn#{turn_num}:")
            
            for record in turn_records:
                if record.get("type") == "user_input":
                    # User input
                    content = record.get("content", "")
                    if isinstance(content, list):
                        # Handle list content
                        content_parts = []
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                content_parts.append(item.get("text", ""))
                        content = " ".join(content_parts)
                    
                    formatted_content = cls._format_multiline_content(content, max_length=500)
                    summary_lines.append(f"  User:")
                    summary_lines.append(f"    {formatted_content}")
                    
                elif record.get("item_type") == "message_output_item":
                    # Agent response
                    raw_content = record.get("raw_content", {})
                    role = raw_content.get("role", "unknown")
                    
                    if role == "assistant":
                        # Extract text content
                        content_parts = []
                        for content_item in raw_content.get("content", []):
                            if isinstance(content_item, dict) and content_item.get("type") == "output_text":
                                content_parts.append(content_item.get("text", ""))
                        content = " ".join(content_parts)
                        
                        if content.strip():  # Only display non-empty content
                            formatted_content = cls._format_multiline_content(content, max_length=500)
                            summary_lines.append(f"  Assistant:")
                            summary_lines.append(f"    {formatted_content}")
                
                elif record.get("item_type") == "tool_call_item":
                    # Tool call
                    raw_content = record.get("raw_content", {})
                    if isinstance(raw_content, dict):
                        tool_name = raw_content.get("name", "unknown")
                        call_id = raw_content.get("call_id", "unknown")
                        arguments = raw_content.get("arguments", "{}")
                        
                        # Format multi-line arg content
                        formatted_args = cls._format_multiline_content(arguments, max_length=300)
                        summary_lines.append(f"  Tool Call: {tool_name}")
                        summary_lines.append(f"    ID: {call_id}")
                        summary_lines.append(f"    Args: {formatted_args}")
                    else:
                        summary_lines.append(f"  Tool Call: unknown")
                    
                elif record.get("item_type") == "tool_call_output_item":
                    # Tool execution result
                    raw_content = record.get("raw_content", {})
                    if isinstance(raw_content, dict):
                        call_id = raw_content.get("call_id", "unknown")
                        output = raw_content.get("output", "")
                        if output.strip():
                            formatted_output = cls._format_multiline_content(output, max_length=400)
                            summary_lines.append(f"  Tool Result (ID: {call_id}):")
                            summary_lines.append(f"    {formatted_output}")
                    else:
                        summary_lines.append(f"  Tool Result: unknown")
        
        summary_lines.append("\nNote: This is a simplified overview. Please use the history record search tool to view the complete content and search information in it.")
        return "\n".join(summary_lines)
    
    @classmethod
    def _format_multiline_content(cls, content: str, max_length: int = 500) -> str:
        """Format multi-line content; handle line breaks and length limits.
        
        Args:
            content: Raw content.
            max_length: Max allowed length.
            
        Returns:
            Formatted content string.
        """
        if not content:
            return "[No content]"
        
        content = content.strip()
        
        # If content isn't long, return as-is (keep newlines)
        if len(content) <= max_length:
            lines = content.split('\n')
            if len(lines) <= 1:
                return content
            else:
                # Multiline: indent each line but the first
                formatted_lines = [lines[0]]
                for line in lines[1:]:
                    formatted_lines.append(f"    {line}")
                return '\n'.join(formatted_lines)
        
        # Content too long, try to truncate by lines first
        lines = content.split('\n')
        if len(lines) > 1:
            accumulated = []
            current_length = 0
            
            for line in lines:
                if current_length + len(line) + 1 <= max_length - 20:  # reserve room for ellipsis and notice
                    accumulated.append(line)
                    current_length += len(line) + 1
                else:
                    break
            
            if accumulated:
                result_lines = [accumulated[0]]
                for line in accumulated[1:]:
                    result_lines.append(f"    {line}")
                
                if len(accumulated) < len(lines):
                    result_lines.append(f"    ... (truncated, total {len(lines)} lines, {len(content)} chars)")
                
                return '\n'.join(result_lines)
        
        # Single-line or line truncation didn't help, do head/tail cutoff
        half_length = (max_length - 20) // 2
        truncated = content[:half_length] + " ... " + content[-half_length:]
        return f"{truncated}\n    (truncated from {len(content)} chars)"

    @classmethod
    def _format_content_with_truncation(cls, content: str, max_length: int = 500) -> str:
        """Format content, truncate if over limit.
        
        Args:
            content: Raw content
            max_length: Max total length
            
        Returns:
            Formatted content string
        """
        if not content:
            return "[No content]"
        
        content = content.strip()
        if len(content) <= max_length:
            return content
        
        # Truncation: 250 chars head + ... + 250 chars tail
        half_length = (max_length - 5) // 2  # minus " ... "
        truncated = content[:half_length] + " ... " + content[-half_length:]
        return f"(actual length: {len(content)} chars, truncated to {max_length} chars) {truncated} "

    @classmethod
    def get_session_stats(cls, history_dir: Union[str, Path], session_id: str) -> Dict[str, Any]:
        """Get session statistics."""
        history_file = Path(history_dir) / f"{session_id}_history.jsonl"
        
        if not history_file.exists():
            return {}
        
        stats = {
            "total_turns": 0,
            "total_messages": 0,
            "tool_calls": 0,
            "truncations": 0,
            "user_input_turns": 0,
            "assistant_turns": 0, # Assistant turns are assistant outputs + all their tool executions count as one
        }
        
        with open(history_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line)
                    stats["total_messages"] += 1
                    
                    if record.get("type") == "user_input":
                        stats["user_input_turns"] += 1
                    if record.get("item_type") == "message_output_item":
                        pass
                    elif record.get("item_type") == "tool_call_item":
                        stats["tool_calls"] += 1
                        
                except json.JSONDecodeError:
                    continue
            # stats["total_turns"] is "turn" from last line + 1 (since user input is included), and watch for 0-based index
            stats["total_turns"] = record.get("turn", 0)+1
            stats["assistant_turns"] = record.get("turn", 0)+1 - stats["user_input_turns"]
            
        
        return stats