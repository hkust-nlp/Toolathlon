# vendor-quote-evaluation

Task family: **hand-written document materials, script-derived ground truth,
text-normalised comparison** (the same family as `interview-report`).

## What the agent has to do

The agent is the procurement officer of the Riverside office expansion. It
receives the quotation letters collected for RFQ-2025-031 (150 ergonomic task
chairs) and the supplier due-diligence notes, must evaluate every vendor
against a written rule set, produce one Word evaluation sheet per vendor and
name the awarded vendor in `award.txt`. Each sheet repeats the vendor's
quotation and due-diligence entry verbatim and ends with a computed conclusion
table (Total Evaluated Cost, criteria met, decision, disqualification reasons).

## Materials (`initial_workspace/`)

| File | Content |
|------|---------|
| `Vendor_Quotations.docx` | 10 hand-written quotation letters from 9 vendors, one multi-line entry each under a `Quotation N` label. Ashford Seating & Furniture appears twice: `ASF-2509-01` (5 Sep) and the superseding `ASF-2509-01-R2` (19 Sep). |
| `Supplier_Due_Diligence_Notes.docx` | 9 entries (`Supplier N`) with registered name, ISO 9001 certificate status, reference checks, delivery history, financial standing and notes. Sorted differently from the quotations; the join key is the three-letter vendor code. |
| `Evaluation_Rules.md` | Requirement constants (quantity 150, award date 15 Oct 2025, budget USD 60,000.00, lead time <= 45 days, mechanism warranty >= 5 years, ISO 9001 + BIFMA X5.1, EUR 1 = USD 1.08), the latest-revision rule, the Total Evaluated Cost formula, the six mandatory criteria with their exact reason phrases, and the award/tie-break rules. |
| `Format.md` | Layout of `Quotation_Evaluation_<CODE>.docx` (heading, code, name, verbatim quotation block, verbatim due-diligence block, 2x4 conclusion table) and of `award.txt`. |

The prose was written by hand; `groundtruth_workspace/author_materials.py`
only typesets it into the two `.docx` files so the text can be edited in one
place and regenerated. `initial_workspace/` is copied into the agent
workspace as-is (no `preprocess/`).

## Expected result

| Code | Vendor | Total Evaluated Cost (USD) | Met | Decision | Reasons |
|------|--------|---------------------------:|-----|----------|---------|
| ASF | Ashford Seating & Furniture | 44,568.00 | 6/6 | **Award** | None |
| NPS | Northpeak Office Supply | 46,515.00 | 6/6 | Compliant - Not Selected | None |
| HMP | Harbor & Main Procurement | 46,600.00 | 6/6 | Compliant - Not Selected | None |
| KWE | Kestrel Workspace Europe GmbH | 46,737.00 | 6/6 | Compliant - Not Selected | None |
| BVL | Blue Valley Logistics & Furnishing | 44,250.00 | 4/6 | Disqualified | Lead time exceeds 45 days; Warranty below 5 years |
| GRD | Granite Ridge Distribution | 44,400.00 | 5/6 | Disqualified | Missing or expired certification |
| SOL | Solstice Contract Interiors | 42,368.00 | 5/6 | Disqualified | Quote expires before award date |
| TRV | Trevane Commercial Furniture | 35,986.40 | 5/6 | Disqualified | Partial quantity |
| PRM | Premier Ergonomics Inc. | 60,610.00 | 5/6 | Disqualified | Exceeds budget ceiling |

`award.txt` = `Ashford Seating & Furniture`. Nine sheets are expected; the
superseded ASF revision gets none.

## Traps planted in the materials

Every trap is resolved explicitly by `Evaluation_Rules.md`, and each one
hands the award to a different wrong vendor or corrupts a sheet:

* **Superseded revision** - using ASF's first letter (60-day lead time)
  disqualifies the true winner and awards NPS.
* **Currency** - KWE quotes in EUR; unconverted it looks cheapest (43,275.00).
* **Discount threshold** - HMP's 10 % applies only from 200 units (order is
  150); ASF's 4 % threshold is exactly 150 ("or more" is inclusive); TRV's 3 %
  applies to its 120 units.
* **Freight included** - GRD and ASF R2 include freight in the unit price;
  discounts never apply to freight.
* **Due diligence** - GRD is the cheapest compliant-looking vendor but its
  ISO 9001 certificate expired in 2024; HMP's certificate is valid until
  20 Oct 2025, i.e. still valid on the award date.
* **Validity as a duration** - SOL is cheapest overall but "valid for 30 days
  from the quotation date" (8 Sep) expires before 15 Oct.
* **Partial quantity** - TRV quotes 120 units; its total is computed on 120
  and it is disqualified.
* **Boundary values** - GRD's lead time is exactly 45 days (compliant); PRM
  lands at 60,610.00, just above the ceiling, only if its discount is applied
  correctly.
* **Two failures** - BVL fails lead time and warranty; both phrases must
  appear.
* **Vendor name source** - the sheet must use the quotation's `Vendor:` name,
  not the registered name from the due-diligence notes.
* Distractor numbers in prose (assembly at USD 12.00 per chair, "if the order
  were increased to 200 chairs") must be ignored.

## Ground-truth derivation (`groundtruth_workspace/`)

```bash
cd tasks/finalpool/vendor-quote-evaluation/groundtruth_workspace
python author_materials.py         # (only after editing the prose) rewrites ../initial_workspace/*.docx
python derive_groundtruth.py       # parses the materials, writes 9 sheets, award.txt, expected_results.json
python check_trap_sensitivity.py   # re-runs the derivation with 11 deliberate mistakes; each must change the result
python ../evaluation/test_check_local.py
```

`derive_groundtruth.py` reads only `initial_workspace/`: it parses the rule
constants and reason phrases from `Evaluation_Rules.md`, extracts the block
after every `Quotation N` / `Supplier N` marker, parses the labelled lines
(quantity, unit price and currency, discount clause and threshold, freight or
"included", lead time, mechanism warranty in years or months, BIFMA, validity
as a date or a duration, ISO 9001 validity) and applies the rules with
`Decimal` arithmetic. All amounts were chosen so that every intermediate value
is an exact number of cents (unit price x quantity, percentage discounts, and
the EUR total 43,275.00 whose cent value is divisible by 25 so that x 1.08 is
exact). `expected_results.json` records every parsed field, the totals, the
per-criterion verdicts and the ranking.

## Evaluation (`evaluation/`)

`check_local.py` is standalone (python-docx only) and grades text, not
formatting:

* every ground-truth `Quotation_Evaluation_<CODE>.docx` must exist in the
  agent workspace; extra files are ignored;
* **body text**: all non-empty paragraphs outside tables are concatenated and
  normalised (NFKC, lower case, all non-alphanumeric characters removed); the
  result must equal the ground truth exactly. Paragraph splitting, fonts,
  bold, alignment and shading are irrelevant, but the two source blocks must
  be copied verbatim and nothing may be added (no labels, notes or
  signatures);
* **table**: the first table needs the four header cells (normalised) and a
  data row whose cost is compared numerically (currency words/symbols,
  thousands separators and spaces ignored, tolerance 0.005), criteria as a
  pair of integers (`6/6`, `6 of 6`), decision by normalised text, reasons as
  an order-insensitive set split on `;`, `,` or new lines;
* **award.txt**: exactly one non-empty line; the quotation name, the
  registered name, the vendor code, or name plus code are accepted.

All problems are reported, not just the first one. `test_check_local.py`
runs 26 positive/negative cases (formatting-free rewrite with `USD` prefixes,
`6 of 6`, lower-case decisions and reordered reasons passes; the superseded
revision, wrong totals for KWE/HMP/TRV, a missing reason, an ignored
due-diligence finding, an extra paragraph, a pasted `Quotation 10` label, the
registered name as vendor name, a missing table and every `award.txt`
mistake fail).

## Verification status

2026-09-23, authoring machine (Windows, `uv run --no-project --with
python-docx`): the derivation reproduces the hand-computed table above, all 11
trap mistakes are live, the evaluator passes the ground truth through the
framework's module invocation
(`python -m tasks.finalpool.vendor-quote-evaluation.evaluation.main`) and all
26 self-test cases behave as expected. No real agent run yet.

## Tools used

* **word** MCP (office-word-mcp-server) to read the two `.docx` materials and
  write the evaluation sheets (heading, paragraphs, table, shading)
* **filesystem** for the Markdown rules/format files and `award.txt`
