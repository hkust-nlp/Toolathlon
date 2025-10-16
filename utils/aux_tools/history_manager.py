# history_manager.py
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

class HistoryManager:
    """Manage reading and searching of history files."""
    
    def __init__(self, history_dir: Path, session_id: str):
        self.history_dir = Path(history_dir)
        self.session_id = session_id
        self.history_file = self.history_dir / f"{session_id}_history.jsonl"
        self._index_cache = None
    
    def _load_history(self) -> List[Dict[str, Any]]:
        """Load the complete history file as a list of records."""
        if not self.history_file.exists():
            return []
        
        history = []
        with open(self.history_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f):
                try:
                    record = json.loads(line)
                    record['_line_index'] = line_num  # Add line index to record
                    history.append(record)
                except json.JSONDecodeError:
                    continue
        
        return history
    
    def search_by_keywords(
        self, 
        keywords: List[str], 
        max_results: Optional[int] = None,
        skip: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Search records that contain all the given keywords.
        Returns: (list of matching records, total matching count)
        """
        history = self._load_history()
        matches = []
        
        # Convert keywords to lowercase for case-insensitive search
        keywords_lower = [k.lower() for k in keywords]
        
        for record in history:
            # Extract search content from raw_content
            search_content = self._extract_search_content(record)
            if search_content:
                search_content_lower = search_content.lower()
                # Check that all keywords appear in the content
                if all(keyword in search_content_lower for keyword in keywords_lower):
                    # Add matching context to record
                    match_context = self._extract_match_context(search_content, keywords)
                    record['match_context'] = match_context
                    matches.append(record)
        
        total_matches = len(matches)
        
        # Apply pagination
        if skip > 0:
            matches = matches[skip:]
        if max_results is not None:
            matches = matches[:max_results]
        
        return matches, total_matches
    
    def _extract_search_content(self, record: Dict[str, Any]) -> str:
        """Extract searchable content from a record."""
        item_type = record.get('item_type', record.get('type', ''))
        
        if item_type == 'message_output_item':
            # Extract message content from raw_content
            raw_content = record.get('raw_content', {})
            if isinstance(raw_content, dict):
                content_parts = []
                for content_item in raw_content.get('content', []):
                    if isinstance(content_item, dict) and content_item.get('type') == 'output_text':
                        content_parts.append(content_item.get('text', ''))
                return ' '.join(content_parts)
        
        elif item_type in ['tool_call_item', 'tool_call_output_item']:
            # For tool call and tool call output, include tool name and arguments
            raw_content = record.get('raw_content', {})
            if isinstance(raw_content, dict):
                tool_name = raw_content.get('name', '')
                arguments = raw_content.get('arguments', '')
                return f"{tool_name} {arguments}"
        
        elif item_type in ['initial_input', 'user_input']:
            # For user input (string or list of strings/objects)
            content = record.get('content', '')
            if isinstance(content, str):
                return content
            elif isinstance(content, list):
                content_parts = []
                for item in content:
                    if isinstance(item, dict):
                        content_parts.append(item.get('content', ''))
                return ' '.join(content_parts)
        
        return ""

    def _extract_role_from_record(self, record: Dict[str, Any]) -> str:
        """Extract role info from a record."""
        item_type = record.get('item_type', record.get('type', ''))
        
        if item_type == 'message_output_item':
            raw_content = record.get('raw_content', {})
            if isinstance(raw_content, dict):
                return raw_content.get('role', 'unknown')
        
        elif item_type in ['initial_input', 'user_input']:
            return 'user'
        
        elif item_type == 'tool_call_item':
            return 'assistant'
        
        elif item_type == 'tool_call_output_item':
            return 'tool'
        
        return 'unknown'

    def _extract_match_context(self, content: str, keywords: List[str], context_length: int = 50) -> str:
        """Extract surrounding context for the first match of any keyword."""
        content_lower = content.lower()
        
        # Find the first keyword match position
        first_match_pos = len(content)
        matched_keyword = ""
        for keyword in keywords:
            pos = content_lower.find(keyword.lower())
            if pos != -1 and pos < first_match_pos:
                first_match_pos = pos
                matched_keyword = keyword
        
        if first_match_pos == len(content):
            return content[:100] + "..." if len(content) > 100 else content
        
        # Extract left and right context around first match
        start = max(0, first_match_pos - context_length)
        end = min(len(content), first_match_pos + len(matched_keyword) + context_length)
        
        context = content[start:end]
        if start > 0:
            context = "..." + context
        if end < len(content):
            context = context + "..."
        
        return context
    
    def get_turn_details(self, turn_number: int, context_turns: int = 2) -> List[Dict[str, Any]]:
        """
        Get the records for a specific turn, including a few turns before and after (context).
        """
        history = self._load_history()
        
        # Collect the indices of all records by turn
        target_records = []
        turn_indices = {}
        
        for i, record in enumerate(history):
            turn = record.get('turn', -1)
            if turn not in turn_indices:
                turn_indices[turn] = []
            turn_indices[turn].append(i)
            
            if turn == turn_number:
                target_records.append(record)
        
        if not target_records:
            return []
        
        # Get min/max turn numbers for context
        min_turn = max(0, turn_number - context_turns)
        max_turn = turn_number + context_turns
        
        context_records = []
        for turn in range(min_turn, max_turn + 1):
            if turn in turn_indices:
                for idx in turn_indices[turn]:
                    record = history[idx].copy()
                    record['is_target_turn'] = (turn == turn_number)
                    context_records.append(record)
        
        return context_records
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the history file."""
        history = self._load_history()
        
        if not history:
            return {
                "total_records": 0,
                "total_turns": 0,
                "date_range": None
            }
        
        # Gather various statistics
        turns = set()
        roles = {}
        item_types = {}
        timestamps = []
        
        for record in history:
            # Turn
            if 'turn' in record:
                turns.add(record['turn'])
            
            # Role (from raw_content)
            role = self._extract_role_from_record(record)
            roles[role] = roles.get(role, 0) + 1
            
            # Item type
            item_type = record.get('item_type', record.get('type', 'unknown'))
            item_types[item_type] = item_types.get(item_type, 0) + 1
            
            # Timestamp
            if 'timestamp' in record:
                timestamps.append(record['timestamp'])
        
        # Calculate date range
        date_range = None
        if timestamps:
            timestamps.sort()
            date_range = {
                "start": timestamps[0],
                "end": timestamps[-1],
                "duration": self._calculate_duration(timestamps[0], timestamps[-1])
            }
        
        return {
            "total_records": len(history),
            "total_turns": len(turns),
            "roles_distribution": roles,
            "item_types_distribution": item_types,
            "date_range": date_range,
            "file_size_bytes": self.history_file.stat().st_size if self.history_file.exists() else 0
        }

    def _extract_searchable_content(self, record: Dict) -> str:
        """Extract all searchable content from a record."""
        content_parts = []
        
        # Handle by different record types
        if record.get("type") == "initial_input":
            content_parts.append(record.get("content", ""))
        
        elif record.get("item_type") == "message_output_item":
            raw_content = record.get("raw_content", {})
            if isinstance(raw_content, dict):
                # Role
                role = raw_content.get("role", "")
                if role:
                    content_parts.append(f"[{role}]")
                
                # Message text
                for content_item in raw_content.get("content", []):
                    if isinstance(content_item, dict) and content_item.get("type") == "output_text":
                        content_parts.append(content_item.get("text", ""))
        
        elif record.get("item_type") == "tool_call_item":
            raw_content = record.get("raw_content", {})
            if isinstance(raw_content, dict):
                tool_name = raw_content.get("name", "")
                if tool_name:
                    content_parts.append(f"[Tool: {tool_name}]")
                
                # Tool arguments
                args = raw_content.get("arguments", {})
                if args:
                    content_parts.append(json.dumps(args, ensure_ascii=False))
        
        elif record.get("item_type") == "tool_call_output_item":
            raw_content = record.get("raw_content", {})
            if isinstance(raw_content, dict):
                output = raw_content.get("output", "")
                if output:
                    content_parts.append(str(output))
        
        elif record.get("item_type") == "user_input":
            content = record.get("content", "")
            if content:
                content_parts.append(content)
        
        return " ".join(content_parts)

    def _calculate_duration(self, start_time: str, end_time: str) -> str:
        """Calculate the duration string between two ISO timestamps."""
        try:
            start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            duration = end - start
            
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            if hours > 0:
                return f"{int(hours)} hours {int(minutes)} minutes"
            elif minutes > 0:
                return f"{int(minutes)} minutes {int(seconds)} seconds"
            else:
                return f"{int(seconds)} seconds"
        except:
            return "unknown"