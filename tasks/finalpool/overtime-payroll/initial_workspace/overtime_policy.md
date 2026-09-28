# Halvard Precision Components — Overtime & Premium Pay Policy

Applies to pay period **2025-08-01 to 2025-08-31** (inclusive).
This document is the authoritative rule set for the monthly overtime report.

## 1. Who is in scope

| Employment Type | In report? | Notes |
| --------------- | ---------- | ----- |
| Full-time       | Yes        | Eligible for overtime and premium pay |
| Part-time       | Yes        | Same rules as Full-time; the 8-hour daily threshold is **not** pro-rated |
| Contractor      | No         | Paid on invoice; exclude entirely |
| Intern          | No         | Stipend-based; exclude entirely |

* Every eligible employee listed in `employee_roster.xlsx` must appear in the
  **Employee Summary** sheet, even if they have no punches at all in the period
  (report zeros for that person).
* Punches whose employee ID does not exist in the roster (e.g. terminated staff
  whose badge is still active) must be ignored.

## 2. Reading the attendance export

`attendance_export.csv` is a raw dump from the badge terminals. Known quirks:

1. **Duplicate rows.** Terminal re-syncs sometimes write the same punch pair
   twice. Rows that are identical in every column count **once**.
2. **ID formatting.** `employee_id` may carry stray leading/trailing whitespace
   or lower-case letters (`" emp-1017"`). Match IDs case-insensitively after
   trimming whitespace. The canonical form is `EMP-####`.
3. **Order.** Rows are not sorted.
4. Timestamps are `YYYY-MM-DD HH:MM` in local plant time (no time zones).

## 3. Assigning a shift to a date

* A shift belongs to the **calendar date of its `clock_in`** timestamp, even if
  it ends after midnight. (A shift clocking in on 2025-08-31 22:00 and out on
  2025-09-01 06:30 belongs to 2025-08-31 and is inside the period; a shift
  clocking in on 2025-07-31 22:00 is outside the period and must be ignored.)
* Only shifts whose clock-in date falls within the pay period are considered.
  Out-of-period rows are ignored completely (they are neither shifts nor
  invalid punches).

## 4. Invalid punches

After de-duplication and period filtering, a row for an eligible employee is an
**invalid punch** if any of the following holds:

* `clock_out` is empty, or
* `clock_out` is earlier than or equal to `clock_in`, or
* the raw duration (`clock_out - clock_in`) exceeds **16 hours** (badge left
  open).

Invalid punches contribute **no hours and no pay**. Report the number of invalid
punches per employee in the **Invalid Punches** column. `Shifts` counts only
valid shifts.

## 5. Paid hours per shift

1. Raw duration = `clock_out − clock_in`, in minutes.
2. **Unpaid meal break:** if the raw duration is **strictly greater than 6 hours**
   (360 minutes), deduct 30 minutes. Otherwise deduct nothing.
3. **Rounding:** round the result to the nearest quarter hour (0.25 h). Because
   punches are recorded to the minute, exact ties cannot occur.

Example: 07:52 → 16:33 is 521 minutes raw → 491 minutes after the break →
8.1833 h → **8.25 h** paid.

## 6. Classifying hours

Determine the **day type** of the shift's assigned date (see §3):

| Day type | Definition | Multiplier | Report column |
| -------- | ---------- | ---------- | ------------- |
| Holiday  | Date is listed in `holiday_calendar_2025.csv` (takes precedence over weekend) | 2.5× | Holiday Hours |
| Weekend  | Saturday or Sunday, not a holiday | 2.0× | Weekend Hours |
| Weekday  | Monday–Friday, not a holiday | see below | Regular Hours / Weekday OT Hours |

* **Weekday:** overtime is assessed **per calendar day**, not per shift. Sum the
  paid hours of all valid shifts assigned to that date. The first **8.0 h** are
  **Regular Hours** (paid at 1.0×). Anything above 8.0 h is **Weekday OT Hours**
  (paid at 1.5×). Employees with split shifts (two shifts on the same date)
  therefore reach overtime when the two shifts together exceed 8 h.
* **Weekend:** every paid hour is a **Weekend Hour** (2.0×). Nothing counts as
  regular.
* **Holiday:** every paid hour is a **Holiday Hour** (2.5×). Nothing counts as
  regular, and the hours are **not** also counted as weekend hours.
* The day type is decided solely by the clock-in date; a shift that crosses
  midnight into a weekend or holiday is still classified by its clock-in date.

`Total Overtime Hours = Weekday OT Hours + Weekend Hours + Holiday Hours`.

## 7. Pay

Let `R` be the employee's Hourly Rate.

* `Regular Pay  = R × Regular Hours`
* `Overtime Pay = R × (1.5 × Weekday OT Hours + 2.0 × Weekend Hours + 2.5 × Holiday Hours)`
* `Gross Pay    = Regular Pay + Overtime Pay`

Report all money in dollars with **2 decimal places** and all hours with
**2 decimal places**.

## 8. Report structure

Use `overtime_report_template.xlsx` exactly (same sheet names, same column
headers, same column order). Save the result as
`overtime_report_2025-08.xlsx` in the workspace.

### Sheet `Employee Summary`

One row per eligible employee, sorted by **Employee ID ascending**. `Name`,
`Department`, `Employment Type` and `Hourly Rate` are copied from the roster.
Columns:
`Employee ID, Name, Department, Employment Type, Hourly Rate, Shifts,
Invalid Punches, Regular Hours, Weekday OT Hours, Weekend Hours, Holiday Hours,
Total Overtime Hours, Regular Pay, Overtime Pay, Gross Pay`.

### Sheet `Department Summary`

One row per department that has at least one eligible employee, sorted by
**Department ascending**. `Headcount` is the number of eligible employees in
that department (i.e. the number of Employee Summary rows), regardless of
whether they worked. The remaining columns are sums over those employees:
`Regular Hours, Total Overtime Hours, Regular Pay, Overtime Pay, Gross Pay`.

### Sheet `OT Alerts`

Every eligible employee whose `Total Overtime Hours` is **strictly greater than
30.0** in the period, sorted by **Total Overtime Hours descending**, then
**Employee ID ascending**. Columns: `Employee ID, Name, Department,
Total Overtime Hours, Overtime Pay`. If nobody qualifies, leave only the header row.
