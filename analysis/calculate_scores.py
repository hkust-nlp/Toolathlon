import json
import pandas as pd
from .topic_mapping import task_classification_mapping


fn1 = "analysis/data/full_stat_3_runs.jsonl"
fn2 = "analysis/data/ytb_stat_3_runs.jsonl"

all_mapping = {}
with open(fn1) as f:
    lines = f.readlines()

def resolve_cat(task_name):
    xx = task_classification_mapping[task_name]
    maintopic = xx.split(">")[0]
    return maintopic

for line in lines:
    linedt = json.loads(line)
    model_name = linedt['model_name']
    if model_name not in all_mapping:
        all_mapping[model_name] = {}
    task_name = linedt['task_name']
    task_category = resolve_cat(task_name)
    if task_category not in all_mapping[model_name]:
        all_mapping[model_name][task_category] = []
    corr = 0
    if linedt['traj_stat'] is not None:
        if linedt['traj_stat']['status_data']['evaluation'] is True:
            corr = 1
    all_mapping[model_name][task_category].append(corr)

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

# 按指定顺序排序类别
custom_order = ["Research & Academic", "Campus & Study", "Finance & Market", "Tech & Dev", "Office & Business", "Daily & Entertainment", "Shopping & E-commerce"]
all_categories = [cat for cat in custom_order if cat in all_categories] + [cat for cat in all_categories if cat not in custom_order]
# 按字母顺序排序模型名称
model_names = sorted(list(model_category_scores.keys()))

# 创建DataFrame
df_data = []
for model_name in model_names:
    row = {'模型名称': model_name}
    for category in all_categories:
        score = model_category_scores[model_name].get(category, 0.0)
        row[category] = f"&{round(score * 100, 1)}"  # 转换为百分数，保留一位小数
    df_data.append(row)

df = pd.DataFrame(df_data)

# 导出为xlsx文件
output_file = "analysis/topic_wise_scores.xlsx"
df.to_excel(output_file, index=False)
print(f"结果已导出到 {output_file}")
