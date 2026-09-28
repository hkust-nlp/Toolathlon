"""Shared constants for the freight-invoice-audit task (audit_schema).

Used by ``generate_data.py`` (writes the agent-facing inputs) and
``reference_solution.py`` (produces the ground-truth workbook).  Keeping the
file names, sheet names and column layouts in one place guarantees that the
template the agent sees and the ground truth the grader compares against can
never drift apart.

The contract constants below are written into the ``Contract Terms`` sheet of
the rate card by the generator and MUST stay in sync with the prose in
``initial_workspace/audit_rules.md`` - that document is what the agent reads.
"""

import datetime as dt

# --------------------------------------------------------------------------- #
# Invoice period (by manifest ship date)
# --------------------------------------------------------------------------- #
PERIOD_START = dt.date(2025, 9, 1)
PERIOD_END = dt.date(2025, 9, 30)
INVOICE_NUMBER = "MPS-2025-09-BHG"

# --------------------------------------------------------------------------- #
# Files in the agent workspace
# --------------------------------------------------------------------------- #
MANIFEST_FILENAME = "shipment_manifest.csv"
INVOICE_FILENAME = "carrier_invoice_2025-09.csv"
RATE_CARD_FILENAME = "rate_card_2025.xlsx"
RULES_FILENAME = "audit_rules.md"
TEMPLATE_FILENAME = "freight_audit_template.xlsx"

# The file the agent must create
OUTPUT_FILENAME = "freight_audit_2025-09.xlsx"

MANIFEST_COLUMNS = [
    "tracking_number", "ship_date", "service", "dest_postal_code", "residential",
    "actual_weight_lb", "length_in", "width_in", "height_in", "declared_value_usd", "order_id",
]
INVOICE_COLUMNS = [
    "invoice_line", "tracking_number", "ship_date", "service", "zone", "billed_weight_lb",
    "base_charge", "residential_surcharge", "declared_value_surcharge", "fuel_surcharge", "total_charge",
]

# --------------------------------------------------------------------------- #
# Rate card workbook
# --------------------------------------------------------------------------- #
SHEET_RATES = "Base Rates"
SHEET_ZONES = "Zones"
SHEET_FUEL = "Fuel Surcharge"
SHEET_TERMS = "Contract Terms"

SERVICES = ["Ground", "Express Saver", "Priority Overnight"]
ZONES = [2, 3, 4, 5, 6, 7, 8]
MAX_WEIGHT_LB = 70

RATES_COLUMNS = ["Service", "Weight (lb)"] + [f"Zone {z}" for z in ZONES]
ZONES_COLUMNS = ["Prefix From", "Prefix To", "Zone"]
FUEL_COLUMNS = ["Week Starting (Monday)", "Fuel Surcharge %"]
TERMS_COLUMNS = ["Term", "Value"]

# Term labels used in the Contract Terms sheet (reference_solution parses them)
TERM_DISCOUNT = {s: f"{s} discount (%)" for s in SERVICES}
TERM_RESIDENTIAL = "Residential surcharge (USD)"
TERM_DECLARED_RATE = "Declared value surcharge (USD per 100.00 or fraction, above threshold)"
TERM_DECLARED_THRESHOLD = "Declared value threshold (USD)"
TERM_DIM_DIVISOR = "Dimensional divisor (cubic inches per lb)"
TERM_DIM_VOLUME = "Dimensional weight applies when volume exceeds (cubic inches)"
TERM_DISPUTE_THRESHOLD = "Dispute threshold (USD)"
TERM_MIN_WEIGHT = "Minimum billable weight (lb)"

# --------------------------------------------------------------------------- #
# Contract constants (see audit_rules.md)
# --------------------------------------------------------------------------- #
DISCOUNT_PERCENT = {"Ground": 20, "Express Saver": 25, "Priority Overnight": 30}
RESIDENTIAL_SURCHARGE_CENTS = 450
DECLARED_VALUE_THRESHOLD_CENTS = 10000       # strictly greater than -> surcharge
DECLARED_VALUE_RATE_CENTS = 105              # per 100.00 or fraction thereof
DIM_DIVISOR = 139
DIM_VOLUME_THRESHOLD = 1728                  # strictly greater than -> dim weight considered
DISPUTE_THRESHOLD_CENTS = 100                # variance >= 1.00 -> dispute
MIN_BILLABLE_WEIGHT_LB = 1

# Fuel surcharge by ISO week (Monday start).  Every percentage has a
# basis-point value divisible by 16, which makes a rounding tie on any
# whole-cent base amount impossible (c * bp = 5000 mod 10000 has no solution).
FUEL_WEEKS = [
    (dt.date(2025, 8, 25), "16.00"),
    (dt.date(2025, 9, 1), "16.32"),
    (dt.date(2025, 9, 8), "16.80"),
    (dt.date(2025, 9, 15), "17.12"),
    (dt.date(2025, 9, 22), "16.64"),
    (dt.date(2025, 9, 29), "17.28"),
    (dt.date(2025, 10, 6), "16.96"),
]

# Destination ZIP prefix (first three digits) ranges -> zone, from origin 432 (Columbus, OH)
ZONE_RANGES = [
    ("430", "459", 2),
    ("150", "196", 3), ("250", "268", 3), ("400", "427", 3), ("460", "479", 3), ("480", "499", 3),
    ("100", "149", 4), ("197", "199", 4), ("200", "249", 4), ("270", "289", 4), ("290", "299", 4),
    ("370", "385", 4), ("530", "549", 4), ("600", "629", 4),
    ("010", "099", 5), ("300", "319", 5), ("350", "369", 5), ("386", "397", 5), ("500", "528", 5),
    ("550", "567", 5), ("630", "658", 5), ("700", "714", 5), ("716", "729", 5),
    ("320", "349", 6), ("570", "577", 6), ("580", "588", 6), ("660", "679", 6), ("680", "693", 6),
    ("730", "749", 6), ("750", "799", 6),
    ("590", "599", 7), ("800", "816", 7), ("820", "831", 7), ("832", "838", 7), ("840", "847", 7),
    ("850", "865", 7), ("870", "884", 7),
    ("889", "898", 8), ("900", "961", 8), ("970", "979", 8), ("980", "994", 8),
]

# --------------------------------------------------------------------------- #
# Report layout (mirrored 1:1 by the template workbook)
# --------------------------------------------------------------------------- #
SHEET_AUDIT = "Shipment Audit"
SHEET_SUMMARY = "Service Summary"
SHEET_DISPUTES = "Disputes"

AUDIT_COLUMNS = [
    "Invoice Line",
    "Tracking Number",
    "Service",
    "Expected Zone",
    "Expected Billed Weight",
    "Expected Total",
    "Billed Total",
    "Variance",
    "Status",
    "Issues",
]

SUMMARY_COLUMNS = [
    "Service",
    "Invoice Lines",
    "Audited Shipments",
    "Billed Total",
    "Expected Total",
    "Overbilled Amount",
    "Underbilled Amount",
    "Disputed Lines",
    "Disputed Amount",
    "Unbilled Shipments",
]

DISPUTE_COLUMNS = [
    "Invoice Line",
    "Tracking Number",
    "Service",
    "Status",
    "Issues",
    "Disputed Amount",
]

REPORT_SHEETS = {
    SHEET_AUDIT: AUDIT_COLUMNS,
    SHEET_SUMMARY: SUMMARY_COLUMNS,
    SHEET_DISPUTES: DISPUTE_COLUMNS,
}

STATUS_OK = "OK"
STATUS_OVER = "Overbilled"
STATUS_UNDER = "Underbilled"
STATUS_DUPLICATE = "Duplicate"
STATUS_UNKNOWN = "Not in manifest"
AUDITED_STATUSES = (STATUS_OK, STATUS_OVER, STATUS_UNDER)

# Component issue codes in the order they must be listed
ISSUE_SERVICE = "Service"
ISSUE_ZONE = "Zone"
ISSUE_WEIGHT = "Weight"
ISSUE_BASE = "Base rate"
ISSUE_RESIDENTIAL = "Residential"
ISSUE_DECLARED = "Declared value"
ISSUE_FUEL = "Fuel"
ISSUE_ORDER = [ISSUE_SERVICE, ISSUE_ZONE, ISSUE_WEIGHT, ISSUE_BASE, ISSUE_RESIDENTIAL, ISSUE_DECLARED, ISSUE_FUEL]
ISSUE_SEPARATOR = "; "
NO_ISSUES = "None"
