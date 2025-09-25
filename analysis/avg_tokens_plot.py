import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import json
from collections import defaultdict
from typing import Dict

# 模型显示名称映射
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
    # "gpt-5-high": "GPT-5-high",
    # "gpt-5-medium": "GPT-5-medium",
    # "gpt-5-low": "GPT-5-low",
    # "qwen3=max": "Qwen3-max",
    # "gpt-5-high": "GPT-5-high",
    # "claude-4.1-opus": "Claude-4.1-Opus",
}

# --- 读取数据 ---
def load_data_from_jsonl(file_path):
    """从JSONL文件读取数据并计算统计信息"""
    model_stats = defaultdict(lambda: {'total_entries': 0, 'successful_entries': 0, 'valid_token_entries': 0, 'total_output_tokens': 0, 'total_llm_calls': 0, 'total_input_tokens': 0})

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line.strip())
            model_name = data['model_name']

            # 统计总条目数
            model_stats[model_name]['total_entries'] += 1

            # 检查是否有有效的traj_stat
            if data.get('traj_stat') is not None:
                traj_stat = data['traj_stat']

                # 检查evaluation状态
                if traj_stat.get('status_data', {}).get('evaluation') == True:
                    model_stats[model_name]['successful_entries'] += 1

                # 统计token信息（只有当traj_stat不为null时）
                tokens_info = traj_stat.get('tokens_info')
                if tokens_info is not None:
                    model_stats[model_name]['valid_token_entries'] += 1
                    model_stats[model_name]['total_output_tokens'] += tokens_info.get('output_tokens', 0)
                    model_stats[model_name]['total_input_tokens'] += tokens_info.get('input_tokens', 0)

                # 统计LLM调用次数
                if 'actual_turn' in traj_stat:
                    model_stats[model_name]['total_llm_calls'] += traj_stat['actual_turn']

    return model_stats

def calculate_metrics(model_stats,mode):
    """计算Pass@1和平均输出token数"""
    results = {}

    for model_name, stats in model_stats.items():
        # 计算Pass@1: 成功的条目数 / 总条目数
        pass_at_1 = (stats['successful_entries'] / stats['total_entries'] * 100) if stats['total_entries'] > 0 else 0

        # 计算平均输出token数: 只考虑有效的token条目
        avg_output_tokens = (stats['total_output_tokens'] / stats['valid_token_entries']) if stats['valid_token_entries'] > 0 else 0
        avg_input_tokens = (stats['total_input_tokens'] / stats['valid_token_entries']) if stats['valid_token_entries'] > 0 else 0
        if mode == "output":
            avg_cost = avg_output_tokens 
        elif mode == "total":
            avg_cost = avg_output_tokens + avg_input_tokens


        # 计算平均LLM调用次数
        avg_llm_calls = (stats['total_llm_calls'] / stats['total_entries']) if stats['total_entries'] > 0 else 0

        results[model_name] = {
            'pass_at_1': pass_at_1,
            'avg_input_tokens': avg_input_tokens,
            'avg_output_tokens': avg_output_tokens,
            'avg_cost': avg_cost,  # 新增cost字段
            'avg_llm_calls': avg_llm_calls,
            'total_entries': stats['total_entries'],
            'successful_entries': stats['successful_entries'],
            'valid_token_entries': stats['valid_token_entries']
        }

    return results

# 读取并处理数据
model_stats1 = load_data_from_jsonl('analysis/data/full_stat_3_runs.jsonl')
model_stats2 = load_data_from_jsonl('analysis/data/ytb_stat_3_runs.jsonl')
# 两者各属性相加
# 加之前检验一下是不是都有属性，有的话是不是都是同一类型
for model_name in model_stats1:
    for key in model_stats1[model_name]:
        if key not in model_stats2[model_name]:
            raise ValueError(f"model_stats2[{model_name}]没有属性{key}")
        if type(model_stats1[model_name][key]) != type(model_stats2[model_name][key]):
            raise ValueError(f"model_stats1[{model_name}][{key}]和model_stats2[{model_name}][{key}]类型不同")
model_stats = {model_name: {key: model_stats1[model_name][key] + model_stats2[model_name][key] for key in model_stats1[model_name]} for model_name in model_stats1}
for mode in ("output","total"):
    results = calculate_metrics(model_stats,mode)

    # 打印统计信息
    print("模型统计信息:")
    for model_name, metrics in results.items():
        display_name = MODEL_DISPLAY_NAME_MAP.get(model_name, model_name)
        print(f"{display_name} ({model_name}):")
        print(f"  总条目数: {metrics['total_entries']}")
        print(f"  成功条目数: {metrics['successful_entries']}")
        print(f"  有效token条目数: {metrics['valid_token_entries']}")
        print(f"  Pass@1: {metrics['pass_at_1']:.1f}%")
        print(f"  平均输出tokens: {metrics['avg_output_tokens']:.0f}")
        print(f"  平均输入tokens: {metrics['avg_input_tokens']:.0f}")
        print(f"  平均cost: {metrics['avg_cost']:.0f}")
        print(f"  平均LLM调用次数: {metrics['avg_llm_calls']:.1f}")
        print()

    # 准备绘图数据 - 使用显示名称
    model_names = list(results.keys())
    display_names = [MODEL_DISPLAY_NAME_MAP.get(name, name) for name in model_names]
    pass_at_1_values = [results[name]['pass_at_1'] for name in model_names]
    avg_cost = [results[name]['avg_cost'] for name in model_names]

    # 为每个模型分配颜色
    colors = plt.cm.tab10(np.linspace(0, 1, len(model_names)))

    # --- 绘图设置 ---
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))  # 单个图像
    # 使用简洁的白色背景风格
    plt.rcParams['axes.facecolor'] = 'white'
    plt.rcParams['figure.facecolor'] = 'white'

    # --- 绘制图: Pass@1 vs Average Cost per Task ---
    ax.scatter(avg_cost, pass_at_1_values, c=colors, s=100, alpha=0.8, marker='s')  # 's' 表示正方形

    # 设置网格样式 - 加深颜色
    ax.grid(True, axis='y', color='#CCCCCC', linewidth=1.2, alpha=1.0)
    ax.set_axisbelow(True)

    # 显示坐标轴线
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(True)  # 显示左轴
    ax.spines['bottom'].set_visible(True)  # 显示底轴
    ax.spines['left'].set_color('#666666')
    ax.spines['bottom'].set_color('#666666')
    ax.spines['left'].set_linewidth(1.0)
    ax.spines['bottom'].set_linewidth(1.0)

    # # 将坐标轴脊柱往外移动一点
    # ax.spines['left'].set_position(('outward', 10))
    # ax.spines['bottom'].set_position(('outward', 10))

    # 为每个点添加标签 - 使用显示名称
    label_positions = {
        'GPT-5': ('right', 'top'),
        'Grok-4': ('right', 'top'),
        'Claude-4-Sonnet': ('left', 'top'),
        'DeepSeek-V3.1': ('right', 'top'),
        'Gemini-2.5-Pro': ('right', 'bottom'),
        'Grok-Code-Fast-1': ('right', 'top'),
        'Kimi-K2-0905': ('left', 'bottom'),
        'GLM-4.5': ('left', 'bottom'),
        'Qwen-3-Coder': ('right', 'bottom'),
        'Grok-4-Fast': ('left', 'top'),
        'Gemini-2.5-Flash': ('right', 'top'),
        'GPT-5-mini': ('left', 'top'),
        'o3': ('right', 'top'),
        'o4-mini': ('left', 'top'),
        'GPT-OSS-120B': ('right', 'top'),
        # 'Qwen3-max': ('right', 'top'),
        # 'GPT-5-high': ('left', 'top'),
        # 'Claude-4.1-Opus': ('left', 'top'),

    }


#  total tokens/output tokens layout
# label_positions = {
#     'GPT-5': ('right', 'top'),
#     'Grok-4': ('right', 'top'),
#     'Claude-4-Sonnet': ('left', 'top'),
#     'DeepSeek-V3.1': ('right', 'top'),
#     'Gemini-2.5-Pro': ('right', 'bottom'),
#     'Grok-Code-Fast-1': ('right', 'top'),
#     'Kimi-K2-0905': ('left', 'bottom'),
#     'GLM-4.5': ('left', 'bottom'),
#     'Qwen-3-Coder': ('right', 'bottom'),
#     'Grok-4-Fast': ('left', 'top'),
#     'Gemini-2.5-Flash': ('left', 'top'),
#     'GPT-5-mini': ('left', 'top'),
#     'o3': ('right', 'top'),
#     'o4-mini': ('left', 'top'),
#     'GPT-OSS-120B': ('right', 'top'),
# }

    for i, display_name in enumerate(display_names):
        # 使用默认位置如果模型不在字典中
        h_align, v_align = label_positions.get(display_name, ('right', 'bottom'))

        # 根据对齐方式设置偏移量
        if h_align == 'right':
            x_offset = 3
            ha = 'left'
        else:  # left
            x_offset = -3
            ha = 'right'

        if v_align == 'top':
            y_offset = 6
            va = 'bottom'
        else:  # bottom
            y_offset = -6
            va = 'top'

        ax.annotate(display_name, (avg_cost[i], pass_at_1_values[i]),
                    textcoords="offset points",
                    xytext=(x_offset, y_offset),
                    ha=ha, va=va, fontsize=20)

    # ax.set_title('Overall Pass@1 vs Average Total Tokens per Task', fontsize=16)
    ax.set_xlabel(f'average {mode} tokens per task', fontsize=28)
    ax.set_ylabel('pass@1 (%)', fontsize=28)

    # 设置Y轴刻度
    max_pass_at_1 = max(pass_at_1_values) if pass_at_1_values else 50
    y_max = int((max_pass_at_1 + 10) // 10 * 10)  # 向上取整到10的倍数
    ax.set_ylim(-2, y_max)
    ax.set_yticks(range(0, y_max + 1, 10))

    # 自定义X轴刻度 - 根据数据范围设置合适的刻度
    min_cost = min(avg_cost) if avg_cost else 0
    max_cost = max(avg_cost) if avg_cost else 25000

    # 设置X轴刻度点 - 可以根据需要自定义
    if mode == "output":
        x_tick_interval = 5000  # 
    elif mode == "total":
        x_tick_interval = 200000  # 
    x_tick_values = list(range(0, int(max_cost) + x_tick_interval, x_tick_interval))
    ax.set_xticks(x_tick_values)

    # 格式化X轴刻度标签
    def cost_formatter(x, pos):
        if x >= 1000:
            return f'{int(x/1000)}K'
        return str(int(x))

    ax.xaxis.set_major_formatter(mticker.FuncFormatter(cost_formatter))

    # 放大坐标轴刻度文字，并将刻度方向设为向外且加大间距
    ax.tick_params(axis='both', which='major', labelsize=24, direction='out', pad=10)

    # 设置X轴范围
    if mode == "output":
        ax.set_xlim(-1000, max_cost * 1.1)  # X轴从负值开始，留一些边距
    elif mode == "total":
        ax.set_xlim(-40000, max_cost * 1.1)  # X轴从负值开始，留一些边距

    # --- 保存图像为PDF ---
    plt.tight_layout()
    plt.savefig(f'analysis/figs/pass_with_avg_{mode}_tokens.pdf', format='pdf', dpi=300, bbox_inches='tight')
    print(f"散点图已保存为 {mode}_tokens.pdf")
    plt.show()