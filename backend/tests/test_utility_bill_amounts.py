"""Regression: utility-bill amount_due must not pick years from dates/charts."""

from __future__ import annotations

import unittest

from app.modules.documents.extract import build_structured_payload, guess_fields
from app.modules.documents.text import find_amount_match, normalize_amount
from app.modules.documents.validation import validate_extraction


class MoneyMatchHelpersTests(unittest.TestCase):
    def test_years_rejected_bare_amounts_accepted(self) -> None:
        year = find_amount_match("Chart labels 2025 2026 2027")
        self.assertIsNone(year)
        money = find_amount_match("Amount Due: ₹2,486.50")
        self.assertIsNotNone(money)
        self.assertEqual(normalize_amount(money.group(0)), "2486.50")
        ocr = find_amount_match("Amount Due: I2,486.50")
        self.assertIsNotNone(ocr)
        self.assertEqual(normalize_amount(ocr.group(0)), "2486.50")


class UtilityBillAmountDueRegressionTests(unittest.TestCase):
    BESCOM = (
        "BANGALORE ELECTRICITY SUPPLY COMPANY LIMITED\n"
        "BESCOM\n"
        "Bill Number: BESCOM-2026-091234\n"
        "Amount Due\n"
        "2026\n"
        "Pay Before: 15 Oct 2026\n"
        "Amount Due: ₹2,486.50\n"
        "Usage chart labels: 2025 2026 2027\n"
    )

    def test_amount_due_not_year_from_scrambled_ocr(self) -> None:
        fields = guess_fields([(1, self.BESCOM)])
        self.assertEqual(fields["documentType"].raw, "utility_bill")
        self.assertEqual(fields["bill_number"].raw, "BESCOM-2026-091234")
        self.assertEqual(fields["provider"].raw, "BANGALORE ELECTRICITY SUPPLY COMPANY LIMITED")
        self.assertEqual(fields["due_date"].normalized, "2026-10-15")
        self.assertEqual(fields["amount_due"].normalized, "2486.50")
        self.assertNotEqual(fields["amount_due"].normalized, "2026")

        validated = validate_extraction(
            "utility_bill",
            build_structured_payload("utility_bill", fields),
        )
        self.assertEqual(validated.amount_due.normalized, "2486.50")
        self.assertEqual(validated.due_date.normalized, "2026-10-15")

    def test_amount_due_label(self) -> None:
        pages = [(1, "City Power\nUtility Bill\nAmount Due: Rs. 1,200.00\nDue Date: 01 Jan 2027\n")]
        fields = guess_fields(pages)
        self.assertEqual(fields["amount_due"].normalized, "1200")

    def test_net_amount_payable_preferred(self) -> None:
        pages = [
            (
                1,
                "Utility Bill\n"
                "City Power Services\n"
                "Bill Number: UB-100\n"
                "Previous Balance: INR 50.00\n"
                "Current Charges: INR 900.00\n"
                "Net Amount Payable: INR 950.00\n"
                "Due Date: 20/11/2026\n"
                "Chart: 2024 2025 2026\n",
            )
        ]
        fields = guess_fields(pages)
        self.assertEqual(fields["amount_due"].normalized, "950")
        self.assertNotEqual(fields["amount_due"].normalized, "2026")

    def test_amount_to_pay_label(self) -> None:
        pages = [
            (
                1,
                "ELECTRICITY BILL\n"
                "Metro Power Co\n"
                "Bill Number: MP-9\n"
                "Amount to Pay: ₹3,333.25\n"
                "Pay Before: 02 Feb 2026\n",
            )
        ]
        fields = guess_fields(pages)
        self.assertEqual(fields["amount_due"].normalized, "3333.25")
        self.assertEqual(fields["due_date"].normalized, "2026-02-02")

    def test_multiple_amounts_prefer_amount_due(self) -> None:
        pages = [
            (
                1,
                "UTILITY BILL\n"
                "Grid Services Ltd\n"
                "Bill Number: GS-22\n"
                "Late Fee: INR 25.00\n"
                "Rebate: INR 10.00\n"
                "Amount Due: INR 2,486.50\n"
                "Due Date: 15 Oct 2026\n",
            )
        ]
        fields = guess_fields(pages)
        self.assertEqual(fields["amount_due"].normalized, "2486.50")

    def test_years_and_dates_do_not_become_amount(self) -> None:
        pages = [
            (
                1,
                "UTILITY BILL\n"
                "North Power\n"
                "Bill Number: NP-2026-1\n"
                "Statement Year 2026\n"
                "Period 01 Jan 2026 - 31 Jan 2026\n"
                "Due Date: 15 Feb 2026\n"
                "Amount Payable: INR 410.00\n",
            )
        ]
        fields = guess_fields(pages)
        self.assertEqual(fields["amount_due"].normalized, "410")
        self.assertNotIn(fields["amount_due"].normalized, {"2026", "2025", "2027"})

    def test_ocr_currency_corruption(self) -> None:
        pages = [
            (
                1,
                "UTILITY BILL\n"
                "City Power\n"
                "Bill Number: CP-1\n"
                "Amount Due: I2,486.50\n"
                "Due Date: 15 Oct 2026\n",
            )
        ]
        fields = guess_fields(pages)
        self.assertEqual(fields["amount_due"].normalized, "2486.50")

    def test_no_monetary_value_leaves_amount_empty(self) -> None:
        pages = [
            (
                1,
                "UTILITY BILL\n"
                "City Power\n"
                "Bill Number: CP-EMPTY\n"
                "Due Date: 15 Oct 2026\n"
                "Notes: See chart for 2025 2026 2027 trends\n",
            )
        ]
        fields = guess_fields(pages)
        self.assertFalse(fields["amount_due"].raw)
        self.assertEqual(fields["due_date"].normalized, "2026-10-15")


if __name__ == "__main__":
    unittest.main()
