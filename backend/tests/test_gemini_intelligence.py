from unittest import TestCase

from app.modules.documents.text import FieldHit
from app.modules.intelligence.gemini import GeminiIntelligenceProvider
from app.modules.intelligence.important import canonicalize_key, important_keys_for
from app.modules.intelligence.types import NormalizedDocument
from app.modules.intelligence.validate import validate_extracted_fields


def _doc(text: str, *, is_image: bool = False, page_count: int = 1) -> NormalizedDocument:
    pages = [(index + 1, text) for index in range(page_count)]
    return NormalizedDocument(
        pages=pages,
        is_pdf=not is_image,
        is_image=is_image,
        page_count=page_count,
        filename="bill.pdf" if not is_image else "bill.jpg",
    )


class FakeGeminiClient:
    def __init__(self, understand: dict, extract: dict) -> None:
        self.understand = understand
        self.extract = extract
        self.calls = 0

    def generate_json(self, contents, schema):
        del contents
        self.calls += 1
        if self.calls == 1:
            schema.model_validate(self.understand)
            return self.understand
        schema.model_validate(self.extract)
        return self.extract


ELECTRICITY_TEXT = """
BESCOM Electricity Bill
Service No: 123456789
Previous balance        ₹1,850
Current charges         ₹2,400
Tax                       ₹200
Total                   ₹4,450
Payment received        ₹1,850
AMOUNT PAYABLE          ₹2,600
Pay before: 30/09/2026
"""


class GeminiIntelligenceTests(TestCase):
    def test_two_pass_keeps_only_actionable_bill_fields(self) -> None:
        client = FakeGeminiClient(
            {
                "document_type": "electricity_bill",
                "document_purpose": "Pay the current electricity bill",
                "status": "supported",
                "reason": "This is an electricity bill. Track the service number, amount payable, and due date.",
                "confidence": 0.96,
                "important_fields": [
                    {"key": "service_number", "label": "Service Number", "kind": "id", "reason": "Account identifier"},
                    {"key": "amount_due", "label": "Amount to Pay", "kind": "amount", "reason": "Current amount payable"},
                    {"key": "due_date", "label": "Pay Before", "kind": "date", "reason": "Payment deadline"},
                ],
            },
            {
                "fields": [
                    {
                        "key": "service_number",
                        "label": "Service Number",
                        "value": "123456789",
                        "normalized_value": "123456789",
                        "currency": "",
                        "confidence": 0.99,
                        "evidence_text": "Service No: 123456789",
                        "evidence_page": 1,
                    },
                    {
                        "key": "amount_due",
                        "label": "Amount to Pay",
                        "value": "2600",
                        "normalized_value": "2600",
                        "currency": "INR",
                        "confidence": 0.98,
                        "evidence_text": "AMOUNT PAYABLE ₹2,600",
                        "evidence_page": 1,
                    },
                    {
                        "key": "due_date",
                        "label": "Pay Before",
                        "value": "30/09/2026",
                        "normalized_value": "2026-09-30",
                        "currency": "",
                        "confidence": 0.97,
                        "evidence_text": "Pay before: 30/09/2026",
                        "evidence_page": 1,
                    },
                    {
                        "key": "tax",
                        "label": "Tax",
                        "value": "200",
                        "normalized_value": "200",
                        "currency": "INR",
                        "confidence": 0.9,
                        "evidence_text": "Tax ₹200",
                        "evidence_page": 1,
                    },
                ]
            },
        )
        provider = GeminiIntelligenceProvider(client=client)
        result = provider.analyze(_doc(ELECTRICITY_TEXT))
        self.assertEqual(client.calls, 2)
        self.assertEqual(result.decision.status, "supported")
        self.assertEqual(result.decision.document_type, "utility_bill")
        self.assertEqual(result.fields["amount_due"].normalized, "2600")
        self.assertEqual(result.fields["due_date"].normalized, "2026-09-30")
        self.assertEqual(result.important_keys, ["service_number", "amount_due", "due_date"])
        self.assertNotIn("tax", result.important_keys)

    def test_validation_drops_invented_values(self) -> None:
        source = "AMOUNT PAYABLE ₹2,600\nPay before: 30/09/2026"
        fields = {
            "amount_due": FieldHit("999999", "999999", 0.99, "AMOUNT PAYABLE ₹2,600", 1),
            "due_date": FieldHit("30/09/2026", "2026-09-30", 0.97, "Pay before: 30/09/2026", 1),
        }
        cleaned = validate_extracted_fields(fields, source)
        self.assertNotIn("amount_due", cleaned)
        self.assertEqual(cleaned["due_date"].normalized, "2026-09-30")

    def test_local_important_keys_prefer_actionable_bill_fields(self) -> None:
        fields = {
            "customer_id": FieldHit("123456789", "123456789", 0.9, "Customer ID: 123456789", 1),
            "amount_due": FieldHit("INR 2600", "2600", 0.9, "AMOUNT PAYABLE ₹2,600", 1),
            "due_date": FieldHit("30/09/2026", "2026-09-30", 0.9, "Pay before: 30/09/2026", 1),
            "service_address": FieldHit("42 Example Road", "42 Example Road", 0.8, "Service Address: 42 Example Road", 1),
            "previous_balance": FieldHit("1850", "1850", 0.8, "Previous balance ₹1,850", 1),
        }
        keys = important_keys_for("utility_bill", fields)
        self.assertIn("amount_due", keys)
        self.assertIn("due_date", keys)
        self.assertNotIn("service_address", keys)
        self.assertNotIn("previous_balance", keys)

    def test_camel_case_keys_merge_and_insurance_hides_provider(self) -> None:
        self.assertEqual(canonicalize_key("policyNumber"), "policy_number")
        self.assertEqual(canonicalize_key("expiryDate"), "expiry_date")
        fields = {
            "policy_number": FieldHit("HLT-TST-2026-7788", "HLT-TST-2026-7788", 0.99, "Policy No HLT-TST-2026-7788", 1),
            "policyNumber": FieldHit("HLT-TST-2026-7788", "HLT-TST-2026-7788", 0.9, "Policy No HLT-TST-2026-7788", 1),
            "provider": FieldHit("Family Health Insurance", "Family Health Insurance", 0.8, "Family Health Insurance", 1),
            "premium": FieldHit("INR 32,400", "32400", 0.95, "Premium INR 32,400", 1),
            "coverage": FieldHit("INR 15,00,000", "1500000", 0.94, "Sum Insured INR 15,00,000", 1),
            "effective_date": FieldHit("01/04/2026", "2026-04-01", 0.93, "01/04/2026", 1),
            "expiry_date": FieldHit("31/03/2027", "2027-03-31", 0.93, "31/03/2027", 1),
            "expiryDate": FieldHit("31/03/2027", "2027-03-31", 0.9, "31/03/2027", 1),
        }
        keys = important_keys_for("health_insurance", fields)
        self.assertEqual(keys.count("policy_number"), 1)
        self.assertNotIn("policyNumber", keys)
        self.assertEqual(keys.count("expiry_date"), 1)
        self.assertNotIn("expiryDate", keys)
        self.assertNotIn("provider", keys)
        self.assertIn("premium", keys)
        self.assertIn("coverage", keys)

    def test_gemini_dedupes_policy_number_aliases(self) -> None:
        client = FakeGeminiClient(
            {
                "document_type": "health_insurance_policy",
                "document_purpose": "Track policy renewal",
                "status": "supported",
                "reason": "Health insurance policy.",
                "confidence": 0.95,
                "important_fields": [
                    {"key": "policy_number", "label": "Policy Number", "kind": "id", "reason": ""},
                    {"key": "policyNumber", "label": "Policy Number", "kind": "id", "reason": ""},
                    {"key": "provider", "label": "Provider", "kind": "text", "reason": ""},
                    {"key": "premium", "label": "Premium", "kind": "amount", "reason": ""},
                    {"key": "expiry_date", "label": "Expiry Date", "kind": "date", "reason": ""},
                    {"key": "expiryDate", "label": "Expiry Date", "kind": "date", "reason": ""},
                ],
            },
            {
                "fields": [
                    {
                        "key": "policy_number",
                        "label": "Policy Number",
                        "value": "HLT-TST-2026-7788",
                        "normalized_value": "HLT-TST-2026-7788",
                        "currency": "",
                        "confidence": 0.99,
                        "evidence_text": "Policy No HLT-TST-2026-7788",
                        "evidence_page": 1,
                    },
                    {
                        "key": "policyNumber",
                        "label": "Policy Number",
                        "value": "HLT-TST-2026-7788",
                        "normalized_value": "HLT-TST-2026-7788",
                        "currency": "",
                        "confidence": 0.9,
                        "evidence_text": "Policy No HLT-TST-2026-7788",
                        "evidence_page": 1,
                    },
                    {
                        "key": "provider",
                        "label": "Provider",
                        "value": "Family Health Insurance",
                        "normalized_value": "Family Health Insurance",
                        "currency": "",
                        "confidence": 0.8,
                        "evidence_text": "Family Health Insurance",
                        "evidence_page": 1,
                    },
                    {
                        "key": "premium",
                        "label": "Premium",
                        "value": "32400",
                        "normalized_value": "32400",
                        "currency": "INR",
                        "confidence": 0.95,
                        "evidence_text": "Premium INR 32,400",
                        "evidence_page": 1,
                    },
                    {
                        "key": "expiryDate",
                        "label": "Expiry Date",
                        "value": "31/03/2027",
                        "normalized_value": "2027-03-31",
                        "currency": "",
                        "confidence": 0.94,
                        "evidence_text": "31/03/2027",
                        "evidence_page": 1,
                    },
                    {
                        "key": "expiry_date",
                        "label": "Expiry Date",
                        "value": "31/03/2027",
                        "normalized_value": "2027-03-31",
                        "currency": "",
                        "confidence": 0.93,
                        "evidence_text": "31/03/2027",
                        "evidence_page": 1,
                    },
                ]
            },
        )
        provider = GeminiIntelligenceProvider(client=client)
        result = provider.analyze(
            _doc("Family Health Insurance\nPolicy No HLT-TST-2026-7788\nPremium INR 32,400\n31/03/2027")
        )
        self.assertEqual(result.important_keys.count("policy_number"), 1)
        self.assertNotIn("policyNumber", result.important_keys)
        self.assertEqual(result.important_keys.count("expiry_date"), 1)
        self.assertNotIn("expiryDate", result.important_keys)
        self.assertNotIn("provider", result.important_keys)

    def test_too_many_pages_skips_model(self) -> None:
        client = FakeGeminiClient({"document_type": "unknown"}, {"fields": []})
        provider = GeminiIntelligenceProvider(client=client)
        result = provider.analyze(_doc("hello", page_count=40))
        self.assertEqual(result.decision.status, "rejected")
        self.assertEqual(result.decision.reason, "Invalid document. Try uploading another.")
        self.assertEqual(client.calls, 0)

    def test_photo_of_bill_is_supported_even_if_model_says_unknown(self) -> None:
        client = FakeGeminiClient(
            {
                "document_type": "mobile_postpaid_bill",
                "document_purpose": "Pay the mobile bill",
                "status": "unknown",
                "reason": "This is a photo.",
                "confidence": 0.55,
                "important_fields": [
                    {"key": "amount_due", "label": "Amount Payable", "kind": "amount", "reason": ""},
                    {"key": "due_date", "label": "Due Date", "kind": "date", "reason": ""},
                    {"key": "mobile_number", "label": "Mobile", "kind": "id", "reason": ""},
                ],
            },
            {
                "fields": [
                    {
                        "key": "amount_due",
                        "label": "Amount Payable",
                        "value": "942.82",
                        "normalized_value": "942.82",
                        "currency": "INR",
                        "confidence": 0.98,
                        "evidence_text": "AMOUNT PAYABLE: INR 942.82",
                        "evidence_page": 1,
                    },
                    {
                        "key": "due_date",
                        "label": "Due Date",
                        "value": "29/09/2026",
                        "normalized_value": "2026-09-30",
                        "currency": "",
                        "confidence": 0.96,
                        "evidence_text": "Due: 29/09/2026",
                        "evidence_page": 1,
                    },
                    {
                        "key": "mobile_number",
                        "label": "Mobile",
                        "value": "+91 90000 00001",
                        "normalized_value": "+91 90000 00001",
                        "currency": "",
                        "confidence": 0.9,
                        "evidence_text": "Mobile: +91 90000 00001",
                        "evidence_page": 1,
                    },
                ]
            },
        )
        provider = GeminiIntelligenceProvider(client=client)
        result = provider.analyze(
            _doc(
                "MOBILE POSTPAID BILL\nAMOUNT PAYABLE: INR 942.82\nDue: 29/09/2026",
                is_image=True,
            )
        )
        self.assertEqual(result.decision.status, "supported")
        self.assertEqual(result.decision.document_type, "utility_bill")
        self.assertEqual(result.fields["amount_due"].normalized, "942.82")
        self.assertEqual(client.calls, 2)

    def test_empty_photo_without_fields_stays_rejected(self) -> None:
        client = FakeGeminiClient(
            {
                "document_type": "unknown",
                "document_purpose": "",
                "status": "rejected",
                "reason": "Natural photo.",
                "confidence": 0.9,
                "important_fields": [],
            },
            {"fields": []},
        )
        provider = GeminiIntelligenceProvider(client=client)
        result = provider.analyze(_doc("", is_image=True))
        self.assertEqual(result.decision.status, "rejected")
        self.assertEqual(client.calls, 1)
