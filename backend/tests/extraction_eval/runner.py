"""EVAL-001 runner: real DOC-005 pipeline against synthetic fixtures."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from app.modules.actions.suggest import suggestions_for
from app.modules.documents.extract import (
    build_structured_payload,
    guess_fields,
    normalize_document_type,
    read_document_pages,
    schema_document_type,
)
from app.modules.documents.validation import validate_extraction

from .comparator import compare_actions, compare_fields, confidence_report
from .config import THRESHOLDS
from .metrics import aggregate, build_document_metrics, render_cli

PACKAGE_DIR = Path(__file__).resolve().parent
DOCUMENTS_DIR = PACKAGE_DIR / "documents"
EXPECTED_DIR = PACKAGE_DIR / "expected"
RESULTS_DIR = PACKAGE_DIR / "results"
RESULTS_PATH = RESULTS_DIR / "latest.json"


def _fields_to_action_map(fields: dict[str, Any]) -> dict[str, SimpleNamespace]:
    out: dict[str, SimpleNamespace] = {}
    for name, hit in fields.items():
        out[name] = SimpleNamespace(
            raw_value=getattr(hit, "raw", "") or "",
            normalized_value=getattr(hit, "normalized", "") or "",
            page_number=getattr(hit, "page", 1) or 1,
            confidence=getattr(hit, "confidence", 0.0),
            evidence_snippet=getattr(hit, "evidence", "") or "",
        )
    return out


def run_real_pipeline(document_path: Path) -> dict[str, Any]:
    """
    Invoke the real extraction path (no mocks):
    read pages → guess_fields → structured payload → schema validate → actions.
    """
    suffix = document_path.suffix.lower()
    if suffix not in {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".docx"}:
        raise ValueError(f"Unsupported fixture type: {document_path.name}")

    if suffix == ".docx":
        from app.modules.documents.docx_extract import extract_docx_pages

        pages = extract_docx_pages(document_path)
    else:
        is_pdf = suffix == ".pdf"
        pages = read_document_pages(document_path, is_pdf=is_pdf)
    fields = guess_fields(pages)
    doc_type_raw = fields["documentType"].normalized or fields["documentType"].raw
    doc_type = normalize_document_type(doc_type_raw)
    payload = build_structured_payload(doc_type, fields)
    validated = validate_extraction(doc_type, payload)
    structured = validated.model_dump(mode="json")

    document = SimpleNamespace(document_type=doc_type, original_filename=document_path.name)
    actions = suggestions_for(document, _fields_to_action_map(fields))
    return {
        "document_type": doc_type,
        "schema_type": schema_document_type(doc_type),
        "structured": structured,
        "actions": actions,
        "fields": fields,
        "pages": pages,
    }


def _load_expected(stem: str) -> dict[str, Any]:
    path = EXPECTED_DIR / f"{stem}.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing expected JSON: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _classification_matches(expected_type: str, actual_type: str) -> bool:
    """Allow insurance subtypes to match expected 'insurance' when declared that way."""
    exp = normalize_document_type(expected_type)
    act = normalize_document_type(actual_type)
    if exp == act:
        return True
    if exp == "insurance" and schema_document_type(act) == "insurance":
        return True
    if act == "insurance" and schema_document_type(exp) == "insurance":
        return True
    return False


def evaluate_document(document_path: Path) -> dict[str, Any]:
    expected = _load_expected(document_path.stem)
    actual = run_real_pipeline(document_path)
    expected_type = expected["document_type"]
    actual_type = actual["document_type"]
    classification_correct = _classification_matches(expected_type, actual_type)

    field_results = compare_fields(expected.get("fields") or {}, actual["structured"])
    action_cmp = compare_actions(expected.get("expected_actions"), actual["actions"])
    conf = confidence_report(actual["structured"])
    metrics = build_document_metrics(field_results)

    field_pass = all(r["passed"] for r in field_results if r["status"] != "unexpected")
    actions_pass = not (
        action_cmp["false_actions"] or action_cmp["missing_actions"] or action_cmp["duplicate_actions"]
    )
    passed = classification_correct and field_pass and actions_pass

    return {
        "filename": document_path.name,
        "expected_document_type": expected_type,
        "actual_document_type": actual_type,
        "classification_correct": classification_correct,
        "passed": passed,
        "field_results": field_results,
        "metrics": metrics,
        "actions": action_cmp,
        "confidence": conf,
        "actual_action_payloads": [
            {"action_type": item.get("action_type"), "title": item.get("title")} for item in actual["actions"]
        ],
    }


def discover_documents() -> list[Path]:
    if not DOCUMENTS_DIR.exists():
        return []
    docs = sorted(
        p
        for p in DOCUMENTS_DIR.iterdir()
        if p.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg", ".docx"} and not p.name.startswith(".")
    )
    return docs


def run_evaluation(*, write_results: bool = True) -> dict[str, Any]:
    documents = discover_documents()
    if not documents:
        raise FileNotFoundError(
            f"No fixtures in {DOCUMENTS_DIR}. Run: python -m tests.extraction_eval.generate_docs"
        )
    report_docs = [evaluate_document(path) for path in documents]
    summary = aggregate(report_docs)
    summary["thresholds"] = dict(THRESHOLDS)
    if write_results:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        # Machine-readable shape required by EVAL-001.
        machine = {
            "documents_evaluated": summary["documents_evaluated"],
            "metrics": summary["metrics"],
            "actions": summary["actions"],
            "confidence": summary["confidence"],
            "by_document_type": summary["by_document_type"],
            "classification": summary["classification"],
            "failures": summary["failures"],
            "thresholds": summary["thresholds"],
            "documents": [
                {
                    "filename": d["filename"],
                    "expected_document_type": d["expected_document_type"],
                    "actual_document_type": d["actual_document_type"],
                    "passed": d["passed"],
                    "field_results": d["field_results"],
                    "actions": d["actions"],
                    "metrics": d["metrics"],
                }
                for d in summary["documents"]
            ],
        }
        RESULTS_PATH.write_text(json.dumps(machine, indent=2), encoding="utf-8")
    return summary


def thresholds_met(summary: dict[str, Any]) -> list[str]:
    """Return list of metric keys that fall below configured floors."""
    failures: list[str] = []
    metrics = summary["metrics"]
    for key, floor in THRESHOLDS.items():
        value = metrics.get(key)
        # N/A metrics (None) are not scored and must not fail thresholds.
        if value is None:
            continue
        if value + 1e-12 < float(floor):
            failures.append(f"{key}={value:.4f} < threshold={floor:.4f}")
    return failures


def main(argv: list[str] | None = None) -> int:
    del argv  # reserved for future flags
    summary = run_evaluation(write_results=True)
    print(render_cli(summary))
    print(f"\nWrote {RESULTS_PATH}")
    missed = thresholds_met(summary)
    if missed:
        print("\nThreshold failures:")
        for item in missed:
            print(f"  - {item}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
