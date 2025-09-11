#!/usr/bin/env python3
"""
SLA超时监控脚本
检查所有未回复的工单，识别超时的工单并生成报告
"""

import asyncio
import os
import sys
# from datetime import datetime, timedelta  # 当前脚本中暂未使用
from rich import print
from rich.console import Console
# from rich.table import Table  # 当前脚本中暂未使用

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
# Go up: sla-timeout-monitor -> fan -> tasks -> mcpbench_dev
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
sys.path.insert(0, project_root)

try:
    from utils.mcp.tool_servers import MCPServerManager, call_tool_with_retry
except ImportError as e:
    print(f"Import error: {e}")
    print("Please run from the project root directory or ensure the project structure is correct")
    sys.exit(1)

# 导入任务特定的配置
try:
    from token_key_session import all_token_key_session as local_token_key_session
except ImportError:
    print("警告: 未找到任务特定的 token_key_session.py，将使用默认配置")
    local_token_key_session = {
        "snowflake_op_allowed_databases": "SLA_MONITOR",
    }

console = Console()


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
                result_text = result.content[0].text
            elif hasattr(result.content[0], 'content'):
                result_text = result.content[0].content
            else:
                result_text = str(result.content[0])
            
            # 如果结果包含"status: success"，说明查询成功但可能没有数据
            if "status: success" in result_text and "Query executed successfully" in result_text:
                print("  ✅ 查询执行成功，但没有返回匹配的数据行")
                return None
            
            return result_text
        return None
        
    except Exception as e:
        print(f"❌ Error executing query ({description}): {e}")
        return None


async def check_sla_timeouts():
    """检查SLA超时工单"""
    print("🚨 SLA TIMEOUT MONITORING")
    print("=" * 60)
    
    # 创建MCP服务器管理器
    mcp_manager = MCPServerManager(
        agent_workspace="./",
        config_dir="configs/mcp_servers",
        local_token_key_session=local_token_key_session
    )
    
    try:
        # 获取Snowflake服务器
        snowflake_server = mcp_manager.servers['snowflake']
        
        async with snowflake_server as server:
            print("\n📋 Step 1: 获取SLA配置...")
            
            # 获取SLA配置
            sla_query = """
            SELECT SERVICE_LEVEL, RESPONSE_TIME_MINUTES, FOLLOWUP_TIME_MINUTES, PRIORITY_ORDER
            FROM SLA_MONITOR.PUBLIC.SLA_CONFIGURATIONS
            ORDER BY PRIORITY_ORDER DESC;
            """
            
            await execute_query(server, sla_query, "Loading SLA configurations")
            print("✅ SLA配置加载完成")
            
            print("\n📋 Step 2: 检查超时工单...")
            
            # 查询所有未首次回复的工单（可能超时）
            timeout_query = """
            SELECT 
                t.TICKET_NUMBER,
                t.SUBJECT,
                t.STATUS,
                t.CREATED_AT,
                t.FIRST_RESPONSE_AT,
                u.NAME as USER_NAME,
                u.EMAIL as USER_EMAIL,
                u.SERVICE_LEVEL,
                u.CUSTOMER_MANAGER,
                s.RESPONSE_TIME_MINUTES,
                s.PRIORITY_ORDER,
                DATEDIFF('minute', t.CREATED_AT::timestamp_ntz, CURRENT_TIMESTAMP()::timestamp_ntz) as MINUTES_SINCE_CREATED,
                CASE 
                    WHEN t.FIRST_RESPONSE_AT IS NULL 
                         AND DATEDIFF('minute', t.CREATED_AT::timestamp_ntz, CURRENT_TIMESTAMP()::timestamp_ntz) > s.RESPONSE_TIME_MINUTES
                    THEN 'TIMEOUT'
                    WHEN t.FIRST_RESPONSE_AT IS NULL 
                         AND DATEDIFF('minute', t.CREATED_AT::timestamp_ntz, CURRENT_TIMESTAMP()::timestamp_ntz) > (s.RESPONSE_TIME_MINUTES * 0.8)
                    THEN 'WARNING'
                    ELSE 'OK'
                END as SLA_STATUS,
                CASE 
                    WHEN t.FIRST_RESPONSE_AT IS NULL 
                         AND DATEDIFF('minute', t.CREATED_AT::timestamp_ntz, CURRENT_TIMESTAMP()::timestamp_ntz) > s.RESPONSE_TIME_MINUTES
                    THEN DATEDIFF('minute', t.CREATED_AT::timestamp_ntz, CURRENT_TIMESTAMP()::timestamp_ntz) - s.RESPONSE_TIME_MINUTES
                    ELSE 0
                END as TIMEOUT_MINUTES
            FROM SLA_MONITOR.PUBLIC.SUPPORT_TICKETS t
            JOIN SLA_MONITOR.PUBLIC.USERS u ON t.USER_ID = u.ID
            JOIN SLA_MONITOR.PUBLIC.SLA_CONFIGURATIONS s ON u.SERVICE_LEVEL = s.SERVICE_LEVEL
            WHERE t.STATUS IN ('open', 'in_progress', 'pending_response')
            ORDER BY s.PRIORITY_ORDER DESC, TIMEOUT_MINUTES DESC;
            """
            
            result = await execute_query(server, timeout_query, "Checking for timeout tickets")
            
            if result:
                print("\n🔍 SLA超时检查结果:")
                print("=" * 80)
                print(result)
            
            print("\n📋 Step 3: 生成超时工单汇总报告...")
            
            # 只获取超时的工单
            timeout_only_query = """
            SELECT 
                t.TICKET_NUMBER,
                t.SUBJECT,
                u.NAME as USER_NAME,
                u.EMAIL as USER_EMAIL,
                u.SERVICE_LEVEL,
                u.CUSTOMER_MANAGER,
                t.CREATED_AT,
                s.RESPONSE_TIME_MINUTES,
                DATEDIFF('minute', t.CREATED_AT::timestamp_ntz, CURRENT_TIMESTAMP()::timestamp_ntz) as MINUTES_SINCE_CREATED,
                DATEDIFF('minute', t.CREATED_AT::timestamp_ntz, CURRENT_TIMESTAMP()::timestamp_ntz) - s.RESPONSE_TIME_MINUTES as TIMEOUT_MINUTES
            FROM SLA_MONITOR.PUBLIC.SUPPORT_TICKETS t
            JOIN SLA_MONITOR.PUBLIC.USERS u ON t.USER_ID = u.ID
            JOIN SLA_MONITOR.PUBLIC.SLA_CONFIGURATIONS s ON u.SERVICE_LEVEL = s.SERVICE_LEVEL
            WHERE t.STATUS IN ('open', 'in_progress', 'pending_response')
              AND t.FIRST_RESPONSE_AT IS NULL 
              AND DATEDIFF('minute', t.CREATED_AT::timestamp_ntz, CURRENT_TIMESTAMP()::timestamp_ntz) > s.RESPONSE_TIME_MINUTES
            ORDER BY s.PRIORITY_ORDER DESC, TIMEOUT_MINUTES DESC;
            """
            
            timeout_result = await execute_query(server, timeout_only_query, "Getting timeout tickets only")
            
            if timeout_result and "Query executed successfully" not in timeout_result:
                print("\n🚨 超时工单详细报告:")
                print("=" * 80)
                print(timeout_result)
                print("\n📧 需要发送通知给客服经理:")
                print("  - dhall@mcp.com (Daniel Hall - 高级客服经理)")
                print("  - andersonp@mcp.com (Pamela Anderson - 客户成功经理)")
                print("\n📧 需要发送致歉邮件给以下超时工单的客户:")
                
                # 解析查询结果提取客户邮箱
                lines = timeout_result.split('\n')
                customer_emails = []
                for line in lines:
                    if 'USER_EMAIL:' in line and '@mcp.com' in line:
                        # 提取USER_EMAIL字段的邮箱地址
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == 'USER_EMAIL:' and i + 1 < len(parts):
                                email = parts[i + 1].strip()
                                if '@mcp.com' in email:
                                    customer_emails.append(email)
                
                if customer_emails:
                    for email in set(customer_emails):  # 去重
                        print(f"  - {email}")
                else:
                    print("  暂时无法从查询结果中解析出具体客户邮箱")
                    print("  请查看上述查询结果中的USER_EMAIL列")
            else:
                print("✅ 当前没有超时的工单！")
                print("   所有工单都在SLA时限内得到了及时响应。")
                
                # 显示当前工单状态以便了解为什么没有超时
                print("\n📋 让我们查看当前工单状态:")
                current_tickets_query = """
                SELECT 
                    t.TICKET_NUMBER,
                    u.SERVICE_LEVEL,
                    t.STATUS,
                    t.CREATED_AT,
                    t.FIRST_RESPONSE_AT,
                    s.RESPONSE_TIME_MINUTES,
                    DATEDIFF('minute', t.CREATED_AT::timestamp_ntz, CURRENT_TIMESTAMP()::timestamp_ntz) as MINUTES_ELAPSED,
                    CASE 
                        WHEN t.FIRST_RESPONSE_AT IS NOT NULL THEN '已回复'
                        WHEN DATEDIFF('minute', t.CREATED_AT::timestamp_ntz, CURRENT_TIMESTAMP()::timestamp_ntz) <= s.RESPONSE_TIME_MINUTES THEN '在时限内'
                        ELSE '应该超时了'
                    END as STATUS_CHECK
                FROM SLA_MONITOR.PUBLIC.SUPPORT_TICKETS t
                JOIN SLA_MONITOR.PUBLIC.USERS u ON t.USER_ID = u.ID
                JOIN SLA_MONITOR.PUBLIC.SLA_CONFIGURATIONS s ON u.SERVICE_LEVEL = s.SERVICE_LEVEL
                ORDER BY t.CREATED_AT DESC;
                """
                
                current_result = await execute_query(server, current_tickets_query, "Checking all current tickets")
                if current_result and "Query executed successfully" not in current_result:
                    print(current_result)
            
            print("\n📋 Step 4: 统计分析...")
            
            # 统计分析查询
            stats_query = """
            SELECT 
                u.SERVICE_LEVEL,
                COUNT(*) as TOTAL_TICKETS,
                COUNT(CASE WHEN t.FIRST_RESPONSE_AT IS NULL THEN 1 END) as PENDING_RESPONSE,
                COUNT(CASE 
                    WHEN t.FIRST_RESPONSE_AT IS NULL 
                         AND DATEDIFF('minute', t.CREATED_AT::timestamp_ntz, CURRENT_TIMESTAMP()::timestamp_ntz) > s.RESPONSE_TIME_MINUTES
                    THEN 1 
                END) as TIMEOUT_COUNT,
                AVG(CASE 
                    WHEN t.FIRST_RESPONSE_AT IS NOT NULL 
                    THEN DATEDIFF('minute', t.CREATED_AT, t.FIRST_RESPONSE_AT)
                END) as AVG_RESPONSE_TIME_MINUTES,
                ROUND(
                    (COUNT(*) - COUNT(CASE 
                        WHEN t.FIRST_RESPONSE_AT IS NULL 
                             AND DATEDIFF('minute', t.CREATED_AT::timestamp_ntz, CURRENT_TIMESTAMP()::timestamp_ntz) > s.RESPONSE_TIME_MINUTES
                        THEN 1 
                    END)) * 100.0 / COUNT(*), 2
                ) as SLA_COMPLIANCE_RATE
            FROM SLA_MONITOR.PUBLIC.SUPPORT_TICKETS t
            JOIN SLA_MONITOR.PUBLIC.USERS u ON t.USER_ID = u.ID
            JOIN SLA_MONITOR.PUBLIC.SLA_CONFIGURATIONS s ON u.SERVICE_LEVEL = s.SERVICE_LEVEL
            GROUP BY u.SERVICE_LEVEL, s.PRIORITY_ORDER
            ORDER BY s.PRIORITY_ORDER DESC;
            """
            
            stats_result = await execute_query(server, stats_query, "Generating SLA statistics")
            
            if stats_result:
                print("\n📊 SLA合规性统计:")
                print("=" * 80)
                print(stats_result)
            
            print("\n🎯 监控完成！")
            print("=" * 60)
            print("✅ 超时工单检查完成")
            print("✅ 客服经理通知列表已生成")
            print("✅ 客户致歉邮件列表已生成")
            print("✅ SLA合规性统计已生成")
        
    except Exception as e:
        print(f"❌ SLA timeout check failed: {e}")
        sys.exit(1)


def main():
    """主函数"""
    print("🚨 启动SLA超时监控检查...")
    asyncio.run(check_sla_timeouts())


if __name__ == "__main__":
    main()