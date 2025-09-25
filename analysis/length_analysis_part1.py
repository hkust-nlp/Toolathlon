import os
import json
import argparse
from collections import defaultdict
from typing import Dict, List, Any, Tuple
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# 指定要分析的模型列表
TARGET_MODELS = [
    "claude-4-sonnet-0514",
    "gpt-5",
    "grok-4-fast",
    "deepseek-v3.1",
    "qwen-3-coder"
]

def set_plot_style():
    plt.rcParams.update({
        "font.sans-serif": ["DejaVu Sans", "Arial", "Liberation Sans"],
        "axes.labelsize": 20,  # 再增大1号
        "xtick.labelsize": 20,  # 再增大1号
        "ytick.labelsize": 20,  # 再增大1号
        "legend.fontsize": 20,  # 保持不变
        "figure.dpi": 110,
        "grid.alpha": 0.3,
        "axes.grid": False,
    })

PALETTE = {
    "bar_primary": "#4B6F8A",
    "bar_secondary": "#6A9FB5",
    "line_primary": "#9B59B6",
    "line_secondary": "#7D8FB0",
    "neutral": "#AEB6C1",
}

MODEL_DISPLAY_NAME_MAP: Dict[str, str] = {
    "claude-4-sonnet-0514": "Claude-4-Sonnet",
    "deepseek-v3.1": "DeepSeek-V3.1",
    "gemini-2.5-pro": "Gemini-2.5-Pro",
    "gemini-2.5-flash": "Gemini-2.5-Flash",
    "grok-code-fast-1": "Grok-Code-Fast-1",
    "kimi-k2-0905": "Kimi-K2-0905",
    "glm-4.5": "GLM-4.5",
    "qwen-3-coder": "Qwen-3-Coder",
    "grok-4-fast": "Grok-4-Fast",
    "gpt-5-mini": "GPT-5-mini",
    "o3": "o3",
    "o4-mini": "o4-mini",
    "gpt-oss-120b": "GPT-OSS-120B",
    "grok-4": "Grok-4",
    "gpt-5": "GPT-5",
    "gpt-5-high": "GPT-5-high",
    "gpt-5-medium": "GPT-5-medium",
    "gpt-5-low": "GPT-5-low",
}

def display_model(model_name: str) -> str:
    return MODEL_DISPLAY_NAME_MAP.get(model_name, model_name)

def read_jsonl(path):
    items = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items

def read_multiple_jsonl(paths):
    """读取多个jsonl文件并合并"""
    all_items = []
    for path in paths:
        print(f"Reading {path}...")
        items = read_jsonl(path)
        all_items.extend(items)
        print(f"Loaded {len(items)} records from {path}")
    return all_items

def compute_task_avg_lengths(items: List[Dict[str, Any]]) -> Dict[str, float]:
    """计算每个任务的平均轨迹长度"""
    task_model_lengths = defaultdict(lambda: defaultdict(list))

    for row in items:
        model = row.get("model_name")
        task_name = row.get("task_name")
        if not model or not task_name:
            continue

        if model in ['qwen-3-max','gpt-oss-120b']:
            continue

        traj = row.get("traj_stat")
        if not traj:
            continue

        actual_turn = traj.get("actual_turn")
        if actual_turn is None:
            continue

        task_model_lengths[task_name][model].append(actual_turn)

    # 计算每个任务的平均长度
    task_avg_lengths = {}
    for task_name, model_data in task_model_lengths.items():
        model_avgs = []
        for model, lengths in model_data.items():
            if lengths:
                model_avg = sum(lengths) / len(lengths)
                model_avgs.append(model_avg)

        if model_avgs:
            task_avg_lengths[task_name] = sum(model_avgs) / len(model_avgs)

    return task_avg_lengths

def categorize_tasks_by_difficulty(task_avg_lengths: Dict[str, float]) -> Tuple[List[str], List[str], List[str], Dict[str, Tuple[float, float]]]:
    """将任务按平均长度分成3组：简单、中等、困难"""
    sorted_tasks = sorted(task_avg_lengths.items(), key=lambda x: x[1])

    n = len(sorted_tasks)
    third = n // 3

    easy_tasks = [task for task, _ in sorted_tasks[:third]]
    medium_tasks = [task for task, _ in sorted_tasks[third:2*third]]
    hard_tasks = [task for task, _ in sorted_tasks[2*third:]]

    # 计算每组的轮数范围
    easy_range = (sorted_tasks[0][1], sorted_tasks[third-1][1]) if easy_tasks else (0, 0)
    medium_range = (sorted_tasks[third][1], sorted_tasks[2*third-1][1]) if medium_tasks else (0, 0)
    hard_range = (sorted_tasks[2*third][1], sorted_tasks[-1][1]) if hard_tasks else (0, 0)

    group_ranges = {
        "Easy": easy_range,
        "Medium": medium_range,
        "Hard": hard_range
    }

    print(f"Easy tasks ({len(easy_tasks)}): avg length range {easy_range[0]:.1f}-{easy_range[1]:.1f}")
    print(f"Medium tasks ({len(medium_tasks)}): avg length range {medium_range[0]:.1f}-{medium_range[1]:.1f}")
    print(f"Hard tasks ({len(hard_tasks)}): avg length range {hard_range[0]:.1f}-{hard_range[1]:.1f}")

    return easy_tasks, medium_tasks, hard_tasks, group_ranges

def compute_model_success_rates_and_avg_turns(items: List[Dict[str, Any]], task_groups: Dict[str, List[str]]) -> Tuple[Dict[str, Dict[str, float]], Dict[str, Dict[str, float]]]:
    """计算每个模型在不同难度组的成功率和平均轮数"""
    model_group_data = defaultdict(lambda: defaultdict(list))
    model_group_turns = defaultdict(lambda: defaultdict(list))

    for row in items:
        model = row.get("model_name")
        task_name = row.get("task_name")
        if not model or not task_name or model not in TARGET_MODELS:
            continue

        traj = row.get("traj_stat")
        if not traj:
            continue

        status_data = traj.get("status_data", {})
        evaluation = status_data.get("evaluation")
        actual_turn = traj.get("actual_turn")

        # 确定任务属于哪个难度组
        for group_name, tasks in task_groups.items():
            if task_name in tasks:
                # 计算成功率时，None认为是失败
                if evaluation is not None:
                    model_group_data[model][group_name].append(evaluation)
                else:
                    model_group_data[model][group_name].append(False)

                # 计算平均轮数时，只统计非None的
                if actual_turn is not None:
                    model_group_turns[model][group_name].append(actual_turn)
                break

    # 计算成功率
    success_rates = {}
    for model in TARGET_MODELS:
        success_rates[model] = {}
        for group_name in task_groups.keys():
            evaluations = model_group_data[model][group_name]
            if evaluations:
                success_count = sum(1 for e in evaluations if e is True)
                success_rates[model][group_name] = success_count / len(evaluations)
            else:
                success_rates[model][group_name] = 0.0

    # 计算平均轮数
    avg_turns = {}
    for model in TARGET_MODELS:
        avg_turns[model] = {}
        for group_name in task_groups.keys():
            turns = model_group_turns[model][group_name]
            if turns:
                avg_turns[model][group_name] = sum(turns) / len(turns)
            else:
                avg_turns[model][group_name] = 0.0

    return success_rates, avg_turns

def plot_difficulty_groups_bar_chart(success_rates: Dict[str, Dict[str, float]], avg_turns: Dict[str, Dict[str, float]], group_ranges: Dict[str, Tuple[float, float]], outdir: str):
    """画3个难度组的柱状图"""
    os.makedirs(outdir, exist_ok=True)

    groups = ["Easy", "Medium", "Hard"]
    models = TARGET_MODELS

    # 准备数据
    data = np.zeros((len(groups), len(models)))
    turns_data = np.zeros((len(groups), len(models)))
    for i, group in enumerate(groups):
        for j, model in enumerate(models):
            data[i, j] = success_rates[model][group] * 100  # 转换为百分比
            turns_data[i, j] = avg_turns[model][group]

    # 更强烈对比的配色方案，从深到浅
    colors = [
        "#1B4F72",                 # 深海蓝 (最深)
        "#148F77",                 # 青绿色
        PALETTE["bar_primary"],    # "#4B6F8A" 海蓝灰 (中间)
        "#8E44AD",                 # 紫色
        "#85929E"                  # 深一点的灰色
    ]

    # 设置图形
    fig, ax = plt.subplots(figsize=(10, 6.5))

    # 设置柱状图参数
    x = np.arange(len(groups))
    width = 0.19  # 增加柱子宽度

    # 画柱状图
    for i, model in enumerate(models):
        offset = (i - len(models) / 2 + 0.5) * width
        bars = ax.bar(x + offset, data[:, i], width,
                     label=display_model(model), color=colors[i])

        # 在柱子上方显示得分+%，数字更贴近柱子顶部
        for j, bar in enumerate(bars):
            height = bar.get_height()
            score = data[j, i]
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.3,  # 由1改为0.3，更贴近柱子
                   f'{int(score)}%', ha='center', va='bottom',
                   fontsize=14,
                    # fontweight='bold'
                    )

        # 在柱子内显示平均轮数（两行显示）
        for j, bar in enumerate(bars):
            height = bar.get_height()
            avg_turn = turns_data[j, i]
            if avg_turn > 0 and height > 4:  # 降低阈值，让更多柱子显示轮数
                ax.text(bar.get_x() + bar.get_width()/2., height/2,
                       f'{int(avg_turn)}\nTurns', ha='center', va='center',
                       fontsize=14, color='white', 
                    #    fontweight='bold'
                       )

    # 在x轴标签上添加轮数范围（一行显示）
    group_labels = []
    for group in groups:
        range_info = group_ranges[group]
        group_labels.append(f"{group} [{range_info[0]:.1f}, {range_info[1]:.1f}]")

    # 设置图形属性（去掉标题）
    ax.set_xlabel("Tasks grouped by avg Turns over all Model Trajectories [Min, Max]", fontsize=20)
    ax.set_ylabel('Success Rate (%)', fontsize=20)
    ax.set_xticks(x)
    ax.set_xticklabels(group_labels)

    # 将legend移到图内
    ax.legend(loc='upper right', bbox_to_anchor=(0.98, 0.98), fontsize=17)

    # 设置y轴范围为0-45
    ax.set_ylim(0, 45)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "difficulty_groups_success_rates.pdf"), bbox_inches='tight')
    plt.close()

def save_task_groups_info(task_groups: Dict[str, List[str]], task_avg_lengths: Dict[str, float], outdir: str):
    """保存任务分组详细信息到文件"""
    os.makedirs(outdir, exist_ok=True)

    output_data = {}
    for group_name, tasks in task_groups.items():
        task_details = []
        for task in tasks:
            avg_length = task_avg_lengths.get(task, 0.0)
            task_details.append({
                "task_name": task,
                "avg_length": avg_length
            })

        # 按平均长度排序
        task_details.sort(key=lambda x: x["avg_length"])

        output_data[group_name] = {
            "task_count": len(task_details),
            "tasks": task_details
        }

    with open(os.path.join(outdir, "task_groups_detailed.json"), "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"Task groups detailed information saved to {os.path.join(outdir, 'task_groups_detailed.json')}")

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input1", default="analysis/data/ytb_stat_3_runs.jsonl",
                        help="First input JSONL file")
    parser.add_argument("--input2", default="analysis/data/full_stat_3_runs.jsonl",
                        help="Second input JSONL file")
    parser.add_argument("--outdir", default="analysis/figs/length_analysis")
    parser.add_argument("--save-json", action="store_true")
    args = parser.parse_args()

    ensure_dir(args.outdir)
    set_plot_style()

    print("Reading and merging data...")
    items = read_multiple_jsonl([args.input1, args.input2])
    print(f"Total loaded {len(items)} records")

    print("Computing task average lengths...")
    task_avg_lengths = compute_task_avg_lengths(items)
    print(f"Found {len(task_avg_lengths)} tasks")

    print("Categorizing tasks by difficulty...")
    easy_tasks, medium_tasks, hard_tasks, group_ranges = categorize_tasks_by_difficulty(task_avg_lengths)

    task_groups = {
        "Easy": easy_tasks,
        "Medium": medium_tasks,
        "Hard": hard_tasks
    }

    print("Computing model success rates and average turns by difficulty groups...")
    success_rates, avg_turns = compute_model_success_rates_and_avg_turns(items, task_groups)

    # 打印结果
    print("\nSuccess rates and average turns by model and difficulty:")
    for model in TARGET_MODELS:
        print(f"{display_model(model)}:")
        for group in ["Easy", "Medium", "Hard"]:
            rate = success_rates[model][group] * 100
            turns = avg_turns[model][group]
            print(f"  {group}: {rate:.1f}% (avg {turns:.1f} turns)")

    print("Saving task groups information...")
    save_task_groups_info(task_groups, task_avg_lengths, args.outdir)

    print("Generating bar chart...")
    plot_difficulty_groups_bar_chart(success_rates, avg_turns, group_ranges, args.outdir)

    if args.save_json:
        data_to_save = {
            "task_avg_lengths": task_avg_lengths,
            "task_groups": task_groups,
            "group_ranges": group_ranges,
            "success_rates": success_rates,
            "avg_turns": avg_turns,
            "target_models": TARGET_MODELS
        }
        with open(os.path.join(args.outdir, "difficulty_analysis_data.json"), "w") as f:
            json.dump(data_to_save, f, indent=2)

    print(f"Analysis complete. Results saved to {args.outdir}")

if __name__ == "__main__":
    main()