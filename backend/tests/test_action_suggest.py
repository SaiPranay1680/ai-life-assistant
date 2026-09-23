from types import SimpleNamespace
from unittest import TestCase

from app.modules.actions.suggest import suggestions_for


def _field(raw: str, normalized: str = "") -> SimpleNamespace:
    return SimpleNamespace(raw_value=raw, normalized_value=normalized or raw, page_number=1)


class ActionSuggestTests(TestCase):
    def test_keep_record_uses_human_title_not_filename(self) -> None:
        document = SimpleNamespace(document_type="generic", original_filename="03_passport_sample.pdf")
        items = suggestions_for(document, {"documentType": _field("Important document")})
        self.assertEqual(items[0]["title"], "Keep passport on file")
        self.assertNotIn("03_passport_sample.pdf", items[0]["title"])
        self.assertNotIn("Source:", items[0]["evidence"])
        self.assertIn("No due date was confirmed", items[0]["explanation"])

    def test_keep_invoice_not_filename(self) -> None:
        document = SimpleNamespace(document_type="purchase_receipt", original_filename="dummy-laptop-invoice.pdf")
        items = suggestions_for(document, {"documentType": _field("Purchase")})
        self.assertEqual(items[0]["title"], "Keep invoice on file")
        self.assertNotIn("dummy-laptop-invoice.pdf", items[0]["title"])
