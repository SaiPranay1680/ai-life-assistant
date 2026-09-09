# Workflows

## 1. First-time (current UI)

```text
Open /
  → no localStorage user → /login
  → submit valid email + password ≥ 6
  → ala-auth-user + ala-token written
  → /dashboard
```

Logout: Settings → Sign out → keys removed → `/login`.

## 2. Golden document-to-action journey (product)

```text
Dashboard → Upload document
  → Smart Inbox (file)
  → Processing job (queued in production)
  → Review / edit fields
  → Confirm
  → Action Card (Pay / Renew / …)
  → Confirm reminder
  → Dashboard + Timeline updated
  → Optional: Ask assistant with citations
```

**Current UI shortcut:** open `/documents/processing?file=car-insurance-policy.pdf` to skip a real file. After steps complete, the app navigates to `/documents/review`, then Confirm goes to `/actions`.

## 3. Data flow today

```text
Page
  → useQuery / useMutation
  → services/api/*.ts
  → import JSON + wait(ms)
  → React render
```

Axios `apiClient` is **not** on this path yet. When FastAPI exists, services should call `apiClient` and keep the same function names (`getDocuments`, `uploadDocument`, …).

## 4. Data flow (target production)

```text
UI
  → HTTPS JSON (cookie or Bearer)
  → FastAPI route (thin)
  → service / domain layer
  → SQLAlchemy (workspace-scoped queries)
  → PostgreSQL

Upload:
  UI → API initiates presign
  → browser PUT to S3
  → API records document + status=uploaded
  → enqueue job
  → worker: scan → parse/OCR → extract → status=ready_for_review
  → UI polls or websocket/SSE (TBD)
```

## 5. AI processing flow (target)

```text
Upload → security check → store object
  → parse native PDF text
  → OCR if needed
  → normalize (keep original + ISO dates)
  → classify document_type
  → extract fields + confidence + page evidence
  → persist
  → user review
  → deterministic action rules (AI only if ambiguous)
  → user confirmation
  → reminder job
```

Rules from the playbook:

- Never invent missing fields.
- Critical values need source evidence.
- Dates stored ISO-8601 after normalization.
- Prefer code over LLM when a rule is safe.

## 6. RAG / ask flow (target)

```text
Ingest: parse → chunk (page-aware) → embed → store with workspace_id
Query:
  authenticate
  → filter chunks by workspace BEFORE search
  → retrieve (+ optional hybrid / rerank)
  → LLM with citations
  → refuse if evidence insufficient
```

Document text is untrusted. Instructions in a PDF must not override system policy.

## 7. Integration workflows (planned)

| Integration | When | Notes |
| --- | --- | --- |
| OIDC IdP | Login | Replace mock localStorage |
| S3 | Upload | Presigned URLs, expiry |
| OCR vendor | Scanned PDFs | Adapter interface |
| LLM vendor | Extract + RAG | Adapter; cost telemetry |
| Email (SES/SMTP) | Reminders | Idempotent send |
| Malware scan | After upload | Fail closed on error |

## 8. Deployment workflow (planned)

```text
PR → lint, typecheck, unit tests, security scan, build
main → DEV
tag → STAGING
manual approval → PRODUCTION
```

Frontend `next build` with `output: "standalone"` is already configured. No pipeline is in `.github/` in the current tree (an earlier CI workflow was removed in the reset).

## 9. Sidebar active-state workflow

- `/documents` exact match for Documents.
- Smart Inbox active for `/documents/upload`, `/documents/processing`, `/documents/review`.
- Other items: prefix match on their href.
