
import json
fn = "analysis/data/full_stat_jsonl.jsonl"

model_wise = {}
with open(fn, "r") as f:
    for line in f:
        item = json.loads(line)
        model_name = item["model_name"]
        model_wise[model_name] = []
        if item['traj_stat'] is not None:
            model_wise[model_name].append(item['traj_stat'])


# analysis over model
for model_name in model_wise:
    valid_traj_stats = model_wise[model_name]
    # 每个结构大概长这样
    # 其中actual_turn是实际发生工具调用的轮数
    # 在stat_for_one_traj中
    #   tool_output_type_count 有四种可能: normal_tool_output, tool_name_not_found, error_in_tool_call, overlong_tool_output
    #   unique_tool_call_name_count 是每种tool被调用了多少次
    #   unique_tool_call_names 是所有被调用的tool的名称
    #   unique_tool_call_count 是所有被调用的tool的种类数
    #   average_tool_call_count 是每轮平均调用了几次tool
    #   max_tool_call_count_per_turn 是每轮最多调用了几次tool
    #   with_message_turns 是多少轮以可见形式进行了思考或者文本输出
    #   tool_call_count 是总共调用了几次tool
    #   stat_for_one_traj 是每个样本的统计结果
    # 在status_data中代表这个任务是不是有正常预处理（pass/fail），运行完成(pass/fail/timeout/max_turn_exceeded/null)，以及评估结果(true/false/null)
    # 在tokens_info中代表这个任务的token消耗
    # tokens_info可能是None，代表这个样本的token消耗没有统计到
    """
{'actual_turn': 27,
 'stat_for_one_traj': {'average_tool_call_count': 1.0,
                       'max_tool_call_count_per_turn': 1,
                       'tool_call_count': 27,
                       'tool_output_type_count': {'normal_tool_output': 27},
                       'unique_tool_call_count': 7,
                       'unique_tool_call_name_count': {'filesystem-read_file': 2,
                                                       'filesystem-write_file': 1,
                                                       'google-cloud-bigquery_get_dataset_info': 1,
                                                       'google-cloud-bigquery_run_query': 15,
                                                       'google-cloud-storage_create_bucket': 1,
                                                       'google-cloud-storage_get_bucket_info': 1,
                                                       'local-python-execute': 6},
                       'unique_tool_call_names': ['google-cloud-bigquery_get_dataset_info',
                                                  'google-cloud-bigquery_run_query',
                                                  'filesystem-read_file',
                                                  'local-python-execute',
                                                  'filesystem-write_file',
                                                  'google-cloud-storage_create_bucket',
                                                  'google-cloud-storage_get_bucket_info'],
                       'with_message_turns': 24},
 'status_data': {'evaluation': True, 'preprocess': 'done', 'running': 'done'},
 'tokens_info': {'input_tokens': 671827,
                 'output_tokens': 18296,
                 'total_tokens': 690123}}
    """
    #### 以下是我们要做的分析
    # 我们首先要分析"The failure of calling tools"
    # 这里用到的数据主要是tool_output_type_count，记录了每次工具调用是否正常，
    #   不正常的情况有tool_name_not_found（输入错误的工具名）, error_in_tool_call（调用工具时报错）
    #   我们想知道在遇到这种情况的时候，模型的反应会如何，比如说，这些错误如何与最终的正确率/完成率相关？以及不同模型遇到这种错误的比例多少
