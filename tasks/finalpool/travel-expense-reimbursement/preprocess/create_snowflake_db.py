#!/usr/bin/env python3

import asyncio
import os
import sys
import re
from typing import Dict, Any, List, Tuple
import random
import json

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..', '..'))
sys.path.insert(0, project_root)

from utils.mcp.tool_servers import MCPServerManager, call_tool_with_retry

parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, parent_dir)
from token_key_session import all_token_key_session as local_token_key_session

from utils.general.helper import print_color

DB_NAME = "TRAVEL_EXPENSE_REIMBURSEMENT"
SCHEMA_NAME = "PUBLIC"
TABLE_NAME = "ENTERPRISE_CONTACTS"
EXPENSE_TABLE_NAME = "2024Q4REIMBURSEMENT"


def slugify_email(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9\s.]", "", name)
    name = re.sub(r"\s+", ".", name)
    name = re.sub(r"\.+", ".", name).strip(".")
    return f"{name}@mcp.com"


async def execute_sql(server, sql_query: str, tool_type: str = "write"):
    if tool_type == "create":
        tool_name = "create_table"
    elif tool_type == "read":
        tool_name = "read_query"
    else:
        tool_name = "write_query"

    arguments = {"query": sql_query}
    return await call_tool_with_retry(server, tool_name=tool_name, arguments=arguments)


def load_employees_from_groundtruth(groundtruth_dir: str) -> List[Tuple[str, str, str, str]]:
    """Load employee list from groundtruth expense_claims.json (employee_id, name, level, department) and return"""
    expense_file = os.path.join(groundtruth_dir, "expense_claims.json")
    if not os.path.exists(expense_file):
        return []
    with open(expense_file, 'r', encoding='utf-8') as f:
        claims = json.load(f)

    seen = {}
    for c in claims:
        key = c.get('employee_id')
        if key and key not in seen:
            seen[key] = (
                c.get('employee_id'),
                c.get('employee_name'),
                c.get('employee_level'),
                c.get('department')
            )
    return list(seen.values())


def load_manager_mapping(groundtruth_dir: str):
    """Load both manager_mapping.json and manager_mapping_no_error.json, return combined employee email mapping and manager information.

    Returns:
      - employee_email_by_id: { employee_id -> email }
      - manager_info_list: [ { 'name', 'email' } ] and deduplicate
      - employees_to_manager: { employee_id -> { name, email } }
    """         
    employee_email_by_id = {}
    manager_info_list = []
    employees_to_manager = {}
    seen_mgr_emails = set()
    
    # Load both mapping files
    mapping_files = ['manager_mapping.json', 'manager_mapping_no_error.json']
    
    for mapping_file in mapping_files:
        mapping_path = os.path.join(groundtruth_dir, mapping_file)
        if not os.path.exists(mapping_path):
            continue
            
        with open(mapping_path, 'r', encoding='utf-8') as f:
            mp = json.load(f)
        
        # groups -> employees (id + email) and managers (name + email)
        for grp in mp.get('groups', []):
            mgr = grp.get('manager') or {}
            mgr_email = mgr.get('email')
            if mgr_email and mgr_email not in seen_mgr_emails:
                manager_info_list.append({'name': mgr.get('name', ''), 'email': mgr_email})
                seen_mgr_emails.add(mgr_email)
            for emp in grp.get('employees', []):
                emp_id = emp.get('employee_id')
                emp_email = emp.get('email')
                if emp_id and emp_email:
                    employee_email_by_id[emp_id] = emp_email
        
        # employees_to_manager map
        for emp_id, mgr in (mp.get('employees_to_manager') or {}).items():
            employees_to_manager[emp_id] = {'name': mgr.get('name', ''), 'email': mgr.get('email', '')}
    
    return employee_email_by_id, manager_info_list, employees_to_manager


def generate_contacts(groundtruth_dir: str) -> List[Dict[str, Any]]:
    """Generate enterprise contacts initial data based on groundtruth employees + manager_mapping.json

    - Employee email uses the email defined in manager_mapping.json, avoid inconsistency with groundtruth
    - Manager contact comes from the manager list in manager_mapping.json
    """
    employees = load_employees_from_groundtruth(groundtruth_dir)
    emp_email_map, manager_info_list, employees_to_manager = load_manager_mapping(groundtruth_dir)

    # Infer title based on department (if no department, fallback to Employee)
    title_by_dept = {
        'Sales Department': 'Sales Manager',
        'Technology Department': 'Software Engineer',
        'Marketing Department': 'Marketing Manager',
        'Finance Department': 'Finance Analyst',
    }

    contacts: List[Dict[str, Any]] = []

    # Add employees
    for emp_id, name, level, dept in employees:
        email = emp_email_map.get(emp_id) or slugify_email(name)
        mgr_email = (employees_to_manager.get(emp_id) or {}).get('email', '')
        contacts.append({
            'employee_id': emp_id,
            'name': name,
            'email': email,
            'title': title_by_dept.get(dept or '', 'Employee'),
            'employee_level': level or '',
            'department': dept or '',
            'manager_email': mgr_email,
            'country': 'USA',
            'city': 'San Francisco',
            'phone': f'+1-555-{random.randint(1000, 5000)}',
            'status': 'active'
        })

    # Add manager contact (from groundtruth manager_mapping.json)
    def make_mgr_emp_id(email: str) -> str:
        local = (email or '').split('@')[0]
        token = re.sub(r"[^A-Za-z0-9]+", "_", local).upper().strip('_')
        return f"MGR_{token}" if token else "MGR"

    added_mgr_emails = set()
    for mgr in manager_info_list:
        mgr_email = mgr.get('email') or ''
        if not mgr_email or mgr_email in added_mgr_emails:
            continue
        added_mgr_emails.add(mgr_email)
        contacts.append({
            'employee_id': make_mgr_emp_id(mgr_email),
            'name': mgr.get('name', ''),
            'email': mgr_email,
            'title': 'People Manager',
            'employee_level': 'M2',
            'department': 'Management',
            'manager_email': '',
            'country': 'USA',
            'city': 'San Francisco',
            'phone': f'+1-555-{random.randint(5001, 9999)}',
            'status': 'active'
        })

    return contacts


async def initialize_database():
    task_root = os.path.abspath(os.path.join(current_dir, '..'))
    groundtruth_dir = os.path.join(task_root, 'groundtruth_workspace')
    contacts = generate_contacts(groundtruth_dir)
    
    # Save contacts data to JSON file for reference
    contacts_json_path = os.path.join(groundtruth_dir, 'enterprise_contacts.json')
    with open(contacts_json_path, 'w', encoding='utf-8') as f:
        json.dump(contacts, f, ensure_ascii=False, indent=2)
    print_color(f"Saved {len(contacts)} contacts to {contacts_json_path}", "green")

    mcp_manager = MCPServerManager(
        agent_workspace="./",
        config_dir="configs/mcp_servers",
        local_token_key_session=local_token_key_session
    )

    snowflake_server = mcp_manager.servers['snowflake']
    async with snowflake_server as server:

        print_color("Dropping and creating existing database ... ", "blue")
        await call_tool_with_retry(server, tool_name="drop_databases", arguments={"databases": [DB_NAME]})
        await call_tool_with_retry(server, tool_name="create_databases", arguments={"databases": [DB_NAME]})
        print_color("Dropped and created existing database", "green")

        print_color("Creating contacts table ... ", "blue")
        create_contacts_sql = f"""
        CREATE TABLE {DB_NAME}.{SCHEMA_NAME}.{TABLE_NAME} (
            ID INTEGER AUTOINCREMENT PRIMARY KEY,
            EMPLOYEE_ID VARCHAR(30) UNIQUE,
            NAME VARCHAR(255) NOT NULL,
            EMAIL VARCHAR(255) NOT NULL UNIQUE,
            TITLE VARCHAR(255),
            EMPLOYEE_LEVEL VARCHAR(10),
            DEPARTMENT VARCHAR(255),
            MANAGER_EMAIL VARCHAR(255),
            COUNTRY VARCHAR(100),
            CITY VARCHAR(100),
            PHONE VARCHAR(50),
            STATUS VARCHAR(20) DEFAULT 'active'
        );"""
        await execute_sql(server, create_contacts_sql, "create")
        print_color("Created contacts table", "green")

        print_color("Inserting contacts ... ", "blue")
        for c in contacts:
            name = c['name'].replace("'", "''")
            title = (c.get('title') or '').replace("'", "''")
            dept = (c.get('department') or '').replace("'", "''")
            insert_sql = f"""
            INSERT INTO {DB_NAME}.{SCHEMA_NAME}.{TABLE_NAME}
            (EMPLOYEE_ID, NAME, EMAIL, TITLE, EMPLOYEE_LEVEL, DEPARTMENT, MANAGER_EMAIL, COUNTRY, CITY, PHONE, STATUS)
            VALUES
            ('{c['employee_id']}', '{name}', '{c['email']}', '{title}', '{c.get('employee_level','')}',
             '{dept}', '{c.get('manager_email','')}', '{c.get('country','')}', '{c.get('city','')}', '{c.get('phone','')}', '{c.get('status','active')}');
            """
            await execute_sql(server, insert_sql)
        print_color("Inserted contacts", "green")

        print_color("Dropping existing expense table ... ", "blue")
        expense_fq = f"{DB_NAME}.{SCHEMA_NAME}.\"{EXPENSE_TABLE_NAME}\""
        create_expense_sql = f"""
        CREATE TABLE {expense_fq} (
            ID INTEGER AUTOINCREMENT PRIMARY KEY,
            CLAIM_ID VARCHAR(40) UNIQUE,
            EMPLOYEE_ID VARCHAR(30),
            EMPLOYEE_NAME VARCHAR(255),
            DEPARTMENT VARCHAR(255),
            DEST_COUNTRY VARCHAR(100),
            DEST_CITY VARCHAR(100),
            TRIP_START DATE,
            TRIP_END DATE,
            NIGHTS INTEGER,
            TOTAL_CLAIMED NUMBER(18,2),
            FLAG INTEGER DEFAULT 0
        );
        """
        await execute_sql(server, create_expense_sql, "create")
        print_color("Created expense table", "green")

        # Skip inserting into 2024Q4REIMBURSEMENT table as requested
        print_color("Skipping insertion into 2024Q4REIMBURSEMENT table as requested", "yellow")


if __name__ == "__main__":
    asyncio.run(initialize_database())
