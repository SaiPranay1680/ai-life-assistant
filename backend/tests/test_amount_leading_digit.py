"""Regression: leading digit of monetary amounts must never be stripped as OCR ₹."""

from __future__ import annotations

import unittest

from app.modules.documents.extract import build_structured_payload, guess_fields
from app.modules.documents.text import (
    canonicalize_amount_raw,
    find_amount_match,
    normalize_amount,
)
from app.modules.documents.validation import validate_extraction


class LeadingDigitPreservationTests(unittest.TestCase):
    """Bare and prefixed amounts that start with 1 must keep that digit."""

    CASES = [
        ("18,500.00", "18500"),
        ("₹18,500.00", "18500"),
        ("₹ 18,500.00", "18500"),
        ("INR 18,500.00", "18500"),
        ("Rs. 18,500.00", "18500"),
        ("10,00,000", "1000000"),
        ("₹10,00,000", "1000000"),
        ("2,486.50", "2486.50"),
        ("₹2,486.50", "2486.50"),
        ("49,560.00", "49560"),
        ("₹49,560.00", "49560"),
        ("1,50,00,000", "15000000"),
        ("₹1,50,00,000", "15000000"),
        ("1,200.00", "1200"),
        ("I18,500.00", "18500"),
        ("I10,00,000", "1000000"),
        ("I2,486.50", "2486.50"),
    ]

    def test_normalize_preserves_leading_digit(self) -> None:
        for raw, expected in self.CASES:
            with self.subTest(raw=raw):
                self.assertEqual(normalize_amount(raw), expected)
                matched = find_amount_match(raw)
                self.assertIsNotNone(matched, msg=f"no amount match for {raw!r}")
                assert matched is not None
                self.assertEqual(normalize_amount(matched.group(0)), expected)
                # Number group must not drop the leading digit.
                number = matched.group(1).replace(",", "")
                self.assertTrue(
                    number.startswith(expected.split(".", 1)[0][:1])
                    or expected.startswith(number[:1]),
                    msg=f"group(1)={matched.group(1)!r} for {raw!r}",
                )

    def test_canonicalize_does_not_drop_leading_one(self) -> None:
        self.assertEqual(canonicalize_amount_raw("18,500.00"), "18,500.00")
        self.assertEqual(canonicalize_amount_raw("10,00,000"), "10,00,000")
        self.assertEqual(canonicalize_amount_raw("1,50,00,000"), "1,50,00,000")
        self.assertEqual(canonicalize_amount_raw("₹18,500.00"), "INR 18,500.00")
        self.assertEqual(canonicalize_amount_raw("I18,500.00"), "INR 18,500.00")
        # Must not produce the truncated OCR forms seen in the UI regression.
        self.assertNotEqual(canonicalize_amount_raw("18,500.00"), "INR 8,500.00")
        self.assertNotEqual(canonicalize_amount_raw("10,00,000"), "INR 0,00,000")


class InsuranceBareAmountLeadingDigitTests(unittest.TestCase):
    """Insurance premium/coverage when currency symbol is missing (OCR drop)."""

    def test_bare_premium_and_sum_insured_keep_leading_one(self) -> None:
        pages = [
            (
                1,
                "HEALTH INSURANCE POLICY\n"
                "Provider: SecureCare Health Insurance Limited\n"
                "Policy Number: SCI-2026-778812\n"
                "Policy Holder: Rahul Kumar\n"
                "Policy Start Date: 01 Sep 2026\n"
                "Policy End Date: 31 Aug 2027\n"
                "Annual Premium : 18,500.00\n"
                "Sum Insured : 10,00,000\n",
            )
        ]
        fields = guess_fields(pages)
        self.assertEqual(fields["premium"].normalized, "18500")
        self.assertEqual(fields["coverage"].normalized, "1000000")
        self.assertNotEqual(fields["premium"].normalized, "8500")
        self.assertNotEqual(fields["coverage"].normalized, "0")
        self.assertNotEqual(fields["coverage"].normalized, "000000")
        premium_raw = fields["premium"].raw.replace(" ", "")
        coverage_raw = fields["coverage"].raw.replace(" ", "")
        self.assertTrue(premium_raw.startswith("18,500") or "18,500" in premium_raw)
        self.assertTrue("10,00,000" in coverage_raw or coverage_raw.startswith("10,00,000"))
        self.assertFalse(premium_raw.startswith("8,500"))
        self.assertFalse(coverage_raw.startswith("0,00,000") or coverage_raw == "INR0,00,000")

        validated = validate_extraction(
            fields["documentType"].raw,
            build_structured_payload(fields["documentType"].raw, fields),
        )
        self.assertEqual(validated.premium.normalized, "18500")
        self.assertEqual(validated.coverage.normalized, "1000000")

    def test_rupee_premium_and_sum_insured(self) -> None:
        pages = [
            (
                1,
                "HEALTH INSURANCE POLICY\n"
                "Provider: SecureCare Health Insurance Limited\n"
                "Policy Number: SCI-2026-778812\n"
                "Policy Holder: Rahul Kumar\n"
                "Policy Start Date: 01 Sep 2026\n"
                "Policy End Date: 31 Aug 2027\n"
                "Annual Premium : ₹18,500.00\n"
                "Sum Insured : ₹10,00,000\n",
            )
        ]
        fields = guess_fields(pages)
        self.assertEqual(fields["premium"].normalized, "18500")
        self.assertEqual(fields["coverage"].normalized, "1000000")


class CrossTypeAmountRegressionTests(unittest.TestCase):
    def test_utility_amount_due(self) -> None:
        pages = [
            (
                1,
                "UTILITY BILL\n"
                "City Power\n"
                "Bill Number: CP-9\n"
                "Amount Due: ₹2,486.50\n"
                "Due Date: 15 Oct 2026\n",
            )
        ]
        fields = guess_fields(pages)
        self.assertEqual(fields["amount_due"].normalized, "2486.50")

    def test_purchase_total(self) -> None:
        pages = [
            (
                1,
                "PURCHASE RECEIPT\n"
                "TechMart\n"
                "Receipt Number: R-100\n"
                "Purchase Date: 01 Sep 2026\n"
                "Subtotal: INR 42,000.00\n"
                "Tax: INR 7,560.00\n"
                "Total: INR 49,560.00\n",
            )
        ]
        fields = guess_fields(pages)
        self.assertEqual(fields["total"].normalized, "49560")

    def test_years_still_rejected(self) -> None:
        self.assertIsNone(find_amount_match("2026"))
        self.assertIsNone(find_amount_match("Chart 2025 2026 2027"))


if __name__ == "__main__":
    unittest.main()
