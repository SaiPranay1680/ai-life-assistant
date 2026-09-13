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

## STOR-001 — AWS S3 object storage

| Field | Value |
| --- | --- |
| Status | Not started |
| Do now (Phase 3–5) | Save files under `backend/uploads/`. Postgres stores `storage_key`, size, mime, sha256 — not PDF bytes |
| Do later | AWS S3 (private bucket, FastAPI keys only) |
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

