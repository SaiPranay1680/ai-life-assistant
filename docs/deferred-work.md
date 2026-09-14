# Deferred work (do not forget)

Work we have decided **not** to do now. Check this file before Phase 8–9.

---

## AUTH-001 — OIDC (Google / Auth0)

| Field | Value |
| --- | --- |
| Status | Not started |
| Do now (Phase 3) | Email + password + JWT. Register, login, `GET /me`, one workspace per user |
| Do later | OIDC login (Google or Auth0) |
| When | Phase 8–9, before real users / production |
| Do not do in | Phase 4 (documents) or Phase 5 (actions) |
| Why later | Need provider app, client id/secret, redirect URLs. Must not block the first API + DB loop |
| Rules that stay the same | Next.js never talks to Postgres. FastAPI checks JWT. Every query uses `workspace_id`. Document id is not authorization |

### Phase 3 done when

- [ ] `POST /auth/register`
- [ ] `POST /auth/login`
- [ ] `GET /me` returns user + workspace
- [ ] Mock `localStorage` login is replaced

### Phase 8–9 OIDC done when

- [ ] User can sign in with the identity provider
- [ ] Local user + workspace still created on first login
- [ ] Password login is kept for local/dev or removed on purpose (decide then)

See Phase 1 Step 5 in [phase-1-decisions.md](./phase-1-decisions.md).

---

## DOC-001 — Documents list and upload (Phase 3)

| Field | Value |
| --- | --- |
| Status | Done for local disk |
| Do now (Phase 3–4) | `GET /documents`, `POST /documents`, View, Delete, local `backend/uploads/` |
| Allowed files | `.pdf` `.jpg` `.jpeg` `.png` — max 20 MB |
| Checks now | JWT + workspace, size, extension, magic bytes, SHA-256 duplicate in workspace, local malware scan |
| Storage | `workspaces/{workspace_id}/documents/{document_id}/original{ext}` |
| Do later | Presigned upload (STOR-001), DOCX (DOC-003) |

### Phase 3 done when

- [x] Register / login / `GET /me`
- [x] `POST /documents` saves a file on disk and a Postgres row
- [x] `GET /documents` lists that workspace only
- [x] Same file again returns duplicate

---

## DOC-002 — Parse / OCR / extract (Phase 4)

| Field | Value |
| --- | --- |
| Status | In progress (MVP in this phase) |
| When | Phase 4 |
| Libraries now | PyMuPDF + RapidOCR |
| Do now | Native PDF text, OCR for images/scans, classify, extract fields + confidence, ISO date normalize, page number, persist, human review save |
| Do later | Worker queue (DOC-004), per-type schemas (DOC-005), PaddleOCR swap, bounding boxes |
| Rules | Unscanned files must not enter OCR. User confirms fields. Never log document text |

### Phase 4 MVP done when

- [x] PDF text via PyMuPDF
- [x] OCR for JPG/PNG and scanned PDFs
- [x] Local security scan before OCR
- [x] Dates stored as raw + ISO (`normalized_value`)
- [x] `page_number` from the page the field was found on
- [x] Review **Confirm** persists corrections

---

## DOC-004 — Async processing worker

Playbook task 33 remainder. Upload must return immediately; OCR/extract must not run inside `GET /documents/{id}`.

| Field | Value |
| --- | --- |
| Status | Not started |
| Do now (Phase 4) | Scan on upload (fast). Extract on first GET poll |
| Do later | Redis / Celery or equivalent worker. Status: `uploaded` → `queued` → `processing` → `ready_for_review` |
| When | After Phase 4 MVP, before production load |
| Do not do in | Phase 5 actions |
| Why later | Extra process and Redis. Local poll is enough for dummy files |

---

## DOC-005 — Per-type extraction schemas

Playbook tasks 38–39 remainder.

| Field | Value |
| --- | --- |
| Status | Not started |
| Do now (Phase 4) | One shared field set: type, provider, policy/account no., start, expiry, amount |
| Do later | JSON schema per type (bill / insurance / purchase / warranty / generic), candidate obligations, unknown/null handling, bounding boxes |
| When | After review persist works |
| Do not do in | Phase 5 until schemas exist |

---

## EVAL-001 — Extraction benchmark

Playbook task 41.

| Field | Value |
| --- | --- |
| Status | Not started |
| Do now | Dummy files only, manual check |
| Do later | Gold set of dummy PDFs/images + expected JSON. Score field accuracy. No real personal documents |
| When | After DOC-002 MVP is stable |
| Do not do in | Phase 5 actions |

---

## DOC-003 — DOCX support

| Field | Value |
| --- | --- |
| Status | Not started |
| When | After PDF / JPG / PNG upload + extract works |
| Library | python-docx |
| Do not do in | Phase 3 |

---

## SEC-001 — ClamAV malware scan

Playbook task 32 remainder (daemon).

| Field | Value |
| --- | --- |
| Status | Not started (daemon) |
| Do now (Phase 4) | Local scan before OCR: EICAR, executable/polyglot, dangerous PDF `/Launch`. Optional `clamscan` if installed. Infected files are rejected and never OCR’d. `scan_status` = `clean` or `infected` |
| Do later | ClamAV daemon (clamd) in Docker/Compose, fail closed if scanner is down |
| When | Phase 8–9, with DEVOPS-001 |
| Rule | Unscanned files must not enter OCR |

---

## STOR-001 — AWS S3 object storage

| Field | Value |
| --- | --- |
| Status | Not started |
| Do now (Phase 3–5) | Save files under `backend/uploads/`. Postgres stores `storage_key`, size, mime, sha256 — not PDF bytes |
| Do later | AWS S3 (private bucket, FastAPI keys only). Presigned upload URLs (playbook task 30) |
| When | Phase 8–9, before real users / production |
| Do not do in | Phase 3 login, Phase 4 extract, Phase 5 actions |
| Why later | Needs AWS account, IAM keys, bucket policy. Local folder proves the same upload path |
| Rules that stay the same | Backend chooses the path `workspaces/{workspace_id}/documents/{document_id}/original.pdf`. Never `NEXT_PUBLIC_` AWS secrets. Never put PDFs in Postgres. Duplicate check is `(workspace_id, sha256)` |

### Phase 3–5 done when

- [ ] Upload API saves file locally
- [ ] Document row exists in Postgres
- [ ] `GET /documents` lists only that workspace

### Phase 8–9 S3 done when

- [ ] Bucket is private (block public access)
- [ ] FastAPI uploads/downloads via S3
- [ ] Local storage can be turned off

See Phase 1 Step 6 in [phase-1-decisions.md](./phase-1-decisions.md).

---

## DEVOPS-001 — Dockerize the full stack

| Field | Value |
| --- | --- |
| Status | Not started |
| Do now (Phase 3) | Docker for Postgres only (`ai-pg`). FastAPI and Next.js still run on the host |
| Do later | Docker Compose: Postgres + FastAPI + Next.js |
| When | Phase 8–9, before real users / production |
| Do not do in | Phase 3 login, Phase 4 extract, Phase 5 actions |
| Why later | No Dockerfiles yet. Host uvicorn/npm is easier while we test health, login, upload |
| Rules that stay the same | Browser talks to FastAPI on a published port. Never put `DATABASE_URL` in `NEXT_PUBLIC_*`. Postgres hostname inside Compose is the service name (`db`), not `localhost` |

### Phase 3 done when

- [ ] `ai-pg` container running
- [ ] `python scripts/check_db.py` prints `DB check result: 1`
- [ ] FastAPI still started with uvicorn on the host

### Phase 8–9 done when

- [ ] `docker compose up` starts db + api + web
- [ ] `/health` works through the API container
- [ ] Browser can open the web container and call the API

---

## ACT-001 — Suggested PAY / RENEW (Phase 5)

| Field | Value |
| --- | --- |
| Status | Done for Phase 5 action MVP |
| Do now | After extraction is **reviewed**, suggest PAY (bill + due date/amount) or RENEW (insurance + expiry). Deduplicate per document + type. Show on `/actions` |
| Do later | Email/push delivery (REM-001). Never real payments (PAY-001) |
| When | Phase 5 |
| Rules | Python rules on confirmed fields. No auto pay/renew/cancel. User still confirms |

### Phase 5 first slice done when

- [x] Confirm insurance → RENEW on `/actions`
- [x] Confirm bill → PAY on `/actions`
- [x] Same document does not create a second duplicate action
- [x] REGISTER / REVIEW / FOLLOW_UP / KEEP_FOR_RECORDS from confirmed types
- [x] Create reminder persists (in-app, no email)
- [x] Not needed dismisses and does not come back

---

## REM-001 — Reminder email / notification delivery

| Field | Value |
| --- | --- |
| Status | Not started |
| Do now (Phase 5) | Reminder row in Postgres, `fire_at`, idempotency key, in-app only. `sent_at` stays empty |
| Do later | Email (or push) send, worker that sets `sent_at` |
| When | After ACT-001. Worker/queue is DOC-004 |
| Do not do in | This Phase 5 first slice |

---

## PAY-001 — Real payments

| Field | Value |
| --- | --- |
| Status | Not started / not in product |
| Do now | PAY means “you may need to pay” as a suggested action only |
| Do later | If ever: user-initiated pay link. Never UPI/card/bank from the assistant |
| When | Not Phase 5 |
| Rule | The system must never pay, renew, or cancel on its own |

---

## RAG-001 — Assistant RAG

| Field | Value |
| --- | --- |
| Status | Not started |
| Do now | Scripted `/assistant` replies |
| Do later | Chunk, embed, workspace-filtered retrieve, citations, refuse if no evidence |
| When | Phase 6 |
| Do not do in | Phase 5 actions |


