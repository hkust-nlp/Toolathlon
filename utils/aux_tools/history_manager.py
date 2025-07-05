# history_manager.py
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

class HistoryManager:
    """管理历史文件的读取和搜索"""
    
    def __init__(self, history_dir: Path, session_id: str):
        self.history_dir = Path(history_dir)
        self.session_id = session_id
        self.history_file = self.history_dir / f"{session_id}_history.jsonl"
        self._index_cache = None
    
    def _load_history(self) -> List[Dict[str, Any]]:
        """加载完整历史"""
        if not self.history_file.exists():
            return []
        
        history = []
        with open(self.history_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f):
                try:
                    record = json.loads(line)
                    record['_line_index'] = line_num  # 添加行索引
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
        """搜索包含关键词的记录
        
        返回: (匹配的记录列表, 总匹配数)
        """
        history = self._load_history()
        matches = []
        
        # 转换关键词为小写以进行不区分大小写的搜索
        keywords_lower = [k.lower() for k in keywords]
        
        for record in history:
            # 搜索内容字段
            content = record.get('content', '')
            if isinstance(content, str):
                content_lower = content.lower()
                # 检查所有关键词是否都出现
                if all(keyword in content_lower for keyword in keywords_lower):
                    # 添加匹配上下文
                    match_context = self._extract_match_context(content, keywords)
                    record['match_context'] = match_context
                    matches.append(record)
        
        total_matches = len(matches)
        
        # 应用分页
        if skip > 0:
            matches = matches[skip:]
        if max_results is not None:
            matches = matches[:max_results]
        
        return matches, total_matches
    
    def _extract_match_context(self, content: str, keywords: List[str], context_length: int = 50) -> str:
        """提取关键词周围的上下文"""
        content_lower = content.lower()
        
        # 找到第一个关键词的位置
        first_match_pos = len(content)
        matched_keyword = ""
        for keyword in keywords:
            pos = content_lower.find(keyword.lower())
            if pos != -1 and pos < first_match_pos:
                first_match_pos = pos
                matched_keyword = keyword
        
        if first_match_pos == len(content):
            return content[:100] + "..." if len(content) > 100 else content
        
        # 提取上下文
        start = max(0, first_match_pos - context_length)
        end = min(len(content), first_match_pos + len(matched_keyword) + context_length)
        
        context = content[start:end]
        if start > 0:
            context = "..." + context
        if end < len(content):
            context = context + "..."
        
        return context
    
    def get_turn_details(self, turn_number: int, context_turns: int = 2) -> List[Dict[str, Any]]:
        """获取特定轮次的详细信息，包括前后文"""
        history = self._load_history()
        
        # 找到目标轮次的所有记录
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
        
        # 获取前后文轮次
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
        """获取历史统计信息"""
        history = self._load_history()
        
        if not history:
            return {
                "total_records": 0,
                "total_turns": 0,
                "date_range": None
            }
        
        # 统计各种信息
        turns = set()
        roles = {}
        item_types = {}
        timestamps = []
        
        for record in history:
            # 轮次
            if 'turn' in record:
                turns.add(record['turn'])
            
            # 角色
            role = record.get('role', 'unknown')
            roles[role] = roles.get(role, 0) + 1
            
            # 类型
            item_type = record.get('item_type', record.get('type', 'unknown'))
            item_types[item_type] = item_types.get(item_type, 0) + 1
            
            # 时间戳
            if 'timestamp' in record:
                timestamps.append(record['timestamp'])
        
        # 计算时间范围
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
    
    def _calculate_duration(self, start_time: str, end_time: str) -> str:
        """计算时间差"""
        try:
            start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            duration = end - start
            
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            if hours > 0:
                return f"{int(hours)}小时{int(minutes)}分钟"
            elif minutes > 0:
                return f"{int(minutes)}分钟{int(seconds)}秒"
            else:
                return f"{int(seconds)}秒"
        except:
            return "未知"