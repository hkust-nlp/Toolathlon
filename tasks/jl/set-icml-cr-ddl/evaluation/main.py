from argparse import ArgumentParser
import os
from utils.general.helper import read_json
import asyncio
from pprint import pprint

from utils.mcp.tool_servers import MCPServerManager

import json

from datetime import datetime
import pytz

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
    print(parsed_time1)
    parsed_time2 = parse_iso_time(groundtruth_iso_time)
    print(parsed_time2)
    
    diff = abs((parsed_time1 - parsed_time2).total_seconds())

    return diff <= tolerance_seconds

async def main(args):
    # print("假装远程测测...")
    xx_MCPServerManager = MCPServerManager(agent_workspace="./") # a pseudo server manager
    google_calendar_server = xx_MCPServerManager.servers['google_calendar']
    await google_calendar_server.connect()

    # available_tools = await google_calendar_server.list_tools()

    # for tool in available_tools:
    #     pprint(tool.model_dump_json())

    events_in_target_date = await google_calendar_server.call_tool(tool_name="list_events",
                                                             arguments={
                                                                    "timeMin": "2025-06-05T00:00:00-12:00",
                                                                    "timeMax": "2025-06-05T23:59:59-12:00",
                                                                    "orderBy": "startTime"
                                                                    })

    await google_calendar_server.cleanup()

    # pprint(events_in_target_date)
    content_text = events_in_target_date.content[0].text
    # print(content_text)
    start_pos = content_text.find("[")
    end_pos = content_text.rfind("]")
    xx = content_text[start_pos:end_pos+1]
    xx_s = json.loads(xx)

    found=False

    gt_time = "2025-06-05T20:59:00-12:00"

    for event in xx_s:
        summary = event['summary']
        if all(x in summary.lower() for x in ['icml','camera', 'ready']):
            start_time = event['start']
            print(f"找到活动时间: {start_time}, 和gt_time: {gt_time} 进行比较")
            if compare_google_calendar_times(start_time,gt_time,300): # 5 mins difference is acceptable
                found=True
                print("符合要求")
            else:
                print("不符合要求")
    
    if not found:
        print("未能找到符合要求的活动安排")
        exit(1)

    print("远程测试通过...")

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--groundtruth_workspace", required=False)
    parser.add_argument("--res_log_file", required=False)
    args = parser.parse_args()

    asyncio.run(main(args))




    