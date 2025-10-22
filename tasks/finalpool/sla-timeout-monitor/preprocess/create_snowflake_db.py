#!/usr/bin/env python3
"""
Snowflake Database Initialization Script
Initialize customer support SLA timeout monitoring system database using MCP Snowflake server
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta
import random
from rich import print
from rich.console import Console
from rich.table import Table

# Add project root directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
# Go up: preprocess -> sla-timeout-monitor -> fan -> tasks -> toolathlon
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..', '..'))
sys.path.insert(0, project_root)
try:
    from utils.mcp.tool_servers import MCPServerManager, call_tool_with_retry
except ImportError as e:
    print(f"Import error: {e}")
    print("Please run from the project root directory or ensure the project structure is correct")
    sys.exit(1)

# Import task-specific configuration for override
# Add parent directory to path and import
parent_dir = os.path.abspath('..')
sys.path.insert(0, parent_dir)
try:
    from token_key_session import all_token_key_session as local_token_key_session
except ImportError:
    print("Warning: Task-specific token_key_session.py not found, will use default configuration")
    local_token_key_session = {
        "snowflake_op_allowed_databases": "SLA_MONITOR",
    }

console = Console()

# SLA configuration - Updated to longer timeframes
SLA_CONFIGS = {
    "max": {"response_time_minutes": 1440, "followup_time_minutes": 1080, "priority": 3},  # 24h, 18h
    "pro": {"response_time_minutes": 2160, "followup_time_minutes": 2160, "priority": 2},  # 36h, 36h
    "basic": {"response_time_minutes": 4320, "followup_time_minutes": 4320, "priority": 1}  # 72h, 72h
}

# Real user data (regular users)
SAMPLE_USERS = [
    {"name": "Raymond Miller", "email": "raymondm@mcp.com", "service_level": "basic", "customer_manager": "dhall@mcp.com"},
    {"name": "Donald Castillo", "email": "donald_castillo@mcp.com", "service_level": "max", "customer_manager": "dhall@mcp.com"},
    {"name": "Brian Ramos", "email": "ramosb@mcp.com", "service_level": "pro", "customer_manager": "andersonp@mcp.com"},
    {"name": "Ashley Ortiz", "email": "ortiza2@mcp.com", "service_level": "basic", "customer_manager": "andersonp@mcp.com"},
    {"name": "Tracy Clark", "email": "clarkt12@mcp.com", "service_level": "pro", "customer_manager": "andersonp@mcp.com"},
    {"name": "Ruth Scott", "email": "rscott53@mcp.com", "service_level": "basic", "customer_manager": "dhall@mcp.com"},
    {"name": "Andrew Wilson", "email": "awilson@mcp.com", "service_level": "pro", "customer_manager": "andersonp@mcp.com"},
    {"name": "Janet Lopez", "email": "janetl@mcp.com", "service_level": "max", "customer_manager": "dhall@mcp.com"},
    {"name": "Jason Hernandez", "email": "hernandezj@mcp.com", "service_level": "basic", "customer_manager": "andersonp@mcp.com"},
    {"name": "Anthony White", "email": "anthonyw@mcp.com", "service_level": "basic", "customer_manager": "andersonp@mcp.com"},
    {"name": "Richard Bennett", "email": "rbennett78@mcp.com", "service_level": "pro", "customer_manager": "dhall@mcp.com"},
    {"name": "Raymond Morgan", "email": "raymondm713@mcp.com", "service_level": "max", "customer_manager": "dhall@mcp.com"},
    {"name": "Rebecca Hall", "email": "rebeccah@mcp.com", "service_level": "max", "customer_manager": "andersonp@mcp.com"},
    {"name": "Anna Wright", "email": "anna.wright@mcp.com", "service_level": "pro", "customer_manager": "andersonp@mcp.com"},
    {"name": "Debra Sanders", "email": "dsanders@mcp.com", "service_level": "basic", "customer_manager": "dhall@mcp.com"},
]

# Customer service manager emails (selected from real emails)
SUPPORT_MANAGERS = [
    "dhall@mcp.com",  # Daniel Hall - Senior Customer Service Manager
    "andersonp@mcp.com"  # Pamela Anderson - Customer Success Manager
]

# Ticket statuses
TICKET_STATUSES = ["open", "in_progress", "pending_response", "resolved", "closed"]

# Ticket types and content templates
TICKET_TYPES = {
    "bug_report": [
        "Application crashes when uploading large files",
        "Login page returns 500 error intermittently", 
        "Export feature not working for CSV format",
        "Dashboard charts not loading properly",
        "Email notifications not being sent"
    ],
    "feature_request": [
        "Need ability to bulk edit user permissions",
        "Request for dark mode theme option",
        "Add integration with third-party calendar",
        "Need advanced filtering options in reports",
        "Request for mobile app version"
    ],
    "account_issue": [
        "Unable to reset password using email link",
        "Account suspended without notification",
        "Billing discrepancy on latest invoice", 
        "Need to transfer account to different email",
        "Subscription not reflecting recent upgrade"
    ],
    "general_inquiry": [
        "How to set up SSO for our organization",
        "Questions about data retention policies",
        "Need training materials for new team members",
        "Clarification on API rate limits",
        "Documentation for webhook setup"
    ]
}


def display_table_structure():
    """Display the table structure to be created"""
    print("\n" + "="*60)
    print("📋 DATABASE SCHEMA DESIGN")
    print("="*60)
    
    # Users table structure
    users_table = Table(title="USERS Table Structure")
    users_table.add_column("Column", style="cyan")
    users_table.add_column("Type", style="magenta")
    users_table.add_column("Description", style="green")
    
    users_table.add_row("ID", "INTEGER AUTOINCREMENT", "Primary key")
    users_table.add_row("NAME", "VARCHAR(255)", "User name")
    users_table.add_row("EMAIL", "VARCHAR(255)", "User email (unique)")
    users_table.add_row("SERVICE_LEVEL", "VARCHAR(50)", "Service level (basic/pro/max)")
    users_table.add_row("CUSTOMER_MANAGER", "VARCHAR(255)", "Dedicated customer manager email")
    users_table.add_row("CREATED_AT", "TIMESTAMP", "Creation time")
    users_table.add_row("UPDATED_AT", "TIMESTAMP", "Update time")
    
    console.print(users_table)
    
    # Tickets table structure  
    tickets_table = Table(title="SUPPORT_TICKETS Table Structure")
    tickets_table.add_column("Column", style="cyan")
    tickets_table.add_column("Type", style="magenta") 
    tickets_table.add_column("Description", style="green")
    
    tickets_table.add_row("ID", "INTEGER AUTOINCREMENT", "Primary key")
    tickets_table.add_row("TICKET_NUMBER", "VARCHAR(50)", "Ticket number (unique)")
    tickets_table.add_row("USER_ID", "INTEGER", "User ID (foreign key)")
    tickets_table.add_row("SUBJECT", "VARCHAR(500)", "Ticket subject")
    tickets_table.add_row("DESCRIPTION", "TEXT", "Ticket detailed description")
    tickets_table.add_row("STATUS", "VARCHAR(50)", "Ticket status")
    tickets_table.add_row("PRIORITY", "VARCHAR(20)", "Priority")
    tickets_table.add_row("TICKET_TYPE", "VARCHAR(50)", "Ticket type")
    tickets_table.add_row("CREATED_AT", "TIMESTAMP", "Creation time")
    tickets_table.add_row("FIRST_RESPONSE_AT", "TIMESTAMP", "First response time")
    tickets_table.add_row("RESOLVED_AT", "TIMESTAMP", "Resolution time")
    tickets_table.add_row("UPDATED_AT", "TIMESTAMP", "Update time")
    
    console.print(tickets_table)


async def execute_sql(server, sql_query: str, description: str = "", tool_type: str = "write"):
    """Execute SQL query"""
    try:
        if description:
            print(f"🔄 {description}")
        
        # Select appropriate tool based on SQL type
        if tool_type == "create":
            tool_name = "create_table"
            arguments = {"query": sql_query}
        elif tool_type == "read":
            tool_name = "read_query"
            arguments = {"query": sql_query}
        else:  # write operations (INSERT, UPDATE, DELETE, DROP, etc.)
            tool_name = "write_query"
            arguments = {"query": sql_query}
        
        # Call MCP tool to execute SQL
        result = await call_tool_with_retry(
            server,
            tool_name=tool_name,
            arguments=arguments
        )
        
        print(f"✅ {description or 'SQL executed successfully'}")
        if hasattr(result, 'content') and result.content:
            # Try different result access methods
            if hasattr(result.content[0], 'text'):
                print(f"   Result: {result.content[0].text}")
            elif hasattr(result.content[0], 'content'):
                print(f"   Result: {result.content[0].content}")
        return True
        
    except Exception as e:
        print(f"❌ Error executing SQL ({description}): {e}")
        return False


async def generate_sample_data(server=None):
    """Generate test data"""
    users_data = []
    tickets_data = []
    
    # Generate user data
    for user in SAMPLE_USERS:
        users_data.append({
            "name": user["name"],
            "email": user["email"],
            "service_level": user["service_level"],
            "customer_manager": user["customer_manager"]
        })
    
    # Get current time from Snowflake if server is available
    if server:
        try:
            current_time_result = await call_tool_with_retry(
                server,
                tool_name="read_query", 
                arguments={"query": "SELECT CURRENT_TIMESTAMP() AS current_time;"}
            )
            
            # Parse Snowflake's current time
            if current_time_result and hasattr(current_time_result, 'content') and current_time_result.content:
                result_text = ""
                if hasattr(current_time_result.content[0], 'text'):
                    result_text = current_time_result.content[0].text
                elif hasattr(current_time_result.content[0], 'content'):
                    result_text = current_time_result.content[0].content
                else:
                    result_text = str(current_time_result.content[0])
                
                print(f"Snowflake current time result: {result_text}")
                
                # Try to extract timestamp from result
                # Look for timestamp pattern
                import re
                timestamp_pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
                matches = re.findall(timestamp_pattern, result_text)
                if matches:
                    current_time_str = matches[0]
                    current_time = datetime.strptime(current_time_str, "%Y-%m-%d %H:%M:%S")
                    print(f"✅ Using Snowflake time: {current_time}")
                else:
                    print("⚠️  Could not parse Snowflake time, using local time")
                    current_time = datetime.now()
            else:
                print("⚠️  Could not get Snowflake time, using local time")
                current_time = datetime.now()
        except Exception as e:
            print(f"⚠️  Error getting Snowflake time: {e}, using local time")
            current_time = datetime.now()
    else:
        current_time = datetime.now()
    
    # Generate ticket data - one ticket per user
    ticket_counter = 1000
    
    tickets_data = []
    
    # Track creation times to ensure at least 10 minute intervals
    used_creation_times = set()
    
    # Generate one ticket for each user
    for user in SAMPLE_USERS:
        ticket_type = random.choice(list(TICKET_TYPES.keys()))
        subject = random.choice(TICKET_TYPES[ticket_type])
        
        # Determine if this ticket should timeout based on service level and random chance
        should_timeout = random.choice([True, False])  # 50% chance to timeout
        
        if should_timeout:
            # Create timeout tickets based on service level - ensure they are well beyond SLA
            if user["service_level"] == "pro":
                # Exceed 36-hour (2160 min) SLA by at least 3 hours 
                hours_ago = random.randint(40, 50)  # 40-50 hours ago
                created_at = current_time - timedelta(hours=hours_ago)
                first_response_at = None
                status = "open"
                priority = "high"
            elif user["service_level"] == "max":
                # Exceed 24-hour (1440 min) SLA by at least 3 hours
                hours_ago = random.randint(28, 35)  # 28-35 hours ago  
                created_at = current_time - timedelta(hours=hours_ago)
                first_response_at = None
                status = "open"
                priority = "critical"
            elif user["service_level"] == "basic":
                # Exceed 72-hour (4320 min) SLA by at least 5 hours
                hours_ago = random.randint(78, 90)  # 78-90 hours ago (3-4 days)
                created_at = current_time - timedelta(hours=hours_ago)
                first_response_at = None
                status = "open"
                priority = "normal"
                
            # Ensure unique creation time with at least 10 minute difference
            while created_at in used_creation_times:
                created_at = created_at - timedelta(minutes=10)
            used_creation_times.add(created_at)
        else:
            # Create normal tickets (well within SLA, even after 2 hour task execution)
            if user["service_level"] == "pro":
                # Well within 36-hour SLA
                hours_ago = random.randint(1, 20)  # 1-20 hours ago
            elif user["service_level"] == "max":
                # Well within 24-hour SLA  
                hours_ago = random.randint(1, 15)  # 1-15 hours ago
            elif user["service_level"] == "basic":
                # Well within 72-hour SLA
                hours_ago = random.randint(1, 40)  # 1-40 hours ago
            
            created_at = current_time - timedelta(hours=hours_ago)
            
            # Ensure unique creation time with at least 10 minute difference
            while created_at in used_creation_times:
                created_at = created_at - timedelta(minutes=10)
            used_creation_times.add(created_at)
            
            # Some have responses, some are still within time limit
            has_response = random.choice([True, False])
            first_response_at = None
            if has_response:
                response_delay_hours = random.randint(1, hours_ago-1) if hours_ago > 1 else 1
                first_response_at = created_at + timedelta(hours=response_delay_hours)
            
            status = "resolved" if has_response else random.choice(["open", "in_progress"])
            priority = "normal"
        
        ticket_data = {
            "ticket_number": f"TK-{ticket_counter}",
            "user_email": user["email"],
            "subject": subject,
            "description": f"Detailed description: {subject}. Customer {user['name']} reported related issues requiring assistance from the technical support team.",
            "status": status,
            "priority": priority,
            "ticket_type": ticket_type,
            "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "first_response_at": first_response_at.strftime("%Y-%m-%d %H:%M:%S") if first_response_at else None
        }
        tickets_data.append(ticket_data)
        ticket_counter += 1
    
    return users_data, tickets_data


async def initialize_database():
    """Main logic for initializing database and return ticket list"""
    print("🏦 SNOWFLAKE DATABASE INITIALIZATION")
    print("=" * 60)
    print("Database: SLA_MONITOR")
    print("Schema: PUBLIC")
    print("Purpose: Customer support SLA timeout monitoring system")
    
    # List to store ticket information for return
    ticket_list = []
    
    # Display table structure design
    display_table_structure()
    
    # Create MCP server manager
    mcp_manager = MCPServerManager(
        agent_workspace="./",
        config_dir="configs/mcp_servers",
        local_token_key_session=local_token_key_session
    )
    
    try:
        # Get Snowflake server
        snowflake_server = mcp_manager.servers['snowflake']
        
        # Connect to server
        async with snowflake_server as server:
            print("\n" + "="*60)
            print("🚀 EXECUTING DATABASE INITIALIZATION")
            print("="*60)
            
            # 1. Drop existing database (if any) then create new database
            # 1.1 Check if the database exists
            check_database_sql = "SELECT EXISTS(SELECT 1 FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = 'SLA_MONITOR');"
            database_exists = await execute_sql(server, check_database_sql, "Checking if database exists", "read")
            if database_exists:
                print("\n📋 Step 0: Dropping existing database...")
                await call_tool_with_retry(server, tool_name="drop_databases", arguments={"databases": ["SLA_MONITOR"]})

            print("\n📋 Step 1: Creating new database...")
            await call_tool_with_retry(server, tool_name="create_databases", arguments={"databases": ["SLA_MONITOR"]})
            
            
            # 2. Create users table
            print("\n📋 Step 2: Creating USERS table...")
            create_users_sql = """
            CREATE TABLE SLA_MONITOR.PUBLIC.USERS (
                ID INTEGER PRIMARY KEY,
                NAME VARCHAR(255) NOT NULL,
                EMAIL VARCHAR(255) NOT NULL UNIQUE,
                SERVICE_LEVEL VARCHAR(50) NOT NULL,
                CUSTOMER_MANAGER VARCHAR(255) NOT NULL,
                CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
                UPDATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
            );"""
            
            await execute_sql(server, create_users_sql, "Creating USERS table", "create")
            
            # 3. Create tickets table
            print("\n📋 Step 3: Creating SUPPORT_TICKETS table...")
            create_tickets_sql = """
            CREATE TABLE SLA_MONITOR.PUBLIC.SUPPORT_TICKETS (
                ID INTEGER AUTOINCREMENT PRIMARY KEY,
                TICKET_NUMBER VARCHAR(50) NOT NULL UNIQUE,
                USER_ID INTEGER NOT NULL,
                SUBJECT VARCHAR(500) NOT NULL,
                DESCRIPTION TEXT,
                STATUS VARCHAR(50) NOT NULL DEFAULT 'open',
                PRIORITY VARCHAR(20) DEFAULT 'normal',
                TICKET_TYPE VARCHAR(50),
                CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
                FIRST_RESPONSE_AT TIMESTAMP,
                RESOLVED_AT TIMESTAMP,
                UPDATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
                FOREIGN KEY (USER_ID) REFERENCES SLA_MONITOR.PUBLIC.USERS(ID)
            );"""
            
            await execute_sql(server, create_tickets_sql, "Creating SUPPORT_TICKETS table", "create")
            
            # 4. Insert test user data
            print("\n📋 Step 4: Inserting sample user data...")
            users_data, tickets_data = await generate_sample_data(server)

            # Calculate time 7 days ago for user creation/update times - get from Snowflake
            print("🔍 Getting Snowflake current time for user timestamps...")
            try:
                current_time_result = await call_tool_with_retry(
                    server,
                    tool_name="read_query", 
                    arguments={"query": "SELECT CURRENT_TIMESTAMP() AS current_time;"}
                )
                
                # Parse Snowflake's current time
                if current_time_result and hasattr(current_time_result, 'content') and current_time_result.content:
                    result_text = ""
                    if hasattr(current_time_result.content[0], 'text'):
                        result_text = current_time_result.content[0].text
                    elif hasattr(current_time_result.content[0], 'content'):
                        result_text = current_time_result.content[0].content
                    else:
                        result_text = str(current_time_result.content[0])
                    
                    # Try to extract timestamp from result
                    import re
                    timestamp_pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
                    matches = re.findall(timestamp_pattern, result_text)
                    if matches:
                        current_time_str = matches[0]
                        current_time = datetime.strptime(current_time_str, "%Y-%m-%d %H:%M:%S")
                        print(f"✅ Using Snowflake time for users: {current_time}")
                    else:
                        print("⚠️  Could not parse Snowflake time, using local time")
                        current_time = datetime.now()
                else:
                    print("⚠️  Could not get Snowflake time, using local time")
                    current_time = datetime.now()
            except Exception as e:
                print(f"⚠️  Error getting Snowflake time: {e}, using local time")
                current_time = datetime.now()
                
            seven_days_ago = current_time - timedelta(days=7)
            seven_days_ago_str = seven_days_ago.strftime("%Y-%m-%d %H:%M:%S")

            for i, user in enumerate(users_data):
                name = user['name'].replace("'", "''")
                user_id = 1001 + i  # Use IDs 1001-1015
                insert_user_sql = f"""
                INSERT INTO SLA_MONITOR.PUBLIC.USERS
                (ID, NAME, EMAIL, SERVICE_LEVEL, CUSTOMER_MANAGER, CREATED_AT, UPDATED_AT)
                VALUES
                ({user_id}, '{name}', '{user['email']}', '{user['service_level']}', '{user['customer_manager']}',
                 '{seven_days_ago_str}', '{seven_days_ago_str}');
                """
                await execute_sql(server, insert_user_sql, f"Inserting user {user['name']} with ID {user_id}", "write")
            
            # 5. Insert test ticket data
            print("\n📋 Step 5: Inserting sample ticket data...")
            
            # Create simple user ID mapping (1001-1015)
            user_id_map = {}
            for i, user in enumerate(users_data):
                user_id_map[user['email']] = 1001 + i
            
            print(f"User ID mapping: {len(user_id_map)} users mapped to IDs 1001-1015")
            
            for ticket in tickets_data:
                subject = ticket['subject'].replace("'", "''")
                description = ticket['description'].replace("'", "''")
                first_response_part = f"'{ticket['first_response_at']}'" if ticket['first_response_at'] else 'NULL'
                user_id = user_id_map.get(ticket['user_email'])
                
                if user_id is None:
                    print(f"❌ Warning: Could not find user ID for {ticket['user_email']}, skipping ticket {ticket['ticket_number']}")
                    continue
                
                # Set updated_at to Snowflake current time for consistency
                try:
                    current_time_result = await call_tool_with_retry(
                        server,
                        tool_name="read_query", 
                        arguments={"query": "SELECT CURRENT_TIMESTAMP() AS current_time;"}
                    )
                    
                    # Parse Snowflake's current time
                    if current_time_result and hasattr(current_time_result, 'content') and current_time_result.content:
                        result_text = ""
                        if hasattr(current_time_result.content[0], 'text'):
                            result_text = current_time_result.content[0].text
                        elif hasattr(current_time_result.content[0], 'content'):
                            result_text = current_time_result.content[0].content
                        else:
                            result_text = str(current_time_result.content[0])
                        
                        # Try to extract timestamp from result
                        import re
                        timestamp_pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
                        matches = re.findall(timestamp_pattern, result_text)
                        if matches:
                            updated_at_str = matches[0]
                        else:
                            updated_at_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        updated_at_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                except Exception as e:
                    updated_at_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                insert_ticket_sql = f"""
                INSERT INTO SLA_MONITOR.PUBLIC.SUPPORT_TICKETS 
                (TICKET_NUMBER, USER_ID, SUBJECT, DESCRIPTION, STATUS, PRIORITY, TICKET_TYPE, CREATED_AT, FIRST_RESPONSE_AT, UPDATED_AT)
                VALUES 
                ('{ticket['ticket_number']}', {user_id}, '{subject}', '{description}', 
                 '{ticket['status']}', '{ticket['priority']}', '{ticket['ticket_type']}', 
                 '{ticket['created_at']}', {first_response_part}, '{updated_at_str}');
                """
                await execute_sql(server, insert_ticket_sql, f"Inserting ticket {ticket['ticket_number']}", "write")
            
            # 6. Verify setup
            print("\n📋 Step 6: Verifying setup...")
            
            verification_queries = [
                ("SELECT COUNT(*) AS TOTAL_USERS FROM SLA_MONITOR.PUBLIC.USERS;", "Counting total users"),
                ("SELECT COUNT(*) AS TOTAL_TICKETS FROM SLA_MONITOR.PUBLIC.SUPPORT_TICKETS;", "Counting total tickets"),
                ("SELECT SERVICE_LEVEL, COUNT(*) AS USER_COUNT FROM SLA_MONITOR.PUBLIC.USERS GROUP BY SERVICE_LEVEL ORDER BY SERVICE_LEVEL;", "Users by service level")
            ]
            
            for sql, desc in verification_queries:
                await execute_sql(server, sql, desc, "read")
            
            # 7. Prepare ticket list for return
            print("\n📋 Step 7: Preparing ticket list for return...")
            for ticket in tickets_data:
                user_email = ticket['user_email']
                # Find the corresponding user data
                user_data = next((u for u in users_data if u['email'] == user_email), None)
                if user_data:
                    # Determine if ticket is overdue
                    created_at = datetime.strptime(ticket['created_at'], "%Y-%m-%d %H:%M:%S")
                    is_overdue = (ticket['status'] in ['open', 'in_progress'] and 
                                ticket['first_response_at'] is None)
                    
                    if is_overdue:
                        # Check if it's actually overdue based on SLA
                        sla_config = SLA_CONFIGS[user_data['service_level']]
                        sla_minutes = sla_config['response_time_minutes']
                        time_diff = (current_time - created_at).total_seconds() / 60  # in minutes
                        is_overdue = time_diff > sla_minutes
                    
                    ticket_info = {
                        'ticket_number': ticket['ticket_number'],
                        'manager_email': user_data['customer_manager'],
                        'user_email': user_email,
                        'service_level': user_data['service_level'],
                        'created_at': ticket['created_at'],
                        'is_overdue': is_overdue
                    }
                    ticket_list.append(ticket_info)
            
            print("\n🎉 DATABASE INITIALIZATION COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            print("✅ Tables created: USERS, SUPPORT_TICKETS")
            print("✅ Sample data inserted for testing")
            print(f"✅ Generated {len(ticket_list)} tickets for monitoring")
            print("\nReady to start SLA timeout monitoring and email notification processing...")
            
            return ticket_list
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        sys.exit(1)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Initialize Snowflake database for SLA timeout monitoring")
    parser.add_argument("--dry-run", action="store_true", help="Show table structure only without executing")
    args = parser.parse_args()
    
    # Set random seed to ensure reproducibility
    random.seed(42)
    
    if args.dry_run:
        print("🏦 SNOWFLAKE DATABASE INITIALIZATION (DRY RUN)")
        print("=" * 60)
        display_table_structure()
        print("\n✅ Dry run completed - use without --dry-run to execute")
    else:
        # Run async initialization and get ticket list
        ticket_list = asyncio.run(initialize_database())
        
        # Display ticket list summary
        print("\n📋 TICKET LIST SUMMARY")
        print("=" * 80)
        overdue_count = sum(1 for t in ticket_list if t['is_overdue'])
        print(f"Total tickets: {len(ticket_list)}")
        print(f"Overdue tickets: {overdue_count}")
        print(f"Within SLA: {len(ticket_list) - overdue_count}")
        
        # Display a few sample tickets
        print("\nSample tickets:")
        for i, ticket in enumerate(ticket_list[:3]):
            status = "🔴 OVERDUE" if ticket['is_overdue'] else "🟢 OK"
            print(f"  {i+1}. {ticket['ticket_number']} - {ticket['service_level']} - {status}")
        
        return ticket_list


if __name__ == "__main__":
    main()