#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath('../../..'))
from utils.mcp.tool_servers import MCPServerManager, call_tool_with_retry

async def check_tables():
    try:
        from token_key_session import all_token_key_session as local_token_key_session
    except ImportError:
        local_token_key_session = {'snowflake_op_allowed_databases': 'SLA_MONITOR'}
    
    mcp_manager = MCPServerManager(agent_workspace='./', config_dir='configs/mcp_servers', local_token_key_session=local_token_key_session)
    snowflake_server = mcp_manager.servers['snowflake']
    async with snowflake_server as server:
        result = await call_tool_with_retry(server, tool_name='read_query', arguments={'query': 'DESCRIBE TABLE SLA_MONITOR.PUBLIC.USERS;'})
        print('USERS表结构:')
        print(result.content[0].text if hasattr(result.content[0], 'text') else result.content[0].content)
        
        print('\n当前用户数据:')
        result2 = await call_tool_with_retry(server, tool_name='read_query', arguments={'query': 'SELECT * FROM SLA_MONITOR.PUBLIC.USERS;'})
        print(result2.content[0].text if hasattr(result2.content[0], 'text') else result2.content[0].content)
        
        print('\n当前超时工单:')
        result3 = await call_tool_with_retry(server, tool_name='read_query', arguments={'query': '''
        SELECT t.TICKET_NUMBER, u.EMAIL, u.SERVICE_LEVEL, t.STATUS, t.CREATED_AT, t.FIRST_RESPONSE_AT
        FROM SLA_MONITOR.PUBLIC.SUPPORT_TICKETS t
        JOIN SLA_MONITOR.PUBLIC.USERS u ON t.USER_ID = u.ID
        WHERE t.STATUS IN ('open', 'in_progress', 'pending_response')
          AND t.FIRST_RESPONSE_AT IS NULL
        ORDER BY u.SERVICE_LEVEL, t.CREATED_AT;
        '''})
        print(result3.content[0].text if hasattr(result3.content[0], 'text') else result3.content[0].content)

asyncio.run(check_tables())