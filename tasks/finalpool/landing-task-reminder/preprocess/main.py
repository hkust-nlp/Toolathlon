import argparse
import json
from datetime import datetime, timedelta
import sys
import os

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
# Go up: preprocess -> landing-task-reminder -> fan -> tasks -> toolathlon
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..', '..'))
sys.path.insert(0, project_root)

from utils.app_specific.snowflake.client import execute_query, get_connection, fetch_all_dict
from utils.app_specific.poste.ops import clear_folder
from utils.general.helper import print_color

# Import task-specific config
task_root = os.path.join(current_dir, '..')
sys.path.insert(0, task_root)
from token_key_session import all_token_key_session

def get_snowflake_current_time():
    result = fetch_all_dict("SELECT CURRENT_TIMESTAMP()")
    return result[0]['CURRENT_TIMESTAMP()']

def clear_all_emails():
    email_config_file = os.path.join(os.path.dirname(__file__), '..', 'groundtruth_workspace', 'involved_emails.json')
    with open(email_config_file, 'r', encoding='utf-8') as f:
        involved_emails_data = json.load(f)
    
    # Clear sender emails
    for sender_email, config in involved_emails_data["sender"].items():
        email_config = {"email": sender_email, **config}
        clear_folder("INBOX", email_config)
        clear_folder("Sent", email_config)
    
    # Clear recipient emails
    for recipient_email, config in involved_emails_data["should_or_shouldnt_receive"].items():
        email_config = {"email": recipient_email, **config}
        clear_folder("INBOX", email_config)
        clear_folder("Sent", email_config)

def init_database(agent_workspace, launch_time):
    conn = get_connection()
    conn.close()
    
    drop_database()
    print_color("✓ Database dropped", "green")
    create_database()
    print_color("✓ Database created", "green")
    
    data_file = f"{os.path.dirname(__file__)}/../groundtruth_workspace/landing_task.json"
    with open(data_file, 'r') as f:
        data = json.load(f)
    
    launch_date = datetime.strptime(launch_time, "%Y-%m-%d %H:%M:%S")
    
    create_employee_table(data, launch_date)
    print_color("✓ Employee table created", "green")
    
    create_employee_landing_table(data, launch_date)
    print_color("✓ Employee_landing table created", "green")
    
    create_public_tasks_table(data, launch_date)
    print_color("✓ Public_tasks table created", "green")
    
    create_group_tasks_tables(data, launch_date)
    print_color("✓ Group_tasks tables created", "green")
    
    clear_all_emails()
    print_color("✓ All emails cleared", "green")

def drop_database():
    db_name = all_token_key_session.snowflake_op_allowed_databases
    execute_query(f"DROP DATABASE IF EXISTS {db_name}")

def create_database():
    db_name = all_token_key_session.snowflake_op_allowed_databases
    execute_query(f"CREATE DATABASE IF NOT EXISTS {db_name}")
    execute_query(f"CREATE SCHEMA IF NOT EXISTS {db_name}.PUBLIC")
    execute_query(f"USE DATABASE {db_name}")
    execute_query(f"USE SCHEMA {db_name}.PUBLIC")

def create_employee_table(data, launch_date):
    
    create_sql = """
    CREATE TABLE LANDING_TASK_REMINDER.PUBLIC.EMPLOYEE (
        employee_id INT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(100) NOT NULL,
        report_to_id INT
    );
    """
    execute_query(create_sql)
    
    all_people = data.get('employees', []) + data.get('managers', []) + data.get('bosses', [])
    
    values = []
    for person in all_people:
        employee_id = person['employee_id']
        name = person['name']
        email = person['email'] 
        report_to_id = person.get('report_to_id', None)
        
        report_to_value = str(report_to_id) if report_to_id else "NULL"
        values.append(f"({employee_id}, '{name}', '{email}', {report_to_value})")
    
    if values:
        batch_insert_sql = f"INSERT INTO LANDING_TASK_REMINDER.PUBLIC.EMPLOYEE VALUES {', '.join(values)}"
        execute_query(batch_insert_sql)

def create_employee_landing_table(data, launch_date):

    create_sql = """
    CREATE TABLE LANDING_TASK_REMINDER.PUBLIC.EMPLOYEE_LANDING (
        employee_id INT PRIMARY KEY,
        landing_date DATE NOT NULL,
        landing_task_assigned BOOLEAN NOT NULL
    )
    """
    execute_query(create_sql)
    
    all_people = data.get('employees', []) + data.get('managers', []) + data.get('bosses', [])
    
    values = []
    for person in all_people:
        employee_id = person['employee_id']
        landing_date_offset = person.get('landing_date_offset_days', 0)
        landing_task_assigned = person.get('landing_task_assigned', False)
        
        actual_landing_date = launch_date + timedelta(days=landing_date_offset)
        landing_date_str = actual_landing_date.strftime('%Y-%m-%d')
        
        values.append(f"({employee_id}, '{landing_date_str}', {landing_task_assigned})")
    
    if values:
        batch_insert_sql = f"INSERT INTO LANDING_TASK_REMINDER.PUBLIC.EMPLOYEE_LANDING VALUES {', '.join(values)}"
        execute_query(batch_insert_sql)

def create_public_tasks_table(data, launch_date):
    
    create_sql = """
    CREATE TABLE LANDING_TASK_REMINDER.PUBLIC.PUBLIC_TASKS (
        task_name VARCHAR(100) NOT NULL,
        employee_id INT NOT NULL,
        create_date DATE NOT NULL,
        ddl DATE NOT NULL,
        finished_flag BOOLEAN NOT NULL
    )
    """
    execute_query(create_sql)
    
    default_public_tasks = [
        "Onboarding Training",
        "Security Training", 
        "Confidentiality Training",
        "Company Culture",
        "Company Strategy"
    ]
    
    all_people = data.get('employees', []) + data.get('managers', []) + data.get('bosses', [])
    
    values = []
    for person in all_people:
        employee_id = person['employee_id']
        landing_date_offset = person.get('landing_date_offset_days', 0)
        
        # Skip adding tasks for new employees (they should be created by agent)
        if landing_date_offset == 0:
            continue
            
        actual_landing_date = launch_date + timedelta(days=landing_date_offset)
        public_tasks = person.get('public_tasks', [])
        
        if public_tasks:
            for task in public_tasks:
                task_name = task['task_name']
                ddl_offset = task['ddl_offset_days']
                finished_flag = task['finished_flag']
                
                create_date_str = actual_landing_date.strftime('%Y-%m-%d')
                ddl_date = actual_landing_date + timedelta(days=ddl_offset)
                ddl_date_str = ddl_date.strftime('%Y-%m-%d')
                
                values.append(f"('{task_name}', {employee_id}, '{create_date_str}', '{ddl_date_str}', {finished_flag})")
        else:
            for task_name in default_public_tasks:
                create_date_str = actual_landing_date.strftime('%Y-%m-%d')
                ddl_date = actual_landing_date + timedelta(days=7)
                ddl_date_str = ddl_date.strftime('%Y-%m-%d')
                
                values.append(f"('{task_name}', {employee_id}, '{create_date_str}', '{ddl_date_str}', true)")
    
    if values:
        batch_insert_sql = f"INSERT INTO LANDING_TASK_REMINDER.PUBLIC.PUBLIC_TASKS VALUES {', '.join(values)}"
        execute_query(batch_insert_sql)

def create_group_tasks_tables(data, launch_date):
    groups = ['Backend', 'Frontend', 'Testing', 'Data']
    
    default_group_tasks = {
        'Backend': ["Backend Development Process", "Backend Development Standards", "Backend Development Environment"],
        'Frontend': ["Frontend Development Process", "Frontend Development Standards", "Frontend Development Environment"],
        'Testing': ["Testing Development Process", "Testing Development Standards", "Testing Development Environment"],
        'Data': ["Data Development Process", "Data Development Standards", "Data Development Environment"]
    }
    
    ddl_days = {'Backend': 30, 'Frontend': 45, 'Testing': 60, 'Data': 75}
    
    for group in groups:
        table_name = f"GROUP_TASKS_{group.upper()}"
        create_sql = f"""
        CREATE TABLE LANDING_TASK_REMINDER.PUBLIC.{table_name} (
            task_name VARCHAR(100) NOT NULL,
            employee_id INT NOT NULL,
            create_date DATE NOT NULL,
            ddl DATE NOT NULL,
            finished_flag BOOLEAN NOT NULL
        )
        """
        execute_query(create_sql)
    
    all_people = data.get('employees', []) + data.get('managers', []) + data.get('bosses', [])
    
    # Collect values by group
    group_values = {group: [] for group in groups}
    
    for person in all_people:
        employee_id = person['employee_id']
        group = person.get('group', '')
        if not group:
            continue
        
        landing_date_offset = person.get('landing_date_offset_days', 0)
        
        # Skip adding tasks for new employees (they should be created by agent)
        if landing_date_offset == 0:
            continue
            
        actual_landing_date = launch_date + timedelta(days=landing_date_offset)
        group_tasks = person.get('group_tasks', [])
        
        if group_tasks:
            for task in group_tasks:
                task_name = task['task_name']
                ddl_offset = task['ddl_offset_days']
                finished_flag = task['finished_flag']
                
                create_date_str = actual_landing_date.strftime('%Y-%m-%d')
                ddl_date = actual_landing_date + timedelta(days=ddl_offset)
                ddl_date_str = ddl_date.strftime('%Y-%m-%d')
                
                group_values[group].append(f"('{task_name}', {employee_id}, '{create_date_str}', '{ddl_date_str}', {finished_flag})")
        else:
            for task_name in default_group_tasks[group]:
                create_date_str = actual_landing_date.strftime('%Y-%m-%d')
                ddl_date = actual_landing_date + timedelta(days=ddl_days[group])
                ddl_date_str = ddl_date.strftime('%Y-%m-%d')
                
                group_values[group].append(f"('{task_name}', {employee_id}, '{create_date_str}', '{ddl_date_str}', true)")
    
    # Batch insert for each group
    for group in groups:
        if group_values[group]:
            table_name = f"GROUP_TASKS_{group.upper()}"
            batch_insert_sql = f"INSERT INTO LANDING_TASK_REMINDER.PUBLIC.{table_name} VALUES {', '.join(group_values[group])}"
            execute_query(batch_insert_sql)

def main():
    parser = argparse.ArgumentParser(description="Given landing.json, create database table")
    parser.add_argument("--agent_workspace", type=str, required=True)
    parser.add_argument("--launch_time", type=str, required=True, default="2025-09-15 00:00:00")
    args = parser.parse_args()
    
    # Use Snowflake database time instead of local time
    snowflake_time = get_snowflake_current_time()
    launch_time = snowflake_time.strftime("%Y-%m-%d %H:%M:%S")
    print_color(f"Using Snowflake time as launch_time: {launch_time}", "blue")
    
    init_database(args.agent_workspace, launch_time)

if __name__ == "__main__":
    main()
