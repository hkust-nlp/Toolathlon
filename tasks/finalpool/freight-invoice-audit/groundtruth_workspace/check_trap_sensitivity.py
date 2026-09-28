#!/usr/bin/env python3
"""Quality gate for the generated data: every planted trap must matter.

This script is an *independent* pandas/float re-implementation of
``audit_rules.md`` with switchable "plausible mistakes".  It asserts that

  1. the faithful implementation reproduces the ground-truth workbook, and
  2. every single mistake changes at least one cell of the Shipment Audit,
     Disputes or Service Summary sheet, i.e. the evaluator can actually tell
     a careless agent from a careful one.

Run after (re)generating data:
    python generate_data.py && python reference_solution.py && python check_trap_sensitivity.py
"""

import datetime as dt
import math
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audit_schema as S  # noqa: E402

WS = os.path.join(os.path.dirname(HERE), "initial_workspace")
GT = os.path.join(HERE, S.OUTPUT_FILENAME)

MISTAKES = {
    "no_tracking_normalization": "invoice tracking numbers are not trimmed / upper-cased",
    "no_dedup": "repeated tracking numbers are audited again instead of flagged as duplicates",
    "dispute_first_duplicate": "the first occurrence is treated as the duplicate, not the later one",
    "drop_unknown_lines": "lines whose tracking number is not in the manifest are left out",
    "postal_as_integer": "postal codes read as numbers (leading zeros lost)",
    "use_invoice_service": "expected charge computed with the service printed on the invoice",
    "fuel_by_invoice_date": "fuel-surcharge week taken from the invoice ship date",
    "dim_never": "dimensional weight ignored",
    "dim_always": "dimensional weight applied regardless of the 1,728 in^3 threshold",
    "dim_at_1728_inclusive": "dimensional weight applied at exactly 1,728 in^3",
    "weight_round_nearest": "actual weight rounded to the nearest pound instead of up",
    "no_discount": "list price billed without the contract discount",
    "fuel_on_list_price": "fuel surcharge applied to the undiscounted list price",
    "fuel_includes_declared": "fuel surcharge applied to the declared value surcharge as well",
    "residential_from_invoice": "residential surcharge taken from the invoice instead of the manifest",
    "declared_threshold_inclusive": "declared value surcharge charged at exactly 100.00",
    "declared_no_fraction": "declared value surcharge per full 100.00 only (floor instead of ceil)",
    "dispute_threshold_exclusive": "disputes only when the variance exceeds 1.00 (> instead of >=)",
    "dispute_underbilled_too": "underbilled lines disputed as well",
    "issues_root_cause_only": "only the first differing component listed in Issues",
    "summary_by_invoice_service": "summary grouped by the invoice service instead of the audit-sheet service",
    "unbilled_includes_out_of_period": "August/October manifest rows counted as unbilled",
    "variance_sign_flipped": "variance computed as expected minus billed",
}


def load(mistakes):
    manifest = pd.read_csv(os.path.join(WS, S.MANIFEST_FILENAME), dtype=str, keep_default_na=False)
    invoice = pd.read_csv(os.path.join(WS, S.INVOICE_FILENAME), dtype=str, keep_default_na=False)
    rates_df = pd.read_excel(os.path.join(WS, S.RATE_CARD_FILENAME), sheet_name=S.SHEET_RATES)
    zones_df = pd.read_excel(os.path.join(WS, S.RATE_CARD_FILENAME), sheet_name=S.SHEET_ZONES, dtype=str)
    fuel_df = pd.read_excel(os.path.join(WS, S.RATE_CARD_FILENAME), sheet_name=S.SHEET_FUEL)
    terms_df = pd.read_excel(os.path.join(WS, S.RATE_CARD_FILENAME), sheet_name=S.SHEET_TERMS)

    manifest["tracking"] = manifest["tracking_number"].str.strip().str.upper()
    if "no_tracking_normalization" in mistakes:
        invoice["tracking"] = invoice["tracking_number"]
    else:
        invoice["tracking"] = invoice["tracking_number"].str.strip().str.upper()
    manifest["ship_date"] = pd.to_datetime(manifest["ship_date"]).dt.date
    invoice["ship_date"] = pd.to_datetime(invoice["ship_date"]).dt.date
    for c in ("actual_weight_lb", "declared_value_usd"):
        manifest[c] = manifest[c].astype(float)
    for c in ("length_in", "width_in", "height_in"):
        manifest[c] = manifest[c].astype(int)
    invoice["invoice_line"] = invoice["invoice_line"].astype(int)
    invoice["zone"] = invoice["zone"].astype(int)
    invoice["billed_weight_lb"] = invoice["billed_weight_lb"].astype(int)
    for c in ("base_charge", "residential_surcharge", "declared_value_surcharge", "fuel_surcharge", "total_charge"):
        invoice[c] = invoice[c].astype(float)
    if "postal_as_integer" in mistakes:
        manifest["dest_postal_code"] = manifest["dest_postal_code"].str.split("-").str[0].astype(int).astype(str)

    rates = {}
    for _, r in rates_df.iterrows():
        rates[(r["Service"], int(r["Weight (lb)"]))] = {z: float(r[f"Zone {z}"]) for z in S.ZONES}
    zones = [(str(r["Prefix From"]).zfill(3), str(r["Prefix To"]).zfill(3), int(r["Zone"])) for _, r in zones_df.iterrows()]
    fuel = {pd.Timestamp(r["Week Starting (Monday)"]).date(): float(r["Fuel Surcharge %"]) for _, r in fuel_df.iterrows()}
    terms = dict(zip(terms_df["Term"], terms_df["Value"]))
    return manifest, invoice, rates, zones, fuel, terms


def r2(x):
    """Round half up to cents on a float that is within 1e-6 of a cent grid or a true value."""
    return math.floor(x * 100 + 0.5 + 1e-9) / 100


def compute(mistakes):
    manifest, invoice, rates, zones, fuel, terms = load(mistakes)
    discount = {s: float(terms[S.TERM_DISCOUNT[s]]) for s in S.SERVICES}
    residential_fee = float(terms[S.TERM_RESIDENTIAL])
    declared_threshold = float(terms[S.TERM_DECLARED_THRESHOLD])
    declared_rate = float(terms[S.TERM_DECLARED_RATE])
    dim_divisor = int(terms[S.TERM_DIM_DIVISOR])
    dim_volume = int(terms[S.TERM_DIM_VOLUME])
    dispute_threshold = float(terms[S.TERM_DISPUTE_THRESHOLD])

    def zone_of(postal):
        prefix = str(postal)[:3]
        for lo, hi, z in zones:
            if lo <= prefix <= hi:
                return z
        raise ValueError(postal)

    def billable(m):
        w = m["actual_weight_lb"]
        actual = max(1, int(round(w)) if "weight_round_nearest" in mistakes else math.ceil(w - 1e-9))
        vol = m["length_in"] * m["width_in"] * m["height_in"]
        if "dim_never" in mistakes:
            applies = False
        elif "dim_always" in mistakes:
            applies = True
        elif "dim_at_1728_inclusive" in mistakes:
            applies = vol >= dim_volume
        else:
            applies = vol > dim_volume
        dim = math.ceil(vol / dim_divisor - 1e-9) if applies else 0
        return max(actual, dim)

    def expected(m, inv):
        service = inv["service"] if "use_invoice_service" in mistakes else m["service"]
        zone = zone_of(m["dest_postal_code"])
        weight = billable(m)
        list_price = rates[(service, weight)][zone]
        base = list_price if "no_discount" in mistakes else r2(list_price * (100 - discount[service]) / 100)
        if "residential_from_invoice" in mistakes:
            res = inv["residential_surcharge"]
        else:
            res = residential_fee if m["residential"] == "Y" else 0.0
        dv = m["declared_value_usd"]
        charge_declared = dv >= declared_threshold if "declared_threshold_inclusive" in mistakes else dv > declared_threshold
        if charge_declared:
            units = math.floor(dv / 100 + 1e-9) if "declared_no_fraction" in mistakes else math.ceil(dv / 100 - 1e-9)
            decl = r2(units * declared_rate)
        else:
            decl = 0.0
        date = inv["ship_date"] if "fuel_by_invoice_date" in mistakes else m["ship_date"]
        pct = fuel[date - dt.timedelta(days=date.weekday())]
        fuel_base = (list_price if "fuel_on_list_price" in mistakes else base) + res
        if "fuel_includes_declared" in mistakes:
            fuel_base += decl
        fuel_amt = r2(fuel_base * pct / 100)
        return service, zone, weight, base, res, decl, fuel_amt, r2(base + res + decl + fuel_amt)

    by_tracking = manifest.set_index("tracking")
    invoice = invoice.sort_values("invoice_line")
    counts = invoice["tracking"].value_counts()
    if "dispute_first_duplicate" in mistakes:
        dup_mask = invoice.duplicated("tracking", keep="last")
    else:
        dup_mask = invoice.duplicated("tracking", keep="first")
    if "no_dedup" in mistakes:
        dup_mask[:] = False

    rows = []
    for (_, inv), is_dup in zip(invoice.iterrows(), dup_mask):
        t = inv["tracking"]
        known = t in by_tracking.index
        billed = inv["total_charge"]
        if is_dup:
            service = by_tracking.loc[t, "service"] if known else inv["service"]
            rows.append([inv["invoice_line"], t, service, None, None, None, billed, billed, S.STATUS_DUPLICATE, S.STATUS_DUPLICATE])
            continue
        if not known:
            if "drop_unknown_lines" in mistakes:
                continue
            rows.append([inv["invoice_line"], t, inv["service"], None, None, None, billed, billed, S.STATUS_UNKNOWN, S.STATUS_UNKNOWN])
            continue
        m = by_tracking.loc[t]
        service, zone, weight, base, res, decl, fuel_amt, total = expected(m, inv)
        variance = r2(billed - total)
        if "variance_sign_flipped" in mistakes:
            variance = -variance
        codes = []
        for code, differs in (
            (S.ISSUE_SERVICE, inv["service"] != service),
            (S.ISSUE_ZONE, inv["zone"] != zone),
            (S.ISSUE_WEIGHT, inv["billed_weight_lb"] != weight),
            (S.ISSUE_BASE, abs(inv["base_charge"] - base) > 1e-6),
            (S.ISSUE_RESIDENTIAL, abs(inv["residential_surcharge"] - res) > 1e-6),
            (S.ISSUE_DECLARED, abs(inv["declared_value_surcharge"] - decl) > 1e-6),
            (S.ISSUE_FUEL, abs(inv["fuel_surcharge"] - fuel_amt) > 1e-6),
        ):
            if differs:
                codes.append(code)
        if "issues_root_cause_only" in mistakes:
            codes = codes[:1]
        status = S.STATUS_OK if abs(variance) < 1e-9 else (S.STATUS_OVER if variance > 0 else S.STATUS_UNDER)
        group_service = inv["service"] if "summary_by_invoice_service" in mistakes else service
        rows.append([inv["invoice_line"], t, group_service, zone, weight, total, billed, variance, status,
                     S.ISSUE_SEPARATOR.join(codes) if codes else S.NO_ISSUES])
    audit = pd.DataFrame(rows, columns=S.AUDIT_COLUMNS).sort_values("Invoice Line").reset_index(drop=True)

    def disputed_amount(r):
        if r["Status"] in (S.STATUS_DUPLICATE, S.STATUS_UNKNOWN):
            return r["Billed Total"]
        if r["Status"] == S.STATUS_OVER:
            over = r["Variance"] > dispute_threshold + 1e-9 if "dispute_threshold_exclusive" in mistakes \
                else r["Variance"] >= dispute_threshold - 1e-9
            return r["Variance"] if over else None
        if r["Status"] == S.STATUS_UNDER and "dispute_underbilled_too" in mistakes:
            return -r["Variance"]
        return None

    audit["_disp"] = audit.apply(disputed_amount, axis=1)
    disputes = audit[audit["_disp"].notna()].copy()
    disputes["Disputed Amount"] = disputes["_disp"].astype(float)
    disputes = disputes.sort_values(["Disputed Amount", "Invoice Line"], ascending=[False, True])
    disputes = disputes[S.DISPUTE_COLUMNS].reset_index(drop=True)

    billed_trackings = set(invoice["tracking"])
    unbilled_mask = ~manifest["tracking"].isin(billed_trackings)
    if "unbilled_includes_out_of_period" not in mistakes:
        unbilled_mask &= (manifest["ship_date"] >= S.PERIOD_START) & (manifest["ship_date"] <= S.PERIOD_END)
    unbilled = manifest[unbilled_mask].groupby("service").size()

    srows = []
    for service in sorted(audit["Service"].unique()):
        g = audit[audit["Service"] == service]
        a = g[g["Status"].isin(S.AUDITED_STATUSES)]
        d = disputes[disputes["Service"] == service]
        srows.append([service, len(g), len(a), r2(g["Billed Total"].sum()), r2(a["Expected Total"].sum()),
                      r2(a.loc[a["Status"] == S.STATUS_OVER, "Variance"].sum()),
                      r2(-a.loc[a["Status"] == S.STATUS_UNDER, "Variance"].sum()),
                      len(d), r2(d["Disputed Amount"].sum()), int(unbilled.get(service, 0))])
    summary = pd.DataFrame(srows, columns=S.SUMMARY_COLUMNS)
    return audit.drop(columns=["_disp"]), summary, disputes


def _blank(value):
    return value is None or value == "" or (isinstance(value, float) and np.isnan(value))


def frame_diff(a, b):
    """Number of differing cells, or -1 when shapes differ."""
    if a.shape != b.shape or list(a.columns) != list(b.columns):
        return -1
    n = 0
    for c in a.columns:
        x, y = a[c].tolist(), b[c].tolist()
        for u, v in zip(x, y):
            u_blank = _blank(u)
            v_blank = _blank(v)
            if u_blank or v_blank:
                n += int(u_blank != v_blank)
            elif isinstance(u, (int, float, np.integer, np.floating)) and isinstance(v, (int, float, np.integer, np.floating)):
                n += int(abs(float(u) - float(v)) > 1e-6)
            else:
                n += int(str(u).strip() != str(v).strip())
    return n


def main():
    # keep_default_na=False: pandas would otherwise read the Issues value "None" as NaN
    gt = pd.read_excel(GT, sheet_name=None, keep_default_na=False)
    gt_audit, gt_summary, gt_disputes = gt[S.SHEET_AUDIT], gt[S.SHEET_SUMMARY], gt[S.SHEET_DISPUTES]

    base = compute(set())
    diffs = [frame_diff(x, y) for x, y in zip(base, (gt_audit, gt_summary, gt_disputes))]
    print(f"faithful re-implementation vs ground truth: audit diff={diffs[0]}, summary diff={diffs[1]}, disputes diff={diffs[2]}")
    assert diffs == [0, 0, 0], "independent implementation disagrees with reference_solution.py"

    failures = []
    print(f"\n{'mistake':<34} {'audit':>7} {'summary':>8} {'disputes':>9}  description")
    for name, desc in MISTAKES.items():
        try:
            audit, summary, disputes = compute({name})
        except ValueError as exc:
            # e.g. postal codes read as integers hit a prefix that no zone covers
            print(f"{name:<34} {'crash':>7} {'':>8} {'':>9}  {desc} (raises: {exc})")
            continue
        da, ds, dd = frame_diff(audit, gt_audit), frame_diff(summary, gt_summary), frame_diff(disputes, gt_disputes)
        print(f"{name:<34} {da:>7} {ds:>8} {dd:>9}  {desc}")
        if da == 0 and ds == 0 and dd == 0:
            failures.append(name)

    if failures:
        print("\nTRAPS WITHOUT EFFECT:", failures)
        sys.exit(1)
    print(f"\nall {len(MISTAKES)} mistakes change the result - every planted trap is live")


if __name__ == "__main__":
    main()
