from unittest import TestCase

from app.modules.intelligence.local import classify_document, extract_fields
from app.modules.intelligence.types import NormalizedDocument


def _doc(text: str, *, is_image: bool = False, page_count: int = 1, filename: str = "demo.pdf") -> NormalizedDocument:
    pages = [(index + 1, text) for index in range(page_count)]
    return NormalizedDocument(
        pages=pages,
        is_pdf=not is_image,
        is_image=is_image,
        page_count=page_count,
        filename=filename,
    )


INSURANCE_TRAP = """
ICICI Lombard Motor Insurance
Policy Number: 3001/123456789
Policy Period: 12 Sep 2026 to 11 Sep 2027
Premium: ₹18,430
Sum Insured: ₹10,00,000
Vehicle: KA01AB1234
"""

ELECTRICITY_BILL = """
BESCOM Electricity Bill
Consumer Number: 1234567890
Bill Amount: ₹3,420
Due Date: 29 Sep 2026
"""

ASSIGNMENT = """
Machine Learning Assignment
Student: Rahul
Course: Computer Science
Submission Date: 30 September 2026
"""

LOREM = """
Lorem ipsum dolor sit amet, consectetur adipiscing elit.
Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
"""


class DocumentIntelligenceTests(TestCase):
    def test_insurance_is_supported(self) -> None:
        decision = classify_document(_doc(INSURANCE_TRAP))
        self.assertEqual(decision.status, "supported")
        self.assertEqual(decision.document_type, "Insurance")

    def test_premium_is_not_sum_insured(self) -> None:
        fields = extract_fields(_doc(INSURANCE_TRAP), "Insurance")
        self.assertEqual(fields["premium"].normalized, "18430")
        self.assertIn("premium", fields["premium"].evidence.lower())
        self.assertNotIn("10,00,000", fields["premium"].raw)

    def test_bill_extracts_due_amount(self) -> None:
        decision = classify_document(_doc(ELECTRICITY_BILL))
        self.assertEqual(decision.status, "supported")
        fields = extract_fields(_doc(ELECTRICITY_BILL), "Bill")
        self.assertEqual(fields["premium"].normalized, "3420")
        self.assertIn("29", fields["expiryDate"].raw)

    def test_assignment_is_unknown(self) -> None:
        decision = classify_document(_doc(ASSIGNMENT))
        self.assertEqual(decision.status, "unknown")
        fields = extract_fields(_doc(ASSIGNMENT), "Other")
        self.assertEqual((fields.get("premium").raw if fields.get("premium") else ""), "")
        self.assertIn("30", fields["expiryDate"].raw)

    def test_lorem_is_not_useful(self) -> None:
        decision = classify_document(_doc(LOREM))
        self.assertEqual(decision.status, "not_useful")

    def test_photo_without_text_is_rejected(self) -> None:
        decision = classify_document(_doc("sky", is_image=True, filename="family.jpg"))
        self.assertEqual(decision.status, "rejected")
        self.assertEqual(decision.category, "photo")

    def test_too_many_pages_is_rejected(self) -> None:
        decision = classify_document(_doc("hello", page_count=40))
        self.assertEqual(decision.status, "rejected")
        self.assertEqual(decision.category, "publication")
