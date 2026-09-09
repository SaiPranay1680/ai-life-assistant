# AI Architecture

**Status:** UI simulates AI. Real OCR, extraction, and RAG are **not** implemented.

## Product rules (non-negotiable)

- AI is advisory. Users confirm before consequential actions.
- Never invent missing fields.
- Every critical extracted value needs source evidence (document + page).
- Prefer **deterministic rules** for actions when dates/amounts are confirmed.
- RAG authorization is applied **before** retrieval, not after the LLM answers.
- Text inside user documents is **untrusted** (indirect prompt injection).
- Answers must refuse or qualify when evidence is insufficient.
- Do not log document content.

## Current UI simulation

| Screen | What it pretends | How |
| --- | --- | --- |
| Processing | Pipeline progress | Client interval, 4 steps |
| Review | Extraction | Static `extraction.json` |
| Actions | Suggested renew | Static `actions.json` + copy about PDF page 1 |
| Assistant | Grounded Q&A | String match in `messages.json` |

This is enough to demo UX. It is **not** evaluation-grade AI.

## Target pipelines

### Document intelligence (Phase 4)

```text
Upload → security → store
  → parse PDF text
  → OCR if image/scanned
  → normalize (keep original + ISO date)
  → classify
  → extract JSON schema per type
  → validate + persist
  → human review
```

MVP types: utility bill, insurance policy, purchase invoice/receipt, warranty, generic important document.

Each schema includes: document_type, issuer, dates, amounts, identifiers, candidate obligations, **per-field confidence**, evidence page, unknown/null handling.

### Action intelligence (Phase 5)

Inputs: type, fields, confidence, preferences, existing actions.  
Outputs: zero or more suggested actions.

Types: PAY, RENEW, REGISTER, REVIEW, FOLLOW_UP, KEEP_FOR_RECORDS.

Duplicate detection required. No auto pay/renew/cancel.

### RAG (Phase 6)

```text
Parse → page-aware chunk → embed → store
Query → auth → workspace filter → retrieve → rerank → LLM → answer + sources
```

Stack intent: FastAPI, PostgreSQL, pgvector, Python workers, LLM provider abstraction.

Observability: latency, token usage, cost per request. Evaluation set required before prompt/model changes.

## Provider abstraction

Do not call a vendor SDK from route handlers. Introduce ports such as:

- `OcrProvider.extract_text(file) -> pages`
- `LlmProvider.complete(prompt, schema)`
- `EmbeddingProvider.embed(texts)`

Swap vendors without rewriting domain modules.

## Evaluation (required before treating AI as “done”)

Gold dataset for bills, insurance, invoices, warranties. Measure classification accuracy, field F1, exact match on dates/amounts, evidence-page accuracy, false action rate, user-correction rate.

RAG: groundedness, hallucination, cross-user retrieval tests (must fail closed).

## Security tests specific to AI

- Prompt injection in chat
- Indirect injection via PDF text
- Retrieval of another user’s embeddings
- XSS via extracted text rendered in the UI (sanitize)

See playbook Phase 8.
