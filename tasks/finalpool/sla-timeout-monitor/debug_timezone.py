#!/usr/bin/env python3
"""
时区诊断脚本 - 检查Snowflake时间设置问题
"""

import asyncio
import os
import sys
from rich import print

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
sys.path.insert(0, project_root)

try:
    from utils.mcp.tool_servers import MCPServerManager, call_tool_with_retry
except ImportError as e:
    print(f"Import error: {e}")
    print("Please run from the project root directory or ensure the project structure is correct")
    sys.exit(1)

try:
    from token_key_session import all_token_key_session as local_token_key_session
except ImportError:
    print("警告: 未找到任务特定的 token_key_session.py，将使用默认配置")
    local_token_key_session = {
        "snowflake_op_allowed_databases": "SLA_MONITOR",
    }


async def execute_query(server, sql_query: str, description: str = ""):
    """执行查询并返回结果"""
    try:
        if description:
            print(f"🔍 {description}")
        
        result = await call_tool_with_retry(
            server,
            tool_name="read_query",
            arguments={"query": sql_query}
        )
        
        if hasattr(result, 'content') and result.content:
            if hasattr(result.content[0], 'text'):
                return result.content[0].text
            elif hasattr(result.content[0], 'content'):
                return result.content[0].content
        return None
        
    except Exception as e:
        print(f"❌ Error executing query ({description}): {e}")
        return None


async def debug_timezone():
    """诊断时区问题"""
    print("🕰️ SNOWFLAKE TIMEZONE DEBUGGING")
    print("=" * 60)
    
    mcp_manager = MCPServerManager(
        agent_workspace="./",
        config_dir="configs/mcp_servers",
        local_token_key_session=local_token_key_session
    )
    
    try:
        snowflake_server = mcp_manager.servers['snowflake']
        
        async with snowflake_server as server:
            
            # 1. 检查时区设置
            timezone_queries = [
                ("SELECT CURRENT_TIMESTAMP() as CURRENT_TIMESTAMP;", "检查当前时间戳"),
                ("SELECT CURRENT_TIMESTAMP()::timestamp_ltz as CURRENT_TIME_LTZ;", "检查时区设置"),
                ("SELECT CURRENT_TIMESTAMP()::timestamp_ntz as CURRENT_TIME_NTZ;", "检查无时区时间"),
                ("SHOW PARAMETERS LIKE 'timezone';", "显示时区参数"),
            ]
            
            for query, desc in timezone_queries:
                result = await execute_query(server, query, desc)
                if result:
                    print(result)
                    print("-" * 40)
            
            # 2. 检查具体工单的时间计算
            print("\n📋 检查具体工单时间计算:")
            ticket_time_query = """
            SELECT 
                TICKET_NUMBER,
                CREATED_AT,
                CURRENT_TIMESTAMP() as CURRENT_TIME,
                CURRENT_TIMESTAMP()::timestamp_ntz as CURRENT_TIME_NTZ,
                CREATED_AT::timestamp_ntz as CREATED_AT_NTZ,
                DATEDIFF('minute', CREATED_AT, CURRENT_TIMESTAMP()) as DIFF_WITH_TZ,
                DATEDIFF('minute', CREATED_AT::timestamp_ntz, CURRENT_TIMESTAMP()::timestamp_ntz) as DIFF_NO_TZ,
                DATEADD('minute', 30, CREATED_AT) as CREATED_PLUS_30MIN,
                CASE 
                    WHEN CURRENT_TIMESTAMP() > DATEADD('minute', 30, CREATED_AT) THEN 'SHOULD_BE_TIMEOUT'
                    ELSE 'NOT_TIMEOUT'
                END as LOGIC_CHECK
            FROM SLA_MONITOR.PUBLIC.SUPPORT_TICKETS 
            WHERE TICKET_NUMBER = 'TK-1014';
            """
            
            result = await execute_query(server, ticket_time_query, "详细时间计算分析")
            if result:
                print(result)
            
            # 3. 尝试修复：使用timestamp_ntz
            print("\n📋 尝试使用无时区时间戳进行计算:")
            fixed_query = """
            SELECT 
                t.TICKET_NUMBER,
                t.SUBJECT,
                t.STATUS,
                t.CREATED_AT,
                t.FIRST_RESPONSE_AT,
                u.EMAIL as USER_EMAIL,
                u.SERVICE_LEVEL,
                s.RESPONSE_TIME_MINUTES,
                DATEDIFF('minute', t.CREATED_AT::timestamp_ntz, CURRENT_TIMESTAMP()::timestamp_ntz) as MINUTES_ELAPSED_FIXED,
                CASE 
                    WHEN t.FIRST_RESPONSE_AT IS NULL 
                         AND DATEDIFF('minute', t.CREATED_AT::timestamp_ntz, CURRENT_TIMESTAMP()::timestamp_ntz) > s.RESPONSE_TIME_MINUTES
                    THEN 'TIMEOUT'
                    WHEN t.FIRST_RESPONSE_AT IS NULL 
                         AND DATEDIFF('minute', t.CREATED_AT::timestamp_ntz, CURRENT_TIMESTAMP()::timestamp_ntz) > (s.RESPONSE_TIME_MINUTES * 0.8)
                    THEN 'WARNING'
                    ELSE 'OK'
                END as SLA_STATUS_FIXED,
                CASE 
                    WHEN t.FIRST_RESPONSE_AT IS NULL 
                         AND DATEDIFF('minute', t.CREATED_AT::timestamp_ntz, CURRENT_TIMESTAMP()::timestamp_ntz) > s.RESPONSE_TIME_MINUTES
                    THEN DATEDIFF('minute', t.CREATED_AT::timestamp_ntz, CURRENT_TIMESTAMP()::timestamp_ntz) - s.RESPONSE_TIME_MINUTES
                    ELSE 0
                END as TIMEOUT_MINUTES_FIXED
            FROM SLA_MONITOR.PUBLIC.SUPPORT_TICKETS t
            JOIN SLA_MONITOR.PUBLIC.USERS u ON t.USER_ID = u.ID
            JOIN SLA_MONITOR.PUBLIC.SLA_CONFIGURATIONS s ON u.SERVICE_LEVEL = s.SERVICE_LEVEL
            WHERE t.STATUS IN ('open', 'in_progress', 'pending_response')
            ORDER BY s.PRIORITY_ORDER DESC, t.CREATED_AT;
            """
            
            result = await execute_query(server, fixed_query, "使用修复的时间计算")
            if result:
                print(result)
        
    except Exception as e:
        print(f"❌ Timezone debugging failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(debug_timezone())