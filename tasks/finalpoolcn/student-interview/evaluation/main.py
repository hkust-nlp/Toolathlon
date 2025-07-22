from argparse import ArgumentParser
import os
from utils.general.helper import read_json
import asyncio
from pprint import pprint
from pathlib import Path
from utils.mcp.tool_servers import MCPServerManager, call_tool_with_retry, ToolCallError

import json

from datetime import datetime
import pytz
from datetime import timedelta

def parse_iso_time(iso_string):
    """
    解析各种格式的 ISO 时间字符串
    """
    # 处理不同的 ISO 格式
    if iso_string.endswith('Z'):
        # UTC 时间
        iso_string = iso_string[:-1] + '+00:00'
    
    try:
        # Python 3.7+ 的方法
        return datetime.fromisoformat(iso_string)
    except:
        # 备选方法：使用 dateutil
        import dateutil.parser
        return dateutil.parser.isoparse(iso_string)


def compare_google_calendar_times(pred_google_time, groundtruth_iso_time, tolerance_seconds=300):
    """
    比较 Google Calendar API 返回的时间
    Google Calendar 可能返回 dateTime 或 date 格式
    """
    def parse_google_time(time_dict):
        if 'dateTime' in time_dict:
            return parse_iso_time(time_dict['dateTime'])
        elif 'date' in time_dict:
            # 全天事件，只有日期
            return datetime.strptime(time_dict['date'], '%Y-%m-%d')
        else:
            raise ValueError("Invalid time format")
    
    parsed_time1 = parse_google_time(pred_google_time)
    parsed_time2 = parse_iso_time(groundtruth_iso_time)
    
    diff = abs((parsed_time1 - parsed_time2).total_seconds())
    print(f"时间差: {diff} 秒 = {diff/60} 分钟 = {diff/3600} 小时")

    return diff <= tolerance_seconds

async def main(args):
    """
    评估学生面试任务的完成情况
    检查点：
    1. 是否正确筛选了有独立一作发表的学生（张小明、王大伟、陈小强）
    2. 是否为符合条件的学生安排了面试时间
    3. 面试时间是否在今天和明天两天内
    """
    print("开始评估学生面试任务...")
    print("=" * 60)
    
    # 1. 检查参数
    print("📋 检查参数:")
    print(f"   agent_workspace: {args.agent_workspace}")
    print(f"   groundtruth_workspace: {args.groundtruth_workspace}")
    print(f"   res_log_file: {args.res_log_file}")
    
    # 2. 确定workspace路径
    workspace_path = args.agent_workspace if args.agent_workspace else "./"
    print(f"   使用的workspace路径: {workspace_path}")
    print(f"   workspace绝对路径: {os.path.abspath(workspace_path)}")
    print(f"   workspace存在: {os.path.exists(workspace_path)}")
    
    # 3. 检查today.txt文件
    print("\n📅 检查today.txt文件:")
    today_file_path = Path(__file__).parent.parent / "groundtruth_workspace" / "today.txt"
    print(f"   today.txt路径: {today_file_path}")
    print(f"   today.txt绝对路径: {today_file_path.absolute()}")
    print(f"   today.txt存在: {today_file_path.exists()}")
    
    if not today_file_path.exists():
        print(f"❌ today.txt文件不存在，尝试其他可能的路径")
        # 尝试其他可能的路径
        alternative_paths = [
            Path(__file__).parent / "groundtruth_workspace" / "today.txt",
            Path(workspace_path) / "groundtruth_workspace" / "today.txt",
            Path(".") / "groundtruth_workspace" / "today.txt"
        ]
        
        for alt_path in alternative_paths:
            print(f"   尝试路径: {alt_path.absolute()} - 存在: {alt_path.exists()}")
            if alt_path.exists():
                today_file_path = alt_path
                print(f"   ✅ 找到today.txt文件: {today_file_path}")
                break
        else:
            print("❌ 无法找到today.txt文件")
            exit(1)
    
    # 4. 读取today文件
    print("\n📖 读取today文件:")
    try:
        with open(today_file_path, 'r', encoding='utf-8') as f:
            today = f.read().strip()
        print(f"   today内容: '{today}'")
        
        today_date = datetime.strptime(today, '%Y-%m-%d').date()
        tomorrow_date = today_date + timedelta(days=1)
        
        print(f"   今天: {today_date}")
        print(f"   明天: {tomorrow_date}")
    except Exception as e:
        print(f"❌ 读取today.txt文件失败: {e}")
        exit(1)
    
    # 5. 初始化MCP服务器管理器并连接服务器
    print("\n🔧 初始化MCP服务器管理器:")
    try:
        print(f"   正在初始化MCPServerManager(agent_workspace='{workspace_path}')...")
        xx_MCPServerManager = MCPServerManager(agent_workspace=workspace_path, debug=True)
        print("   ✅ MCP服务器管理器初始化成功")
        
        print("   可用的服务器:")
        for server_name in xx_MCPServerManager.servers.keys():
            print(f"     - {server_name}")
            
        if 'google_calendar' not in xx_MCPServerManager.servers:
            print("   ❌ google_calendar服务器不可用")
            print("   可用服务器列表:", list(xx_MCPServerManager.servers.keys()))
            exit(1)
        
        # 连接Google Calendar服务器
        print("   🔗 正在连接Google Calendar服务器...")
        await xx_MCPServerManager.connect_servers(['google_calendar'])
        
        if not xx_MCPServerManager.is_server_connected('google_calendar'):
            print("   ❌ Google Calendar服务器连接失败")
            exit(1)
            
        print("   ✅ Google Calendar服务器连接成功")
        
    except Exception as e:
        print(f"   ❌ MCP服务器管理器初始化失败: {e}")
        print(f"   错误类型: {type(e)}")
        import traceback
        print(f"   错误详情:\n{traceback.format_exc()}")
        exit(1)

    # 6. 查询日历事件
    print("\n📅 查询日历事件:")
    try:
        # 使用MCPServerManager的上下文管理器
        async with xx_MCPServerManager:
            # 获取已连接的Google Calendar服务器
            google_calendar_server = xx_MCPServerManager.connected_servers['google_calendar']
            print("   📋 获取到已连接的Google Calendar服务器")
            
            # 查询今天的事件
            print(f"   🔍 查询今天的事件 ({today_date})...")
            today_query_params = {
                "timeMin": f"{today_date}T00:00:00+08:00",
                "timeMax": f"{today_date}T23:59:59+08:00",
                "orderBy": "startTime"
            }
            print(f"   查询参数: {today_query_params}")
            
            today_events = await call_tool_with_retry(google_calendar_server, "list_events", today_query_params)
            print("   ✅ 今天事件查询成功")
            print(f"   今天事件响应类型: {type(today_events)}")
            
            # 查询明天的事件
            print(f"   🔍 查询明天的事件 ({tomorrow_date})...")
            tomorrow_query_params = {
                "timeMin": f"{tomorrow_date}T00:00:00+08:00",
                "timeMax": f"{tomorrow_date}T23:59:59+08:00",
                "orderBy": "startTime"
            }
            print(f"   查询参数: {tomorrow_query_params}")
            
            tomorrow_events = await call_tool_with_retry(google_calendar_server, "list_events", tomorrow_query_params)
            print("   ✅ 明天事件查询成功")
            print(f"   明天事件响应类型: {type(tomorrow_events)}")
            
            # 额外查询：尝试更宽泛的时间范围，包含多个时区
            print(f"   🔍 额外查询：更宽泛的时间范围...")
            broad_query_params = {
                "timeMin": f"{today_date}T00:00:00Z",  # UTC时间
                "timeMax": f"{tomorrow_date}T23:59:59Z",
                "orderBy": "startTime"
            }
            print(f"   宽泛查询参数: {broad_query_params}")

            broad_events = await call_tool_with_retry(google_calendar_server, "list_events", broad_query_params)
            print("   ✅ 宽泛时间范围查询成功")
            print(f"   宽泛查询事件响应类型: {type(broad_events)}")
            
    except ToolCallError as e:
        print(f"   ❌ 工具调用失败: {e}")
        print(f"   错误类型: {type(e)}")
        import traceback
        print(f"   错误详情:\n{traceback.format_exc()}")
        exit(2)
    except Exception as e:
        print(f"   ❌ 其他错误: {e}")
        print(f"   错误类型: {type(e)}")
        import traceback
        print(f"   错误详情:\n{traceback.format_exc()}")
        exit(1)

    print("\n🔍 解析事件数据:")
    # 解析事件数据
    def extract_events(events_response):
        try:
            print(f"   事件响应内容预览: {str(events_response)[:200]}...")
            content_text = events_response.content[0].text
            start_pos = content_text.find("[")
            end_pos = content_text.rfind("]")
            if start_pos >= 0 and end_pos >= 0:
                events_json = content_text[start_pos:end_pos+1]
                return json.loads(events_json)
            return []
        except Exception as e:
            print(f"   ❌ 解析事件数据失败: {e}")
            print(f"   响应对象: {events_response}")
            return []

    today_events_list = extract_events(today_events)
    tomorrow_events_list = extract_events(tomorrow_events)
    broad_events_list = extract_events(broad_events)

    all_events = today_events_list + tomorrow_events_list + broad_events_list

    print(f"   今天事件数: {len(today_events_list)}")
    print(f"   明天事件数: {len(tomorrow_events_list)}")
    print(f"   宽泛查询事件数: {len(broad_events_list)}")
    print(f"   总事件数（去重前）: {len(all_events)}")

    # 去重：根据事件ID去重
    seen_ids = set()
    unique_events = []
    for event in all_events:
        event_id = event.get('id')
        if event_id and event_id not in seen_ids:
            seen_ids.add(event_id)
            unique_events.append(event)
        elif not event_id:  # 没有ID的事件也保留
            unique_events.append(event)

    all_events = unique_events
    print(f"   去重后总事件数: {len(all_events)}")

    # 显示事件详情
    if all_events:
        print("   📋 事件详情:")
        for i, event in enumerate(all_events):
            print(f"     事件 {i+1}: {event.get('summary', 'No summary')}")
            if 'start' in event:
                start_time = event['start']
                if 'dateTime' in start_time:
                    print(f"       开始时间: {start_time['dateTime']}")
                elif 'date' in start_time:
                    print(f"       日期: {start_time['date']}")
            if 'id' in event:
                print(f"       事件ID: {event['id']}")
    else:
        print("   ⚠️  没有找到任何事件")
    
    # 定义有独立一作发表的学生名单（根据邮件内容）
    qualified_students = {"张小明", "王大伟", "陈小强"}
    
    print(f"\n🎯 开始评估面试安排:")
    print(f"   合格学生名单: {qualified_students}")
    
    # 检查面试安排
    interview_events = []
    scheduled_students = set()
    
    for event in all_events:
        summary = event.get('summary', '')
        description = event.get('description', '')
        
        # 检查是否是面试相关的事件
        if any(keyword in summary.lower() for keyword in ['面试', 'interview', '学生']) or \
           any(keyword in description.lower() for keyword in ['面试', 'interview', '学生']):
            
            # 检查是否包含合格学生的姓名
            for student in qualified_students:
                if student in summary or student in description:
                    interview_events.append({
                        'event': event,
                        'student': student,
                        'summary': summary,
                        'start_time': event.get('start'),
                        'end_time': event.get('end')
                    })
                    scheduled_students.add(student)
                    break
    
    print(f"\n📊 面试安排检查结果:")
    print(f"   合格学生: {qualified_students}")
    print(f"   已安排面试的学生: {scheduled_students}")
    print(f"   找到面试事件数: {len(interview_events)}")
    
    # 评估结果
    success = True
    score = 0
    total_score = 100
    
    # 检查点1: 是否为所有合格学生安排了面试 (50分)
    if scheduled_students == qualified_students:
        print("✅ 正确为所有有独立一作发表的学生安排了面试")
        score += 50
    else:
        missing_students = qualified_students - scheduled_students
        extra_students = scheduled_students - qualified_students
        print(f"❌ 面试安排不完整")
        if missing_students:
            print(f"   未安排面试的合格学生: {missing_students}")
        if extra_students:
            print(f"   错误安排面试的学生: {extra_students}")
        success = False
    
    # 检查点2: 面试时间是否在今天和明天范围内，且符合时长和工作时间要求 (30分)
    valid_time_events = 0
    conflict_events = 0
    time_issues = []

    for interview in interview_events:
        start_time = interview['start_time']
        end_time = interview['end_time']
        student = interview['student']
        
        if 'dateTime' in start_time and 'dateTime' in end_time:
            event_start_dt = parse_iso_time(start_time['dateTime'])
            event_end_dt = parse_iso_time(end_time['dateTime'])
            event_date = event_start_dt.date()
            
            # 检查1: 日期是否在今天和明天范围内
            if event_date == today_date or event_date == tomorrow_date:
                
                # 检查2: 面试时长是否 >= 90分钟
                duration_minutes = (event_end_dt - event_start_dt).total_seconds() / 60
                if duration_minutes >= 90:
                    
                    # 检查3: 工作时间（8:00-17:00）
                    start_hour = event_start_dt.hour
                    end_hour = event_end_dt.hour
                    start_minute = event_start_dt.minute
                    end_minute = event_end_dt.minute
                    
                    # 开始时间不早于8:00，结束时间不晚于17:00
                    if (start_hour >= 8) and (end_hour < 17 or (end_hour == 17 and end_minute == 0)):
                        
                        # 检查4: 是否与已有事件冲突
                        conflicts_detected = False
                        
                        if event_date == today_date:
                            # 检查与今天15:00-17:00的冲突
                            existing_start_dt = datetime.combine(today_date, datetime.min.time().replace(hour=15))
                            existing_end_dt = datetime.combine(today_date, datetime.min.time().replace(hour=17))
                            
                            # 将已有事件时间设置为与面试事件相同的时区
                            if event_start_dt.tzinfo:
                                existing_start_dt = existing_start_dt.replace(tzinfo=event_start_dt.tzinfo)
                                existing_end_dt = existing_end_dt.replace(tzinfo=event_start_dt.tzinfo)
                            
                            # 检查时间重叠
                            if (event_start_dt < existing_end_dt and event_end_dt > existing_start_dt):
                                conflicts_detected = True
                                conflict_events += 1
                                time_issues.append(f"❌ {student} 的面试时间与学术委员会会议冲突 (15:00-17:00)")
                                
                        elif event_date == tomorrow_date:
                            # 检查与明天09:00-11:00的冲突
                            existing_start_dt = datetime.combine(tomorrow_date, datetime.min.time().replace(hour=9))
                            existing_end_dt = datetime.combine(tomorrow_date, datetime.min.time().replace(hour=11))
                            
                            # 将已有事件时间设置为与面试事件相同的时区
                            if event_start_dt.tzinfo:
                                existing_start_dt = existing_start_dt.replace(tzinfo=event_start_dt.tzinfo)
                                existing_end_dt = existing_end_dt.replace(tzinfo=event_start_dt.tzinfo)
                            
                            # 检查时间重叠
                            if (event_start_dt < existing_end_dt and event_end_dt > existing_start_dt):
                                conflicts_detected = True
                                conflict_events += 1
                                time_issues.append(f"❌ {student} 的面试时间与博士生论文答辩冲突 (09:00-11:00)")
                        
                        if not conflicts_detected:
                            valid_time_events += 1
                            print(f"✅ {student} 的面试安排完全合理:")
                            print(f"   时间: {event_date} {event_start_dt.strftime('%H:%M')}-{event_end_dt.strftime('%H:%M')}")
                            print(f"   时长: {duration_minutes:.0f}分钟")
                            print(f"   无冲突")
                            
                    else:
                        time_issues.append(f"❌ {student} 的面试时间不在工作时间内 (8:00-17:00)")
                        
                else:
                    time_issues.append(f"❌ {student} 的面试时长不足90分钟 (实际: {duration_minutes:.0f}分钟)")
                    
            else:
                time_issues.append(f"❌ {student} 的面试时间超出范围 (不在今明两天内): {event_date}")

    # 打印所有时间问题
    if time_issues:
        print(f"\n⚠️  发现时间安排问题:")
        for issue in time_issues:
            print(f"   {issue}")

    if valid_time_events == len(interview_events) and len(interview_events) > 0 and conflict_events == 0 and len(time_issues) == 0:
        score += 30
        print("✅ 所有面试时间都在合理范围内，时长足够，在工作时间内，且无冲突")
    elif len(time_issues) > 0:
        print(f"❌ 发现 {len(time_issues)} 个时间安排问题")
        success = False
    else:
        success = False
    
    # 检查点3: 每个学生都有具体的时间安排 (20分)
    if len(interview_events) >= len(qualified_students):
        print("✅ 每个合格学生都有具体的面试时间安排")
        score += 20
    else:
        print("❌ 面试时间安排不够具体")
        success = False
    
    print(f"\n📊 评估完成!")
    print(f"   总分: {score}/{total_score}")
    print(f"   任务{'成功' if success else '失败'}")
    
    # 详细输出面试安排
    if interview_events:
        print(f"\n📋 详细面试安排:")
        for interview in interview_events:
            print(f"   - {interview['student']}: {interview['summary']}")
            if 'dateTime' in interview['start_time']:
                start_dt = parse_iso_time(interview['start_time']['dateTime'])
                end_dt = parse_iso_time(interview['end_time']['dateTime'])
                print(f"     时间: {start_dt.strftime('%Y-%m-%d %H:%M')} - {end_dt.strftime('%H:%M')}")
    
    if not success:
        exit(1)
    
    print("✅ 远程测试通过...")

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--groundtruth_workspace", required=False)
    parser.add_argument("--res_log_file", required=False)
    args = parser.parse_args()

    asyncio.run(main(args))




    