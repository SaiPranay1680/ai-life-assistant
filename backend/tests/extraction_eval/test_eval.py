"""Unit + integration tests for EVAL-001 evaluator (not DOC-005 redesign)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.extraction_eval.comparator import (
    amount_to_decimal,
    amounts_equivalent,
    compare_actions,
    compare_field,
    compare_fields,
    confidence_report,
    dates_equivalent,
    evidence_matches,
)
from tests.extraction_eval.config import THRESHOLDS
from tests.extraction_eval.metrics import aggregate, build_document_metrics
from tests.extraction_eval.runner import (
    RESULTS_PATH,
    evaluate_document,
    run_evaluation,
    run_real_pipeline,
    thresholds_met,
)

PACKAGE = Path(__file__).resolve().parent
DOCUMENTS = PACKAGE / "documents"


class TestDateNormalization:
    def test_named_slash_and_iso_equivalent(self) -> None:
        assert dates_equivalent("18 Sep 2026", "18/09/2026")
        assert dates_equivalent("18/09/2026", "2026-09-18")
        assert dates_equivalent("18 Sep 2026", "2026-09-18")

    def test_different_dates_not_equivalent(self) -> None:
        assert not dates_equivalent("18 Sep 2026", "19 Sep 2026")
        assert not dates_equivalent("2026-09-18", "2026-09-19")


class TestAmountNormalization:
    def test_currency_and_ocr_variants(self) -> None:
        assert amounts_equivalent("₹42,000.00", "42000")
        assert amounts_equivalent("₹ 42,000", "42000.00")
        assert amounts_equivalent("42,000", "42000")
        assert amounts_equivalent("I42,000.00", "₹42,000.00")
        assert amounts_equivalent("INR 49,560.00", "49560")

    def test_decimal_quantize(self) -> None:
        assert amount_to_decimal("1245.00") == amount_to_decimal("1245")
        assert amount_to_decimal("980.50") is not None

    def test_different_amounts_not_equal(self) -> None:
        assert not amounts_equivalent("42000", "49560")


class TestFieldComparison:
    def test_correct_incorrect_missing(self) -> None:
        structured = {
            "merchant": {
                "raw": "TechWorld Electronics",
                "normalized": "TechWorld Electronics",
                "confidence": 0.9,
                "evidence": [{"page_number": 1, "snippet": "Merchant: TechWorld Electronics"}],
            },
            "total": {
                "raw": "INR 49,560.00",
                "normalized": "49560",
                "confidence": 0.9,
                "evidence": [{"page_number": 1, "snippet": "Total: INR 49,560.00"}],
            },
        }
        expected = {
            "merchant": {"normalized": "TechWorld Electronics", "page": 1},
            "total": {"normalized": "49560.00", "page": 1},
            "tax": {"normalized": "7560.00", "page": 1},
        }
        results = compare_fields(expected, structured)
        by_name = {row["field"]: row for row in results}
        assert by_name["merchant"]["status"] == "correct"
        assert by_name["total"]["status"] == "correct"
        assert by_name["tax"]["status"] == "missing"

    def test_incorrect_amount(self) -> None:
        row = compare_field(
            "total",
            {"normalized": "49560.00"},
            {"raw": "100", "normalized": "100", "confidence": 0.5, "evidence": []},
        )
        assert row["status"] == "incorrect"


class TestEvidenceValidation:
    def test_presence_page_and_substring(self) -> None:
        actual = {
            "raw": "INR 1,245.00",
            "normalized": "1245",
            "confidence": 0.9,
            "evidence": [{"page_number": 1, "snippet": "Amount Due: INR 1,245.00"}],
        }
        result = evidence_matches(
            {"normalized": "1245.00", "page": 1, "evidence_contains": "1,245"},
            actual,
        )
        assert result["presence_ok"]
        assert result["page_ok"]
        assert result["contains_ok"]

    def test_wrong_page_fails_page_check(self) -> None:
        actual = {
            "raw": "x",
            "normalized": "x",
            "evidence": [{"page_number": 2, "snippet": "x"}],
        }
        result = evidence_matches({"page": 1, "require_evidence": True}, actual)
        assert result["presence_ok"]
        assert not result["page_ok"]


class TestConfidenceValidation:
    def test_valid_and_invalid_confidence(self) -> None:
        structured = {
            "document_type": {"raw": "utility_bill", "normalized": "utility_bill", "confidence": 0.7},
            "provider": {
                "raw": "City Power",
                "normalized": "City Power",
                "confidence": 0.9,
                "evidence": [],
            },
            "bill_number": {
                "raw": "B-1",
                "normalized": "B-1",
                "confidence": 1.5,
                "evidence": [],
            },
            "due_date": {
                "raw": "15 Sep 2026",
                "normalized": "2026-09-15",
                "confidence": None,
                "evidence": [],
            },
        }
        report = confidence_report(structured)
        assert report["fields_with_confidence"] == 2
        assert report["fields_without_confidence"] == 1
        assert len(report["invalid_confidence_values"]) == 1
        assert report["invalid_confidence_values"][0]["field"] == "bill_number"


class TestActionDetection:
    def test_false_missing_duplicate(self) -> None:
        cmp = compare_actions(
            [{"action_type": "PAY"}],
            [{"action_type": "PAY"}, {"action_type": "PAY"}, {"action_type": "RENEW"}],
        )
        assert "RENEW" in cmp["false_actions"]
        assert "PAY" in cmp["duplicate_actions"]
        assert cmp["missing_actions"] == []

    def test_missing_action(self) -> None:
        cmp = compare_actions([{"action_type": "REVIEW"}], [])
        assert cmp["missing_actions"] == ["REVIEW"]

    def test_empty_expected_flags_false_actions(self) -> None:
        cmp = compare_actions([], [{"action_type": "PAY"}])
        assert cmp["false_actions"] == ["PAY"]


class TestClassificationComparison:
    def test_classification_via_evaluate_document(self) -> None:
        path = DOCUMENTS / "warranty_001.pdf"
        if not path.exists():
            pytest.skip("fixtures not generated")
        result = evaluate_document(path)
        assert result["expected_document_type"] == "warranty"
        assert result["actual_document_type"] == "warranty"
        assert result["classification_correct"] is True


@pytest.mark.extraction_eval
class TestIntegrationEvaluation:
    def test_real_pipeline_on_utility_bill(self) -> None:
        path = DOCUMENTS / "utility_bill_001.pdf"
        if not path.exists():
            pytest.skip("fixtures not generated")
        out = run_real_pipeline(path)
        assert out["document_type"] == "utility_bill"
        assert out["structured"]["provider"]["normalized"] == "Bengaluru Power & Light Services"
        assert amounts_equivalent(out["structured"]["amount_due"]["normalized"], "1245")

    def test_full_suite_writes_results_and_meets_thresholds(self) -> None:
        if not any(DOCUMENTS.glob("*.pdf")):
            pytest.skip("fixtures not generated")
        summary = run_evaluation(write_results=True)
        assert summary["documents_evaluated"] >= 10
        assert RESULTS_PATH.exists()
        payload = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
        assert "metrics" in payload
        assert "documents" in payload
        assert payload["documents_evaluated"] == summary["documents_evaluated"]
        assert payload["documents_evaluated"] >= 14  # 10 PDF + 4 DOCX fixtures
        # Soft floors (default 0.0) — raise THRESHOLDS deliberately for regression gates.
        assert thresholds_met(summary) == []
        assert THRESHOLDS["classification_accuracy"] == 0.0

        # Metrics object shape for machine consumers.
        for key in (
            "classification_accuracy",
            "field_accuracy",
            "date_accuracy",
            "amount_accuracy",
            "evidence_presence_accuracy",
            "evidence_page_accuracy",
        ):
            assert key in payload["metrics"]
            value = payload["metrics"][key]
            assert value is not None
            assert 0.0 <= value <= 1.0

        assert payload["by_document_type"]["generic"]["amount_accuracy"] is None
        assert payload["by_document_type"]["warranty"]["amount_accuracy"] is None
        assert payload["by_document_type"]["insurance"]["amount_accuracy"] == 1.0
        assert payload["by_document_type"]["purchase_receipt"]["amount_accuracy"] == 1.0
        assert payload["by_document_type"]["utility_bill"]["amount_accuracy"] == 1.0
        assert payload["metrics"]["amount_accuracy"] == 1.0
        assert payload["failures"] == []
        assert payload["actions"] == {"false_actions": 0, "missing_actions": 0, "duplicate_actions": 0}

        # Per-document: types without amounts must report null, not 0.0.
        for doc in payload["documents"]:
            if doc["expected_document_type"] in {"generic", "warranty"}:
                assert doc["metrics"]["amount_total"] == 0
                assert doc["metrics"]["amount_accuracy"] is None
                assert doc["passed"] is True

    def test_metrics_aggregate_counts(self) -> None:
        field_results = [
            {
                "field": "a",
                "status": "correct",
                "passed": True,
                "expected": "1",
                "actual": "1",
                "is_date": False,
                "is_amount": True,
                "evidence": {"presence_ok": True, "page_ok": True},
            },
            {
                "field": "b",
                "status": "missing",
                "passed": False,
                "expected": "2026-01-01",
                "actual": None,
                "is_date": True,
                "is_amount": False,
                "evidence": {"presence_ok": False, "page_ok": False},
            },
        ]
        metrics = build_document_metrics(field_results)
        assert metrics["correct_fields"] == 1
        assert metrics["missing_fields"] == 1
        summary = aggregate(
            [
                {
                    "filename": "x.pdf",
                    "expected_document_type": "utility_bill",
                    "actual_document_type": "utility_bill",
                    "classification_correct": True,
                    "passed": False,
                    "field_results": field_results,
                    "metrics": metrics,
                    "actions": {"false_actions": [], "missing_actions": [], "duplicate_actions": []},
                    "confidence": {"invalid_confidence_values": []},
                }
            ]
        )
        assert summary["documents_evaluated"] == 1
        assert summary["metrics"]["classification_accuracy"] == 1.0


class TestAmountAccuracyReporting:
    def test_amount_total_zero_yields_none(self) -> None:
        metrics = build_document_metrics(
            [
                {
                    "field": "product",
                    "status": "correct",
                    "passed": True,
                    "expected": "NoiseBuds",
                    "actual": "NoiseBuds",
                    "is_date": False,
                    "is_amount": False,
                    "evidence": {"presence_ok": True, "page_ok": True},
                }
            ]
        )
        assert metrics["amount_total"] == 0
        assert metrics["amount_accuracy"] is None

    def test_amount_total_positive_all_correct(self) -> None:
        metrics = build_document_metrics(
            [
                {
                    "field": "total",
                    "status": "correct",
                    "passed": True,
                    "expected": "49560",
                    "actual": "49560",
                    "is_date": False,
                    "is_amount": True,
                    "evidence": {"presence_ok": True, "page_ok": True},
                }
            ]
        )
        assert metrics["amount_total"] == 1
        assert metrics["amount_accuracy"] == 1.0

    def test_amount_total_positive_incorrect_is_below_one(self) -> None:
        metrics = build_document_metrics(
            [
                {
                    "field": "total",
                    "status": "incorrect",
                    "passed": False,
                    "expected": "49560",
                    "actual": "100",
                    "is_date": False,
                    "is_amount": True,
                    "evidence": {"presence_ok": True, "page_ok": True},
                },
                {
                    "field": "tax",
                    "status": "correct",
                    "passed": True,
                    "expected": "7560",
                    "actual": "7560",
                    "is_date": False,
                    "is_amount": True,
                    "evidence": {"presence_ok": True, "page_ok": True},
                },
            ]
        )
        assert metrics["amount_total"] == 2
        assert metrics["amount_incorrect"] == 1
        assert metrics["amount_accuracy"] == 0.5
        assert metrics["amount_accuracy"] < 1.0

    def test_generic_no_amounts_does_not_fail_aggregate(self) -> None:
        field_results = [
            {
                "field": "title",
                "status": "correct",
                "passed": True,
                "expected": "PASSPORT",
                "actual": "PASSPORT",
                "is_date": False,
                "is_amount": False,
                "evidence": {"presence_ok": True, "page_ok": True},
            }
        ]
        metrics = build_document_metrics(field_results)
        summary = aggregate(
            [
                {
                    "filename": "generic_001.pdf",
                    "expected_document_type": "generic",
                    "actual_document_type": "generic",
                    "classification_correct": True,
                    "passed": True,
                    "field_results": field_results,
                    "metrics": metrics,
                    "actions": {"false_actions": [], "missing_actions": [], "duplicate_actions": []},
                    "confidence": {"invalid_confidence_values": []},
                }
            ]
        )
        assert summary["by_document_type"]["generic"]["amount_accuracy"] is None
        assert summary["metrics"]["amount_accuracy"] is None
        assert summary["failures"] == []
        from tests.extraction_eval.metrics import render_cli

        cli = render_cli(summary)
        assert "Amounts:        N/A" in cli

    def test_warranty_no_amounts_does_not_fail_aggregate(self) -> None:
        field_results = [
            {
                "field": "product",
                "status": "correct",
                "passed": True,
                "expected": "Monitor",
                "actual": "Monitor",
                "is_date": False,
                "is_amount": False,
                "evidence": {"presence_ok": True, "page_ok": True},
            }
        ]
        metrics = build_document_metrics(field_results)
        summary = aggregate(
            [
                {
                    "filename": "warranty_001.pdf",
                    "expected_document_type": "warranty",
                    "actual_document_type": "warranty",
                    "classification_correct": True,
                    "passed": True,
                    "field_results": field_results,
                    "metrics": metrics,
                    "actions": {"false_actions": [], "missing_actions": [], "duplicate_actions": []},
                    "confidence": {"invalid_confidence_values": []},
                }
            ]
        )
        assert summary["by_document_type"]["warranty"]["amount_accuracy"] is None
        assert summary["failures"] == []
        assert thresholds_met(summary) == []
