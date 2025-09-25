import os
import json
import argparse
from collections import defaultdict, Counter
from typing import Dict, List, Any, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def set_plot_style():
    plt.rcParams.update({
        "font.sans-serif": ["DejaVu Sans", "Arial", "Liberation Sans"],
        "axes.labelsize": 12,  # 原11增大2号
        "xtick.labelsize": 11,  # 原10增大2号
        "ytick.labelsize": 11,  # 原10增大2号
        "legend.fontsize": 11,  # 原10增大2号
        "figure.dpi": 110,
        # "axes.spines.top": False,
        # "axes.spines.right": False,
        "grid.alpha": 0.3,
        "axes.grid": False,
    })

PALETTE = {
    "bar_primary": "#4B6F8A",     # 海蓝灰（主柱状图）
    "bar_secondary": "#6A9FB5",   # 天蓝（辅柱状图）
    "line_primary": "#9B59B6",    # 亮红紫色（主折线）
    "line_secondary": "#7D8FB0",  # 紫蓝（辅折线）
    "neutral": "#AEB6C1",         # 浅灰蓝（中性色）
}

# 模型展示名映射（可按需修改）
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

def pretty_label(label: str) -> str:
    if "error_in_tool_call" in label:
        return label.replace("error_in_tool_call", "Tool Call Error")
    if "name_not_found" in label:
        return label.replace("name_not_found", "Wrong Tool Name")
    return str(label).replace("_", " ")


def read_jsonl(path):
    items = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def compute_attempt_success_rate_by_model(items: List[Dict[str, Any]], denom_per_attempt: int = 108) -> Dict[str, float]:
    # 针对多次 attempt，按模型-尝试号聚合成功数，计算每次成功率 success_count/denom，然后对尝试取均值
    # evaluation 仅 True/False/None；只统计 True 为成功
    by_model_attempt: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
    attempts_seen: Dict[str, set] = defaultdict(set)
    for row in items:
        model = row.get("model_name")
        attempt = int(row.get("attempt_num", 1))
        traj = row.get("traj_stat") or {}
        status = traj.get("status_data", {})
        evaluation = status.get("evaluation")
        if evaluation is True:
            by_model_attempt[model][attempt] += 1
        attempts_seen[model].add(attempt)

    result: Dict[str, float] = {}
    for model, att_map in by_model_attempt.items():
        rates = []
        for att in sorted(attempts_seen[model]):
            succ = att_map.get(att, 0)
            rate = succ / denom_per_attempt if denom_per_attempt > 0 else 0.0
            rates.append(rate)
        result[model] = (sum(rates) / len(rates)) if rates else 0.0
    # 对于没有任何成功（或无数据）的模型仍返回 0.0，以便画图
    # 还需覆盖那些完全没在 by_model_attempt 出现但在 items 中存在的模型（全失败或全 None）
    models_in_items = {row.get("model_name") for row in items}
    for m in models_in_items:
        if m not in result:
            # 若该模型存在 attempt 但无成功，仍需计算均值（全为 0）
            # 统计有多少 attempt
            atts = {int(row.get("attempt_num", 1)) for row in items if row.get("model_name") == m}
            if atts:
                result[m] = 0.0
    return result


def safe_get_tool_fail_counts(tool_output_type_count: Dict[str, int]) -> Tuple[int, int]:
    # 仅统计两类失败：tool_name_not_found、error_in_tool_call
    if not tool_output_type_count:
        return 0, 0
    return (
        int(tool_output_type_count.get("tool_name_not_found", 0)),
        int(tool_output_type_count.get("error_in_tool_call", 0)),
    )


def group_by_model(items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    # 默认：合并所有 attempt 的样本到同一模型下，做样本级统计
    model_wise: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in items:
        model_name = row["model_name"]
        if row.get("traj_stat") is not None:
            model_wise[model_name].append(row["traj_stat"])
    return model_wise


def is_success(evaluation_value: Any) -> bool:
    # evaluation 只有 True/False/None
    return evaluation_value is True


def summarize_per_model(trajs: List[Dict[str, Any]]) -> Dict[str, Any]:
    # 聚合每个样本的基础字段
    per_traj_summary = []
    for t in trajs:
        status_data = t.get("status_data", {})
        evaluation = status_data.get("evaluation")
        running = status_data.get("running")
        s = t.get("stat_for_one_traj", {})
        tool_call_count = int(s.get("tool_call_count", 0))
        toc = s.get("tool_output_type_count", {}) or {}
        name_not_found, error_call = safe_get_tool_fail_counts(toc)
        merged_fail = name_not_found + error_call

        per_traj_summary.append({
            "tool_call_count": tool_call_count,
            "name_not_found": name_not_found,
            "error_in_tool_call": error_call,
            "merged_fail": merged_fail,
            "evaluation": evaluation,
            "running": running,
        })

    # 失败率（加权/非加权）
    total_calls = sum(x["tool_call_count"] for x in per_traj_summary)
    total_nnf = sum(x["name_not_found"] for x in per_traj_summary)
    total_err = sum(x["error_in_tool_call"] for x in per_traj_summary)
    total_merged = sum(x["merged_fail"] for x in per_traj_summary)

    weighted = {
        "name_not_found": (total_nnf / total_calls) if total_calls > 0 else 0.0,
        "error_in_tool_call": (total_err / total_calls) if total_calls > 0 else 0.0,
        "merged": (total_merged / total_calls) if total_calls > 0 else 0.0,
    }

    # 非加权（逐样本平均），排除 tool_call_count=0 的样本
    per_traj_rates_nnf = [x["name_not_found"] / x["tool_call_count"] for x in per_traj_summary if x["tool_call_count"] > 0]
    per_traj_rates_err = [x["error_in_tool_call"] / x["tool_call_count"] for x in per_traj_summary if x["tool_call_count"] > 0]
    per_traj_rates_merged = [x["merged_fail"] / x["tool_call_count"] for x in per_traj_summary if x["tool_call_count"] > 0]

    unweighted = {
        "name_not_found": (sum(per_traj_rates_nnf) / len(per_traj_rates_nnf)) if per_traj_rates_nnf else 0.0,
        "error_in_tool_call": (sum(per_traj_rates_err) / len(per_traj_rates_err)) if per_traj_rates_err else 0.0,
        "merged": (sum(per_traj_rates_merged) / len(per_traj_rates_merged)) if per_traj_rates_merged else 0.0,
    }

    zero_call_samples = sum(1 for x in per_traj_summary if x["tool_call_count"] == 0)

    # 有失败样本占比
    any_fail_samples = sum(1 for x in per_traj_summary if x["merged_fail"] > 0)
    any_fail_ratio = any_fail_samples / len(per_traj_summary) if per_traj_summary else 0.0

    # 分开两类错误的存在性统计（至少一个失败的样本占比）
    any_name_not_found_samples = sum(1 for x in per_traj_summary if x["name_not_found"] > 0)
    any_error_in_tool_call_samples = sum(1 for x in per_traj_summary if x["error_in_tool_call"] > 0)
    any_name_not_found_ratio = any_name_not_found_samples / len(per_traj_summary) if per_traj_summary else 0.0
    any_error_in_tool_call_ratio = any_error_in_tool_call_samples / len(per_traj_summary) if per_traj_summary else 0.0

    # 分桶：仅区分是否存在错误（按合并失败次数）
    bucket_order = ["no_error", "has_error"]
    def to_bucket(v: int) -> str:
        return "has_error" if v > 0 else "no_error"

    # 计算每桶样本数与成功率（evaluation=True 的比例）
    bucket_counts = Counter()
    bucket_eval_true = Counter()
    bucket_eval_total = Counter()
    for x in per_traj_summary:
        b = to_bucket(x["merged_fail"])
        bucket_counts[b] += 1
        if x["evaluation"] is not None:
            bucket_eval_total[b] += 1
            if is_success(x["evaluation"]):
                bucket_eval_true[b] += 1

    bucket_success_rate = {}
    for b in bucket_order:
        total = bucket_eval_total.get(b, 0)
        succ = bucket_eval_true.get(b, 0)
        bucket_success_rate[b] = (succ / total) if total > 0 else None

    # 有失败 vs 无失败 的成功率
    with_fail_eval = [x for x in per_traj_summary if x["merged_fail"] > 0 and x["evaluation"] is not None]
    without_fail_eval = [x for x in per_traj_summary if x["merged_fail"] == 0 and x["evaluation"] is not None]
    with_fail_success = (sum(1 for x in with_fail_eval if is_success(x["evaluation"])) / len(with_fail_eval)) if with_fail_eval else None
    # 这里麻烦再输出一下两边的实际分子分母
    with_fail_success_tsr = f"{sum(1 for x in with_fail_eval if is_success(x['evaluation']))} / {len(with_fail_eval)}"
    without_fail_success = (sum(1 for x in without_fail_eval if is_success(x["evaluation"])) / len(without_fail_eval)) if without_fail_eval else None
    without_fail_success_tsr = f"{sum(1 for x in without_fail_eval if is_success(x['evaluation']))} / {len(without_fail_eval)}"

    # 模型整体成功率（仅 evaluation 非空样本）
    overall_eval_samples = [x for x in per_traj_summary if x["evaluation"] is not None]
    overall_eval_true = sum(1 for x in overall_eval_samples if is_success(x["evaluation"]))
    overall_eval_total = len(overall_eval_samples)
    overall_success_rate = (overall_eval_true / overall_eval_total) if overall_eval_total > 0 else None

    # 分开两类错误的成功率影响（有该错误 vs 无该错误）
    nnf_with_eval = [x for x in per_traj_summary if x["name_not_found"] > 0 and x["evaluation"] is not None]
    nnf_without_eval = [x for x in per_traj_summary if x["name_not_found"] == 0 and x["evaluation"] is not None]
    nnf_with_success = (sum(1 for x in nnf_with_eval if is_success(x["evaluation"])) / len(nnf_with_eval)) if nnf_with_eval else None
    nnf_without_success = (sum(1 for x in nnf_without_eval if is_success(x["evaluation"])) / len(nnf_without_eval)) if nnf_without_eval else None
    nnf_delta_success = (nnf_with_success - nnf_without_success) if (nnf_with_success is not None and nnf_without_success is not None) else None

    err_with_eval = [x for x in per_traj_summary if x["error_in_tool_call"] > 0 and x["evaluation"] is not None]
    err_without_eval = [x for x in per_traj_summary if x["error_in_tool_call"] == 0 and x["evaluation"] is not None]
    err_with_success = (sum(1 for x in err_with_eval if is_success(x["evaluation"])) / len(err_with_eval)) if err_with_eval else None
    err_without_success = (sum(1 for x in err_without_eval if is_success(x["evaluation"])) / len(err_without_eval)) if err_without_eval else None
    err_delta_success = (err_with_success - err_without_success) if (err_with_success is not None and err_without_success is not None) else None

    # running 交叉
    # 1) 分桶 × running 样本数
    bucket_running_counts: Dict[Tuple[str, str], int] = Counter()
    for x in per_traj_summary:
        b = to_bucket(x["merged_fail"])
        r = x["running"] if x["running"] is not None else "other"
        bucket_running_counts[(b, r)] += 1

    # 2) 按 running 的加权失败率（两类分开）
    running_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for x in per_traj_summary:
        r = x["running"] if x["running"] is not None else "other"
        running_groups[r].append(x)

    running_weighted_rates = {}
    for r, xs in running_groups.items():
        calls = sum(t["tool_call_count"] for t in xs)
        nnf = sum(t["name_not_found"] for t in xs)
        err = sum(t["error_in_tool_call"] for t in xs)
        running_weighted_rates[r] = {
            "name_not_found": (nnf / calls) if calls > 0 else 0.0,
            "error_in_tool_call": (err / calls) if calls > 0 else 0.0,
        }

    return {
        "per_traj_summary": per_traj_summary,
        "weighted_failure_rate": weighted,
        "unweighted_failure_rate": unweighted,
        "zero_call_samples": zero_call_samples,
        "any_fail_ratio": any_fail_ratio,
        "any_name_not_found_ratio": any_name_not_found_ratio,
        "any_name_not_found_tsr": f"{any_name_not_found_samples} / {len(per_traj_summary)}",
        "any_error_in_tool_call_ratio": any_error_in_tool_call_ratio,
        "any_error_in_tool_call_tsr": f"{any_error_in_tool_call_samples} / {len(per_traj_summary)}",
        "bucket_order": bucket_order,
        "bucket_counts": {b: bucket_counts.get(b, 0) for b in bucket_order},
        "bucket_success_rate": bucket_success_rate,
        "with_fail_success": with_fail_success,
        "with_fail_success_tsr": with_fail_success_tsr,
        "without_fail_success": without_fail_success,
        "without_fail_success_tsr": without_fail_success_tsr,
        "overall_success_rate": overall_success_rate,
        "overall_success_tsr": f"{overall_eval_true} / {overall_eval_total}",
        # per-error-type success impact
        "name_not_found_success_with": nnf_with_success,
        "name_not_found_success_without": nnf_without_success,
        "name_not_found_success_delta": nnf_delta_success,
        "error_in_tool_call_success_with": err_with_success,
        "error_in_tool_call_success_without": err_without_success,
        "error_in_tool_call_success_delta": err_delta_success,
        "bucket_running_counts": bucket_running_counts,
        "running_weighted_rates": running_weighted_rates,
    }


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def plot_failure_rates(model: str, summary: Dict[str, Any], outdir: str):
    ensure_dir(outdir)
    weighted = summary["weighted_failure_rate"]
    unweighted = summary["unweighted_failure_rate"]

    labels = ["name_not_found", "error_in_tool_call", "merged"]
    w_vals = [weighted[k] for k in labels]
    u_vals = [unweighted[k] for k in labels]

    plt.figure(figsize=(7, 2.4))
    x = range(len(labels))
    plt.bar([i - 0.2 for i in x], w_vals, width=0.4, label="weighted", color=PALETTE["bar_primary"]) 
    plt.bar([i + 0.2 for i in x], u_vals, width=0.4, label="unweighted", color=PALETTE["bar_secondary"]) 
    plt.xticks(list(x), labels, rotation=20)
    plt.ylabel("failure rate")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, f"{model}_failure_rates.png"))
    plt.close()


def plot_bucket_counts_and_success(model: str, summary: Dict[str, Any], outdir: str):
    ensure_dir(outdir)
    order = summary["bucket_order"]
    counts = [summary["bucket_counts"].get(b, 0) for b in order]
    success_rates = [summary["bucket_success_rate"].get(b) for b in order]

    fig, ax1 = plt.subplots(figsize=(6, 2.4))
    ax1.bar(order, counts, color=PALETTE["bar_primary"], alpha=0.9)
    ax1.set_ylabel("num samples")
    ax1.set_xlabel("has tool error (merged)")

    ax2 = ax1.twinx()
    # 缺失成功率的桶置 0 绘制
    sr_plot = [r if r is not None else 0.0 for r in success_rates]
    ax2.plot(order, sr_plot, color=PALETTE["line_primary"], marker="d", linestyle="--", linewidth=1.8, label="Pass@1")
    ax2.set_ylabel("Pass@1 (%)")

    fig.tight_layout()
    fig.savefig(os.path.join(outdir, f"{model}_bucket_counts_success.png"))
    plt.close(fig)


def plot_bucket_running_heatmap(model: str, summary: Dict[str, Any], outdir: str):
    ensure_dir(outdir)
    bucket_order = summary["bucket_order"]
    # 收集 running 种类
    running_keys = sorted({k[1] for k in summary["bucket_running_counts"].keys()})
    # 构建矩阵
    import numpy as np
    mat = np.zeros((len(bucket_order), len(running_keys)), dtype=int)
    for i, b in enumerate(bucket_order):
        for j, r in enumerate(running_keys):
            mat[i, j] = summary["bucket_running_counts"].get((b, r), 0)

    plt.figure(figsize=(max(6, len(running_keys) * 1.2), 3.6))
    im = plt.imshow(mat, aspect="auto", cmap="viridis")
    plt.colorbar(im, fraction=0.046, pad=0.04)
    plt.xticks(range(len(running_keys)), running_keys, rotation=30)
    plt.yticks(range(len(bucket_order)), bucket_order)
    plt.xlabel("running")
    plt.ylabel("has tool error (merged)")
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, f"{model}_bucket_running_heatmap.png"))
    plt.close()


def plot_running_weighted_rates(model: str, summary: Dict[str, Any], outdir: str):
    ensure_dir(outdir)
    running_keys = sorted(summary["running_weighted_rates"].keys())
    nnf_vals = [summary["running_weighted_rates"][r]["name_not_found"] for r in running_keys]
    err_vals = [summary["running_weighted_rates"][r]["error_in_tool_call"] for r in running_keys]

    x = range(len(running_keys))
    plt.figure(figsize=(max(7, len(running_keys) * 0.8), 2.4))
    plt.bar([i - 0.2 for i in x], nnf_vals, width=0.4, label=pretty_label("name_not_found"), color=PALETTE["bar_primary"]) 
    plt.bar([i + 0.2 for i in x], err_vals, width=0.4, label=pretty_label("error_in_tool_call"), color=PALETTE["bar_secondary"]) 
    plt.xticks(list(x), running_keys, rotation=20)
    plt.ylabel("weighted failure rate")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, f"{model}_running_weighted_rates.png"))
    plt.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="analysis/data/full_stat_3_runs.jsonl")
    parser.add_argument("--input_second", default="analysis/data/ytb_stat_3_runs.jsonl")
    parser.add_argument("--outdir", default="analysis/figs/tool_call_errors")
    parser.add_argument("--save-json", action="store_true")
    args = parser.parse_args()

    ensure_dir(args.outdir)
    set_plot_style()

    items1 = read_jsonl(args.input)
    items2 = read_jsonl(args.input_second)
    items = items1 + items2
    model_wise = group_by_model(items)
    # 多 attempt 情况：计算按 attempt 的成功率均值（分母 108）
    attempt_success_rate_by_model = compute_attempt_success_rate_by_model(items, denom_per_attempt=108)

    # 汇总跨模型对比用的容器
    success_rows = []   # 每模型：整体成功率
    presence_rows = []  # 每模型：两类错误的“有错轨迹占比”
    impact_rows = []    # 每模型：两类错误的 Δ成功率

    for model, trajs in model_wise.items():
        if model in ['qwen-3-max','gpt-oss-120b']:
            continue
        summary = summarize_per_model(trajs)

        # 输出摘要
        print(f"\n===== {model} =====")
        print("weighted:", summary["weighted_failure_rate"])
        print("unweighted:", summary["unweighted_failure_rate"])
        print("zero_call_samples:", summary["zero_call_samples"])
        print("any_fail_ratio:", round(summary["any_fail_ratio"], 4))
        print("any_name_not_found_ratio:", round(summary["any_name_not_found_ratio"], 4), f"({summary['any_name_not_found_tsr']})")
        print("any_error_in_tool_call_ratio:", round(summary["any_error_in_tool_call_ratio"], 4), f"({summary['any_error_in_tool_call_tsr']})")
        print("with_fail_success:", summary["with_fail_success"], f"({summary['with_fail_success_tsr']})", 
        "without_fail_success:", summary["without_fail_success"], f"({summary['without_fail_success_tsr']})") 

        model_outdir = os.path.join(args.outdir, model)
        ensure_dir(model_outdir)

        plot_failure_rates(model, summary, model_outdir)
        plot_bucket_counts_and_success(model, summary, model_outdir)
        plot_bucket_running_heatmap(model, summary, model_outdir)
        plot_running_weighted_rates(model, summary, model_outdir)

        if args.save_json:
            with open(os.path.join(model_outdir, f"{model}_summary.json"), "w") as f:
                json.dump({k: v for k, v in summary.items() if k != "per_traj_summary"}, f, indent=2)

        # 收集跨模型数据
        # 使用多 attempt 成功率定义（如有多个 attempt 则取均值；单 attempt 也适用）
        success_rows.append({
            "model": model,
            "success_rate": attempt_success_rate_by_model.get(model, summary.get("overall_success_rate")),
        })

        presence_rows.append({
            "model": model,
            "name_not_found_ratio": summary["any_name_not_found_ratio"],
            "error_in_tool_call_ratio": summary["any_error_in_tool_call_ratio"],
        })

        impact_rows.append({
            "model": model,
            "name_not_found_delta": summary["name_not_found_success_delta"],
            "error_in_tool_call_delta": summary["error_in_tool_call_success_delta"],
        })

    # 计算所有模型的最大数量，确保图表宽度一致
    all_models = set()
    if success_rows:
        all_models.update(r["model"] for r in success_rows)
    if presence_rows:
        all_models.update(r["model"] for r in presence_rows)
    if impact_rows:
        all_models.update(r["model"] for r in impact_rows)
    max_model_count = len(all_models)

    # 生成跨模型汇总图：成功率（百分比，0-最大值+5）
    if success_rows:
        # 排序（按成功率降序）
        success_rows.sort(key=lambda r: (r["success_rate"] if r["success_rate"] is not None else -1), reverse=True)
        models = [r["model"] for r in success_rows]
        sr_pct = [100.0 * (r["success_rate"] or 0.0) for r in success_rows]

        summary_dir = os.path.join(args.outdir, "summary")
        ensure_dir(summary_dir)

        import numpy as np
        x = np.arange(len(models))
        plt.figure(figsize=(max(10, max_model_count * 0.8), 2.5))
        disp_models = [display_model(m) for m in models]
        plt.bar(x, sr_pct, width=0.6, color=PALETTE["bar_primary"])
        plt.xticks(x, disp_models, rotation=30, ha="right")
        ymax = (max(sr_pct) + 5.0) if sr_pct else 100.0
        plt.ylim(0, ymax)
        plt.ylabel("Pass@1 (%)")
        # 手动设置边距确保与另一个图对齐，高度降低后调整边距
        plt.subplots_adjust(left=0.08, right=0.94, top=0.99, bottom=0.25)
        plt.savefig(os.path.join(summary_dir, "success_rate_by_model.pdf"))
        plt.close()

    # 生成跨模型汇总图：错误出现占比（百分比，0-最大值+5）
    if presence_rows:
        # 排序（按 error_in_tool_call_ratio 降序）
        presence_rows.sort(key=lambda r: (r["error_in_tool_call_ratio"] if r["error_in_tool_call_ratio"] is not None else -1), reverse=True)
        models = [r["model"] for r in presence_rows]
        nnf_pct = [100.0 * (r["name_not_found_ratio"] or 0.0) for r in presence_rows]
        err_pct = [100.0 * (r["error_in_tool_call_ratio"] or 0.0) for r in presence_rows]

        # 成功率与模型对齐（百分比）
        success_map = {r["model"]: (100.0 * (r["success_rate"] or 0.0)) for r in success_rows}
        sr_pct_line = [success_map.get(m, 0.0) for m in models]

        summary_dir = os.path.join(args.outdir, "summary")
        ensure_dir(summary_dir)

        import numpy as np
        x = np.arange(len(models))
        width = 0.38
        fig, ax1 = plt.subplots(figsize=(max(10, max_model_count * 0.8), 2.5))
        b1 = ax1.bar(x - width/2, nnf_pct, width=width, label=pretty_label("name_not_found"), color=PALETTE["bar_primary"]) 
        b2 = ax1.bar(x + width/2, err_pct, width=width, label=pretty_label("error_in_tool_call"), color=PALETTE["bar_secondary"]) 
        disp_models = [display_model(m) for m in models]
        ax1.set_xticks(x, disp_models, rotation=30, ha="right")
        ymax = max(nnf_pct + err_pct) + 5.0 if (nnf_pct or err_pct) else 100.0
        ax1.set_ylim(0, ymax)
        ax1.set_ylabel("Error Presence (%)")

        # 右轴成功率折线
        ax2 = ax1.twinx()
        ymax2 = (max(sr_pct_line) + 5.0) if sr_pct_line else 100.0
        ax2.set_ylim(0, ymax2)
        l1, = ax2.plot(x, sr_pct_line, color=PALETTE["line_primary"], marker="o", linestyle="--", linewidth=1.2, label="Pass@1")
        ax2.set_ylabel("Pass@1 (%)")

        # 合并图例
        handles = [b1, b2, l1]
        labels = [pretty_label(h.get_label()) for h in handles]
        # 手动设置一下 legend 位置，再网上一点
        ax1.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 1.02))

        # 手动设置边距确保与另一个图对齐，高度降低后增加底部空间给legend
        fig.subplots_adjust(left=0.08, right=0.94, top=0.99, bottom=0.35)
        fig.savefig(os.path.join(summary_dir, "error_presence_by_model.pdf"))
        plt.close(fig)

    if impact_rows:
        # 排序（按 error_in_tool_call_delta 升序，负值更靠左）
        impact_rows.sort(key=lambda r: (r["error_in_tool_call_delta"] if r["error_in_tool_call_delta"] is not None else 0.0))
        models = [r["model"] for r in impact_rows]
        nnf_delta_pct = [100.0 * r["name_not_found_delta"] if r["name_not_found_delta"] is not None else 0.0 for r in impact_rows]
        err_delta_pct = [100.0 * r["error_in_tool_call_delta"] if r["error_in_tool_call_delta"] is not None else 0.0 for r in impact_rows]

        summary_dir = os.path.join(args.outdir, "summary")
        ensure_dir(summary_dir)

        import numpy as np
        x = np.arange(len(models))
        width = 0.38
        plt.figure(figsize=(max(10, max_model_count * 0.8), 2.5))
        disp_models = [display_model(m) for m in models]
        plt.bar(x - width/2, nnf_delta_pct, width=width, label=pretty_label("name_not_found ΔSR"), color=PALETTE["bar_primary"]) 
        plt.bar(x + width/2, err_delta_pct, width=width, label=pretty_label("error_in_tool_call ΔSR"), color=PALETTE["bar_secondary"]) 
        plt.axhline(0, color="#333", linewidth=1)
        plt.xticks(x, disp_models, rotation=30, ha="right")
        plt.ylabel("Δ Success Rate (%)")
        plt.legend()
        # 手动设置边距确保与另一个图对齐，高度降低后增加底部空间给legend
        plt.subplots_adjust(left=0.08, right=0.94, top=0.88, bottom=0.35)
        plt.savefig(os.path.join(summary_dir, "success_rate_impact_by_model.pdf"))
        plt.close()


if __name__ == "__main__":
    main()


