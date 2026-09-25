"""DOC-005: Per-type extraction schema validation tests."""

from __future__ import annotations

import unittest

from app.modules.documents.extract import (
    FieldHit,
    build_structured_payload,
    classify_document,
    display_document_type,
    empty_field,
    guess_fields,
    normalize_amount,
    normalize_document_type,
)
from app.modules.documents.schemas import (
    ExtractedValue,
    GenericExtraction,
    InsuranceExtraction,
    PurchaseReceiptExtraction,
    UtilityBillExtraction,
    WarrantyExtraction,
)
from app.modules.documents.validation import EXTRACTION_SCHEMA_REGISTRY, validate_extraction


def _value(raw: str, normalized: str | None = None, confidence: float = 0.9, page: int = 1, snippet: str | None = None) -> dict:
    return {
        "raw": raw,
        "normalized": normalized if normalized is not None else raw,
        "confidence": confidence,
        "evidence": [{"page_number": page, "snippet": snippet or raw}],
    }


class ExtractedValueTests(unittest.TestCase):
    def test_confidence_below_zero_rejected(self) -> None:
        with self.assertRaises(Exception):
            ExtractedValue(raw="x", normalized="x", confidence=-0.1, evidence=[])

    def test_confidence_above_one_rejected(self) -> None:
        with self.assertRaises(Exception):
            ExtractedValue(raw="x", normalized="x", confidence=1.1, evidence=[])

    def test_null_confidence_allowed(self) -> None:
        value = ExtractedValue(raw=None, normalized=None, confidence=None, evidence=[])
        self.assertIsNone(value.confidence)


class SchemaRegistryTests(unittest.TestCase):
    def test_registry_keys(self) -> None:
        self.assertEqual(
            set(EXTRACTION_SCHEMA_REGISTRY),
            {"utility_bill", "insurance", "purchase_receipt", "warranty", "generic"},
        )

    def test_invalid_document_type_rejected(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            validate_extraction("not_a_real_type", {"document_type": _value("x")})
        self.assertIn("Unsupported document type", str(ctx.exception))


class UtilityBillSchemaTests(unittest.TestCase):
    def test_utility_bill_schema_selected(self) -> None:
        data = {
            "document_type": _value("utility_bill"),
            "provider": _value("City Power"),
            "account_number": _value("ACC-1001"),
            "due_date": _value("15 Oct 2026", "2026-10-15", confidence=0.9, snippet="Due Date: 15 Oct 2026"),
            "amount_due": _value("₹1,245.00", "1245.00", confidence=0.96, snippet="Amount Due: ₹1,245.00"),
            "billing_period_start": None,
            "billing_period_end": None,
            "previous_balance": None,
            "current_charges": None,
            "currency": _value("INR", "INR"),
        }
        result = validate_extraction("utility_bill", data)
        self.assertIsInstance(result, UtilityBillExtraction)
        self.assertEqual(result.amount_due.normalized, "1245.00")
        self.assertEqual(result.due_date.normalized, "2026-10-15")
        self.assertEqual(result.amount_due.confidence, 0.96)
        self.assertEqual(result.amount_due.evidence[0].page_number, 1)
        self.assertIn("Amount Due", result.amount_due.evidence[0].snippet)

    def test_missing_fields_remain_null(self) -> None:
        result = validate_extraction(
            "utility_bill",
            {"document_type": _value("utility_bill")},
        )
        self.assertIsNone(result.amount_due)
        self.assertIsNone(result.due_date)
        self.assertIsNone(result.previous_balance)


class InsuranceSchemaTests(unittest.TestCase):
    def test_insurance_fields(self) -> None:
        data = {
            "document_type": _value("insurance"),
            "provider": _value("SafeCover"),
            "policy_number": _value("AI-482019"),
            "effective_date": _value("01 Jan 2026", "2026-01-01"),
            "expiry_date": _value("12 October 2026", "2026-10-12"),
            "premium": _value("₹8,500", "8500"),
            "policy_holder": None,
            "deductible": None,
            "coverage": None,
            "currency": None,
        }
        result = validate_extraction("insurance", data)
        self.assertIsInstance(result, InsuranceExtraction)
        self.assertEqual(result.policy_number.raw, "AI-482019")
        self.assertEqual(result.effective_date.normalized, "2026-01-01")
        self.assertEqual(result.expiry_date.normalized, "2026-10-12")
        self.assertEqual(result.premium.normalized, "8500")


class PurchaseReceiptSchemaTests(unittest.TestCase):
    def test_purchase_receipt_fields_and_items(self) -> None:
        data = {
            "document_type": _value("purchase_receipt"),
            "merchant": _value("ElectroMart"),
            "purchase_date": _value("05 Mar 2026", "2026-03-05"),
            "transaction_date": _value("05 Mar 2026", "2026-03-05"),
            "receipt_number": _value("RCPT-77"),
            "items": [
                {
                    "name": _value("USB Cable"),
                    "quantity": _value("2", "2"),
                    "amount": _value("200", "200"),
                    "unit_price": _value("100", "100"),
                    "total": None,
                }
            ],
            "subtotal": _value("200", "200"),
            "tax": None,
            "discount": None,
            "total": _value("₹236", "236"),
            "payment_method": _value("UPI"),
            "currency": _value("INR", "INR"),
        }
        result = validate_extraction("purchase_receipt", data)
        self.assertIsInstance(result, PurchaseReceiptExtraction)
        self.assertEqual(result.merchant.raw, "ElectroMart")
        self.assertEqual(result.purchase_date.normalized, "2026-03-05")
        self.assertEqual(result.transaction_date.normalized, "2026-03-05")
        self.assertEqual(len(result.items or []), 1)
        self.assertEqual(result.items[0].name.raw, "USB Cable")
        self.assertEqual(result.items[0].amount.normalized, "200")
        self.assertEqual(result.total.normalized, "236")
        self.assertEqual(result.payment_method.raw, "UPI")


class WarrantySchemaTests(unittest.TestCase):
    def test_warranty_product_fields(self) -> None:
        data = {
            "document_type": _value("warranty"),
            "product": _value("Blender Pro"),
            "brand": _value("Acme"),
            "model": _value("BP-200"),
            "serial_number": _value("SN99881"),
            "warranty_provider": _value("Acme Care"),
            "purchase_date": _value("01 Feb 2025", "2025-02-01"),
            "warranty_start": _value("01 Feb 2025", "2025-02-01"),
            "warranty_expiry": _value("01 Feb 2027", "2027-02-01"),
            "warranty_duration": _value("2 years"),
        }
        result = validate_extraction("warranty", data)
        self.assertIsInstance(result, WarrantyExtraction)
        self.assertEqual(result.product.raw, "Blender Pro")
        self.assertEqual(result.brand.raw, "Acme")
        self.assertEqual(result.model.raw, "BP-200")
        self.assertEqual(result.serial_number.raw, "SN99881")
        self.assertEqual(result.warranty_provider.raw, "Acme Care")
        self.assertEqual(result.warranty_expiry.normalized, "2027-02-01")


class GenericSchemaTests(unittest.TestCase):
    def test_unknown_extra_fields_ignored_and_nulls_allowed(self) -> None:
        data = {
            "document_type": _value("generic"),
            "provider": None,
            "title": None,
            "document_date": None,
            "key_values": None,
            "unexpected_field": "should be ignored",
        }
        result = validate_extraction("generic", data)
        self.assertIsInstance(result, GenericExtraction)
        self.assertIsNone(result.provider)
        self.assertIsNone(result.title)
        self.assertIsNone(result.key_values)


class ClassificationAndGuessTests(unittest.TestCase):
    def test_classify_stable_ids(self) -> None:
        self.assertEqual(classify_document("Car Insurance Policy Premium"), "car_insurance")
        self.assertEqual(classify_document("HEALTH INSURANCE POLICY"), "health_insurance")
        self.assertEqual(classify_document("Amount Due on this electricity bill"), "utility_bill")
        self.assertEqual(classify_document("Store receipt invoice"), "purchase_receipt")
        self.assertEqual(classify_document("Product warranty card"), "warranty")
        self.assertEqual(classify_document("Misc note"), "generic")
        self.assertEqual(classify_document("General life insurance policy"), "insurance")

    def test_normalize_legacy_labels(self) -> None:
        self.assertEqual(normalize_document_type("Bill"), "utility_bill")
        self.assertEqual(normalize_document_type("Insurance"), "insurance")
        self.assertEqual(normalize_document_type("Car Insurance"), "car_insurance")
        self.assertEqual(normalize_document_type("Health Insurance"), "health_insurance")
        self.assertEqual(normalize_document_type("Purchase"), "purchase_receipt")
        self.assertEqual(normalize_document_type("Warranty"), "warranty")
        self.assertEqual(normalize_document_type("Important document"), "generic")

    def test_insurance_subtype_display_and_schema(self) -> None:
        self.assertEqual(display_document_type("car_insurance"), "Car Insurance")
        self.assertEqual(display_document_type("health_insurance"), "Health Insurance")
        health = guess_fields(
            [
                (
                    1,
                    "HEALTH INSURANCE POLICY\nProvider: SecureCare\nPolicy Number: SCI-1\n"
                    "Start Date: 01 Sep 2026\nExpiry Date: 31 Aug 2027\nPremium: 18500\n",
                )
            ]
        )
        self.assertEqual(health["documentType"].raw, "health_insurance")
        validated = validate_extraction("health_insurance", build_structured_payload("health_insurance", health))
        self.assertIsInstance(validated, InsuranceExtraction)
        car = guess_fields([(1, "Car Insurance Policy\nMotor cover premium due\nPolicy Number: CAR-9\n")])
        self.assertEqual(car["documentType"].raw, "car_insurance")
        self.assertEqual(display_document_type(car["documentType"].raw), "Car Insurance")

    def test_guess_fields_utility_bill_does_not_set_policy_premium_as_insurance(self) -> None:
        pages = [
            (
                1,
                "City Power Utility Bill\nAccount Number: ACC-9001\nAmount Due: ₹1,245.00\nDue Date: 15/10/2026\n",
            )
        ]
        fields = guess_fields(pages)
        self.assertEqual(fields["documentType"].raw, "utility_bill")
        self.assertTrue(fields["amount_due"].raw)
        self.assertTrue(fields["due_date"].raw)
        self.assertNotIn("policy_number", fields)
        # Must NOT invent insurance-shaped legacy aliases for utility bills.
        self.assertNotIn("policyNumber", fields)
        self.assertNotIn("startDate", fields)
        self.assertNotIn("expiryDate", fields)
        self.assertNotIn("premium", fields)
        payload = build_structured_payload("utility_bill", fields)
        self.assertNotIn("policyNumber", payload)
        self.assertNotIn("premium", payload)
        self.assertNotIn("startDate", payload)
        self.assertNotIn("expiryDate", payload)


class UtilityBillEndToEndRegressionTests(unittest.TestCase):
    """Regression for utility_bill_test.pdf style content (DOC-005 E2E)."""

    SAMPLE = (
        "UTILITY BILL\n"
        "Bengaluru Power & Light Services\n"
        "Bill Number: BPL-2026-091842\n"
        "Customer ID: CUST-458921\n"
        "Billing Period: 01 Aug 2026 - 31 Aug 2026\n"
        "Due Date: 15 Sep 2026\n"
        "Amount Due: ₹1,245.00\n"
        "Service Address: 42 Example Road, Bengaluru, Karnataka\n"
    )

    def test_utility_bill_extraction_matches_expected_fields(self) -> None:
        pages = [(1, self.SAMPLE)]
        fields = guess_fields(pages)

        self.assertEqual(fields["documentType"].raw, "utility_bill")
        self.assertEqual(fields["provider"].raw, "Bengaluru Power & Light Services")
        self.assertNotEqual(fields["provider"].raw.upper(), "UTILITY BILL")
        self.assertEqual(fields["bill_number"].raw, "BPL-2026-091842")
        self.assertEqual(fields["customer_id"].raw, "CUST-458921")
        self.assertEqual(fields["billing_period_start"].raw, "01 Aug 2026")
        self.assertEqual(fields["billing_period_start"].normalized, "2026-08-01")
        self.assertEqual(fields["billing_period_end"].raw, "31 Aug 2026")
        self.assertEqual(fields["billing_period_end"].normalized, "2026-08-31")
        self.assertEqual(fields["due_date"].raw, "15 Sep 2026")
        self.assertEqual(fields["due_date"].normalized, "2026-09-15")
        self.assertEqual(fields["amount_due"].normalized, "1245")
        self.assertEqual(fields["service_address"].raw, "42 Example Road, Bengaluru, Karnataka")

        # Evidence / confidence preserved on found values.
        self.assertGreater(fields["amount_due"].confidence, 0)
        self.assertIn("Amount Due", fields["amount_due"].evidence)
        self.assertEqual(fields["amount_due"].page, 1)

        # No insurance-shaped pollution.
        for banned in ("policyNumber", "startDate", "expiryDate", "premium", "policy_number"):
            self.assertNotIn(banned, fields)

        payload = build_structured_payload("utility_bill", fields)
        validated = validate_extraction("utility_bill", payload)
        self.assertIsInstance(validated, UtilityBillExtraction)
        self.assertEqual(validated.provider.raw, "Bengaluru Power & Light Services")
        self.assertEqual(validated.bill_number.raw, "BPL-2026-091842")
        self.assertEqual(validated.customer_id.raw, "CUST-458921")
        self.assertEqual(validated.billing_period_start.normalized, "2026-08-01")
        self.assertEqual(validated.billing_period_end.normalized, "2026-08-31")
        self.assertEqual(validated.due_date.normalized, "2026-09-15")
        self.assertEqual(validated.amount_due.normalized, "1245")
        self.assertEqual(validated.service_address.raw, "42 Example Road, Bengaluru, Karnataka")
        self.assertEqual(validated.document_type.normalized, "utility_bill")

        dumped = validated.model_dump(mode="json")
        for banned in ("policyNumber", "startDate", "expiryDate", "premium"):
            self.assertNotIn(banned, dumped)


class PurchaseReceiptEndToEndRegressionTests(unittest.TestCase):
    SAMPLE = (
        "PURCHASE RECEIPT\n"
        "Merchant: TechWorld Electronics\n"
        "Receipt Number: TW-REC-2026-004581\n"
        "Purchase Date: 18 Sep 2026\n"
        "Item 1: 27-inch Monitor — Qty 1 — ₹24,000\n"
        "Item 2: Mechanical Keyboard — Qty 1 — ₹8,000\n"
        "Item 3: Wireless Mouse — Qty 2 — ₹5,000 each\n"
        "Subtotal: ₹42,000.00\n"
        "Tax: ₹7,560.00\n"
        "Total: ₹49,560.00\n"
        "Payment Method: Credit Card\n"
    )

    def test_purchase_receipt_does_not_use_insurance_fields(self) -> None:
        fields = guess_fields([(1, self.SAMPLE)])
        self.assertEqual(fields["documentType"].raw, "purchase_receipt")
        self.assertEqual(fields["merchant"].raw, "TechWorld Electronics")
        self.assertNotEqual(fields["merchant"].raw.upper(), "PURCHASE RECEIPT")
        self.assertEqual(fields["receipt_number"].raw, "TW-REC-2026-004581")
        self.assertEqual(fields["purchase_date"].raw, "18 Sep 2026")
        self.assertEqual(fields["purchase_date"].normalized, "2026-09-18")
        # Purchase Date must not be aliased into transaction_date.
        self.assertFalse(bool(fields.get("transaction_date") and fields["transaction_date"].raw))
        self.assertEqual(fields["subtotal"].normalized, "42000")
        self.assertEqual(fields["tax"].normalized, "7560")
        self.assertEqual(fields["total"].normalized, "49560")
        self.assertEqual(fields["payment_method"].raw, "Credit Card")

        for banned in ("policyNumber", "startDate", "expiryDate", "premium", "provider"):
            self.assertNotIn(banned, fields)

        payload = build_structured_payload("purchase_receipt", fields)
        validated = validate_extraction("purchase_receipt", payload)
        self.assertIsInstance(validated, PurchaseReceiptExtraction)
        self.assertEqual(validated.merchant.raw, "TechWorld Electronics")
        self.assertEqual(validated.receipt_number.raw, "TW-REC-2026-004581")
        self.assertEqual(validated.purchase_date.normalized, "2026-09-18")
        self.assertIsNone(validated.transaction_date)
        self.assertEqual(len(validated.items or []), 3)
        self.assertEqual(validated.items[0].name.raw, "27-inch Monitor")
        self.assertEqual(validated.items[0].quantity.normalized, "1")
        self.assertEqual(validated.items[0].amount.normalized, "24000")
        self.assertEqual(validated.items[1].name.raw, "Mechanical Keyboard")
        self.assertEqual(validated.items[2].name.raw, "Wireless Mouse")
        self.assertEqual(validated.items[2].quantity.normalized, "2")
        self.assertEqual(validated.items[2].amount.normalized, "5000")
        self.assertEqual(validated.subtotal.normalized, "42000")
        self.assertEqual(validated.tax.normalized, "7560")
        self.assertEqual(validated.total.normalized, "49560")
        self.assertEqual(validated.payment_method.raw, "Credit Card")

        dumped = validated.model_dump(mode="json")
        for banned in ("policyNumber", "startDate", "expiryDate", "premium", "provider"):
            self.assertNotIn(banned, dumped)

    def test_ocr_rupee_as_i_amounts_and_items(self) -> None:
        """Regression: OCR often renders ₹ as the letter I before digits."""
        sample = (
            "PURCHASE RECEIPT\n"
            "Merchant: TechWorld Electronics\n"
            "Receipt Number: TW-REC-2026-004581\n"
            "Purchase Date: 18 Sep 2026\n"
            "Item 1: 27-inch Monitor — Qty 1 — I24,000\n"
            "Item 2: Mechanical Keyboard — Qty 1 — I8,000\n"
            "Item 3: Wireless Mouse — Qty 2 — I5,000 each\n"
            "Subtotal: I42,000.00\n"
            "Tax: I7,560.00\n"
            "Total: I49,560.00\n"
            "Payment Method: Credit Card\n"
        )
        self.assertEqual(normalize_amount("I42,000.00"), "42000")
        self.assertEqual(normalize_amount("I7,560.00"), "7560")
        self.assertEqual(normalize_amount("₹49,560.00"), "49560")
        self.assertEqual(normalize_amount("INR 49,560.00"), "49560")
        from app.modules.documents.extract import canonicalize_amount_raw

        self.assertEqual(canonicalize_amount_raw("I42,000.00"), "INR 42,000.00")
        self.assertEqual(canonicalize_amount_raw("₹7,560.00"), "INR 7,560.00")
        self.assertEqual(canonicalize_amount_raw("INR49560"), "INR 49560")
        self.assertEqual(canonicalize_amount_raw("INR 49,560.00"), "INR 49,560.00")

        fields = guess_fields([(1, sample)])
        self.assertEqual(fields["documentType"].raw, "purchase_receipt")
        self.assertEqual(fields["merchant"].raw, "TechWorld Electronics")
        self.assertEqual(fields["subtotal"].raw, "INR 42,000.00")
        self.assertEqual(fields["tax"].raw, "INR 7,560.00")
        self.assertEqual(fields["total"].raw, "INR 49,560.00")
        self.assertEqual(fields["subtotal"].normalized, "42000")
        self.assertEqual(fields["tax"].normalized, "7560")
        self.assertEqual(fields["total"].normalized, "49560")
        self.assertEqual(fields["currency"].normalized, "INR")

        payload = build_structured_payload("purchase_receipt", fields)
        validated = validate_extraction("purchase_receipt", payload)
        self.assertEqual(len(validated.items or []), 3)
        self.assertEqual(validated.items[0].amount.raw, "INR 24,000")
        self.assertEqual(validated.items[0].amount.normalized, "24000")
        self.assertEqual(validated.items[1].amount.normalized, "8000")
        self.assertEqual(validated.items[2].amount.normalized, "5000")
        self.assertEqual(validated.subtotal.normalized, "42000")
        self.assertEqual(validated.tax.normalized, "7560")
        self.assertEqual(validated.total.normalized, "49560")

    def test_ocr_rupee_as_i_table_layout_amounts(self) -> None:
        """Label and amount on separate lines (common PDF table extraction)."""
        sample = (
            "PURCHASE RECEIPT\n"
            "Merchant: TechWorld Electronics\n"
            "Receipt Number: TW-REC-2026-004581\n"
            "Purchase Date: 18 Sep 2026\n"
            "Item 1: 27-inch Monitor — Qty 1 — I24,000\n"
            "Subtotal\n"
            "I42,000.00\n"
            "Tax\n"
            "I7,560.00\n"
            "Total\n"
            "I49,560.00\n"
            "Payment Method: Credit Card\n"
        )
        fields = guess_fields([(1, sample)])
        self.assertEqual(fields["subtotal"].normalized, "42000")
        self.assertEqual(fields["tax"].normalized, "7560")
        self.assertEqual(fields["total"].normalized, "49560")


class WarrantyEndToEndRegressionTests(unittest.TestCase):
    """Regression for warranty_doc005_test.pdf style content (DOC-005 E2E)."""

    SAMPLE = (
        "WARRANTY CERTIFICATE\n"
        "Product: UltraView 27-inch 4K Monitor\n"
        "Brand: UltraView\n"
        "Model: UV-27-4K-2026\n"
        "Serial Number: UV27SN884291\n"
        "Warranty Provider: TechWorld Electronics\n"
        "Purchase Date: 18 Sep 2026\n"
        "Warranty Start: 18 Sep 2026\n"
        "Warranty Expiry: 17 Sep 2028\n"
        "Warranty Duration: 24 months\n"
    )

    def test_warranty_extraction_matches_expected_fields(self) -> None:
        fields = guess_fields([(1, self.SAMPLE)])
        self.assertEqual(fields["documentType"].raw, "warranty")
        self.assertEqual(fields["product"].raw, "UltraView 27-inch 4K Monitor")
        self.assertEqual(fields["brand"].raw, "UltraView")
        self.assertEqual(fields["model"].raw, "UV-27-4K-2026")
        self.assertEqual(fields["serial_number"].raw, "UV27SN884291")
        self.assertEqual(fields["warranty_provider"].raw, "TechWorld Electronics")
        self.assertEqual(fields["purchase_date"].raw, "18 Sep 2026")
        self.assertEqual(fields["purchase_date"].normalized, "2026-09-18")
        self.assertEqual(fields["warranty_start"].raw, "18 Sep 2026")
        self.assertEqual(fields["warranty_start"].normalized, "2026-09-18")
        self.assertEqual(fields["warranty_expiry"].raw, "17 Sep 2028")
        self.assertEqual(fields["warranty_expiry"].normalized, "2028-09-17")
        self.assertEqual(fields["warranty_duration"].raw, "24 months")

        # Serial must NOT alias into policyNumber; no insurance-shaped flats.
        for banned in (
            "policyNumber",
            "startDate",
            "expiryDate",
            "premium",
            "provider",
            "policy_number",
            "product_name",
            "model_number",
            "warranty_end",
        ):
            self.assertNotIn(banned, fields)

        payload = build_structured_payload("warranty", fields)
        validated = validate_extraction("warranty", payload)
        self.assertIsInstance(validated, WarrantyExtraction)
        self.assertEqual(validated.product.raw, "UltraView 27-inch 4K Monitor")
        self.assertEqual(validated.brand.raw, "UltraView")
        self.assertEqual(validated.model.raw, "UV-27-4K-2026")
        self.assertEqual(validated.serial_number.raw, "UV27SN884291")
        self.assertEqual(validated.warranty_provider.raw, "TechWorld Electronics")
        self.assertEqual(validated.purchase_date.normalized, "2026-09-18")
        self.assertEqual(validated.warranty_start.normalized, "2026-09-18")
        self.assertEqual(validated.warranty_expiry.normalized, "2028-09-17")
        self.assertEqual(validated.warranty_duration.raw, "24 months")
        self.assertEqual(validated.document_type.normalized, "warranty")

        dumped = validated.model_dump(mode="json")
        for banned in (
            "policyNumber",
            "startDate",
            "expiryDate",
            "premium",
            "provider",
            "product_name",
            "model_number",
            "warranty_end",
        ):
            self.assertNotIn(banned, dumped)


class ClassificationAndGuessExtraTests(unittest.TestCase):
    def test_guess_fields_does_not_fabricate_empty_complex_items(self) -> None:
        pages = [(1, "ElectroMart Receipt\nTotal: ₹500.00\nDate: 05/03/2026\n")]
        fields = guess_fields(pages)
        self.assertEqual(fields["documentType"].raw, "purchase_receipt")
        payload = build_structured_payload("purchase_receipt", fields)
        self.assertIsNone(payload.get("items"))
        validated = validate_extraction("purchase_receipt", payload)
        self.assertIsNone(validated.items)

    def test_empty_field_stays_null_in_payload(self) -> None:
        fields = {
            "documentType": FieldHit("generic", "generic", 0.5, "", 1),
            "provider": empty_field(),
            "title": empty_field(),
            "document_date": empty_field(),
            "key_values": empty_field(),
        }
        payload = build_structured_payload("generic", fields)
        self.assertIsNone(payload["provider"])
        self.assertIsNone(payload["title"])
        validated = validate_extraction("generic", payload)
        self.assertIsNone(validated.provider)


class DocumentPreviewTests(unittest.TestCase):
    """Left-panel preview must include the full parsed document text."""

    INSURANCE_SAMPLE = (
        "HEALTH INSURANCE POLICY\n"
        "SYNTHETIC TEST DOCUMENT — FOR DOC-005 EXTRACTION TESTING\n"
        "Field\n"
        "Value\n"
        "Provider\n"
        "SecureCare Insurance Pvt. Ltd.\n"
        "Policy Number\n"
        "SCI-HLTH-2026-778812\n"
        "Policy Holder\n"
        "Test Customer\n"
        "Start Date\n"
        "01 Sep 2026\n"
        "Expiry Date\n"
        "31 Aug 2027\n"
        "Premium\n"
        "₹18,500.00\n"
        "Coverage Amount\n"
        "₹5,00,000.00\n"
    )

    def test_preview_includes_lines_beyond_former_eight_line_cap(self) -> None:
        from app.modules.documents.service import build_preview_lines

        lines = build_preview_lines(self.INSURANCE_SAMPLE)
        joined = "\n".join(lines)
        self.assertGreater(len(lines), 8)
        self.assertIn("Policy Holder", joined)
        self.assertIn("Test Customer", joined)
        self.assertIn("Start Date", joined)
        self.assertIn("01 Sep 2026", joined)
        self.assertIn("Expiry Date", joined)
        self.assertIn("31 Aug 2027", joined)
        self.assertIn("Premium", joined)
        self.assertIn("18,500.00", joined)
        self.assertIn("Coverage Amount", joined)
        self.assertIn("5,00,000.00", joined)

    def test_preview_preserves_order_of_all_nonempty_lines(self) -> None:
        from app.modules.documents.service import build_preview_lines

        lines = build_preview_lines(self.INSURANCE_SAMPLE)
        self.assertEqual(lines[0], "HEALTH INSURANCE POLICY")
        self.assertEqual(lines[-1], "₹5,00,000.00")


if __name__ == "__main__":
    unittest.main()
