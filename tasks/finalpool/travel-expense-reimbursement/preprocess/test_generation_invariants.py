import json
import os
import sys
import tempfile
import unittest
from decimal import Decimal

from PyPDF2 import PdfReader

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.append(PROJECT_ROOT)

from main import create_invoice_pdf
from generate_claims import generate_all_expense_claims
from generate_groundtruth_from_policy import (
    find_policy_violations,
    generate_claims_for_employee,
    inject_form_errors,
)
from generate_policy_pdf import build_policy_story
from load_employees import load_employees_from_mapping_files


GROUNDTRUTH_DIR = os.path.abspath(os.path.join(HERE, "..", "groundtruth_workspace"))


class GeneratedClaimInvariantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(
            os.path.join(GROUNDTRUTH_DIR, "policy_standards_en.json"),
            "r",
            encoding="utf-8",
        ) as policy_file:
            cls.policy = json.load(policy_file)
        employees_with_errors, employees_no_errors = load_employees_from_mapping_files(
            GROUNDTRUTH_DIR
        )
        cls.clean_employee_ids = {
            employee["employee_id"] for employee in employees_no_errors
        }
        cls.claims = generate_all_expense_claims(
            employees_with_errors,
            employees_no_errors,
            cls.policy,
            7,
            generate_claims_for_employee,
            inject_form_errors,
            find_policy_violations,
        )

    def test_final_violation_labels_are_derived_from_final_line_items(self):
        for claim in self.claims:
            with self.subTest(claim_id=claim["claim_id"]):
                self.assertEqual(
                    claim["_policy_violations"],
                    find_policy_violations(claim, self.policy),
                )

    def test_checked_in_groundtruth_matches_the_deterministic_generator(self):
        with open(
            os.path.join(GROUNDTRUTH_DIR, "expense_claims.json"),
            "r",
            encoding="utf-8",
        ) as claims_file:
            checked_in_claims = json.load(claims_file)

        self.assertEqual(checked_in_claims, self.claims)

    def test_checked_in_groundtruth_satisfies_same_violation_invariant(self):
        with open(
            os.path.join(GROUNDTRUTH_DIR, "expense_claims.json"),
            "r",
            encoding="utf-8",
        ) as claims_file:
            checked_in_claims = json.load(claims_file)

        self.assertEqual(checked_in_claims, self.claims)
        for claim in checked_in_claims:
            with self.subTest(claim_id=claim["claim_id"]):
                self.assertEqual(
                    claim["_policy_violations"],
                    find_policy_violations(claim, self.policy),
                )

    def test_clean_group_is_generated_compliant_and_financially_consistent(self):
        clean_claims = [
            claim
            for claim in self.claims
            if claim["employee_id"] in self.clean_employee_ids
        ]
        self.assertTrue(clean_claims)

        for claim in clean_claims:
            with self.subTest(claim_id=claim["claim_id"]):
                self.assertEqual(claim["_form_errors"], [])
                self.assertEqual(claim["_policy_violations"], [])

                line_total = sum(
                    Decimal(str(item["amount"])) for item in claim["line_items"]
                ).quantize(Decimal("0.01"))
                self.assertEqual(
                    Decimal(str(claim["total_claimed"])).quantize(Decimal("0.01")),
                    line_total,
                )

                for item in claim["line_items"]:
                    self.assertEqual(len(item["receipts"]), 1)
                    receipt = item["receipts"][0]
                    self.assertEqual(receipt["amount"], item["amount"])
                    self.assertTrue(receipt["invoice_number"])
                    self.assertTrue(receipt["description"])
                    tax_rate = (
                        Decimal("0.08")
                        if item["category"] in ("Meals", "Transportation", "Miscellaneous")
                        else Decimal("0.10")
                    )
                    expected_tax = (
                        Decimal(str(item["amount"])) * tax_rate
                    ).quantize(Decimal("0.01"))
                    self.assertEqual(
                        Decimal(str(receipt["tax_amount"])).quantize(Decimal("0.01")),
                        expected_tax,
                    )
                    if receipt.get("client_entertainment"):
                        self.assertIs(receipt.get("manager_pre_approval"), True)
                        self.assertTrue(receipt.get("attendee_list"))
                        self.assertTrue(receipt.get("business_purpose"))

    def test_client_entertainment_evidence_is_visible_in_invoice_pdf(self):
        item = {
            "date": "2024-10-05",
            "category": "Meals",
            "receipts": [{
                "invoice_number": "INV-ENT-1",
                "date": "2024-10-05",
                "vendor": "Client Restaurant",
                "amount": 700.0,
                "city": "London",
                "country": "United Kingdom",
                "category": "Meals",
                "tax_amount": 56.0,
                "description": "Client dinner",
                "client_entertainment": True,
                "manager_pre_approval": True,
                "attendee_list": "Client representatives and employee",
                "business_purpose": "Client business meal",
            }],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = os.path.join(temp_dir, "invoice.pdf")
            create_invoice_pdf(pdf_path, item, 1)
            pdf_text = " ".join(
                page.extract_text() or "" for page in PdfReader(pdf_path).pages
            )

        self.assertIn("Client Entertainment:", pdf_text)
        self.assertIn("Manager Pre-Approval:", pdf_text)
        self.assertIn("Client representatives and employee", pdf_text)
        self.assertIn("Client business meal", pdf_text)

    def test_entertainment_multiplier_requires_complete_visible_evidence(self):
        receipt = {"client_entertainment": True}
        claim = {
            "dest_country": "Australia",
            "dest_city": "Sydney",
            "employee_level": "L1",
            "line_items": [{
                "date": "2024-10-01",
                "category": "Meals",
                "amount": 700.0,
                "receipts": [receipt],
            }],
        }
        self.assertEqual(
            [item["type"] for item in find_policy_violations(claim, self.policy)],
            ["meals_over_cap"],
        )

        receipt.update({
            "manager_pre_approval": True,
            "attendee_list": "Client representatives and employee",
            "business_purpose": "Client business meal",
        })
        self.assertEqual(find_policy_violations(claim, self.policy), [])

    def test_policy_material_explicitly_forbids_cross_date_offsetting(self):
        cap_assessment = self.policy["global_rules"]["cap_assessment"]
        self.assertIn("separately for each night", cap_assessment)
        self.assertIn("separately for each calendar date", cap_assessment)
        self.assertIn("must not offset", cap_assessment)

        policy_text = " ".join(
            flowable.getPlainText()
            for flowable in build_policy_story(self.policy)
            if hasattr(flowable, "getPlainText")
        )
        self.assertIn(cap_assessment, policy_text)

    def test_low_spend_date_cannot_offset_an_over_cap_date(self):
        claim = {
            "dest_country": "Australia",
            "dest_city": "Sydney",
            "employee_level": "L1",
            "line_items": [
                {
                    "date": "2024-10-01",
                    "category": "Accommodation",
                    "amount": 100.0,
                    "receipts": [{"nights": 1}],
                },
                {
                    "date": "2024-10-02",
                    "category": "Accommodation",
                    "amount": 1600.0,
                    "receipts": [{"nights": 1}],
                },
                {
                    "date": "2024-10-01",
                    "category": "Meals",
                    "amount": 100.0,
                    "receipts": [{"client_entertainment": False}],
                },
                {
                    "date": "2024-10-02",
                    "category": "Meals",
                    "amount": 600.0,
                    "receipts": [{"client_entertainment": False}],
                },
                {
                    "date": "2024-10-01",
                    "category": "Transportation",
                    "amount": 10.0,
                    "receipts": [{}],
                },
                {
                    "date": "2024-10-02",
                    "category": "Transportation",
                    "amount": 360.0,
                    "receipts": [{}],
                },
            ],
        }

        violations = find_policy_violations(claim, self.policy)
        self.assertEqual(
            [(item["type"], item.get("date")) for item in violations],
            [
                ("accommodation_over_cap", "2024-10-02"),
                ("meals_over_cap", "2024-10-02"),
                ("local_transport_over_cap", "2024-10-02"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
