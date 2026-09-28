"""Local checker for the vendor-quote-evaluation task.

The agent must produce one ``Quotation_Evaluation_<CODE>.docx`` per vendor and
an ``award.txt``.  The ground-truth sheets are generated from the materials by
``groundtruth_workspace/derive_groundtruth.py``.

Comparison rules (text normalisation, formatting is deliberately not graded):

* Every ground-truth sheet must have a counterpart in the agent workspace.
* Body text: all non-empty paragraphs outside tables are concatenated and
  normalised (Unicode NFKC, lower case, every non-alphanumeric character
  removed).  The agent's text must equal the ground truth exactly, so the
  quotation and due-diligence blocks have to be copied verbatim and nothing
  may be added; how the text is split into paragraphs does not matter.
* Table: the first table must have the four header cells (normalised) and a
  data row in which the cost is compared numerically (currency symbols,
  thousands separators and spacing are ignored, tolerance 0.005), the
  criteria count as a pair of integers (``6/6``, ``6 of 6``), the decision by
  normalised text, and the reasons as an order-insensitive set of normalised
  phrases split on ``;``/``,``/new lines.
* ``award.txt`` must contain a single non-empty line naming the awarded vendor:
  the name from the quotation, the registered name from the due-diligence
  notes or the vendor code (optionally combined) are all accepted.

Every failure found is reported; the checker does not stop at the first one.
"""

from __future__ import annotations

import difflib
import glob
import json
import os
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Set, Tuple

from docx import Document

OUTPUT_PREFIX = "Quotation_Evaluation_"
AWARD_FILE = "award.txt"
RESULTS_FILE = "expected_results.json"
DECISION_AWARD = "Award"
COST_TOLERANCE = Decimal("0.005")


# --------------------------------------------------------------------------- #
# normalisation helpers
# --------------------------------------------------------------------------- #
def normalize_text(text: Optional[str]) -> str:
    """Lower-case NFKC text with every non-alphanumeric character removed."""
    text = unicodedata.normalize("NFKC", text or "")
    return re.sub(r"[\W_]+", "", text).lower()


def parse_amount(text: Optional[str]) -> Optional[Decimal]:
    cleaned = unicodedata.normalize("NFKC", text or "")
    cleaned = re.sub(r"(?i)\busd?\b|us\$|\$|,|\s", "", cleaned)
    try:
        return Decimal(cleaned) if re.fullmatch(r"-?\d+(?:\.\d+)?", cleaned) else None
    except InvalidOperation:  # pragma: no cover
        return None


def parse_ratio(text: Optional[str]) -> Optional[Tuple[int, int]]:
    match = re.search(r"(\d+)\s*(?:/|of|out of|:)\s*(\d+)", unicodedata.normalize("NFKC", text or ""))
    return (int(match.group(1)), int(match.group(2))) if match else None


def reason_set(text: Optional[str]) -> Set[str]:
    items = [normalize_text(part) for part in re.split(r"[;,\n]+", text or "")]
    items = [item for item in items if item]
    if items == ["none"]:
        return set()
    return set(items)


def body_signature(doc) -> str:
    return "".join(normalize_text(p.text) for p in doc.paragraphs if p.text.strip())


def table_rows(doc, index: int = 0) -> Optional[List[List[str]]]:
    if len(doc.tables) <= index:
        return None
    rows = [[cell.text for cell in row.cells] for row in doc.tables[index].rows]
    while rows and all(not cell.strip() for cell in rows[-1]):
        rows.pop()
    return rows


def diff_summary(expected: str, actual: str, context: int = 40) -> str:
    matcher = difflib.SequenceMatcher(None, expected, actual, autojunk=False)
    similarity = matcher.ratio() * 100
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        exp = expected[max(0, i1 - context):i2 + context]
        act = actual[max(0, j1 - context):j2 + context]
        return (f"similarity {similarity:.1f}%, first difference ({tag}) near position {i1}: "
                f"expected ...{exp}... got ...{act}...")
    return f"similarity {similarity:.1f}%"


# --------------------------------------------------------------------------- #
# comparisons
# --------------------------------------------------------------------------- #
def compare_body(gt_doc, agent_doc) -> List[str]:
    expected = body_signature(gt_doc)
    actual = body_signature(agent_doc)
    if expected == actual:
        return []
    return ["body text differs from the expected sheet: " + diff_summary(expected, actual)]


def compare_table(gt_doc, agent_doc) -> List[str]:
    gt_rows = table_rows(gt_doc)
    agent_rows = table_rows(agent_doc)
    if not agent_rows:
        return ["no table found (the Evaluation Conclusion table is missing)"]
    if len(agent_rows) < 2:
        return ["the Evaluation Conclusion table needs a header row and a data row"]
    ncol = len(gt_rows[0])
    if len(agent_rows[0]) < ncol:
        return [f"the Evaluation Conclusion table needs {ncol} columns, found {len(agent_rows[0])}"]

    problems = []
    for j in range(ncol):
        if normalize_text(agent_rows[0][j]) != normalize_text(gt_rows[0][j]):
            problems.append(f"table header cell {j + 1}: expected {gt_rows[0][j]!r}, got {agent_rows[0][j]!r}")
    if problems:
        return problems

    gt_data, agent_data = gt_rows[1], agent_rows[1]

    expected_cost = parse_amount(gt_data[0])
    actual_cost = parse_amount(agent_data[0])
    if actual_cost is None:
        problems.append(f"Total Evaluated Cost: could not read a number from {agent_data[0]!r}")
    elif abs(actual_cost - expected_cost) > COST_TOLERANCE:
        problems.append(f"Total Evaluated Cost: expected {gt_data[0]}, got {agent_data[0]!r}")

    expected_ratio = parse_ratio(gt_data[1])
    actual_ratio = parse_ratio(agent_data[1])
    if actual_ratio != expected_ratio:
        problems.append(f"Mandatory Criteria Met: expected {gt_data[1]}, got {agent_data[1]!r}")

    if normalize_text(agent_data[2]) != normalize_text(gt_data[2]):
        problems.append(f"Decision: expected {gt_data[2]!r}, got {agent_data[2]!r}")

    if reason_set(agent_data[3]) != reason_set(gt_data[3]):
        problems.append(f"Disqualification Reasons: expected {gt_data[3]!r}, got {agent_data[3]!r}")
    return problems


def _decision_of(doc) -> str:
    rows = table_rows(doc)
    return rows[1][2] if rows and len(rows) > 1 and len(rows[1]) > 2 else ""


def award_aliases(groundtruth_workspace: str, gt_files: List[str]) -> Tuple[str, Set[str]]:
    """Expected award name plus every normalised spelling that is accepted."""
    with open(os.path.join(groundtruth_workspace, AWARD_FILE), encoding="utf-8-sig") as fh:
        expected_name = fh.read().strip()

    code, registered = None, None
    results_path = os.path.join(groundtruth_workspace, RESULTS_FILE)
    if os.path.exists(results_path):
        with open(results_path, encoding="utf-8") as fh:
            payload = json.load(fh)
        code = payload.get("award", {}).get("code")
        for vendor in payload.get("vendors", []):
            if vendor.get("code") == code:
                registered = vendor.get("registered_name")
    if code is None:
        for path in gt_files:
            if normalize_text(_decision_of(Document(path))) == normalize_text(DECISION_AWARD):
                code = os.path.basename(path)[len(OUTPUT_PREFIX):-len(".docx")]

    names = {expected_name}
    if registered:
        names.add(registered)
    aliases = {normalize_text(n) for n in names}
    if code:
        aliases.add(normalize_text(code))
        for name in names:
            aliases.add(normalize_text(f"{name} {code}"))
            aliases.add(normalize_text(f"{code} {name}"))
    return expected_name, aliases


def check_award(agent_workspace: str, groundtruth_workspace: str, gt_files: List[str]) -> List[str]:
    path = os.path.join(agent_workspace, AWARD_FILE)
    if not os.path.exists(path):
        return [f"missing {AWARD_FILE}"]
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        content = fh.read()
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return [f"{AWARD_FILE} is empty"]
    if len(lines) > 1:
        return [f"{AWARD_FILE} must contain only the awarded vendor's name, found {len(lines)} lines: {lines}"]
    expected_name, aliases = award_aliases(groundtruth_workspace, gt_files)
    if normalize_text(lines[0]) not in aliases:
        return [f"{AWARD_FILE}: expected {expected_name!r}, found {lines[0]!r}"]
    return []


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #
def check_local(agent_workspace: str, groundtruth_workspace: str) -> Tuple[bool, str]:
    gt_files = sorted(glob.glob(os.path.join(groundtruth_workspace, f"{OUTPUT_PREFIX}*.docx")))
    if not gt_files:
        return False, f"no ground-truth sheets found in {groundtruth_workspace}"

    problems: List[str] = []
    for gt_path in gt_files:
        name = os.path.basename(gt_path)
        agent_path = os.path.join(agent_workspace, name)
        print(f"Checking {name}")
        if not os.path.exists(agent_path):
            problems.append(f"{name}: missing in the agent workspace")
            print("  missing")
            continue
        try:
            gt_doc = Document(gt_path)
            agent_doc = Document(agent_path)
        except Exception as exc:  # corrupt or not a docx
            problems.append(f"{name}: cannot be opened as a Word document ({exc})")
            print("  cannot open")
            continue
        issues = compare_body(gt_doc, agent_doc) + compare_table(gt_doc, agent_doc)
        for issue in issues:
            print(f"  {issue}")
        if not issues:
            print("  ok")
        problems.extend(f"{name}: {issue}" for issue in issues)

    award_issues = check_award(agent_workspace, groundtruth_workspace, gt_files)
    for issue in award_issues:
        print(f"  {issue}")
    problems.extend(award_issues)

    if problems:
        return False, f"{len(problems)} problem(s): " + " | ".join(problems)
    return True, f"all {len(gt_files)} sheets and {AWARD_FILE} match"
