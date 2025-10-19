#!/usr/bin/env python3
"""
MCP Server Connectivity Checker

This script checks if all MCP servers required by tasks can be successfully connected.
It scans task configurations, extracts required MCP server names, and attempts to
connect to each unique server to verify connectivity.

Usage:
    uv run --active check_mcp_connectivity.py [--task-dir PATH] [--timeout SECONDS] [--debug] [--quiet]

Examples:
    uv run --active check_mcp_connectivity.py --task-dir tasks/finalpool --timeout 30 --debug
    uv run --active check_mcp_connectivity.py --timeout 10 --quiet
    uv run --active check_mcp_connectivity.py --quiet --output report.json
"""

import asyncio
import argparse
import json
import sys
import time
import os
import logging
import warnings
from pathlib import Path
from typing import Dict, List, Set, Optional
from collections import defaultdict
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO

from utils.mcp.tool_servers import MCPServerManager


class MCPConnectivityChecker:
    """Checks MCP server connectivity for all tasks"""
    
    def __init__(self, task_dir: str, timeout: int = 30, debug: bool = False, quiet: bool = False):
        self.task_dir = Path(task_dir)
        self.timeout = timeout
        self.debug = debug
        self.quiet = quiet
        self.results = {}
        
        # Suppress various logging unless debug mode
        if not debug:
            self._suppress_logging()
    
    def _suppress_logging(self):
        """Suppress noisy logging from MCP and other libraries"""
        # Suppress asyncio warnings
        warnings.filterwarnings("ignore", category=RuntimeWarning, module="asyncio")
        
        # Suppress MCP library logging
        logging.getLogger("mcp").setLevel(logging.CRITICAL)
        logging.getLogger("agents").setLevel(logging.CRITICAL)
        logging.getLogger("httpx").setLevel(logging.CRITICAL)
        logging.getLogger("anyio").setLevel(logging.CRITICAL)
        logging.getLogger("httpcore").setLevel(logging.CRITICAL)
        
        # Set root logger to only show critical errors
        logging.getLogger().setLevel(logging.CRITICAL)
        
    def scan_tasks_for_mcp_servers(self) -> Dict[str, List[str]]:
        """
        Scan all tasks in the directory and extract required MCP servers
        
        Returns:
            Dict mapping task names to list of required MCP servers
        """
        task_servers = {}
        
        if not self.task_dir.exists():
            raise ValueError(f"Task directory does not exist: {self.task_dir}")
        
        if not self.quiet:
            print(f"Scanning tasks in: {self.task_dir}")
        
        # Find all task_config.json files
        for task_config_path in self.task_dir.rglob("task_config.json"):
            task_name = task_config_path.parent.name
            
            try:
                with open(task_config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                servers = config.get('needed_mcp_servers', [])
                if servers:
                    task_servers[task_name] = servers
                    if self.debug:
                        print(f"  Found task '{task_name}' requiring servers: {servers}")
                else:
                    if self.debug:
                        print(f"  Task '{task_name}' requires no MCP servers")
                        
            except Exception as e:
                print(f"  Error reading {task_config_path}: {e}")
                
        return task_servers
    
    def get_unique_servers(self, task_servers: Dict[str, List[str]]) -> Set[str]:
        """Extract unique server names from all tasks"""
        unique_servers = set()
        for servers in task_servers.values():
            unique_servers.update(servers)
        return unique_servers
    
    async def check_server_connectivity(self, server_name: str, mcp_manager: MCPServerManager) -> Dict:
        """
        Check if a single server can be connected
        
        Returns:
            Dict with connection status and details
        """
        result = {
            'server': server_name,
            'status': 'unknown',
            'error': None,
            'tools_count': 0,
            'connection_time': 0,
            'available_in_config': server_name in mcp_manager.servers
        }
        
        if not result['available_in_config']:
            result['status'] = 'config_missing'
            result['error'] = f"Server '{server_name}' not found in MCP server configurations"
            return result
        
        start_time = time.time()
        
        try:
            # Attempt to connect with timeout, suppressing stderr unless debug mode
            if self.debug:
                await asyncio.wait_for(
                    mcp_manager.connect_servers([server_name]),
                    timeout=self.timeout
                )
            else:
                # Suppress stderr output during connection attempts
                stderr_buffer = StringIO()
                with redirect_stderr(stderr_buffer):
                    await asyncio.wait_for(
                        mcp_manager.connect_servers([server_name]),
                        timeout=self.timeout
                    )
            
            # Check if connection was successful
            if mcp_manager.is_server_connected(server_name):
                result['status'] = 'connected'
                result['connection_time'] = time.time() - start_time
                
                # Try to get tools list to verify functionality
                try:
                    server = mcp_manager.connected_servers[server_name]
                    tools = await server.list_tools()
                    result['tools_count'] = len(tools)
                    if self.debug:
                        print(f"    Server '{server_name}' has {len(tools)} tools available")
                except Exception as e:
                    result['error'] = f"Connected but failed to list tools: {e}"
                    
            else:
                result['status'] = 'connection_failed'
                result['error'] = "Connection attempted but server not in connected list"
                
        except asyncio.TimeoutError:
            result['status'] = 'timeout' 
            result['error'] = f"Connection timeout after {self.timeout} seconds"
            
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            
        finally:
            result['connection_time'] = time.time() - start_time
            
        return result
    
    async def check_all_servers(self, unique_servers: Set[str]) -> Dict[str, Dict]:
        """Check connectivity for all unique servers, handling each independently"""
        results = {}
        
        if not self.quiet:
            print(f"\nChecking connectivity for {len(unique_servers)} unique servers...")
        
        for server_name in sorted(unique_servers):
            if not self.quiet:
                print(f"  Testing server: {server_name}")
            
            # Initialize MCP server manager for each server to avoid interference
            try:
                # Suppress output during manager initialization unless debug
                if self.debug:
                    mcp_manager = MCPServerManager(
                        agent_workspace="./temp_workspace",
                        debug=self.debug
                    )
                else:
                    stderr_buffer = StringIO()
                    stdout_buffer = StringIO()
                    with redirect_stderr(stderr_buffer), redirect_stdout(stdout_buffer):
                        mcp_manager = MCPServerManager(
                            agent_workspace="./temp_workspace",
                            debug=self.debug
                        )
                
                async with mcp_manager:  # Use context manager for proper cleanup
                    result = await self.check_server_connectivity(server_name, mcp_manager)
                    results[server_name] = result
                    
                    # Print immediate result unless in quiet mode
                    if not self.quiet:
                        status_emoji = {
                            'connected': '✅',
                            'timeout': '⏰',
                            'connection_failed': '❌',
                            'config_missing': '⚠️',
                            'error': '💥'
                        }.get(result['status'], '❓')
                        
                        print(f"    {status_emoji} {result['status'].upper()}", end="")
                        
                        if result['status'] == 'connected':
                            print(f" ({result['tools_count']} tools, {result['connection_time']:.2f}s)")
                        elif result['error']:
                            print(f" - {result['error']}")
                        else:
                            print()
                        
            except Exception as e:
                # If manager initialization fails, record the error
                results[server_name] = {
                    'server': server_name,
                    'status': 'manager_error',
                    'error': f"Failed to initialize MCP manager: {e}",
                    'tools_count': 0,
                    'connection_time': 0,
                    'available_in_config': False
                }
                if not self.quiet:
                    print(f"    💥 MANAGER_ERROR - {e}")
        
        return results
    
    def generate_report(self, task_servers: Dict[str, List[str]], 
                       connectivity_results: Dict[str, Dict]) -> Dict:
        """Generate comprehensive connectivity report"""
        
        # Count statuses
        status_counts = defaultdict(int)
        for result in connectivity_results.values():
            status_counts[result['status']] += 1
        
        # Find tasks that might be affected by connectivity issues
        affected_tasks = []
        for task_name, servers in task_servers.items():
            task_issues = []
            for server in servers:
                if server in connectivity_results:
                    result = connectivity_results[server]
                    if result['status'] != 'connected':
                        task_issues.append({
                            'server': server,
                            'status': result['status'],
                            'error': result['error']
                        })
            
            if task_issues:
                affected_tasks.append({
                    'task': task_name,
                    'issues': task_issues
                })
        
        report = {
            'summary': {
                'total_tasks_scanned': len(task_servers),
                'total_unique_servers': len(connectivity_results),
                'status_counts': dict(status_counts),
                'all_connected': status_counts['connected'] == len(connectivity_results)
            },
            'server_details': connectivity_results,
            'affected_tasks': affected_tasks,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return report
    
    def print_summary(self, report: Dict):
        """Print human-readable summary with clear success/failure lists"""
        summary = report['summary']
        server_details = report['server_details']
        
        print(f"\n{'='*60}")
        print("MCP SERVER CONNECTIVITY REPORT")
        print(f"{'='*60}")
        print(f"Timestamp: {report['timestamp']}")
        print(f"Tasks scanned: {summary['total_tasks_scanned']}")
        print(f"Unique servers: {summary['total_unique_servers']}")
        print()
        
        # Status summary
        print("SERVER STATUS SUMMARY:")
        for status, count in summary['status_counts'].items():
            emoji = {
                'connected': '✅',
                'timeout': '⏰', 
                'connection_failed': '❌',
                'config_missing': '⚠️',
                'error': '💥',
                'manager_error': '🔧'
            }.get(status, '❓')
            print(f"  {emoji} {status.upper()}: {count}")
        
        print()
        
        # Separate successful and unsuccessful servers
        successful_servers = []
        unsuccessful_servers = []
        
        for server_name, details in server_details.items():
            if details['status'] == 'connected':
                successful_servers.append((server_name, details))
            else:
                unsuccessful_servers.append((server_name, details))
        
        # Show successful servers
        if successful_servers:
            print(f"✅ SUCCESSFUL CONNECTIONS ({len(successful_servers)}):")
            for server_name, details in successful_servers:
                tools_info = f"({details['tools_count']} tools)" if details['tools_count'] > 0 else ""
                time_info = f"{details['connection_time']:.2f}s"
                print(f"  ✅ {server_name} - {tools_info} {time_info}")
        
        print()
        
        # Show unsuccessful servers
        if unsuccessful_servers:
            print(f"❌ FAILED CONNECTIONS ({len(unsuccessful_servers)}):")
            for server_name, details in unsuccessful_servers:
                status_emoji = {
                    'timeout': '⏰',
                    'connection_failed': '❌',
                    'config_missing': '⚠️',
                    'error': '💥',
                    'manager_error': '🔧'
                }.get(details['status'], '❓')
                print(f"  {status_emoji} {server_name} - {details['status'].upper()}")
                if details['error']:
                    print(f"      Error: {details['error']}")
        
        print()
        
        if summary['all_connected']:
            print("🎉 ALL SERVERS CONNECTED SUCCESSFULLY!")
        else:
            print("⚠️  SOME SERVERS HAVE CONNECTIVITY ISSUES")
            
            if report['affected_tasks']:
                print(f"\nAFFECTED TASKS ({len(report['affected_tasks'])}):")
                for task_info in report['affected_tasks']:
                    print(f"  📋 {task_info['task']}:")
                    for issue in task_info['issues']:
                        status_emoji = {
                            'timeout': '⏰',
                            'connection_failed': '❌',
                            'config_missing': '⚠️',
                            'error': '💥',
                            'manager_error': '🔧'
                        }.get(issue['status'], '❓')
                        print(f"    {status_emoji} {issue['server']}: {issue['status']}")
        
        print(f"\n{'='*60}")
    
    async def run(self) -> Dict:
        """Run the complete connectivity check"""
        if not self.quiet:
            print("Starting MCP Server Connectivity Check...")
        
        # Step 1: Scan tasks for required servers
        task_servers = self.scan_tasks_for_mcp_servers()
        if not self.quiet:
            print(f"Found {len(task_servers)} tasks requiring MCP servers")
        
        # Step 2: Get unique servers
        unique_servers = self.get_unique_servers(task_servers)
        if not self.quiet:
            print(f"Unique servers to test: {sorted(unique_servers)}")
        
        # Step 3: Check connectivity
        connectivity_results = await self.check_all_servers(unique_servers)
        
        # Step 4: Generate report
        report = self.generate_report(task_servers, connectivity_results)
        
        # Step 5: Print summary
        self.print_summary(report)
        
        return report


async def main():
    parser = argparse.ArgumentParser(
        description="Check MCP server connectivity for tasks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--task-dir', 
        default='tasks/finalpool',
        help='Directory containing tasks to scan (default: tasks/finalpool)'
    )
    parser.add_argument(
        '--timeout', 
        type=int, 
        default=30,
        help='Connection timeout in seconds (default: 30)'
    )
    parser.add_argument(
        '--debug', 
        action='store_true',
        help='Enable debug output'
    )
    parser.add_argument(
        '--quiet', 
        action='store_true',
        help='Suppress detailed progress output, only show final report'
    )
    parser.add_argument(
        '--output', 
        help='Save detailed report to JSON file'
    )
    
    args = parser.parse_args()
    
    # Create checker and run
    checker = MCPConnectivityChecker(
        task_dir=args.task_dir,
        timeout=args.timeout,
        debug=args.debug,
        quiet=args.quiet
    )
    
    try:
        report = await checker.run()
        
        # Save to file if requested
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"\nDetailed report saved to: {args.output}")
        
        # Exit with error code if not all servers connected
        if not report['summary']['all_connected']:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(130)
    except Exception as e:
        if not args.quiet:
            print(f"Error during connectivity check: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())