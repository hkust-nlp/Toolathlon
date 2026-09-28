# Freight Invoice Audit Task

Task family: **programmatic generation + reference implementation** (the same
family as `overtime-payroll`), domain: logistics / accounts-payable audit.

## Task Description
The agent is the logistics analyst of Brightwater Home Goods, an online
retailer shipping from Columbus, OH. The parcel carrier Meridian Parcel
Service has sent invoice MPS-2025-09-BHG for the September 2025 shipments.
From the carrier's invoice, our own shipment manifest and the contracted
rate card the agent must build the monthly audit workbook: one audited row
per invoice line (expected zone, billable weight and charge, variance, status,
component issues), a per-service summary and the dispute list. All business
rules live in `audit_rules.md` inside the workspace; the agent has to read the
rules and apply them to deliberately messy data.

## Input Data (`initial_workspace/`)
| File | Content |
| ---- | ------- |
| `shipment_manifest.csv` | 622 shipments (600 in September, 12 in late August, 10 in early October): tracking number, ship date, service, destination postal code (text, may start with `0`, may carry a ZIP+4 suffix), residential flag, actual weight, dimensions, declared value, order id. Shuffled. |
| `carrier_invoice_2025-09.csv` | 606 invoice lines: tracking number (with noise), the carrier's scan date, service, zone, billed weight, base charge, residential surcharge, declared value surcharge, fuel surcharge, total. |
| `rate_card_2025.xlsx` | `Base Rates` (3 services x 70 lb x zones 2-8, list prices), `Zones` (41 ZIP-prefix ranges), `Fuel Surcharge` (7 weekly percentages, Monday-start), `Contract Terms` (discounts 20/25/30 %, residential 4.50, declared value 1.05 per 100.00 or fraction above 100.00, dim divisor 139, dim threshold 1,728 in^3, minimum 1 lb, dispute threshold 1.00). |
| `audit_rules.md` | The authoritative rule set: tracking normalisation, duplicate / not-in-manifest classification, zone lookup, billable weight, discounted base charge, surcharges, fuel week by manifest date, variance and status, issue codes, disputes, summary definitions, report layout and sort orders. |
| `freight_audit_template.xlsx` | Empty three-sheet workbook (`Shipment Audit`, `Service Summary`, `Disputes`) with the required headers. |

## Expected Output
`freight_audit_2025-09.xlsx` in the workspace, with the three template sheets
filled in (literal values, money with two decimals, sorted as the rules
prescribe, empty cells where the rules say so).

## Traps Planted in the Data
All of them are explicitly covered by `audit_rules.md`:
* 24 invoice tracking numbers with stray whitespace / lower-case letters
* destination postal codes with leading zeros (`03884`) and ZIP+4 suffixes;
  reading them as integers loses the zero and even hits an unmapped prefix
* 9 duplicate invoice lines (later line number is the duplicate), 3 of them
  copies of erroneous lines
* 6 invoice lines for tracking numbers that are not ours
* 14 September shipments never billed; 5 late-August shipments carried over
  onto this invoice (audited normally, fuel week 2025-08-25); October rows
  that belong to another invoice
* invoice ship dates 1-3 days after the manifest date, 33 of them crossing
  into the next fuel-surcharge week
* packages of exactly 1,728 in^3 (no dimensional weight) next to 1,872 in^3
  ones; whole-pound and 0.4 lb actual weights; a 69.6 lb package at the table
  maximum
* declared values of exactly 100.00 (no surcharge), 150.00, 250.00, 600.00
* carrier errors: zone one step too high (12) or too low (4), billed weight
  one pound too high (8), dimensional weight ignored (8), Ground billed as
  Express Saver (6), residential surcharge on commercial addresses (10) or
  missing (4), fuel taken from the previous week (10, all below the dispute
  threshold), declared value surcharge at exactly 100.00 (4) or missing (3),
  base charges off by 0.99 / 1.00 / 1.01 around the dispute threshold
* independent component comparison: a wrong zone reads `Zone; Base rate; Fuel`

## Data Construction (`groundtruth_workspace/`)
Everything is programmatic and deterministic (`random.Random(20250930)`):

```bash
cd tasks/finalpool/freight-invoice-audit/groundtruth_workspace
python generate_data.py            # writes the four input files into ../initial_workspace
python reference_solution.py       # reads initial_workspace, writes freight_audit_2025-09.xlsx (ground truth)
python check_trap_sensitivity.py   # independent pandas re-implementation + 23 "plausible mistakes";
                                   # asserts each mistake changes the result
python ../evaluation/test_check_local.py
```

* `audit_schema.py` holds the shared file names, sheet/column layouts and the
  contract constants; keep it in sync with `audit_rules.md`.
* List prices are `a + b*w + (zone-2)*(c + d*w)` rounded to 0.20, so every
  20 % / 25 % / 30 % discount is an exact cent amount; all fuel percentages
  have basis-point values divisible by 16, which makes a half-cent rounding
  tie impossible. "Round to the cent" therefore never depends on the
  rounding mode an agent uses.
* `reference_solution.py` reads the rate card and contract terms from the
  workbook (not from the schema) and works in integer cents.
* Regenerating with the same seed reproduces byte-identical CSV files and
  identical workbook cell values.

Ground-truth summary: 606 audit rows (519 OK, 45 Overbilled, 27 Underbilled,
9 Duplicate, 6 Not in manifest), 51 disputes totalling 627.49, 14 unbilled
September shipments (Ground 9, Express Saver 4, Priority Overnight 1).

| Service | Lines | Audited | Billed | Expected | Overbilled | Underbilled | Disputes |
| ------- | ----: | ------: | -----: | -------: | ---------: | ----------: | -------: |
| Express Saver | 133 | 129 | 4,956.85 | 4,736.23 | 30.40 | 12.38 | 14 |
| Ground | 420 | 410 | 9,560.45 | 9,253.60 | 138.42 | 49.25 | 35 |
| Priority Overnight | 53 | 52 | 2,758.18 | 2,733.14 | 5.42 | 18.17 | 2 |

## Evaluation (`evaluation/`)
`check_local.py` compares the agent's workbook with the ground truth:
* the three sheets must exist (extra sheets are ignored);
* headers must match the template exactly (whitespace-normalised, same order);
* row counts must match and rows are compared in order (the rules fix the
  sort of every sheet);
* text cells are whitespace-normalised; in `Issues` the spacing around `;` is
  normalised and an empty cell is accepted for `None`;
* whole-number columns (line numbers, zones, weights, counts) must match
  exactly; other numbers are compared with an absolute tolerance of 0.005;
* cells empty in the ground truth (expected values of Duplicate / Not in
  manifest lines) must be empty;
* formula cells are not evaluated, so agents must write literal values.

`python evaluation/test_check_local.py` runs 25 positive/negative cases
against the checker.

## Verification status
2026-09-23, authoring machine (Windows, `uv run --no-project --with openpyxl
--with pandas`): generation is byte-deterministic, the independent pandas
implementation reproduces the ground truth cell for cell, all 23 planted
mistakes change the result, the evaluator passes the ground truth through the
framework's module invocation
(`python -m tasks.finalpool.freight-invoice-audit.evaluation.main`) and all 25
self-test cases behave as expected. No real agent run yet.

## Tools Used
* **Excel MCP** to read the rate card and template and write the report
* **filesystem / terminal** and `python_execute` to process the two CSV files
