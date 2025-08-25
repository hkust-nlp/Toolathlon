from argparse import ArgumentParser
from pathlib import Path
import json
import yfinance as yf
import pandas as pd
import re
from io import StringIO

def compare_rating(rating, stock_result):
    grade_to_direction = {
        # “Up”-predictions
        "Overweight":     "up",
        "Outperform":     "up",
        "Buy":            "up",
        "Strong Buy":     "up",
        "Positive":       "up",
        "Accumulate":     "up",

        # “Flat”-predictions
        "Neutral":        "flat",
        "Hold":           "flat",
        "Sector Weight":  "flat",   # 跟随所在行业走势，近似“横盘”
        "Perform":       "flat",
        "Market Perform": "flat",
        "Equal-Weight":   "flat",

        # “Down”-predictions
        "Sell":           "down",
        "Underperform":   "down",
        "Underweight":    "down",
    }
    direction = grade_to_direction.get(rating, None)

    if direction is None:
        print(f"Unknown rating: {rating}")
        return None
    
    results = {}
    start = stock_result['start']
    for horizon in ["4m", "5m", "6m"]:
        price = stock_result[horizon]
        if price is None:
            results[horizon] = None
            continue

        if direction == "up":
            results[horizon] = price > start
        elif direction == "flat":
            ret = (price - start) / start
            results[horizon] = abs(ret) <= 0.02
        elif direction == "down":
            results[horizon] = price < start
    return results

def compute_excess_return(stock_result, bench_result):
    """
    计算股票和基准指数在指定日期及之后 4、5、6 个月的超额收益。
    超额收益 = 股票收益 - 基准指数收益

    Args:
        stock_result: dict
            股票的收盘价结果，格式同 get_stock_price 的返回值。
        bench_result: dict
            基准指数的收盘价结果，格式同 get_stock_price 的返回值。

    Returns:
        dict:
            {
                "4m": excess_return_4m,
                "5m": excess_return_5m,
                "6m": excess_return_6m
            }
    """
    excess_returns = {}
    start_stock = stock_result['start']
    start_bench = bench_result['start']
    for horizon in ["4m", "5m", "6m"]:
        stock_price = stock_result[horizon]
        bench_price = bench_result[horizon]
        if stock_price is None or bench_price is None:
            excess_returns[horizon] = None
        else:
            R_stock = (stock_price - start_stock) / start_stock
            R_bench = (bench_price - start_bench) / start_bench

            excess_returns[horizon] = (R_stock - R_bench) * 100  # 转为百分比形式

    return excess_returns
    
def get_stock_price(stock_hist: pd.DataFrame, bench_hist: pd.DataFrame, date, rating) -> dict:
    """
    同时返回股票和基准指数在指定日期及之后 4、5、6 个月的收盘价，
    并自动对齐输入日期与历史数据的时区。
    """
    def _prepare(hist: pd.DataFrame):
        h = hist.sort_index()
        return h.index, h['Close']

    stock_dates, stock_close = _prepare(stock_hist)
    bench_dates, bench_close = _prepare(bench_hist)

    # 1. 解析输入日期，并对齐到 stock_dates 的时区
    dt0 = pd.to_datetime(date)
    tz = stock_dates.tz  # 可能是 UTC，也可能是 None
    if tz is not None and dt0.tzinfo is None:
        dt0 = dt0.tz_localize(tz)
    elif tz is None and dt0.tzinfo is not None:
        dt0 = dt0.tz_convert(None)

    def _nearest_price(dates: pd.DatetimeIndex, closes: pd.Series, target: pd.Timestamp) -> float | None:
        # 先把 target 对齐到 dates 的时区
        if dates.tz is not None and target.tzinfo is None:
            target = target.tz_localize(dates.tz)
        elif dates.tz is None and target.tzinfo is not None:
            target = target.tz_convert(None)

        if target > dates[-1]:
            return None
        pos = dates.get_indexer([target], method='nearest')[0]
        return float(closes.iloc[pos])

    def _get_prices(dates, closes):
        out = {'start': _nearest_price(dates, closes, dt0)}
        for m in (4, 5, 6):
            tgt = dt0 + pd.DateOffset(months=m)
            out[f'{m}m'] = _nearest_price(dates, closes, tgt)
        return out

    return {
        "stock":     _get_prices(stock_dates, stock_close),
        "benchmark": _get_prices(bench_dates, bench_close)
    }


def get_gt(ticker):
    stock = yf.Ticker(ticker)
    stock_hist = stock.history(period='2y')
    bench = yf.Ticker('^GSPC')  # S&P 500
    bench_hist = bench.history(period='2y')
    ratings = stock.upgrades_downgrades
    two_years_ago = pd.Timestamp.today() - pd.DateOffset(years=2)
    recent_ratings = ratings[ratings.index >= two_years_ago]

    # 初始化统计容器
    results = {
        "4m": {"hit": 0, "excess": 0.0, "signals": 0, "fails": 0},
        "5m": {"hit": 0, "excess": 0.0, "signals": 0, "fails": 0},
        "6m": {"hit": 0, "excess": 0.0, "signals": 0, "fails": 0},
    }

    # 遍历每条评级
    for dt, row in recent_ratings.iterrows():
        rating = row["ToGrade"]
        # 先获取股价与基准价格数据
        info = get_stock_price(stock_hist, bench_hist, dt, rating)
        stock_res = info["stock"]
        bench_res = info["benchmark"]

        # 如果 start 缺失，则整条信号无效
        if stock_res["start"] is None or bench_res["start"] is None:
            for h in ("4m", "5m", "6m"):
                results[h]["fails"] += 1
            continue

        # 方向命中情况
        hit_map = compare_rating(rating, stock_res)

        # 超额收益
        excess_map = compute_excess_return(stock_res, bench_res)

        # 累计到统计中
        for h in ("4m", "5m", "6m"):
            # 如果未来价格缺失，则视为剔除
            if stock_res[h] is None or bench_res[h] is None:
                results[h]["fails"] += 1
                continue

            results[h]["signals"] += 1
            # 命中记 1，否则记 0
            if hit_map[h]:
                results[h]["hit"] += 1
            # 累加超额收益
            results[h]["excess"] += excess_map[h]

    # 计算 Hit Rate (%) 与 Avg Excess Return (%)
    summary = {}
    for h, stats in results.items():
        n = stats["signals"]
        hit_rate = (stats["hit"] / n * 100) if n > 0 else None
        avg_excess = (stats["excess"] / n) if n > 0 else None

        summary[h] = {
            "Hit Rate (%)": round(hit_rate, 2) if hit_rate is not None else None,
            "Avg Excess Return (%)": round(avg_excess, 2) if avg_excess is not None else None,
            "#Signals": stats["signals"],
            "Fails": stats["fails"],
        }

    return summary

def load_results_md(workspace: Path) -> str:
    """
    优先读取 workspace/results.md；
    若不存在则读取 workspace/results_template.md；
    都不存在则退出(1)。
    """
    for name in ("results.md", "results_template.md"):
        p = workspace / name
        if p.exists():
            return p.read_text(encoding="utf-8")
    exit(1)

def parse_table(md: str) -> pd.DataFrame:
    """
    从 Markdown 文本中提取第一张表格，
    并返回 pandas.DataFrame。
    """
    # 找到 ## Table 之后的表格段
    tbl_match = re.search(r"## Table\s*(\|[\s\S]+?)\n## ", md)
    if not tbl_match:
        print("No table found in the Markdown content.")
        exit(1)
    tbl_md = tbl_match.group(1).strip()
    # 用 pandas 解析
    df = pd.read_csv(
        StringIO(tbl_md),
        sep="|",
        engine="python",
        header=0,
        skipinitialspace=True,
        usecols=lambda x: x.strip() != ""
    )
    # 清洗列名与数据
    df.columns = [c.strip() for c in df.columns]
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
    df = df[pd.to_numeric(df["Hit Rate (%)"], errors="coerce").notna()]
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    return df

def parse_choice(md: str) -> str:
    """
    提取 "Choice: (NVDA or AAPL)" 的值
    """
    m = re.search(r"^Choice:\s*(NVDA|AAPL)\s*$", md, flags=re.MULTILINE)
    if not m:
        print("No choice found in the Markdown content.")
        exit(1)
    return m.group(1)

def parse_data_range(md: str):
    """
    提取 Start/End 日期 (格式 YYYY-MM-DD)
    """
    m_start = re.search(r"Start:\s*(\d{4}-\d{2}-\d{2})", md)
    m_end   = re.search(r"End:\s*(\d{4}-\d{2}-\d{2})", md)
    if not (m_start and m_end):
        print("No Start or End date found in the Markdown content.")
        exit(1)
    return pd.to_datetime(m_start.group(1)), pd.to_datetime(m_end.group(1))

def main():
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True)
    args = parser.parse_args()
    print(f"Using agent workspace: {args.agent_workspace}")
    ws = Path(args.agent_workspace)

    print("🔍 Loading results from workspace...")
    md = load_results_md(ws)
    
    print("🔍 Parsing table, choice, and data range...")
    df = parse_table(md)
    choice = parse_choice(md)
    start_date, end_date = parse_data_range(md)

    print(f"⏳ Computing ground truth for NVDA and AAPL...")
    nvda_stats = get_gt("NVDA")
    aapl_stats = get_gt("AAPL")

    print("🔍 Verifying reported table against ground truth...")
    # 阈值设置
    pct_thresh = 0.02   # 2%
    count_ratio_thresh = 0.05  # 5%

    for _, row in df.iterrows():
        ticker = row["Ticker"]
        horizon = row["Horizon"].split()[0] + "m"  # e.g. "4 months" → "4m"
        reported_hit = float(row["Hit Rate (%)"])
        reported_excess = float(row["Avg Excess Return (%)"])
        reported_signals = int(row["#Signals"])
        reported_excluded = int(row.get("#Excluded", row.get("Fails", 0)))

        stats = nvda_stats if ticker == "NVDA" else aapl_stats
        actual = stats[horizon]
        actual_hit = actual["Hit Rate (%)"]
        actual_excess = actual["Avg Excess Return (%)"]
        actual_signals = actual["#Signals"]
        actual_excluded = actual["Fails"]

        print(f"\n— {ticker} {horizon} —")
        print(f"  Hit Rate: reported {reported_hit}%, actual {actual_hit}%")
        if abs(reported_hit - actual_hit) > pct_thresh * 100:
            print(f"❌ Hit Rate diff > {pct_thresh*100}%")
            exit(1)

        print(f"  Avg Excess Return: reported {reported_excess}%, actual {actual_excess}%")
        if abs(reported_excess - actual_excess) > pct_thresh * 100:
            print(f"❌ Avg Excess Return diff > {pct_thresh*100}%")
            exit(1)

        print(f"  #Signals: reported {reported_signals}, actual {actual_signals}")
        if actual_signals > 0 and abs(reported_signals - actual_signals) / actual_signals > count_ratio_thresh:
            print(f"❌ #Signals diff ratio > {count_ratio_thresh*100}%")
            exit(1)

        print(f"  #Excluded: reported {reported_excluded}, actual {actual_excluded}")
        if actual_excluded > 0 and abs(reported_excluded - actual_excluded) / actual_excluded > count_ratio_thresh:
            print(f"❌ #Excluded diff ratio > {count_ratio_thresh*100}%")
            exit(1)

    print("\n🔍 Verifying More Reliable choice...")
    nvda_mean_hit = sum(nvda_stats[h]["Hit Rate (%)"] for h in nvda_stats) / 3
    aapl_mean_hit = sum(aapl_stats[h]["Hit Rate (%)"] for h in aapl_stats) / 3
    more_reliable = "NVDA" if nvda_mean_hit >= aapl_mean_hit else "AAPL"
    print(f"  Reported Choice: {choice}, Ground Truth: {more_reliable}")
    if choice != more_reliable:
        print("❌ Choice does not match ground truth.")
        exit(1)

    print("\n🔍 Verifying Data Range...")
    today = pd.Timestamp.today().normalize()
    two_years_ago = today - pd.DateOffset(years=2)
    print(f"  Reported Start: {start_date.date()}, Expected ~ {two_years_ago.date()}")
    if abs((start_date - two_years_ago).days) > 10:
        print("❌ Start date out of allowed range.")
        exit(1)

    print(f"  Reported End:   {end_date.date()}, Expected ~ {today.date()}")
    if abs((end_date - today).days) > 1:
        print("❌ End date out of allowed range.")
        exit(1)

    print("\n✅ All checks passed.")

if __name__ == "__main__":
    main()
    




    