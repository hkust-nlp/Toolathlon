# Overtime Payroll Report Task

## Task Description
The agent plays the payroll assistant of a small manufacturing company. From a
raw badge-terminal export it must build the August 2025 overtime report:
per-employee hours and pay, per-department totals and a list of employees whose
overtime exceeds the alert threshold. All business rules live in a policy
document inside the workspace; the agent has to read the rules and apply them
to deliberately messy data.

## Input Data (`initial_workspace/`)
| File | Content |
| ---- | ------- |
| `employee_roster.xlsx` | 50 employees: ID, name, department, employment type, hourly rate, hire date. 45 are overtime-eligible (Full-time / Part-time); 3 contractors and 2 interns must be excluded. |
| `attendance_export.csv` | 1,125 raw punch rows (`employee_id, clock_in, clock_out, terminal`) covering 2025-07-30 to 2025-09-02. |
| `holiday_calendar_2025.csv` | Company holidays; August contains a Friday holiday (08-15) and a Saturday holiday (08-23). |
| `overtime_policy.md` | The authoritative rule set: eligibility, de-duplication, ID normalisation, shift-date assignment, invalid punches, meal break, quarter-hour rounding, weekday/weekend/holiday classification, pay multipliers, report layout and sort orders. |
| `overtime_report_template.xlsx` | Empty three-sheet workbook (`Employee Summary`, `Department Summary`, `OT Alerts`) with the required headers. |

## Expected Output
`overtime_report_2025-08.xlsx` in the workspace, with the three template sheets
filled in (literal values, two decimals, sorted as the policy prescribes).

## Traps Planted in the Data
All of them are explicitly covered by `overtime_policy.md`:
* exact duplicate rows (27, including a triplicated invalid row)
* employee IDs with stray whitespace / lower case (43 rows)
* rows outside the pay period (late July / early September), including a
  night shift that clocks in on 07-31 and out on 08-01
* night shifts crossing midnight into a holiday / into September
* invalid punches: missing clock-out, clock-out <= clock-in, spans > 16 h
* an exactly-16-hour shift (valid) next to a 16 h 01 min shift (invalid)
* part-time shifts of exactly 6 h (no meal break) and 6 h 01-20 min (break)
* split shifts whose two halves only exceed 8 h when summed per day
* a holiday that falls on a Saturday (holiday rate beats weekend rate)
* punches for contractors, interns and two terminated badges not in the roster
* eligible employees with no punches, or only invalid punches (must still be
  listed with zeros)
* employees engineered to land at 29.75 / 30.00 / 30.25 overtime hours around
  the strict `> 30.0` alert threshold

## Data Construction (`groundtruth_workspace/`)
Everything is programmatic and deterministic (`random.Random(20250831)`):

```bash
cd tasks/finalpool/overtime-payroll/groundtruth_workspace
python generate_data.py            # writes the four input files into ../initial_workspace
python reference_solution.py       # reads initial_workspace, writes overtime_report_2025-08.xlsx (ground truth)
python check_trap_sensitivity.py   # independent pandas re-implementation + 18 "plausible mistakes";
                                   # asserts each mistake changes the result
```

* `payroll_schema.py` holds the shared file names, sheet/column layouts and
  the numeric policy constants; keep it in sync with `overtime_policy.md`.
* `reference_solution.py` implements the policy with exact `Fraction`
  arithmetic. All hourly rates have a cent value divisible by 8 and paid hours
  are quarter hours, so every pay figure is an exact number of cents and
  rounding never has to break a tie.
* Regenerating with the same seed reproduces byte-identical CSV files and
  identical workbook cell values.

Ground-truth summary: 45 employee rows, 6 department rows, 8 alert rows,
843 valid shifts, 18 invalid punches, gross payroll 192,172.00.

## Evaluation (`evaluation/`)
`check_local.py` compares the agent's workbook with the ground truth:
* the three sheets must exist (extra sheets are ignored);
* headers must match the template exactly (whitespace-normalised, same order);
* row counts must match and rows are compared in order (the policy fixes the
  sort of every sheet);
* text cells are whitespace-normalised; count columns must match exactly;
  other numbers are compared with an absolute tolerance of 0.005;
* formula cells are not evaluated, so agents must write literal values.

`python evaluation/test_check_local.py` runs 23 positive/negative cases
against the checker.

## Tools Used
* **Excel MCP** to read the roster/template and write the report
* **filesystem / terminal** and `python_execute` to process the CSV
