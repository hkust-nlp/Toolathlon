import json
import pandas as pd
import numpy as np
from .topic_mapping import task_classification_mapping


import glob

# 读取所有full_stat运行文件
run_files = [
    "analysis/data/ytb_stat_3_runs.jsonl",
    "analysis/data/full_stat_3_runs.jsonl"
]

all_mapping = {}
model_run_scores = {}  # 新增：存储每个模型每次运行的得分

all_lines = []
for run_file in run_files:
    with open(run_file) as f:
        all_lines.extend(f.readlines())

def resolve_cat(task_name):
    xx = task_classification_mapping[task_name]
    maintopic = xx.split(">")[0]
    return maintopic

for line in all_lines:
    linedt = json.loads(line)
    model_name = linedt['model_name']
    run_id = linedt.get('attempt_num', 0)  # 假设有run_id字段，如果没有默认为0

    # 初始化数据结构
    if model_name not in all_mapping:
        all_mapping[model_name] = {}
        model_run_scores[model_name] = {}

    if run_id not in model_run_scores[model_name]:
        model_run_scores[model_name][run_id] = {'total_score': 0, 'task_results': {}, 'turns': []}

    task_name = linedt['task_name']
    task_category = resolve_cat(task_name)

    # 类别级别的统计
    if task_category not in all_mapping[model_name]:
        all_mapping[model_name][task_category] = []
    corr = 0
    if linedt['traj_stat'] is not None:
        if linedt['traj_stat']['status_data']['evaluation'] is True:
            corr = 1

    all_mapping[model_name][task_category].append(corr)

    # 整体得分统计
    model_run_scores[model_name][run_id]['total_score'] += corr
    model_run_scores[model_name][run_id]['task_results'][task_name] = corr

    # 收集turn信息（排除无效的turn）
    if linedt['traj_stat'] is not None and 'actual_turn' in linedt['traj_stat']:
        model_run_scores[model_name][run_id]['turns'].append(linedt['traj_stat']['actual_turn'])

# 计算每个模型在每个类别上的平均成功率
model_category_scores = {}
all_categories = set()

for model_name, category_data in all_mapping.items():
    model_category_scores[model_name] = {}
    for category, scores in category_data.items():
        if scores:  # 确保有数据
            avg_score = sum(scores) / len(scores)
            model_category_scores[model_name][category] = avg_score
        else:
            model_category_scores[model_name][category] = 0.0
        all_categories.add(category)

# 新增：计算每个模型的三次尝试统计
model_overall_stats = {}
for model_name, run_data in model_run_scores.items():
    # print(run_data)
    # raise Exception("stop")
    run_scores = []
    task_success_count = {}  # 记录每个任务在几次运行中成功的次数

    # 初始化任务成功计数
    all_tasks = set()
    for run_id, run_info in run_data.items():
        all_tasks.update(run_info['task_results'].keys())

    for task in all_tasks:
        task_success_count[task] = 0

    # 计算每次运行的得分和任务成功情况
    all_turns = []
    num_runs = len(run_data)
    for run_id, run_info in run_data.items():
        total_score = run_info['total_score'] / 108.0  # 除以108得到每次尝试的得分
        run_scores.append(total_score)

        # 收集所有有效的turn
        all_turns.extend(run_info['turns'])

        # 统计每个任务的成功情况
        for task, success in run_info['task_results'].items():
            if success == 1:
                task_success_count[task] += 1

    # 计算统计指标
    if run_scores:
        mean_score = np.mean(run_scores)
        std_score = np.std(run_scores) if len(run_scores) > 1 else 0.0

        # 至少对一次的任务比例
        at_least_once = sum(1 for count in task_success_count.values() if count >= 1) / len(task_success_count) if task_success_count else 0.0

        # 所有运行都做对的任务比例
        all_runs_correct = sum(1 for count in task_success_count.values() if count == num_runs) / len(task_success_count) if task_success_count else 0.0

        # 计算平均轮数
        avg_turns = np.mean(all_turns) if all_turns else 0.0

        model_overall_stats[model_name] = {
            'mean_score': mean_score,
            'std_score': std_score,
            'at_least_once_ratio': at_least_once,
            'all_runs_correct_ratio': all_runs_correct,
            'avg_turns': avg_turns
        }

# 按指定顺序排序类别
custom_order = ["Research & Academic", "Campus & Study", "Finance & Market", "Tech & Dev", "Office & Business", "Daily & Entertainment", "Shopping & E-commerce"]
# all_categories_list = list(all_categories)  # 先转换为列表
# all_categories = [cat for cat in custom_order if cat in all_categories_list] + [cat for cat in all_categories_list if cat not in custom_order]
all_categories = [x+" " for x in custom_order]
# raise Exception("stop")
# 按平均分从大到小排序模型名称
model_names = sorted(list(model_category_scores.keys()),
                    key=lambda x: model_overall_stats.get(x, {'mean_score': 0})['mean_score'],
                    reverse=True)

# 创建DataFrame
df_data = []
for model_name in model_names:
    row = {'模型名称': model_name}

    # 添加类别得分
    for category in all_categories:
        score = model_category_scores[model_name].get(category, 0.0)
        row[category] = f"&{round(score * 100, 1)}"  # 转换为百分数，保留一位小数

    # 添加整体统计指标
    if model_name in model_overall_stats:
        stats = model_overall_stats[model_name]
        row['均分±标准差'] = f"&${round(stats['mean_score'] * 100, 1)}_{{\\pm {round(stats['std_score'] * 100, 1)}}}$"
        row['至少一次正确比例'] = f"&{round(stats['at_least_once_ratio'] * 100, 1)}"
        row['所有运行都正确比例'] = f"&{round(stats['all_runs_correct_ratio'] * 100, 1)}"
        row['平均轮数'] = f"&{round(stats['avg_turns'], 1)}"
    else:
        row['均分±标准差'] = "&$0.0_{\\pm 0.0}$"
        row['至少一次正确比例'] = "&0.0"
        row['所有运行都正确比例'] = "&0.0"
        row['平均轮数'] = "&0.0"
    # print(row)
    # raise Exception("stop")
    df_data.append(row)

# 指定列顺序
columns_order = ['模型名称'] + all_categories + ['均分±标准差', '至少一次正确比例', '所有运行都正确比例', '平均轮数']
# print(columns_order)
# raise Exception("stop")
df = pd.DataFrame(df_data)

# 重新排列列顺序
df = df[columns_order]

# 导出为xlsx文件
output_file = "analysis/topic_wise_scores.tsv"
df.to_csv(output_file, index=False, sep="\t")
print(f"结果已导出到 {output_file}")
