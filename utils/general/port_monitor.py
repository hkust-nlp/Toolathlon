#!/usr/bin/env python3
"""
Port Monitor Script
Displays currently occupied ports and their associated processes.

Overall Logic:

  Main Steps:

  1. Data Collection Stage:
    - Use the `netstat -tulpn` command to get basic information for all listening ports.
    - Use the `lsof` command to get more detailed process info for common ports.
    - Parse command outputs to extract port numbers, protocols, addresses, and process info.
  2. Data Processing Stage:
    - Filter out IPv6 ports (for a cleaner output).
    - Sort by port number.
    - Classify ports by service type:
        - System Services (e.g. SSH, mail, DNS)
        - Web Services (HTTP, HTTPS, etc.)
        - Database Services (MySQL, PostgreSQL, etc.)
        - Development Services (Node.js, test servers, etc.)
        - Unknown Services
  3. Information Display Stage:
    - Display port usage by category.
    - Format process info to show process name and PID.
    - Show a summary at the end.

  Core Functions:

  - run_command(): Executes a shell command and returns its result.
  - parse_netstat_output(): Parses netstat output to retrieve port information.
  - parse_lsof_output(): Uses lsof to get detailed process info for common ports.
  - categorize_ports(): Categorizes ports by their service type.
  - format_process_info(): Formats process information for display.

  Advantages:

  - Automatic categorization for easy understanding of port purposes.
  - Combines netstat and lsof for richer information.
  - Friendly and readable output formatting.
  - Permission hints to inform users how to get complete info.

  This design enables users to quickly understand which services are using which ports and the operational status of their system.

"""

import subprocess
import re
import sys
from typing import Dict, List, Tuple, Optional


def run_command(cmd: str) -> str:
    """Execute a shell command and return its output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        print(f"Error executing command '{cmd}': {e}")
        return ""


def parse_netstat_output() -> List[Dict[str, str]]:
    """Parse netstat output to extract port and process information."""
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
    """Get detailed process information by PID."""
    if not pid or pid == '-':
        return None

    cmd = f"ps -p {pid} -o pid,ppid,user,cmd --no-headers 2>/dev/null"
    output = run_command(cmd)

    if output.strip():
        return output.strip()
    return None


def parse_lsof_output() -> Dict[str, str]:
    """Use lsof to get more detailed process information for common ports."""
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
    """Categorize ports by type."""
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
    """Format process information for better readability."""
    if process_str == 'Unknown' or process_str == '-':
        return "Unknown process"

    # Extract PID and process name
    match = re.search(r'(\d+)/([\w\-\.]+)', process_str)
    if match:
        pid, name = match.groups()
        return f"{name} (PID: {pid})"

    return process_str


def main():
    """Main function to display port usage information."""
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