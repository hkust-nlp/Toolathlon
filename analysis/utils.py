# this is to extract all the necessary information in a task trajectory
import json
import os
from pprint import pprint

from agents import tool
from utils.general.helper import read_json


def read_jsonl(jsonl_file):
    with open(jsonl_file, "r") as f:
        return [json.loads(line) for line in f if line.strip()!=""]

def match_tool_calls_and_results(tool_calls, tool_results):
    # 匹配 tool_calls 和 tool_results，根据 call_id
    # 返回 (tool_call, tool_output) 的二元组列表
    # 如果匹配不上就报错

    # 创建一个字典来根据 call_id 索引 tool_results
    result_dict = {}
    for result in tool_results:
        call_id = result['call_id']
        if call_id in result_dict:
            raise ValueError(f"Duplicate call_id in tool_results: {call_id}")
        result_dict[call_id] = result

    # 匹配 tool_calls 和对应的 tool_results
    matched_pairs = []
    for tool_call in tool_calls:
        call_id = tool_call['call_id']
        if call_id not in result_dict:
            raise ValueError(f"No matching tool_result found for call_id: {call_id}")
        matched_pairs.append((tool_call, result_dict[call_id]))

    # 检查是否所有 tool_results 都被匹配了
    if len(matched_pairs) != len(tool_results):
        raise ValueError(f"Number of matched pairs ({len(matched_pairs)}) doesn't match number of tool_results ({len(tool_results)})")

    return matched_pairs

def extract_info_for_one_traj(task_dir):
    status_file = os.path.join(task_dir, "status.json")
    status_data = read_json(status_file)

    conversation_dir = os.path.join(task_dir, "conversation_history")
    if not os.path.exists(conversation_dir):
        return None

    # conversation_file就是conversation_dir下唯一的文件
    conversation_file = os.listdir(conversation_dir)[0]
    conversation_data = read_jsonl(os.path.join(conversation_dir, conversation_file))

    num_of_turn = conversation_data[-1]["turn"]

    each_turn_info = {}

    for item in conversation_data:
        turn_id = item['turn']
        if 'type' in item:
            assert item['type'] == 'user_input'
            continue
        else:
            if turn_id not in each_turn_info:
                each_turn_info[turn_id] = {"think_or_respond": None, "tool_calls":[],"tool_results":[],"matched_tool_calls":[]}
            # not a user input turn
            if item['item_type'] == 'message_output_item':
                content = item['raw_content']['content']
                assert each_turn_info[turn_id]['think_or_respond'] is None
                each_turn_info[turn_id]['think_or_respond'] = content
            elif item['item_type'] == 'tool_call_item':
                content = item['raw_content']
                each_turn_info[turn_id]['tool_calls'].append(content)
            elif item['item_type'] == 'tool_call_output_item':
                content = item['raw_content']
                each_turn_info[turn_id]['tool_results'].append(content)
            else:
                raise ValueError(f"Unknown item type: {item['item_type']}")
        
        # 现在我们要对这一轮的"tool_calls"和"tool_results"进行配对
        # call_id一致的就是能对上的，我们把对上的变为(tool_call, tool_outupt) 的一个二元组放到each_turn_info[turn_id]['matched_tool_calls']中
        # 应该不存在对不上的情况！
        # 总之这应该是一个两列表的匹配问题
        # each_turn_info[turn_id]['matched_tool_calls'] = match_tool_calls_and_results(each_turn_info[turn_id]['tool_calls'], each_turn_info[turn_id]['tool_results'])
    
    for turn_id in each_turn_info:
        each_turn_info[turn_id]['matched_tool_calls'] = match_tool_calls_and_results(each_turn_info[turn_id]['tool_calls'], each_turn_info[turn_id]['tool_results'])

    return {"resolved_traj": each_turn_info, 
            "status": status_data,
            "num_of_turn": num_of_turn}

def categorize_tool_output(tool_name,tool_output_str):
    tooloutput_type = None
    if tool_output_str.strip().startswith("Error running tool"):
        tooloutput_type = "error_in_tool_call"
    if tool_output_str.strip().endswith("Please check this file carefully, as it may be very long!)"):
        assert tooloutput_type is None
        tooloutput_type = "overlong_tool_output"
    if tool_output_str.strip().startswith(f"Tool {tool_name} not found in agent"):
        assert tooloutput_type is None
        tooloutput_type = "tool_name_not_found"
    if tooloutput_type is None:
        tooloutput_type = "normal_tool_output"
    return tooloutput_type

def analyze_one_traj(resolved_traj, actual_turn):
    with_message_turns = 0
    tool_call_count = 0
    unique_tool_call_names = []
    unique_tool_call_name_count = {}
    tool_output_type_count = {}
    tool_call_count_per_turn = []
    for turn_id, turn_info in resolved_traj.items():        
        if turn_info['think_or_respond'] is not None:
            with_message_turns += 1
        tool_call_in_turn = len(turn_info['matched_tool_calls'])
        tool_call_count += tool_call_in_turn
        # print(turn_id,turn_info['think_or_respond'] is not None ,tool_call_in_turn)
        for tool_call, tool_output in turn_info['matched_tool_calls']:
            tool_name = tool_call['name']
            if tool_name not in unique_tool_call_name_count:
                unique_tool_call_name_count[tool_name] = 0
            unique_tool_call_name_count[tool_name] += 1
            if tool_name not in unique_tool_call_names:
                unique_tool_call_names.append(tool_name)
            tool_output_str = tool_output['output']
            tool_call_type = categorize_tool_output(tool_name,tool_output_str)
            if tool_call_type not in tool_output_type_count:
                tool_output_type_count[tool_call_type] = 0
            tool_output_type_count[tool_call_type] += 1
        tool_call_count_per_turn.append(tool_call_in_turn)
    # # 有多少turn是有可见的think/respond的
    # print(f"with_message_turns: {with_message_turns}")
    # # 总共调了多少次tool
    # print(f"tool_call_count: {tool_call_count}")
    # # 有哪些tool被调用了
    # print(f"unique_tool_call_names: {unique_tool_call_names}")
    # # 调用这么多次tool里，分布是怎么样的
    # print(f"tool_output_type_count: {tool_output_type_count}")
    # # 每轮平均调几次tool
    # print(f"average_tool_call_count: {tool_call_count / (len(resolved_traj)-1)}") # 减掉最后一轮交卷的
    # # 最多一轮内调多少次tool
    # print(f"max_tool_call_count_per_turn: {max(tool_call_count_per_turn)}")

    return {
        "with_message_turns": with_message_turns, # 有多少轮说了话
        "tool_call_count": tool_call_count, # 总共调用了几次tool
        "unique_tool_call_names": unique_tool_call_names, # 有哪些tool被调用了
        "unique_tool_call_count": len(unique_tool_call_names), # 有多少种tool被调用了
        "unique_tool_call_name_count": unique_tool_call_name_count, # 每种tool被调用了多少次
        "tool_output_type_count": tool_output_type_count, # 调用tool的输出类型分布
        "average_tool_call_count": tool_call_count / actual_turn, # 减掉最后一轮交卷的
        "max_tool_call_count_per_turn": max(tool_call_count_per_turn)
    }

def prepare_all_stat_for_one_traj(task_dir):
    result = extract_info_for_one_traj(task_dir)
    if result is None:
        return None
    resolved_traj = result["resolved_traj"]
    status_data = result["status"]
    # status_data['evaluation']可能是 pass/fail也可能是True/False/None, 需要统一转成True/False/None
    if status_data['evaluation'] == "pass" or status_data['evaluation'] == True:
        status_data['evaluation'] = True
    elif status_data['evaluation'] == "fail" or status_data['evaluation'] == False:
        status_data['evaluation'] = False
    else:
        status_data['evaluation'] = None
    num_of_turn = result["num_of_turn"]
    actual_with_tool_turn = num_of_turn - (1 if len(resolved_traj[num_of_turn]['matched_tool_calls'])==0 else 0) # just remove the last turn if it is a think_or_respond turn
    stat_for_one_traj = analyze_one_traj(resolved_traj, actual_with_tool_turn)
    
    # 如果有结果的话，再统计下token数
    log_file = os.path.join(task_dir, "traj_log.json")
    if os.path.exists(log_file):
        log_data = read_json(log_file)
        total_tokens = log_data['key_stats']['total_tokens']
        input_tokens = log_data['key_stats']['input_tokens']
        output_tokens = log_data['key_stats']['output_tokens']
        tokens_info = {
            "total_tokens": total_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens
        }
    else:
        tokens_info = None
        
    
    return {
        # "resolved_traj": resolved_traj,
        "status_data": status_data,
        # "num_of_turn": num_of_turn,
        "actual_turn": actual_with_tool_turn,
        "stat_for_one_traj": stat_for_one_traj,
        "tokens_info": tokens_info
    }

if __name__=="__main__":
    example_dir="dumps_finalexp/claude-4-sonnet-0514_09210140_3/finalpool/ab-testing"
    all_stat_for_one_traj = prepare_all_stat_for_one_traj(example_dir)
    pprint(all_stat_for_one_traj)

