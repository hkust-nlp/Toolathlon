"""Shared constants for the overtime-payroll task (payroll_schema).

Used by ``generate_data.py`` (writes the agent-facing inputs) and
``reference_solution.py`` (produces the ground-truth report).  Keeping the
file names, sheet names and column layouts in one place guarantees that the
template the agent sees and the ground truth the grader compares against can
never drift apart.

The numeric policy constants below MUST stay in sync with the prose in
``initial_workspace/overtime_policy.md`` - that document is what the agent reads.
"""

import datetime as dt

# --------------------------------------------------------------------------- #
# Pay period
# --------------------------------------------------------------------------- #
PERIOD_START = dt.date(2025, 8, 1)
PERIOD_END = dt.date(2025, 8, 31)

# --------------------------------------------------------------------------- #
# Files in the agent workspace
# --------------------------------------------------------------------------- #
ROSTER_FILENAME = "employee_roster.xlsx"
ROSTER_SHEET = "Roster"
ATTENDANCE_FILENAME = "attendance_export.csv"
HOLIDAYS_FILENAME = "holiday_calendar_2025.csv"
POLICY_FILENAME = "overtime_policy.md"
TEMPLATE_FILENAME = "overtime_report_template.xlsx"

# The file the agent must create
OUTPUT_FILENAME = "overtime_report_2025-08.xlsx"

ROSTER_COLUMNS = ["Employee ID", "Name", "Department", "Employment Type", "Hourly Rate", "Hire Date"]
ATTENDANCE_COLUMNS = ["employee_id", "clock_in", "clock_out", "terminal"]
HOLIDAY_COLUMNS = ["date", "holiday_name"]

# --------------------------------------------------------------------------- #
# Report layout (mirrored 1:1 by the template workbook)
# --------------------------------------------------------------------------- #
SHEET_EMPLOYEE = "Employee Summary"
SHEET_DEPARTMENT = "Department Summary"
SHEET_ALERTS = "OT Alerts"

EMPLOYEE_COLUMNS = [
    "Employee ID",
    "Name",
    "Department",
    "Employment Type",
    "Hourly Rate",
    "Shifts",
    "Invalid Punches",
    "Regular Hours",
    "Weekday OT Hours",
    "Weekend Hours",
    "Holiday Hours",
    "Total Overtime Hours",
    "Regular Pay",
    "Overtime Pay",
    "Gross Pay",
]

DEPARTMENT_COLUMNS = [
    "Department",
    "Headcount",
    "Regular Hours",
    "Total Overtime Hours",
    "Regular Pay",
    "Overtime Pay",
    "Gross Pay",
]

ALERT_COLUMNS = [
    "Employee ID",
    "Name",
    "Department",
    "Total Overtime Hours",
    "Overtime Pay",
]

REPORT_SHEETS = {
    SHEET_EMPLOYEE: EMPLOYEE_COLUMNS,
    SHEET_DEPARTMENT: DEPARTMENT_COLUMNS,
    SHEET_ALERTS: ALERT_COLUMNS,
}

# --------------------------------------------------------------------------- #
# Policy constants (see overtime_policy.md)
# --------------------------------------------------------------------------- #
ELIGIBLE_EMPLOYMENT_TYPES = ("Full-time", "Part-time")

MEAL_BREAK_THRESHOLD_MINUTES = 6 * 60   # deduct only if raw duration > 6h
MEAL_BREAK_MINUTES = 30                 # 0.5 h unpaid
ROUNDING_MINUTES = 15                   # paid hours rounded to nearest 0.25 h

REGULAR_HOURS_PER_SHIFT = 8.0
WEEKDAY_OT_MULTIPLIER = 1.5
WEEKEND_MULTIPLIER = 2.0
HOLIDAY_MULTIPLIER = 2.5

OT_ALERT_THRESHOLD_HOURS = 30.0         # strictly greater than -> alert
