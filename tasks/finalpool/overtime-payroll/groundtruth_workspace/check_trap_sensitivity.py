#!/usr/bin/env python3
"""Quality gate for the generated data: every planted trap must matter.

This script is an *independent* float-based re-implementation of
``overtime_policy.md`` (pandas instead of Fractions/openpyxl) with switchable
"plausible mistakes".  It asserts that

  1. the faithful implementation reproduces the ground-truth workbook, and
  2. every single mistake changes at least one cell of the Employee Summary,
     i.e. the evaluator can actually tell a careless agent from a careful one.

Run after (re)generating data:
    python generate_data.py && python reference_solution.py && python check_trap_sensitivity.py
"""

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import payroll_schema as S  # noqa: E402

WS = os.path.join(os.path.dirname(HERE), "initial_workspace")
GT = os.path.join(HERE, S.OUTPUT_FILENAME)

MISTAKES = {
    "no_dedup": "duplicate export rows are counted twice",
    "no_id_normalization": "employee IDs are not trimmed / upper-cased",
    "no_period_filter": "rows outside 2025-08 are not dropped",
    "period_by_clock_out": "period membership decided by the clock-out date",
    "daytype_by_clock_out": "weekend/holiday decided by the clock-out date",
    "holiday_as_weekend": "holidays paid as weekend (2.0x) instead of 2.5x",
    "weekend_beats_holiday": "a Saturday holiday treated as a plain weekend",
    "weekend_regular_first": "weekend shifts get 8 regular hours before premium",
    "per_shift_ot": "daily 8 h threshold applied per shift, not per day",
    "break_at_6h_inclusive": "meal break deducted at exactly 6 h",
    "no_break": "meal break never deducted",
    "floor_quarter_hour": "paid hours rounded down instead of to nearest",
    "invalid_at_16h_inclusive": "an exactly-16-hour shift treated as invalid",
    "no_16h_rule": "badge-left-open spans (> 16 h) treated as valid",
    "include_contractors_interns": "contractors and interns included",
    "count_out_of_period_invalid": "out-of-period broken rows counted as invalid punches",
    "drop_zero_employees": "eligible employees without shifts omitted",
    "alert_threshold_inclusive": "OT alert at >= 30 h instead of > 30 h",
}


def load(mistakes):
    roster = pd.read_excel(os.path.join(WS, S.ROSTER_FILENAME))
    hol = set(pd.to_datetime(pd.read_csv(os.path.join(WS, S.HOLIDAYS_FILENAME))["date"]).dt.date)
    att = pd.read_csv(os.path.join(WS, S.ATTENDANCE_FILENAME), dtype=str, keep_default_na=False)
    if "no_dedup" not in mistakes:
        att = att.drop_duplicates()
    if "no_id_normalization" not in mistakes:
        att["employee_id"] = att["employee_id"].str.strip().str.upper()
    att["ci"] = pd.to_datetime(att["clock_in"], format="%Y-%m-%d %H:%M")
    att["co"] = pd.to_datetime(att["clock_out"].replace("", np.nan), format="%Y-%m-%d %H:%M")
    return roster, hol, att


def compute(mistakes):
    roster, hol, att = load(mistakes)
    if "include_contractors_interns" in mistakes:
        elig = roster.copy()
    else:
        elig = roster[roster["Employment Type"].isin(S.ELIGIBLE_EMPLOYMENT_TYPES)].copy()
    att = att[att["employee_id"].isin(elig["Employee ID"])].copy()

    anchor = "co" if "period_by_clock_out" in mistakes else "ci"
    att["pdate"] = att[anchor].dt.date
    if "no_period_filter" not in mistakes:
        keep = (att["pdate"] >= S.PERIOD_START) & (att["pdate"] <= S.PERIOD_END)
        if "count_out_of_period_invalid" in mistakes:
            keep |= att["co"].isna()
        att = att[keep.fillna(False)].copy()

    att["raw"] = (att["co"] - att["ci"]).dt.total_seconds() / 60
    limit = 16 * 60
    if "no_16h_rule" in mistakes:
        too_long = pd.Series(False, index=att.index)
    elif "invalid_at_16h_inclusive" in mistakes:
        too_long = att["raw"] >= limit
    else:
        too_long = att["raw"] > limit
    att["invalid"] = att["co"].isna() | (att["raw"] <= 0) | too_long
    valid = att[~att["invalid"]].copy()

    if "no_break" in mistakes:
        valid["paid_min"] = valid["raw"]
    elif "break_at_6h_inclusive" in mistakes:
        valid["paid_min"] = valid["raw"].where(valid["raw"] < 360, valid["raw"] - 30)
    else:
        valid["paid_min"] = valid["raw"].where(valid["raw"] <= 360, valid["raw"] - 30)
    if "floor_quarter_hour" in mistakes:
        valid["paid"] = np.floor(valid["paid_min"] / 15) * 0.25
    else:
        valid["paid"] = (valid["paid_min"] / 15).round() * 0.25

    dt_anchor = "co" if "daytype_by_clock_out" in mistakes else "ci"
    valid["ddate"] = valid[dt_anchor].dt.date

    def kind(d):
        is_hol, is_we = d in hol, d.weekday() >= 5
        if "weekend_beats_holiday" in mistakes and is_we:
            return "weekend"
        if is_hol:
            return "weekend" if "holiday_as_weekend" in mistakes else "holiday"
        return "weekend" if is_we else "weekday"

    valid["kind"] = valid["ddate"].map(kind)

    rows = []
    for _, e in elig.sort_values("Employee ID").iterrows():
        eid = e["Employee ID"]
        v = valid[valid["employee_id"] == eid]
        if "per_shift_ot" in mistakes:
            wd = v[v["kind"] == "weekday"]["paid"]
        else:
            wd = v[v["kind"] == "weekday"].groupby("ddate")["paid"].sum()
        reg = float(np.minimum(wd, 8.0).sum())
        wot = float(np.maximum(wd - 8.0, 0).sum())
        we_series = v[v["kind"] == "weekend"].groupby("ddate")["paid"].sum()
        if "weekend_regular_first" in mistakes:
            reg += float(np.minimum(we_series, 8.0).sum())
            we = float(np.maximum(we_series - 8.0, 0).sum())
            we_mult = 1.5
        else:
            we = float(we_series.sum())
            we_mult = 2.0
        ho = float(v[v["kind"] == "holiday"]["paid"].sum())
        n_shifts = len(v)
        if "drop_zero_employees" in mistakes and n_shifts == 0:
            continue
        r = float(e["Hourly Rate"])
        rp = round(r * reg, 2)
        op = round(r * (1.5 * wot + we_mult * we + 2.5 * ho), 2)
        rows.append([eid, e["Name"], e["Department"], e["Employment Type"], r, n_shifts,
                     int(((att["employee_id"] == eid) & att["invalid"]).sum()),
                     reg, wot, we, ho, round(wot + we + ho, 2), rp, op, round(rp + op, 2)])
    emp = pd.DataFrame(rows, columns=S.EMPLOYEE_COLUMNS)
    thr = 30.0
    if "alert_threshold_inclusive" in mistakes:
        alerts = emp[emp["Total Overtime Hours"] >= thr]
    else:
        alerts = emp[emp["Total Overtime Hours"] > thr]
    alerts = alerts.sort_values(["Total Overtime Hours", "Employee ID"], ascending=[False, True])
    return emp.reset_index(drop=True), alerts[S.ALERT_COLUMNS].reset_index(drop=True)


def frame_diff(a, b):
    """Number of differing cells, or -1 when shapes / IDs differ."""
    if a.shape != b.shape or list(a.columns) != list(b.columns):
        return -1
    if list(a["Employee ID"]) != list(b["Employee ID"]):
        return -1
    n = 0
    for c in a.columns:
        if a[c].dtype.kind in "fi" and b[c].dtype.kind in "fi":
            n += int(((a[c].astype(float) - b[c].astype(float)).abs() > 1e-6).sum())
        else:
            n += int((a[c].astype(str) != b[c].astype(str)).sum())
    return n


def main():
    gt = pd.read_excel(GT, sheet_name=None)
    gt_emp, gt_alerts = gt[S.SHEET_EMPLOYEE], gt[S.SHEET_ALERTS]

    base_emp, base_alerts = compute(set())
    d_emp, d_alerts = frame_diff(base_emp, gt_emp), frame_diff(base_alerts, gt_alerts)
    print(f"faithful re-implementation vs ground truth: employee diff={d_emp}, alerts diff={d_alerts}")
    assert d_emp == 0 and d_alerts == 0, "independent implementation disagrees with reference_solution.py"

    failures = []
    print(f"\n{'mistake':<30} {'employee cells':>15} {'alert rows':>11}  description")
    for name, desc in MISTAKES.items():
        emp, alerts = compute({name})
        de = frame_diff(emp, gt_emp)
        da = "shape" if frame_diff(alerts, gt_alerts) != 0 else "same"
        changed = de != 0 or da != "same"
        print(f"{name:<30} {de:>15} {da:>11}  {desc}")
        if not changed:
            failures.append(name)

    if failures:
        print("\nTRAPS WITHOUT EFFECT:", failures)
        sys.exit(1)
    print(f"\nall {len(MISTAKES)} mistakes change the result - every planted trap is live")


if __name__ == "__main__":
    main()
