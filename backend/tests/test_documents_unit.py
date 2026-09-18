from types import SimpleNamespace

from app.modules.actions.suggest import suggestions_for
from app.modules.documents.extract import classify_document, normalize_amount, normalize_date
from app.modules.documents.validation import detect_mime, validate_file_type


def test_document_signatures_and_extensions_must_agree():
    assert detect_mime(b"%PDF-1.7") == "application/pdf"
    validate_file_type(".pdf", "application/pdf")
    try:
        validate_file_type(".png", "application/pdf")
    except ValueError as exc:
        assert "does not match" in str(exc)
    else:
        raise AssertionError("A mismatched extension must be rejected")


def test_extraction_normalizes_dates_and_amounts():
    assert normalize_date("12 October 2026") == "2026-10-12"
    assert normalize_date("31/02/2026") == ""
    assert normalize_amount("Rs. 4,850.00") == "4850.00"
    assert classify_document("Policy premium and insurance expiry") == "Insurance"


def test_reviewed_insurance_becomes_a_renewal_suggestion():
    field = lambda raw, normalized="": SimpleNamespace(raw_value=raw, normalized_value=normalized, page_number=1)
    document = SimpleNamespace(document_type="Insurance", original_filename="policy.pdf")
    suggestions = suggestions_for(document, {"provider": field("Acme Insurance"), "expiryDate": field("12 October 2026", "2026-10-12"), "premium": field("4850")})
    assert suggestions[0]["action_type"] == "RENEW"
    assert suggestions[0]["due_at"].isoformat() == "2026-10-12"
