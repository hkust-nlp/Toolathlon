import os
import json
import argparse
from collections import defaultdict, Counter
from typing import Dict, List, Any, Tuple
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

def set_plot_style():
    plt.rcParams.update({
        "font.sans-serif": ["DejaVu Sans", "Arial", "Liberation Sans"],
        "axes.labelsize": 12,
        "xtick.labelsize": 11,
        "ytick.labelsize": 11,
        "legend.fontsize": 11,
        "figure.dpi": 110,
        "grid.alpha": 0.3,
        "axes.grid": False,
    })

PALETTE = {
    "primary": "#4B6F8A",
    "secondary": "#6A9FB5",
    "accent": "#9B59B6",
    "warning": "#E67E22",
    "success": "#27AE60",
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

def is_success(evaluation_value: Any) -> bool:
    return evaluation_value is True

def extract_overlong_data(items: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, List[float]]]:
    """
    提取overlong tool returns相关数据
    返回：(每条轨迹的数据, 按模型分组的成功率)
    """
    trajectory_data = []
    model_success_rates = defaultdict(list)

    for row in items:
        model = row.get("model_name")
        if not model:
            continue

        traj = row.get("traj_stat")
        if not traj:
            continue

        status_data = traj.get("status_data", {})
        evaluation = status_data.get("evaluation")
        if evaluation is None:
            continue

        stat = traj.get("stat_for_one_traj", {})
        tool_output_type_count = stat.get("tool_output_type_count", {})

        # 获取overlong数量
        overlong_count = tool_output_type_count.get("overlong_tool_output", 0)
        total_tool_calls = stat.get("tool_call_count", 0)

        # 分类：是否包含overlong
        has_overlong = overlong_count > 0
        success = is_success(evaluation)

        trajectory_data.append({
            "model": model,
            "overlong_count": overlong_count,
            "total_tool_calls": total_tool_calls,
            "has_overlong": has_overlong,
            "success": success,
            "task_name": row.get("task_name", "unknown")
        })

        # 按模型收集成功率
        model_success_rates[model].append(1.0 if success else 0.0)

    return trajectory_data, model_success_rates

def plot_overlong_donut_chart(trajectory_data: List[Dict[str, Any]], outdir: str):
    """绘制环形图显示包含overlong的任务占比"""
    os.makedirs(outdir, exist_ok=True)

    # 统计包含overlong的任务数量
    has_overlong_count = sum(1 for t in trajectory_data if t["has_overlong"])
    no_overlong_count = len(trajectory_data) - has_overlong_count

    # 数据准备
    sizes = [has_overlong_count, no_overlong_count]
    labels = [f'With Overlong\n({has_overlong_count})', f'Without Overlong\n({no_overlong_count})']
    colors = [PALETTE["warning"], PALETTE["success"]]

    # 创建环形图
    fig, ax = plt.subplots(figsize=(8, 8))

    # 绘制外环
    wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                                     startangle=90, pctdistance=0.85)

    # 创建内圆形成环形效果
    centre_circle = plt.Circle((0, 0), 0.70, fc='white')
    ax.add_artist(centre_circle)

    # 在中心添加总数文本
    ax.text(0, 0, f'Total Tasks\n{len(trajectory_data)}',
           horizontalalignment='center', verticalalignment='center',
           fontsize=14, fontweight='bold')

    ax.axis('equal')
    plt.title('Tasks Distribution by Overlong Tool Returns', fontsize=16, pad=20)
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "overlong_donut_chart.pdf"))
    plt.close()

def plot_model_success_rate_scatter(trajectory_data: List[Dict[str, Any]], outdir: str):
    """绘制散点图：X轴无overlong成功率，Y轴有overlong成功率，每个点是一个模型"""
    os.makedirs(outdir, exist_ok=True)

    # 按模型分组统计成功率
    model_stats = {}

    for t in trajectory_data:
        model = t["model"]
        if model not in model_stats:
            model_stats[model] = {"with_overlong": [], "without_overlong": []}

        success = 1.0 if t["success"] else 0.0
        if t["has_overlong"]:
            model_stats[model]["with_overlong"].append(success)
        else:
            model_stats[model]["without_overlong"].append(success)

    # 准备散点图数据
    scatter_data = []
    for model, data in model_stats.items():
        # 只包含两种情况都有数据的模型
        if data["with_overlong"] and data["without_overlong"]:
            no_overlong_rate = np.mean(data["without_overlong"]) * 100  # 转换为百分比
            with_overlong_rate = np.mean(data["with_overlong"]) * 100  # 转换为百分比

            scatter_data.append({
                "model": model,
                "display_name": display_model(model),
                "no_overlong_rate": no_overlong_rate,
                "with_overlong_rate": with_overlong_rate,
                "no_overlong_count": len(data["without_overlong"]),
                "with_overlong_count": len(data["with_overlong"])
            })

    if not scatter_data:
        print("Warning: No models with both overlong and non-overlong data found")
        return

    # 创建散点图 - 放大图表
    fig, ax = plt.subplots(figsize=(7, 7))

    # 绘制散点 - 根据模型系列使用相近颜色和不同形状
    model_style_map = {
        # GPT系列 - 蓝色系
        "gpt-5": {"color": "#1f77b4", "marker": "o"},          # 深蓝圆形
        "gpt-5-mini": {"color": "#5fa3d3", "marker": "s"},     # 中蓝方形
        "gpt-5-high": {"color": "#0d5aa7", "marker": "^"},     # 更深蓝三角
        "gpt-5-medium": {"color": "#3a8bc0", "marker": "D"},   # 蓝色菱形
        "gpt-5-low": {"color": "#6bb3dc", "marker": "v"},      # 浅蓝下三角
        "o3": {"color": "#8cc8e5", "marker": "p"},             # 很浅蓝五角
        "o4-mini": {"color": "#a8d5eb", "marker": "h"},        # 极浅蓝六角
        "gpt-oss-120b": {"color": "#4a90c2", "marker": "*"},   # 中蓝星形

        # Grok系列 - 绿色系
        "grok-4": {"color": "#2ca02c", "marker": "o"},         # 深绿圆形
        "grok-4-fast": {"color": "#5cb85c", "marker": "s"},    # 中绿方形
        "grok-code-fast-1": {"color": "#7cc97c", "marker": "^"}, # 浅绿三角

        # Gemini系列 - 橙色系
        "gemini-2.5-pro": {"color": "#ff7f0e", "marker": "o"}, # 深橙圆形
        "gemini-2.5-flash": {"color": "#ffb366", "marker": "s"}, # 浅橙方形

        # Claude系列 - 紫色系
        "claude-4-sonnet-0514": {"color": "#9467bd", "marker": "o"}, # 紫色圆形

        # DeepSeek系列 - 红色系
        "deepseek-v3.1": {"color": "#d62728", "marker": "o"},  # 红色圆形

        # 其他模型 - 不同颜色
        "kimi-k2-0905": {"color": "#8c564b", "marker": "o"},   # 棕色
        "glm-4.5": {"color": "#e377c2", "marker": "o"},        # 粉色
        "qwen-3-coder": {"color": "#7f7f7f", "marker": "o"},   # 灰色
    }

    # 按系列顺序绘制散点，确保图例中同系列排在一起
    model_order = [
        # GPT系列
        "gpt-5", "gpt-5-high", "gpt-5-medium", "gpt-5-low", "gpt-5-mini",
        "o3", "o4-mini", "gpt-oss-120b",
        # Grok系列
        "grok-4", "grok-4-fast", "grok-code-fast-1",
        # Gemini系列
        "gemini-2.5-pro", "gemini-2.5-flash",
        # Claude系列
        "claude-4-sonnet-0514",
        # DeepSeek系列
        "deepseek-v3.1",
        # 其他模型
        "kimi-k2-0905", "glm-4.5", "qwen-3-coder"
    ]

    # 创建模型数据的字典以便快速查找
    scatter_data_dict = {data["model"]: data for data in scatter_data}

    # 按指定顺序绘制散点
    for model_key in model_order:
        if model_key in scatter_data_dict:
            if model_key in ['qwen-3-max','gpt-oss-120b']:
                continue
            data = scatter_data_dict[model_key]
            style = model_style_map.get(model_key, {"color": "#bcbd22", "marker": "o"})

            ax.scatter(data["no_overlong_rate"], data["with_overlong_rate"],
                      s=200, alpha=0.9, color=style["color"], marker=style["marker"],
                      label=data["display_name"], edgecolors='black', linewidth=1.5)

    # 绘制任何不在预定义顺序中的模型
    for data in scatter_data:
        if data["model"] not in model_order:
            if data["model"] in ['qwen-3-max','gpt-oss-120b']:
                continue
            style = model_style_map.get(data["model"], {"color": "#bcbd22", "marker": "o"})
            ax.scatter(data["no_overlong_rate"], data["with_overlong_rate"],
                      s=200, alpha=0.9, color=style["color"], marker=style["marker"],
                      label=data["display_name"], edgecolors='black', linewidth=1.5)

    # 绘制对角线 (y=x) - 从-1到41
    ax.plot([-2, 42], [-2, 42], 'k--', alpha=0.4, linewidth=2)

    # 设置轴和标题 - 放大字体，去掉标题
    ax.set_xlabel('Success Rate - No Overlong Tool Output (%)', fontsize=20)
    ax.set_ylabel('Success Rate - With Overlong Tool Output (%)', fontsize=20)

    # 设置轴范围为-1到41，但只显示0-40的刻度
    ax.set_xlim(-1, 41)
    ax.set_ylim(-1, 41)

    # 设置刻度 - 0,10,20,30,40
    ticks = [0, 10, 20, 30, 40]
    ax.set_xticks(ticks)
    ax.set_yticks(ticks)

    # 放大刻度标签字体
    ax.tick_params(axis='both', which='major', labelsize=17)

    # 添加网格
    ax.grid(True, alpha=0.3)

    # 添加图例 - 放在左上角，两列显示，放大字体
    ax.legend(loc='upper left', fontsize=13, frameon=True, fancybox=True, shadow=True, ncol=1)

    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "model_overlong_scatter.pdf"))
    plt.close()

    # 打印详细数据表格
    print("\n=== MODEL PERFORMANCE BY OVERLONG STATUS ===")
    print(f"{'Model':<20} {'No Overlong':<12} {'With Overlong':<14} {'Difference':<12} {'Samples (No/With)'}")
    print("-" * 80)

    print(f"{'Model':<20} {'No Overlong':<12} {'With Overlong':<14} {'Difference':<12} {'Samples (No/With)':<20} {'Overlong Ratio':<10}")
    print("-" * 100)
    for data in sorted(scatter_data, key=lambda x: x["no_overlong_rate"] - x["with_overlong_rate"], reverse=True):
        diff = data["no_overlong_rate"] - data["with_overlong_rate"]
        total = data['no_overlong_count'] + data['with_overlong_count']
        overlong_ratio = (data['with_overlong_count'] / total * 100) if total > 0 else 0.0
        print(f"{data['display_name']:<20} "
              f"{data['no_overlong_rate']:.1f}%       "
              f"{data['with_overlong_rate']:.1f}%         "
              f"{diff:+.1f}%       "
              f"{data['no_overlong_count']}/{data['with_overlong_count']:<16}"
              f"{overlong_ratio:.1f}%")

    return scatter_data

def plot_overlong_scatter(trajectory_data: List[Dict[str, Any]], outdir: str):
    """绘制散点图显示overlong数量与成功率的关系"""
    os.makedirs(outdir, exist_ok=True)

    # 按模型分组数据
    model_groups = defaultdict(list)
    for t in trajectory_data:
        model_groups[t["model"]].append(t)

    fig, ax = plt.subplots(figsize=(10, 6))

    # 为每个模型绘制散点
    colors = plt.cm.Set3(np.linspace(0, 1, len(model_groups)))

    for i, (model, data) in enumerate(model_groups.items()):
        if model in ['qwen-3-max','gpt-oss-120b']:
            continue
        x_values = [t["overlong_count"] for t in data]
        y_values = [1.0 if t["success"] else 0.0 for t in data]

        # 添加少量随机扰动避免重叠
        y_jitter = np.random.normal(0, 0.02, len(y_values))
        y_values_jittered = np.array(y_values) + y_jitter

        ax.scatter(x_values, y_values_jittered,
                  alpha=0.6, s=50, color=colors[i],
                  label=display_model(model))

    ax.set_xlabel('Number of Overlong Tool Returns')
    ax.set_ylabel('Success (with jitter)')
    ax.set_title('Relationship between Overlong Tool Returns and Success Rate')
    ax.set_ylim(-0.1, 1.1)
    ax.grid(True, alpha=0.3)

    # 添加图例，如果模型太多则放在图外
    if len(model_groups) > 8:
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    else:
        ax.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "overlong_scatter_plot.pdf"))
    plt.close()

def compute_summary_statistics(trajectory_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """计算总结统计信息"""
    total_tasks = len(trajectory_data)
    tasks_with_overlong = sum(1 for t in trajectory_data if t["has_overlong"])
    tasks_without_overlong = total_tasks - tasks_with_overlong

    # 成功率统计
    success_with_overlong = sum(1 for t in trajectory_data if t["has_overlong"] and t["success"])
    success_without_overlong = sum(1 for t in trajectory_data if not t["has_overlong"] and t["success"])

    success_rate_with = success_with_overlong / tasks_with_overlong if tasks_with_overlong > 0 else 0
    success_rate_without = success_without_overlong / tasks_without_overlong if tasks_without_overlong > 0 else 0

    # overlong数量统计
    overlong_counts = [t["overlong_count"] for t in trajectory_data if t["has_overlong"]]

    return {
        "total_tasks": total_tasks,
        "tasks_with_overlong": tasks_with_overlong,
        "tasks_without_overlong": tasks_without_overlong,
        "overlong_percentage": (tasks_with_overlong / total_tasks) * 100,
        "success_rate_with_overlong": success_rate_with,
        "success_rate_without_overlong": success_rate_without,
        "success_rate_difference": success_rate_without - success_rate_with,
        "avg_overlong_count": np.mean(overlong_counts) if overlong_counts else 0,
        "max_overlong_count": max(overlong_counts) if overlong_counts else 0,
    }

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="analysis/data/full_stat_3_runs.jsonl")
    parser.add_argument("--input_second", default="analysis/data/ytb_stat_3_runs.jsonl")
    parser.add_argument("--outdir", default="analysis/figs/overlong_analysis")
    parser.add_argument("--save-json", action="store_true")
    args = parser.parse_args()

    ensure_dir(args.outdir)
    set_plot_style()

    print("Reading data...")
    items1 = read_jsonl(args.input)
    items2 = read_jsonl(args.input_second)
    items = items1 + items2
    print(f"Loaded {len(items)} records")

    print("Extracting overlong data...")
    trajectory_data, model_success_rates = extract_overlong_data(items)
    print(f"Processed {len(trajectory_data)} trajectories")

    print("Computing summary statistics...")
    summary_stats = compute_summary_statistics(trajectory_data)

    print("\n=== OVERLONG TOOL RETURNS ANALYSIS ===")
    print(f"Total tasks: {summary_stats['total_tasks']}")
    print(f"Tasks with overlong: {summary_stats['tasks_with_overlong']} ({summary_stats['overlong_percentage']:.1f}%)")
    print(f"Tasks without overlong: {summary_stats['tasks_without_overlong']}")
    print(f"Success rate with overlong: {summary_stats['success_rate_with_overlong']:.3f}")
    print(f"Success rate without overlong: {summary_stats['success_rate_without_overlong']:.3f}")
    print(f"Success rate difference: {summary_stats['success_rate_difference']:.3f}")
    print(f"Average overlong count: {summary_stats['avg_overlong_count']:.1f}")
    print(f"Max overlong count: {summary_stats['max_overlong_count']}")

    print("Generating visualizations...")
    plot_overlong_donut_chart(trajectory_data, args.outdir)
    plot_model_success_rate_scatter(trajectory_data, args.outdir)
    plot_overlong_scatter(trajectory_data, args.outdir)

    if args.save_json:
        # 保存详细数据
        output_data = {
            "summary_statistics": summary_stats,
            "trajectory_data": trajectory_data,
        }
        with open(os.path.join(args.outdir, "overlong_analysis_data.json"), "w") as f:
            json.dump(output_data, f, indent=2)

    print(f"Analysis complete. Results saved to {args.outdir}")

if __name__ == "__main__":
    main()