# Phase 1 decisions

Approved one step at a time. Do not start the next step until the current step is marked **Approved**.

## Step 1 of 8 — Who talks to whom

**Status:** Approved (2026-09-13)

```text
Browser → Next.js (:3000) → FastAPI (:8000) → PostgreSQL (:5432)
```

**Rules**

- Browser never talks to the database directly.
- Frontend never talks to Redis, files, or AI vendors.
- One backend app (modular monolith). Not microservices.
- Keep the existing `backend/` folder. Do not create `services/api/` now.

**Later (not this step):** Redis, workers, file storage, AI/OCR, email.

## Step 2 of 8 — Module list

**Status:** Approved (2026-09-13)

Identity, Workspace, Documents, Intelligence, Actions, Reminders, Notifications, Audit, Privacy. Assistant is listed but built in Phase 6 only.

## Step 3 of 8 — Sync vs async

**Status:** Approved (2026-09-13)

Upload returns immediately. OCR/extract/reminders run in a worker. Confirm action is always sync.

## Step 4 of 8 — Data model

**Status:** Approved (2026-09-13)

User → Workspace → Document → ExtractionField / Action → Reminder, plus AuditEvent. No PDF bytes in Postgres. Every tenant row has `workspace_id`. Use `workspaces`, not `organizations`.

## Step 5 of 8 — Auth

**Status:** Approved (2026-09-13)

**Phase 3 now:** email + password + JWT. `POST /auth/register`, `POST /auth/login`, `GET /me`, one personal workspace on first login.

**Phase 8–9 later:** OIDC (Google / Auth0). Tracked in [deferred-work.md](./deferred-work.md) as **AUTH-001**. Do not implement OIDC in Phase 4 or 5.

## Step 6 of 8 — File storage and privacy

**Status:** Approved (2026-09-13)

**Phase 3–5 now:** files on disk at `backend/uploads/`. Postgres stores metadata only. FastAPI chooses the path. Validate size, type, hash in Python. Do not log document text.

**Phase 8–9 later:** AWS S3. Tracked in [deferred-work.md](./deferred-work.md) as **STOR-001**. Malware scanner (ClamAV) is also later; stub/hook only until then.

## Step 7 of 8 — AI and privacy

**Status:** Approved (2026-09-13)

AI is advisory. Do not invent fields. Evidence + user confirm before actions. Prefer Python rules over LLM. Document text is untrusted. RAG / assistant is Phase 6. Never log document text.

## Step 8 of 8 — Threat model and Phase 1 exit

**Status:** Approved (2026-09-13)

Workspace isolation, JWT in FastAPI, file validation, untrusted PDF text, no PII in logs, parameterized SQL. OIDC, S3, and full-stack Docker stay in [deferred-work.md](./deferred-work.md) (AUTH-001, STOR-001, DEVOPS-001).

**Phase 1 complete.** Next: Phase 3 engineering foundation, one test at a time.
