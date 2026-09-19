# Go-live checklist

Things to provision and configure before hosting for real users.  
**Local Docker Redis / local `.env` are not deployed by `git push`.** Live needs its own services and environment variables.

Never put production secrets in git. Do not copy real passwords from a developer `.env` into this doc or into PRs.

---

## A. Services that must exist in live (not in git)

| # | Thing | Local (dev) | Live must have | Configure via |
| --- | --- | --- | --- | --- |
| 1 | PostgreSQL | Local DB or Docker | Managed / hosted Postgres | `DATABASE_URL` |
| 2 | Redis | Docker container on laptop (e.g. `ai-redis`) | Managed Redis or Redis on the server | `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` |
| 3 | FastAPI (backend) | `uvicorn` on laptop | Always-on API process or container | Host, port, HTTPS |
| 4 | Celery worker | Separate process on laptop | **Separate** worker process/container (required) | Same Redis + DB env as API |
| 5 | Next.js (web) | `npm run dev` | Built app (`npm start` / standalone) | `NEXT_PUBLIC_API_URL` |
| 6 | File storage | `backend/uploads/` + `backend/quarantine/` on disk | Same disk **or** S3 (`STORAGE_BACKEND=s3`) | `STORAGE_BACKEND`, `UPLOAD_DIR`, `QUARANTINE_DIR`, S3 buckets |
| 7 | ClamAV | Optional on laptop (`CLAMAV_REQUIRED=false`) | Required daemon (`CLAMAV_REQUIRED=true`) | `CLAMAV_HOST`, `CLAMAV_PORT` |
| 8 | Secrets | Local `.env` (gitignored) | Host / cloud secret store — never commit `.env` | All secrets |

---

## B. Environment variables to set in live

Use a secret manager or host env. Values below are **placeholders only** (same idea as `backend/.env.example`).

### Backend

| Variable | Local placeholder (example only) | Live: set to |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+asyncpg://USER:PASSWORD@HOST:5432/DB_NAME` | Production DB credentials and host |
| `REDIS_URL` | `redis://localhost:6379/0` | Production Redis URL |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Production Redis (broker) |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/1` | Production Redis (results) |
| `FRONTEND_URL` | `http://localhost:3000` | Real public web origin (CORS) |
| `JWT_SECRET` | `dev-only-change-me` | Strong random secret (must change) |
| `JWT_ALGORITHM` | `HS256` | Keep unless moving to asymmetric keys |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Production session policy |
| `STORAGE_BACKEND` | `local` | `s3` in live |
| `UPLOAD_DIR` | Local permanent path | Unused when `STORAGE_BACKEND=s3` |
| `QUARANTINE_DIR` | Local quarantine path | Unused when `STORAGE_BACKEND=s3` |
| `AWS_REGION` | (empty / unused) | e.g. `ap-south-1` |
| `AWS_S3_QUARANTINE_BUCKET` | (unused) | Private quarantine bucket |
| `AWS_S3_PERMANENT_BUCKET` | (unused) | Private permanent bucket |
| `CLAMAV_HOST` | `127.0.0.1` | ClamAV daemon hostname |
| `CLAMAV_PORT` | `3310` | ClamAV daemon port |
| `CLAMAV_REQUIRED` | `false` on laptop | `true` in staging/live |

### Frontend

| Variable | Local placeholder | Live: set to |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Public HTTPS API base URL |

---

## C. Processes that must be running in live

| Process | Role | If missing |
| --- | --- | --- |
| API (uvicorn / container) | HTTP API, auth, upload enqueue | Login / upload fail |
| Celery worker | OCR / extract jobs from Redis | Documents stuck in `queued` / Processing |
| Redis | Job queue / broker | Enqueue fails |
| Postgres | System of record | All DB operations fail |
| Web (Next.js) | UI | Users cannot open the app |
| ClamAV | Malware scan before promote | Uploads fail closed (`CLAMAV_REQUIRED=true`) |

---

## D. Deferred items before real production users

Tracked in [deferred-work.md](./deferred-work.md):

| ID | Item | Why |
| --- | --- | --- |
| DEVOPS-001 | Full Docker Compose / container deploy | API + web + worker + Redis + DB together |
| STOR-001 | Provision live S3 buckets + IAM | Adapter is in code; set `STORAGE_BACKEND=s3` |
| SEC-001 | Run ClamAV daemon in staging/live | App fail-closes when `CLAMAV_REQUIRED=true` |
| AUTH-001 | OIDC (Google / Auth0) | Optional stronger auth for real users |

Also for Phase 8–9 style go-live:

- [ ] HTTPS + domain
- [ ] DB migrations run on deploy (before traffic)
- [ ] Backups + rollback plan tested
- [ ] Never log document text / PII
- [ ] Alerts: API errors, queue depth, worker down
- [ ] Secrets only in managed store (not git, not chat logs)

---

## E. Local vs live (mental model)

| | Local | Live |
| --- | --- | --- |
| Redis | Docker on the developer PC | Cloud or server Redis |
| Application code | Same FastAPI + Celery | Same code from git |
| Difference | `localhost` URLs in a private `.env` | Production URLs and secrets on the host |

`git push` deploys **code**, not your laptop’s Docker Redis or your private `.env`.

---

## F. Minimum live smoke test

1. `GET /health` returns OK  
2. `GET /health/ready` returns OK with scanner available when `CLAMAV_REQUIRED=true`  
3. Register / login works  
4. Upload → `queued` → worker runs → `ready_for_review`  
5. EICAR / infected upload is rejected; nothing in permanent storage; no OCR  
6. Stop ClamAV with `CLAMAV_REQUIRED=true` → upload returns 503  
7. Stop worker → new upload stays `queued` (GET must not start OCR)  
8. Start worker → document completes  

---

## Related docs

- [deployment-guide.md](./deployment-guide.md)  
- [deferred-work.md](./deferred-work.md)  
- [technology-stack.md](./technology-stack.md)  
