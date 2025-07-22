import asyncio
import json
from argparse import ArgumentParser
from pathlib import Path
from datetime import datetime, timedelta
from utils.mcp.tool_servers import MCPServerManager, call_tool_with_retry, ToolCallError

async def setup_calendar_events(credentials_file: str):
    """
    在Google Calendar中设置初始事件，使教授的日历不完全空白
    
    设置策略：
    - 今天下午3-5点：已有其他会议
    - 明天上午9-11点：已有其他事务
    这样Agent需要避开这些时间段来安排面试
    """
    print("=" * 60)
    print("设置Google Calendar初始状态")
    print("=" * 60)
    
    # 读取今天的日期
    today_file_path = Path(__file__).parent.parent / "groundtruth_workspace" / "today.txt"
    if not today_file_path.exists():
        print(f"❌ today.txt文件不存在: {today_file_path}")
        return False
        
    with open(today_file_path, 'r', encoding='utf-8') as f:
        today_str = f.read().strip()  # ISO like 2025-07-21
    
    today_date = datetime.strptime(today_str, '%Y-%m-%d').date()
    tomorrow_date = today_date + timedelta(days=1)
    
    print(f"📅 今天: {today_date}")
    print(f"📅 明天: {tomorrow_date}")
    
    # 初始化MCP服务器管理器
    try:
        print("\n🔧 初始化MCP服务器管理器...")
        mcp_manager = MCPServerManager(agent_workspace="./", debug=True)
        
        # 连接Google Calendar服务器
        print("🔗 连接Google Calendar服务器...")
        await mcp_manager.connect_servers(['google_calendar'])
        
        if not mcp_manager.is_server_connected('google_calendar'):
            print("❌ Google Calendar服务器连接失败")
            return False
            
        google_calendar_server = mcp_manager.connected_servers['google_calendar']
        print("✅ Google Calendar服务器连接成功")
        
    except Exception as e:
        print(f"❌ MCP服务器初始化失败: {e}")
        return False
    
    # 定义要创建的事件
    events_to_create = [
        {
            "summary": "学术委员会会议",
            "description": "讨论本学期课程安排和教学计划\n地点：会议室A\n参与人员：各系主任",
            "location": "HKUST 会议室A", 
            "start": {
                "dateTime": f"{today_date}T15:00:00+08:00",
                "timeZone": "Asia/Hong_Kong"
            },
            "end": {
                "dateTime": f"{today_date}T17:00:00+08:00", 
                "timeZone": "Asia/Hong_Kong"
            }
        },
        {
            "summary": "博士生论文答辩",
            "description": "学生：李明华\n论文题目：基于深度学习的图像分析方法研究\n答辩委员会成员到场",
            "location": "HKUST 学术报告厅",
            "start": {
                "dateTime": f"{tomorrow_date}T09:00:00+08:00",
                "timeZone": "Asia/Hong_Kong"
            },
            "end": {
                "dateTime": f"{tomorrow_date}T11:00:00+08:00",
                "timeZone": "Asia/Hong_Kong"
            }
        }
    ]
    
    # 创建事件
    created_events = []
    async with mcp_manager:
        for i, event_data in enumerate(events_to_create, 1):
            try:
                print(f"\n📝 创建事件 {i}/{len(events_to_create)}: {event_data['summary']}")
                print(f"   时间: {event_data['start']['dateTime']} - {event_data['end']['dateTime']}")
                
                result = await call_tool_with_retry(
                    google_calendar_server, 
                    "create_event", 
                    event_data
                )
                
                print(f"   ✅ 事件创建成功")
                created_events.append(result)
                
            except ToolCallError as e:
                print(f"   ❌ 事件创建失败: {e}")
                return False
            except Exception as e:
                print(f"   ❌ 创建事件时发生错误: {e}")
                return False
    
    print(f"\n🎉 成功创建 {len(created_events)} 个初始日历事件!")
    print("📋 事件汇总:")
    for i, event_data in enumerate(events_to_create, 1):
        start_time = datetime.fromisoformat(event_data['start']['dateTime'].replace('+08:00', ''))
        end_time = datetime.fromisoformat(event_data['end']['dateTime'].replace('+08:00', ''))
        print(f"   {i}. {event_data['summary']}")
        print(f"      {start_time.strftime('%Y-%m-%d %H:%M')} - {end_time.strftime('%H:%M')}")
        print(f"      地点: {event_data['location']}")
    
    print("\n✅ Google Calendar初始状态设置完成!")
    return True

async def main():
    parser = ArgumentParser(description="设置Google Calendar初始事件")
    parser.add_argument("--credentials_file", default="configs/credentials.json", help="Google API凭证文件路径")
    args = parser.parse_args()
    
    success = await setup_calendar_events(args.credentials_file)
    
    if not success:
        print("\n❌ Google Calendar初始状态设置失败")
        exit(1)
    
    print("\n🎯 初始状态设置说明:")
    print("   - 今天下午3-5点：学术委员会会议（Agent需要避开此时间段）")
    print("   - 明天上午9-11点：博士生论文答辩（Agent需要避开此时间段）")
    print("   - Agent应该在其他时间段安排学生面试")

if __name__ == "__main__":
    asyncio.run(main()) 