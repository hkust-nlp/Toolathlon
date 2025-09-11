#!/usr/bin/env python3
"""
修复时区数据脚本 - 重新生成正确时区的测试工单
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
import random
from rich import print

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
sys.path.insert(0, project_root)

try:
    from utils.mcp.tool_servers import MCPServerManager, call_tool_with_retry
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

try:
    from token_key_session import all_token_key_session as local_token_key_session
except ImportError:
    local_token_key_session = {"snowflake_op_allowed_databases": "SLA_MONITOR"}


async def execute_sql(server, sql_query: str, description: str = ""):
    """执行SQL查询"""
    try:
        if description:
            print(f"🔄 {description}")
        
        result = await call_tool_with_retry(
            server,
            tool_name="write_query",
            arguments={"query": sql_query}
        )
        
        print(f"✅ {description}")
        return True
        
    except Exception as e:
        print(f"❌ Error ({description}): {e}")
        return False


async def fix_timezone_data():
    """修复时区数据"""
    print("🔧 FIXING TIMEZONE DATA")
    print("=" * 60)
    
    mcp_manager = MCPServerManager(
        agent_workspace="./",
        config_dir="configs/mcp_servers", 
        local_token_key_session=local_token_key_session
    )
    
    try:
        snowflake_server = mcp_manager.servers['snowflake']
        
        async with snowflake_server as server:
            
            # 1. 清空现有工单数据
            print("📋 Step 1: 清空现有工单数据...")
            await execute_sql(server, "DELETE FROM SLA_MONITOR.PUBLIC.SUPPORT_TICKETS;", "删除所有工单")
            
            # 2. 生成正确时区的测试数据
            print("\n📋 Step 2: 生成正确时区的测试数据...")
            
            # 用户列表
            users = [
                {"email": "raymondm@mcp.com", "service_level": "basic"},
                {"email": "donald_castillo@mcp.com", "service_level": "max"},
                {"email": "ramosb@mcp.com", "service_level": "pro"},
                {"email": "ortiza2@mcp.com", "service_level": "basic"},
                {"email": "clarkt12@mcp.com", "service_level": "pro"},
            ]
            
            # 工单主题
            subjects = [
                "Application crashes when uploading large files",
                "Login page returns 500 error intermittently", 
                "How to set up SSO for our organization",
                "Need ability to bulk edit user permissions",
                "Unable to reset password using email link"
            ]
            
            # 使用洛杉矶时区作为基准时间
            la_tz = timezone(timedelta(hours=-7))
            current_time = datetime.now(la_tz)
            
            random.seed(42)  # 确保可重现
            
            ticket_counter = 1000
            for i in range(10):  # 生成10个工单
                user = random.choice(users)
                subject = random.choice(subjects)
                
                # 生成不同的创建时间来模拟不同的SLA状态
                if i < 3:  # 前3个工单：明显超时
                    hours_ago = random.randint(2, 8)  # 2-8小时前
                    minutes_ago = random.randint(0, 59)
                    created_at = current_time - timedelta(hours=hours_ago, minutes=minutes_ago)
                    has_response = False  # 未回复
                elif i < 6:  # 中间3个：即将超时或刚好超时
                    if user['service_level'] == 'max':
                        minutes_ago = random.randint(35, 120)  # 35-120分钟前（超过30分钟）
                    elif user['service_level'] == 'pro':
                        minutes_ago = random.randint(65, 180)  # 65-180分钟前（超过60分钟）
                    else:  # basic
                        minutes_ago = random.randint(185, 300) # 185-300分钟前（超过180分钟）
                    created_at = current_time - timedelta(minutes=minutes_ago)
                    has_response = False  # 未回复
                else:  # 后4个：正常处理
                    minutes_ago = random.randint(5, 25)  # 5-25分钟前
                    created_at = current_time - timedelta(minutes=minutes_ago)
                    has_response = random.choice([True, False])  # 可能已回复
                
                # 转换为无时区格式
                created_at_str = created_at.strftime("%Y-%m-%d %H:%M:%S")
                
                status = "open" if not has_response else random.choice(["in_progress", "pending_response"])
                first_response_at = "NULL"
                if has_response:
                    response_delay = random.randint(10, 60)
                    response_time = created_at + timedelta(minutes=response_delay)
                    first_response_at = f"'{response_time.strftime('%Y-%m-%d %H:%M:%S')}'"
                
                insert_sql = f"""
                INSERT INTO SLA_MONITOR.PUBLIC.SUPPORT_TICKETS 
                (TICKET_NUMBER, USER_ID, SUBJECT, DESCRIPTION, STATUS, PRIORITY, TICKET_TYPE, CREATED_AT, FIRST_RESPONSE_AT)
                VALUES 
                ('TK-{ticket_counter}', 
                 (SELECT ID FROM SLA_MONITOR.PUBLIC.USERS WHERE EMAIL = '{user['email']}' LIMIT 1),
                 '{subject}', 
                 '详细描述: {subject}. 用户报告了相关问题，需要技术支持团队的协助。',
                 '{status}', 'normal', 'technical', 
                 '{created_at_str}', {first_response_at});
                """
                
                await execute_sql(server, insert_sql, f"插入工单 TK-{ticket_counter} ({user['service_level']}级别)")
                ticket_counter += 1
            
            print("\n🎉 时区数据修复完成！")
            print("✅ 生成了10个新工单，时间使用正确的洛杉矶时区")
            print("✅ 包含明显超时、即将超时、和正常工单")
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")


if __name__ == "__main__":
    asyncio.run(fix_timezone_data())