"""Score dummy gold cases for purpose + evidence extraction. No real personal documents."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.modules.intelligence.local import classify_document, extract_fields
from app.modules.intelligence.types import NormalizedDocument

CASES = [
    {
        "id": "insurance_trap",
        "text": "ICICI Lombard Motor Insurance\nPolicy Number: 3001/123456789\nPremium: ₹18,430\nSum Insured: ₹10,00,000\nExpiry Date: 11 Sep 2027",
        "expect_status": "supported",
        "expect_type": "Insurance",
        "expect_fields": {"premium": "18430", "policyNumber": "3001/123456789"},
    },
    {
        "id": "electricity_bill",
        "text": "BESCOM Electricity Bill\nConsumer Number: 1234567890\nBill Amount: ₹3,420\nDue Date: 29 Sep 2026",
        "expect_status": "supported",
        "expect_type": "Bill",
        "expect_fields": {"premium": "3420"},
    },
    {
        "id": "assignment",
        "text": "Machine Learning Assignment\nSubmission Date: 30 September 2026",
        "expect_status": "unknown",
        "expect_type": "Other",
        "expect_fields": {},
    },
    {
        "id": "lorem",
        "text": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        "expect_status": "not_useful",
        "expect_type": "Other",
        "expect_fields": {},
    },
]


def _doc(text: str) -> NormalizedDocument:
    return NormalizedDocument(pages=[(1, text)], is_pdf=True, is_image=False, page_count=1, filename="gold.pdf")


def main() -> int:
    passed = 0
    for case in CASES:
        document = _doc(case["text"])
        decision = classify_document(document)
        ok = decision.status == case["expect_status"] and decision.document_type == case["expect_type"]
        if ok and case["expect_fields"]:
            fields = extract_fields(document, decision.document_type)
            for name, expected in case["expect_fields"].items():
                actual = fields[name].normalized or fields[name].raw
                if expected not in actual:
                    ok = False
                    print(f"FAIL {case['id']} field {name}: got {actual!r} want {expected!r}")
        if ok:
            passed += 1
            print(f"PASS {case['id']}")
        else:
            print(f"FAIL {case['id']} status={decision.status} type={decision.document_type}")
    print(f"{passed}/{len(CASES)} gold cases passed")
    return 0 if passed == len(CASES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
