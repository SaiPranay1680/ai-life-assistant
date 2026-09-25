"""Regression: insurance premium/coverage must not pick years or labels as money."""

from __future__ import annotations

import unittest

from app.modules.documents.extract import build_structured_payload, guess_fields
from app.modules.documents.text import find_amount_match, normalize_amount
from app.modules.documents.validation import validate_extraction


class IndianAmountFormatTests(unittest.TestCase):
    def test_indian_and_western_amounts(self) -> None:
        indian = find_amount_match("Sum Insured: ₹10,00,000")
        self.assertIsNotNone(indian)
        self.assertEqual(normalize_amount(indian.group(0)), "1000000")
        western = find_amount_match("Annual Premium: ₹18,500.00")
        self.assertIsNotNone(western)
        self.assertEqual(normalize_amount(western.group(0)), "18500")
        # Must not match the mid-fragment ",00,000" alone.
        self.assertNotEqual(indian.group(1), "00,000")


class InsurancePremiumCoverageRegressionTests(unittest.TestCase):
    SAMPLE = (
        "HEALTH INSURANCE POLICY\n"
        "Provider: SecureCare Health Insurance Limited\n"
        "Policy Number: SCI-2026-778812\n"
        "Policy Holder: Rahul Kumar\n"
        "Policy Start Date: 01 Sep 2026\n"
        "Policy End Date: 31 Aug 2027\n"
        "Annual Premium: ₹18,500.00\n"
        "Sum Insured: ₹10,00,000\n"
        "Coverage: Sum Insured\n"
        "Chart years: 2025 2026 2027\n"
    )

    def test_securecare_style_document(self) -> None:
        fields = guess_fields([(1, self.SAMPLE)])
        self.assertIn("insurance", fields["documentType"].raw)
        self.assertEqual(fields["policy_number"].raw, "SCI-2026-778812")
        self.assertEqual(fields["policy_holder"].raw, "Rahul Kumar")
        self.assertEqual(fields["effective_date"].normalized, "2026-09-01")
        self.assertEqual(fields["expiry_date"].normalized, "2027-08-31")
        self.assertEqual(fields["premium"].normalized, "18500")
        self.assertNotEqual(fields["premium"].normalized, "2026")
        self.assertEqual(fields["coverage"].normalized, "1000000")
        self.assertNotEqual((fields["coverage"].raw or "").strip().lower(), "sum insured")
        self.assertIn("18,500", fields["premium"].evidence.replace(" ", ""))
        self.assertTrue(
            "10,00,000" in fields["coverage"].evidence.replace(" ", "")
            or "1000000" in fields["coverage"].evidence.replace(",", "")
        )
        self.assertTrue(
            "premium" in fields["premium"].evidence.lower() or "18,500" in fields["premium"].evidence
        )
        self.assertTrue(
            "insured" in fields["coverage"].evidence.lower() or "10,00,000" in fields["coverage"].evidence
        )
        provider = (fields["provider"].raw or "").lower()
        self.assertIn("securecare", provider)

        validated = validate_extraction(
            fields["documentType"].raw,
            build_structured_payload(fields["documentType"].raw, fields),
        )
        self.assertEqual(validated.premium.normalized, "18500")
        self.assertEqual(validated.coverage.normalized, "1000000")

    def test_annual_premium_with_year_noise(self) -> None:
        pages = [
            (
                1,
                "HEALTH INSURANCE POLICY\n"
                "SecureCare Insurance\n"
                "Policy Number: POL-2026-9\n"
                "Policy Start Date: 01 Sep 2026\n"
                "Policy End Date: 31 Aug 2027\n"
                "Annual Premium\n"
                "2026\n"
                "INR 18,500.00\n"
                "Sum Insured\n"
                "INR 5,00,000\n",
            )
        ]
        fields = guess_fields(pages)
        self.assertEqual(fields["premium"].normalized, "18500")
        self.assertEqual(fields["coverage"].normalized, "500000")
        self.assertNotEqual(fields["premium"].normalized, "2026")

    def test_multiple_monetary_values_prefer_premium_and_sum_insured(self) -> None:
        pages = [
            (
                1,
                "Insurance Policy\n"
                "Provider: SafeLife\n"
                "Policy Number: SL-100\n"
                "GST: INR 2,000.00\n"
                "Annual Premium: INR 18,500.00\n"
                "Sum Insured: INR 10,00,000\n"
                "Start Date: 01/01/2026\n"
                "End Date: 31/12/2026\n",
            )
        ]
        fields = guess_fields(pages)
        self.assertEqual(fields["premium"].normalized, "18500")
        self.assertEqual(fields["coverage"].normalized, "1000000")

    def test_policy_number_not_used_as_premium(self) -> None:
        pages = [
            (
                1,
                "Insurance Policy\n"
                "Provider: SafeLife\n"
                "Policy Number: SCI-2026-778812\n"
                "Premium: Rs. 9,999.00\n"
                "Expiry Date: 01 Jan 2027\n",
            )
        ]
        fields = guess_fields(pages)
        self.assertEqual(fields["policy_number"].raw, "SCI-2026-778812")
        self.assertEqual(fields["premium"].normalized, "9999")

    def test_missing_premium_and_coverage_stay_empty(self) -> None:
        pages = [
            (
                1,
                "Insurance Policy\n"
                "Provider: SafeLife\n"
                "Policy Number: SL-EMPTY\n"
                "Policy Holder: Test User\n"
                "Start Date: 01 Sep 2026\n"
                "End Date: 31 Aug 2027\n"
                "Notes: renew in 2026\n",
            )
        ]
        fields = guess_fields(pages)
        self.assertFalse(fields["premium"].raw)
        self.assertFalse(fields["coverage"].raw)

    def test_ocr_currency_corruption_on_premium(self) -> None:
        pages = [
            (
                1,
                "HEALTH INSURANCE\n"
                "Provider: CareCo\n"
                "Policy Number: CC-1\n"
                "Annual Premium: I18,500.00\n"
                "Sum Insured: I10,00,000\n"
                "Start Date: 01 Sep 2026\n"
                "End Date: 31 Aug 2027\n",
            )
        ]
        fields = guess_fields(pages)
        self.assertEqual(fields["premium"].normalized, "18500")
        self.assertEqual(fields["coverage"].normalized, "1000000")

    def test_coverage_is_value_not_label(self) -> None:
        pages = [
            (
                1,
                "Insurance\n"
                "Provider: CareCo\n"
                "Policy Number: CC-2\n"
                "Coverage: Sum Insured\n"
                "Sum Insured: ₹1,50,00,000\n"
                "Premium: ₹1,200.00\n"
                "Expiry Date: 01 Jan 2028\n",
            )
        ]
        fields = guess_fields(pages)
        self.assertEqual(fields["coverage"].normalized, "15000000")
        self.assertNotEqual(fields["coverage"].raw.strip().lower(), "sum insured")
        self.assertEqual(fields["premium"].normalized, "1200")


if __name__ == "__main__":
    unittest.main()
