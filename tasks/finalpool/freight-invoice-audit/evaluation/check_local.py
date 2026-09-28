"""Local checker for the freight-invoice-audit task.

Compares the agent's ``freight_audit_2025-09.xlsx`` with the ground-truth
workbook produced by ``groundtruth_workspace/reference_solution.py``.

Rules:
  * the three report sheets must exist (extra sheets are ignored);
  * every sheet's header row must match the template exactly (whitespace
    normalised) and in the same order;
  * the number of data rows must match, and rows are compared in order (the
    rules fix the sort order of every sheet);
  * text cells are compared after whitespace normalisation; in the Issues
    column the spacing around ``;`` is normalised as well and an empty cell is
    accepted where the ground truth says ``None`` (pandas turns that string
    into NaN when it reads a workbook);
  * count / whole-number columns (Invoice Line, Expected Zone, Expected Billed
    Weight, Invoice Lines, Audited Shipments, Disputed Lines, Unbilled
    Shipments) must match exactly;
  * every other numeric column is compared with an absolute tolerance of
    0.005, i.e. the agent's value must round to the same two decimals;
  * cells that are empty in the ground truth (expected values of Duplicate /
    Not in manifest lines) must be empty in the agent's workbook too;
  * the workbook is opened with ``data_only=True`` so formula cells without a
    cached value read as empty and are reported as such.
"""

import os
import re

from openpyxl import load_workbook

OUTPUT_FILENAME = "freight_audit_2025-09.xlsx"
NUMERIC_TOLERANCE = 0.005 + 1e-9
INTEGER_COLUMNS = {
    "Invoice Line", "Expected Zone", "Expected Billed Weight",
    "Invoice Lines", "Audited Shipments", "Disputed Lines", "Unbilled Shipments",
}
SEPARATOR_COLUMNS = {"Issues"}
NO_ISSUES_TEXT = "None"      # in the Issues column an empty cell is accepted as "None"


def _norm_str(value, column=None):
    text = re.sub(r"\s+", " ", str(value).replace(" ", " ")).strip()
    if column in SEPARATOR_COLUMNS:
        text = re.sub(r"\s*;\s*", "; ", text)
    return text


def _is_blank(value):
    return value is None or (isinstance(value, str) and not value.strip())


def _as_number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "").replace("$", "")
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _load_sheets(path):
    wb = load_workbook(path, data_only=True)
    sheets = {}
    for ws in wb.worksheets:
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
        while rows and all(_is_blank(c) for c in rows[-1]):
            rows.pop()
        sheets[ws.title] = rows
    wb.close()
    return sheets


def _compare_cell(column, agent_value, gt_value):
    if _is_blank(gt_value):
        if _is_blank(agent_value):
            return True, ""
        return False, f"expected an empty cell, got {agent_value!r}"

    if isinstance(gt_value, (int, float)) and not isinstance(gt_value, bool):
        if agent_value is None:
            return False, ("cell is empty (note: formulas are not evaluated by the grader, "
                           "write literal values)")
        number = _as_number(agent_value)
        if number is None:
            return False, f"expected a number, got {agent_value!r}"
        if column in INTEGER_COLUMNS:
            if abs(number - float(gt_value)) > 1e-9:
                return False, f"expected {gt_value}, got {agent_value}"
        elif abs(number - float(gt_value)) > NUMERIC_TOLERANCE:
            return False, f"expected {float(gt_value):.2f}, got {agent_value}"
        return True, ""

    if _is_blank(agent_value):
        if column in SEPARATOR_COLUMNS and _norm_str(gt_value) == NO_ISSUES_TEXT:
            return True, ""          # an empty Issues cell is accepted for "None"
        return False, f"expected {gt_value!r}, got an empty cell"
    if _norm_str(agent_value, column) != _norm_str(gt_value, column):
        return False, f"expected {gt_value!r}, got {agent_value!r}"
    return True, ""


def _compare_sheet(name, agent_rows, gt_rows):
    gt_header = [_norm_str(h) for h in gt_rows[0]]
    if not agent_rows:
        return False, f"sheet '{name}' is empty; expected header {gt_header}"

    agent_header = ["" if _is_blank(h) else _norm_str(h) for h in agent_rows[0]]
    while agent_header and agent_header[-1] == "":
        agent_header.pop()
    if agent_header != gt_header:
        return False, f"sheet '{name}': header mismatch. Expected {gt_header}, got {agent_header}"

    ncol = len(gt_header)
    agent_body = agent_rows[1:]
    gt_body = gt_rows[1:]
    if len(agent_body) != len(gt_body):
        return False, f"sheet '{name}': expected {len(gt_body)} data rows, found {len(agent_body)}"

    for idx, (a_row, g_row) in enumerate(zip(agent_body, gt_body), start=2):
        a_row = list(a_row[:ncol]) + [None] * max(0, ncol - len(a_row))
        g_row = list(g_row[:ncol]) + [None] * max(0, ncol - len(g_row))
        for j, column in enumerate(gt_header):
            ok, why = _compare_cell(column, a_row[j], g_row[j])
            if not ok:
                return False, f"sheet '{name}', row {idx}, column '{column}': {why}"
    return True, ""


def check_local(agent_workspace: str, groundtruth_workspace: str):
    agent_file = os.path.join(agent_workspace, OUTPUT_FILENAME)
    gt_file = os.path.join(groundtruth_workspace, OUTPUT_FILENAME)

    if not os.path.exists(gt_file):
        return False, f"ground-truth file is missing: {gt_file}"
    if not os.path.exists(agent_file):
        return False, f"{OUTPUT_FILENAME} was not found in the agent workspace"

    try:
        agent_sheets = _load_sheets(agent_file)
    except Exception as exc:  # corrupted / not an xlsx
        return False, f"cannot open {OUTPUT_FILENAME}: {exc}"
    gt_sheets = _load_sheets(gt_file)

    missing = [s for s in gt_sheets if s not in agent_sheets]
    if missing:
        return False, f"missing sheet(s) {missing}; workbook contains {list(agent_sheets)}"

    for name, gt_rows in gt_sheets.items():
        ok, message = _compare_sheet(name, agent_sheets[name], gt_rows)
        if not ok:
            return False, message
        print(f"sheet '{name}': {len(gt_rows) - 1} data rows match")

    return True, "all sheets match the ground truth"
