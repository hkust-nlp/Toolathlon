import os
import sys
import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import patch

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.append(PROJECT_ROOT)

from main import (
    expense_row_differences,
    expected_expense_row,
    fetch_expense_rows_by_claim_id,
)


def sample_claim():
    return {
        "claim_id": "EXP2024008",
        "department": "Finance Department",
        "dest_city": "Seoul",
        "dest_country": "South Korea",
        "employee_id": "EMP004",
        "employee_name": "Sandra Davis",
        "nights": 3,
        "total_claimed": 4321.5,
        "trip_start": "2024-09-15",
        "trip_end": "2024-09-17",
        "_policy_violations": [{"type": "accommodation_over_cap"}],
    }


class ExpenseDatabaseComparisonTests(unittest.TestCase):
    def test_snowflake_types_are_normalized_without_weakening_comparison(self):
        claim = sample_claim()
        actual = expected_expense_row(claim)
        actual["TOTAL_CLAIMED"] = Decimal("4321.50")
        actual["TRIP_START"] = date(2024, 9, 15)
        actual["TRIP_END"] = date(2024, 9, 17)

        self.assertEqual(expense_row_differences(claim, actual), [])

    def test_wrong_flag_is_reported_as_a_field_difference(self):
        claim = sample_claim()
        actual = expected_expense_row(claim)
        actual["FLAG"] = 0

        self.assertEqual(
            expense_row_differences(claim, actual),
            ["FLAG: expected=1, actual=0"],
        )

    def test_fetch_uses_only_claim_id_as_row_identity(self):
        with patch("main.fetch_all_dict", return_value=[]) as fetch:
            self.assertEqual(fetch_expense_rows_by_claim_id("EXP'42"), [])

        query = fetch.call_args.args[0]
        self.assertIn("WHERE CLAIM_ID = 'EXP''42'", query)
        where_clause = query.split("WHERE", 1)[1]
        self.assertNotIn("FLAG =", where_clause)
        self.assertNotIn("TOTAL_CLAIMED =", where_clause)


if __name__ == "__main__":
    unittest.main()
