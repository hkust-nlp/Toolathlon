import json
import os
import csv
import sqlite3
from typing import Optional, List, Dict, Any, Union, Callable
from datetime import datetime
import threading
from pathlib import Path
from utils.general.base_models import CostReport, Tool, ToolCall
import time
import logging

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class RequestLogger:
    """
    Request logger supporting concurrent file-safe writing.
    """
    
    def __init__(self, log_file: Optional[str] = None, enable_console: bool = False):
        """
        Initialize the logger.
        
        Args:
            log_file: Path to the log file. If None, file logging is disabled.
            enable_console: Whether to also print logs to the console.
        """
        self.log_file = log_file
        self.enable_console = enable_console
        self._lock = threading.Lock()
        self._request_counter = 0
        
        # Ensure directory exists if logging to file
        if self.log_file:
            Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
            self._write_header()
    
    def _write_header(self):
        """Write log file header."""
        header = {
            "log_created_at": datetime.now().isoformat(),
            "log_type": "openai_chat_completion_log",
            "version": "1.0"
        }
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps(header, ensure_ascii=False) + '\n')
            f.write("=" * 80 + '\n')
    
    def get_next_request_index(self) -> int:
        """
        Thread-safe increment and return next request index.
        """
        with self._lock:
            self._request_counter += 1
            return self._request_counter
    
    def log_request(
        self,
        request_index: int,
        request_id: str,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: Optional[int],
        tools: Optional[List[Tool]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        **kwargs
    ):
        """Log a request entry."""
        log_entry = {
            "type": "REQUEST",
            "request_index": request_index,
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": messages,
            "tools": [tool.model_dump() for tool in tools] if tools else None,
            "tool_choice": tool_choice,
            "extra_params": kwargs
        }
        
        self._write_log(log_entry)
    
    def log_response(
        self,
        request_index: int,
        request_id: str,
        content: str,
        reasoning_content: str,
        tool_calls: Optional[List[ToolCall]] = None,
        cost_report: Optional[CostReport] = None,
        duration_ms: Optional[float] = None
    ):
        """Log a response entry."""
        log_entry = {
            "type": "RESPONSE",
            "request_index": request_index,
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
            "content": content,
            "reasoning_content": reasoning_content,
            "tool_calls": None if tool_calls is None else [tc.model_dump() for tc in tool_calls],
            "cost_report": cost_report.model_dump() if cost_report else None,
            "duration_ms": duration_ms
        }
        
        self._write_log(log_entry)
    
    def log_error(
        self,
        request_index: int,
        request_id: str,
        error: Exception,
        duration_ms: Optional[float] = None
    ):
        """Log an error entry."""
        log_entry = {
            "type": "ERROR",
            "request_index": request_index,
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "duration_ms": duration_ms
        }
        
        self._write_log(log_entry)
    
    def _write_log(self, log_entry: Dict[str, Any]):
        """
        Thread-safe write log entry to file and/or console.
        """
        with self._lock:
            # Write to file if enabled
            if self.log_file:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False, indent=2) + '\n')
                    f.write("-" * 40 + '\n')
            
            # Print to console if enabled
            if self.enable_console:
                print(f"[{log_entry['type']}] Request #{log_entry['request_index']} - {log_entry['timestamp']}")
                if log_entry['type'] == 'ERROR':
                    print(f"  Error: {log_entry['error_message']}")

class AdvancedRequestLogger(RequestLogger):
    """
    Advanced request logger supporting SQLite storage for easy query and aggregation.
    """
    
    def __init__(self, log_file: Optional[str] = None, db_file: Optional[str] = None):
        super().__init__(log_file)
        self.db_file = db_file
        
        if self.db_file:
            self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database tables if needed."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Requests table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS requests (
                request_index INTEGER PRIMARY KEY,
                request_id TEXT UNIQUE,
                timestamp TEXT,
                model TEXT,
                temperature REAL,
                max_tokens INTEGER,
                messages TEXT,
                extra_params TEXT
            )
        ''')
        
        # Responses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS responses (
                request_index INTEGER PRIMARY KEY,
                request_id TEXT,
                timestamp TEXT,
                content TEXT,
                usage TEXT,
                cost_report TEXT,
                duration_ms REAL,
                success BOOLEAN,
                error_message TEXT,
                FOREIGN KEY (request_id) REFERENCES requests(request_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def log_request(self, request_index: int, request_id: str, messages: List[Dict[str, str]], 
                   model: str, temperature: float, max_tokens: Optional[int], **kwargs):
        """
        Log request to file and database.
        """
        super().log_request(request_index, request_id, messages, model, temperature, max_tokens, **kwargs)
        
        if self.db_file:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO requests 
                (request_index, request_id, timestamp, model, temperature, max_tokens, messages, extra_params)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                request_index,
                request_id,
                datetime.now().isoformat(),
                model,
                temperature,
                max_tokens,
                json.dumps(messages, ensure_ascii=False),
                json.dumps(kwargs, ensure_ascii=False)
            ))
            
            conn.commit()
            conn.close()

class LogAnalyzer:
    """Log file analysis tool."""
    
    def __init__(self, log_file: str):
        self.log_file = log_file
        self.entries = []
        self._load_logs()
    
    def _load_logs(self):
        """Load log entries from file."""
        with open(self.log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        current_entry = ""
        for line in lines:
            if line.strip() == "-" * 40:
                if current_entry:
                    try:
                        entry = json.loads(current_entry)
                        if isinstance(entry, dict) and 'type' in entry:
                            self.entries.append(entry)
                    except json.JSONDecodeError:
                        pass
                current_entry = ""
            elif not line.startswith("="):
                current_entry += line
    
    def get_request_response_pairs(self) -> List[Dict[str, Any]]:
        """Extract request-response pairs as a list of dicts."""
        pairs = []
        request_map = {}
        
        for entry in self.entries:
            if entry['type'] == 'REQUEST':
                request_map[entry['request_index']] = entry
            elif entry['type'] in ['RESPONSE', 'ERROR']:
                request = request_map.get(entry['request_index'])
                if request:
                    pairs.append({
                        'request': request,
                        'response': entry,
                        'success': entry['type'] == 'RESPONSE',
                        'duration_ms': entry.get('duration_ms')
                    })
        
        return pairs
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get summary statistics from the log."""
        pairs = self.get_request_response_pairs()
        
        total_requests = len(pairs)
        successful_requests = sum(1 for p in pairs if p['success'])
        failed_requests = total_requests - successful_requests
        
        durations = [p['duration_ms'] for p in pairs if p.get('duration_ms')]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        total_cost = 0
        total_tokens = {'input': 0, 'output': 0}
        
        for pair in pairs:
            if pair['success'] and pair['response'].get('cost_report'):
                cost_report = pair['response']['cost_report']
                total_cost += cost_report.get('total_cost', 0)
                total_tokens['input'] += cost_report.get('input_tokens', 0)
                total_tokens['output'] += cost_report.get('output_tokens', 0)
        
        return {
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'success_rate': successful_requests / total_requests if total_requests > 0 else 0,
            'average_duration_ms': avg_duration,
            'total_cost': total_cost,
            'total_tokens': total_tokens,
            'requests_by_model': self._count_by_model(pairs)
        }
    
    def _count_by_model(self, pairs: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count requests by model."""
        model_counts = {}
        for pair in pairs:
            model = pair['request'].get('model', 'unknown')
            model_counts[model] = model_counts.get(model, 0) + 1
        return model_counts
    
    def export_to_csv(self, output_file: str):
        """Export request/response summary to a CSV file."""
        pairs = self.get_request_response_pairs()
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Request Index', 'Request ID', 'Timestamp', 'Model', 
                'User Message', 'Assistant Response', 'Success', 
                'Duration (ms)', 'Input Tokens', 'Output Tokens', 'Cost'
            ])
            
            for pair in pairs:
                request = pair['request']
                response = pair['response']
                
                # Get user message
                user_message = ""
                for msg in request.get('messages', []):
                    if msg.get('role') == 'user':
                        user_message = msg.get('content', '')
                        break
                
                # Get assistant response or error message
                if pair['success']:
                    assistant_response = response.get('content', '')
                else:
                    assistant_response = f"ERROR: {response.get('error_message', 'Unknown error')}"
                
                cost_report = response.get('cost_report', {})
                
                writer.writerow([
                    request['request_index'],
                    request['request_id'],
                    request['timestamp'],
                    request.get('model', ''),
                    user_message,
                    assistant_response,
                    'Yes' if pair['success'] else 'No',
                    response.get('duration_ms', ''),
                    cost_report.get('input_tokens', ''),
                    cost_report.get('output_tokens', ''),
                    cost_report.get('total_cost', '')
                ])

class LogMonitor:
    """Realtime log file monitor."""
    
    def __init__(self, log_file: str, callback: Callable[[str], None]):
        self.log_file = log_file
        self.callback = callback
        self._stop_event = threading.Event()
        self._monitor_thread = None
    
    def start(self):
        """Start monitoring the log file."""
        self._monitor_thread = threading.Thread(target=self._monitor_loop)
        self._monitor_thread.daemon = True
        self._monitor_thread.start()
    
    def stop(self):
        """Stop monitoring."""
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join()
    
    def _monitor_loop(self):
        """Internal loop for monitoring file changes."""
        last_position = 0
        
        while not self._stop_event.is_set():
            try:
                if os.path.exists(self.log_file):
                    with open(self.log_file, 'r', encoding='utf-8') as f:
                        f.seek(last_position)
                        new_content = f.read()
                        if new_content:
                            self.callback(new_content)
                            last_position = f.tell()
            except Exception as e:
                logger.error(f"Error while monitoring log file: {e}")
            
            time.sleep(0.5)  # Check every 0.5 second

