#!/usr/bin/env python3
"""
Port Monitor Script
Displays currently occupied ports and their associated processes

这个脚本的整体逻辑如下：

  主要流程：

  1. 数据收集阶段：
    - 使用 netstat -tulpn 命令获取所有监听端口的基本信息
    - 使用 lsof 命令针对常见端口获取更详细的进程信息
    - 解析命令输出，提取端口号、协议、地址和进程信息
  2. 数据处理阶段：
    - 过滤掉IPv6端口（简化输出）
    - 按端口号排序
    - 将端口按服务类型分类：
        - 系统服务（SSH、邮件、DNS等）
      - Web服务（HTTP、HTTPS等）
      - 数据库服务（MySQL、PostgreSQL等）
      - 开发服务（Node.js、测试服务器等）
      - 未知服务
  3. 信息展示阶段：
    - 按分类显示端口使用情况
    - 格式化进程信息，显示进程名和PID
    - 提供使用摘要统计

  核心函数：

  - run_command(): 执行shell命令并返回结果
  - parse_netstat_output(): 解析netstat输出获取端口信息
  - parse_lsof_output(): 使用lsof获取常见端口的详细进程信息
  - categorize_ports(): 按服务类型对端口进行分类
  - format_process_info(): 格式化进程信息显示

  优点：

  - 自动分类，便于理解各端口用途
  - 结合netstat和lsof，信息更全面
  - 友好的输出格式，易于阅读
  - 权限提示，告知用户如何获取完整信息

  这样设计让用户能快速了解系统端口占用情况和各服务的运行状态。

"""

import subprocess
import re
import sys
from typing import Dict, List, Tuple, Optional


def run_command(cmd: str) -> str:
    """Execute a shell command and return its output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        print(f"Error executing command '{cmd}': {e}")
        return ""


def parse_netstat_output() -> List[Dict[str, str]]:
    """Parse netstat output to extract port and process information"""
    cmd = "netstat -tulpn 2>/dev/null | grep LISTEN"
    output = run_command(cmd)
    
    ports_info = []
    for line in output.strip().split('\n'):
        if not line or ':::' in line:  # Skip IPv6 entries for cleaner output
            continue
            
        parts = line.split()
        if len(parts) >= 7:
            protocol = parts[0]
            address = parts[3]
            process_info = parts[6] if parts[6] != '-' else 'Unknown'
            
            # Extract port number
            if ':' in address:
                port = address.split(':')[-1]
            else:
                continue
                
            ports_info.append({
                'protocol': protocol,
                'port': port,
                'address': address,
                'process': process_info
            })
    
    return ports_info


def get_process_details(pid: str) -> Optional[str]:
    """Get detailed process information by PID"""
    if not pid or pid == '-':
        return None
        
    cmd = f"ps -p {pid} -o pid,ppid,user,cmd --no-headers 2>/dev/null"
    output = run_command(cmd)
    
    if output.strip():
        return output.strip()
    return None


def parse_lsof_output() -> Dict[str, str]:
    """Use lsof to get more detailed process information for common ports"""
    common_ports = ['22', '80', '443', '3000', '8000', '8080', '9000', '5432', '3306', '6379', '25', '53', '111']
    port_processes = {}
    
    for port in common_ports:
        cmd = f"lsof -i :{port} -P -n 2>/dev/null | grep LISTEN"
        output = run_command(cmd)
        
        if output:
            lines = output.strip().split('\n')
            for line in lines:
                parts = line.split()
                if len(parts) >= 2:
                    process_name = parts[0]
                    pid = parts[1]
                    port_processes[port] = f"{process_name} (PID: {pid})"
    
    return port_processes


def categorize_ports(ports_info: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    """Categorize ports by type"""
    categories = {
        'System Services': [],
        'Web Services': [],
        'Database Services': [],
        'Development Services': [],
        'Unknown Services': []
    }
    
    system_ports = ['22', '25', '53', '111', '139', '445']
    web_ports = ['80', '443', '8000', '8080', '3000', '4000', '5000', '9000']
    db_ports = ['3306', '5432', '6379', '27017']
    dev_ports = ['3000', '3001', '4000', '5000', '5001', '8000', '8080', '9090', '9091']
    
    for port_info in ports_info:
        port = port_info['port']
        
        if port in system_ports:
            categories['System Services'].append(port_info)
        elif port in web_ports and port not in dev_ports:
            categories['Web Services'].append(port_info)
        elif port in db_ports:
            categories['Database Services'].append(port_info)
        elif port in dev_ports or 'node' in port_info['process'].lower():
            categories['Development Services'].append(port_info)
        else:
            categories['Unknown Services'].append(port_info)
    
    return categories


def format_process_info(process_str: str) -> str:
    """Format process information for better readability"""
    if process_str == 'Unknown' or process_str == '-':
        return "Unknown process"
    
    # Extract PID and process name
    match = re.search(r'(\d+)/([\w\-\.]+)', process_str)
    if match:
        pid, name = match.groups()
        return f"{name} (PID: {pid})"
    
    return process_str


def main():
    """Main function to display port usage information"""
    print("=" * 80)
    print("PORT USAGE MONITOR")
    print("=" * 80)
    print()
    
    # Get port information
    ports_info = parse_netstat_output()
    lsof_processes = parse_lsof_output()
    
    if not ports_info:
        print("No listening ports found or insufficient permissions.")
        print("Try running with sudo for complete information.")
        return
    
    # Sort ports by port number
    ports_info.sort(key=lambda x: int(x['port']) if x['port'].isdigit() else 0)
    
    # Categorize ports
    categories = categorize_ports(ports_info)
    
    # Display categorized results
    for category, ports in categories.items():
        if not ports:
            continue
            
        print(f"\n{category.upper()}")
        print("-" * len(category))
        
        for port_info in ports:
            port = port_info['port']
            protocol = port_info['protocol'].upper()
            address = port_info['address']
            
            # Use lsof info if available, otherwise use netstat info
            if port in lsof_processes:
                process_display = lsof_processes[port]
            else:
                process_display = format_process_info(port_info['process'])
            
            print(f"  Port {port:>5} ({protocol:>3}) | {address:<20} | {process_display}")
    
    # Summary
    total_ports = len(ports_info)
    known_processes = sum(1 for p in ports_info if p['process'] != 'Unknown' and p['process'] != '-')
    
    print(f"\n{'='*80}")
    print(f"SUMMARY: {total_ports} ports in use | {known_processes} with known processes")
    print(f"{'='*80}")
    
    if known_processes < total_ports:
        print("\nNote: Some process information requires root privileges to view.")
        print("Run with 'sudo python3 port_monitor.py' for complete details.")


if __name__ == "__main__":
    main()