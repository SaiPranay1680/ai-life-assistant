"""Aggregate EVAL-001 metrics and render CLI / JSON reports."""

from __future__ import annotations

from typing import Any


def _ratio(correct: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return correct / total


def _amount_accuracy(correct: int, total: int) -> float | None:
    """
    Amount accuracy is undefined when there are no amount fields to score.
    Returning None (JSON null / CLI N/A) avoids looking like a 0% failure.
    """
    if total <= 0:
        return None
    return correct / total


def _pct(ratio: float | None) -> str:
    if ratio is None:
        return "N/A"
    return f"{ratio * 100:.2f}%"


def build_document_metrics(field_results: list[dict[str, Any]]) -> dict[str, Any]:
    expected = [r for r in field_results if r["status"] != "unexpected"]
    correct = sum(1 for r in expected if r["status"] == "correct")
    dates = [r for r in expected if r.get("is_date")]
    amounts = [r for r in expected if r.get("is_amount")]
    evidence_rows = [r for r in expected if r["status"] != "missing"]

    date_correct = sum(1 for r in dates if r["status"] == "correct")
    amount_correct = sum(1 for r in amounts if r["status"] == "correct")
    evidence_presence = sum(1 for r in evidence_rows if r.get("evidence", {}).get("presence_ok"))
    evidence_page = sum(1 for r in evidence_rows if r.get("evidence", {}).get("page_ok"))

    return {
        "expected_fields": len(expected),
        "correct_fields": correct,
        "incorrect_fields": sum(1 for r in expected if r["status"] == "incorrect"),
        "missing_fields": sum(1 for r in expected if r["status"] == "missing"),
        "unexpected_fields": sum(1 for r in field_results if r["status"] == "unexpected"),
        "field_accuracy": _ratio(correct, len(expected)),
        "date_total": len(dates),
        "date_correct": date_correct,
        "date_incorrect": sum(1 for r in dates if r["status"] == "incorrect"),
        "date_missing": sum(1 for r in dates if r["status"] == "missing"),
        "date_accuracy": _ratio(date_correct, len(dates)),
        "amount_total": len(amounts),
        "amount_correct": amount_correct,
        "amount_incorrect": sum(1 for r in amounts if r["status"] == "incorrect"),
        "amount_missing": sum(1 for r in amounts if r["status"] == "missing"),
        "amount_accuracy": _amount_accuracy(amount_correct, len(amounts)),
        "evidence_presence_total": len(evidence_rows),
        "evidence_presence_correct": evidence_presence,
        "evidence_presence_accuracy": _ratio(evidence_presence, len(evidence_rows)),
        "evidence_page_total": len(evidence_rows),
        "evidence_page_correct": evidence_page,
        "evidence_page_accuracy": _ratio(evidence_page, len(evidence_rows)),
    }


def aggregate(report_docs: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(report_docs)
    class_correct = sum(1 for d in report_docs if d.get("classification_correct"))
    class_failures = [
        {
            "filename": d["filename"],
            "expected": d["expected_document_type"],
            "actual": d["actual_document_type"],
        }
        for d in report_docs
        if not d.get("classification_correct")
    ]

    field_correct = sum(d["metrics"]["correct_fields"] for d in report_docs)
    field_total = sum(d["metrics"]["expected_fields"] for d in report_docs)
    date_correct = sum(d["metrics"]["date_correct"] for d in report_docs)
    date_total = sum(d["metrics"]["date_total"] for d in report_docs)
    amount_correct = sum(d["metrics"]["amount_correct"] for d in report_docs)
    amount_total = sum(d["metrics"]["amount_total"] for d in report_docs)
    ev_pres_correct = sum(d["metrics"]["evidence_presence_correct"] for d in report_docs)
    ev_pres_total = sum(d["metrics"]["evidence_presence_total"] for d in report_docs)
    ev_page_correct = sum(d["metrics"]["evidence_page_correct"] for d in report_docs)
    ev_page_total = sum(d["metrics"]["evidence_page_total"] for d in report_docs)

    false_actions = sum(len(d["actions"]["false_actions"]) for d in report_docs)
    missing_actions = sum(len(d["actions"]["missing_actions"]) for d in report_docs)
    duplicate_actions = sum(len(d["actions"]["duplicate_actions"]) for d in report_docs)
    invalid_confidence = sum(len(d.get("confidence", {}).get("invalid_confidence_values", [])) for d in report_docs)

    by_type: dict[str, list[dict[str, Any]]] = {}
    for doc in report_docs:
        key = doc["expected_document_type"]
        # Collapse insurance subtypes for the by-type section.
        if "insurance" in key:
            key = "insurance"
        by_type.setdefault(key, []).append(doc)

    type_summaries: dict[str, Any] = {}
    for type_id, docs in sorted(by_type.items()):
        type_amount_total = sum(d["metrics"]["amount_total"] for d in docs)
        type_summaries[type_id] = {
            "documents": len(docs),
            "classification_accuracy": _ratio(sum(1 for d in docs if d["classification_correct"]), len(docs)),
            "field_accuracy": _ratio(
                sum(d["metrics"]["correct_fields"] for d in docs),
                sum(d["metrics"]["expected_fields"] for d in docs),
            ),
            "date_accuracy": _ratio(
                sum(d["metrics"]["date_correct"] for d in docs),
                sum(d["metrics"]["date_total"] for d in docs),
            ),
            "amount_accuracy": _amount_accuracy(
                sum(d["metrics"]["amount_correct"] for d in docs),
                type_amount_total,
            ),
        }

    failures: list[dict[str, Any]] = []
    for doc in report_docs:
        for row in doc["field_results"]:
            if row["status"] in {"incorrect", "missing"}:
                failures.append(
                    {
                        "filename": doc["filename"],
                        "field": row["field"],
                        "expected": row["expected"],
                        "actual": row["actual"],
                        "result": "FAIL",
                        "status": row["status"],
                    }
                )
        for action_type in doc["actions"]["false_actions"]:
            failures.append(
                {
                    "filename": doc["filename"],
                    "field": "action",
                    "expected": None,
                    "actual": action_type,
                    "result": "FALSE_ACTION",
                    "status": "false_action",
                }
            )
        for action_type in doc["actions"]["missing_actions"]:
            failures.append(
                {
                    "filename": doc["filename"],
                    "field": "action",
                    "expected": action_type,
                    "actual": None,
                    "result": "MISSING_ACTION",
                    "status": "missing_action",
                }
            )

    return {
        "documents_evaluated": total,
        "classification": {
            "total": total,
            "correct": class_correct,
            "incorrect": total - class_correct,
            "accuracy": _ratio(class_correct, total),
            "failures": class_failures,
        },
        "metrics": {
            "classification_accuracy": _ratio(class_correct, total),
            "field_accuracy": _ratio(field_correct, field_total),
            "date_accuracy": _ratio(date_correct, date_total),
            "amount_accuracy": _amount_accuracy(amount_correct, amount_total),
            "evidence_presence_accuracy": _ratio(ev_pres_correct, ev_pres_total),
            "evidence_page_accuracy": _ratio(ev_page_correct, ev_page_total),
        },
        "actions": {
            "false_actions": false_actions,
            "missing_actions": missing_actions,
            "duplicate_actions": duplicate_actions,
        },
        "confidence": {
            "invalid_confidence_values": invalid_confidence,
        },
        "by_document_type": type_summaries,
        "failures": failures,
        "documents": report_docs,
    }


def render_cli(summary: dict[str, Any]) -> str:
    lines: list[str] = []
    m = summary["metrics"]
    a = summary["actions"]
    lines.append("=" * 40)
    lines.append("EVAL-001 EXTRACTION EVALUATION")
    lines.append("=" * 40)
    lines.append("")
    lines.append(f"Documents evaluated: {summary['documents_evaluated']}")
    lines.append("")
    lines.append(f"Classification Accuracy:      {_pct(m['classification_accuracy'])}")
    lines.append(f"Field Accuracy:               {_pct(m['field_accuracy'])}")
    lines.append(f"Date Accuracy:                {_pct(m['date_accuracy'])}")
    lines.append(f"Amount Accuracy:              {_pct(m['amount_accuracy'])}")
    lines.append(f"Evidence Presence Accuracy:   {_pct(m['evidence_presence_accuracy'])}")
    lines.append(f"Evidence Page Accuracy:       {_pct(m['evidence_page_accuracy'])}")
    lines.append("")
    lines.append(f"Invalid Confidence Values:    {summary['confidence']['invalid_confidence_values']}")
    lines.append("")
    lines.append(f"False Actions:                {a['false_actions']}")
    lines.append(f"Missing Actions:              {a['missing_actions']}")
    lines.append(f"Duplicate Actions:            {a['duplicate_actions']}")
    lines.append("")
    lines.append("-" * 40)
    lines.append("BY DOCUMENT TYPE")
    lines.append("-" * 40)
    lines.append("")
    labels = {
        "utility_bill": "Utility Bill",
        "insurance": "Insurance",
        "purchase_receipt": "Purchase Receipt",
        "warranty": "Warranty",
        "generic": "Generic",
    }
    for type_id, block in summary["by_document_type"].items():
        lines.append(labels.get(type_id, type_id))
        lines.append(f"  Classification: {_pct(block['classification_accuracy'])}")
        lines.append(f"  Fields:         {_pct(block['field_accuracy'])}")
        docs = [
            d
            for d in summary["documents"]
            if (
                d["expected_document_type"] == type_id
                or ("insurance" in d["expected_document_type"] and type_id == "insurance")
            )
        ]
        if any(d["metrics"]["date_total"] for d in docs):
            lines.append(f"  Dates:          {_pct(block['date_accuracy'])}")
        # Always surface amount accuracy: real score or N/A when no amount fields.
        lines.append(f"  Amounts:        {_pct(block['amount_accuracy'])}")
        lines.append("")
    lines.append("-" * 40)
    lines.append("FAILURES")
    lines.append("-" * 40)
    lines.append("")
    if not summary["failures"] and not summary["classification"]["failures"]:
        lines.append("None")
    else:
        for fail in summary["classification"]["failures"]:
            lines.append(f"Document: {fail['filename']}")
            lines.append("Classification: FAIL")
            lines.append(f"Expected: {fail['expected']}")
            lines.append(f"Actual: {fail['actual']}")
            lines.append("")
        for fail in summary["failures"]:
            lines.append(f"Document: {fail['filename']}")
            lines.append(f"Field: {fail['field']}")
            lines.append(f"Expected: {fail['expected']}")
            lines.append(f"Actual: {fail['actual']}")
            lines.append(f"Result: {fail['result']}")
            lines.append("")
    lines.append("=" * 40)
    return "\n".join(lines)
