# Architecture & Technical Decisions

## High-level architecture (target)

The execution playbook defines a **modular monolith**, not microservices.

```text
Browser (Next.js)
        │  HTTPS / JSON
        ▼
FastAPI modular monolith
        │
        ├── PostgreSQL + pgvector     system of record + later RAG vectors
        ├── Redis / queue             jobs and cache
        ├── Python workers            OCR, extraction, embeddings, reminders
        ├── S3-compatible storage     files (not DB BLOBs)
        ├── AI / OCR providers        behind an abstraction
        └── Email                     reminder notifications
```

**Trust boundary:** the browser never talks to Postgres, Redis, or S3 with service credentials. The API enforces authentication and `workspace_id` on every read/write.

## Current architecture (what is in git)

```text
Browser
   │
   ▼
Next.js App Router (apps/web)
   │
   ├── React Context (auth)
   ├── TanStack Query
   ├── Axios instance (prepared, mostly unused)
   └── Local JSON in src/data/  ← mock “backend”
```

There is **no** FastAPI process, database, or worker in the current working tree. Services in `src/services/api/` return fixture data after a short `wait()` so the UI can be developed independently.

## Application structure (frontend)

```text
apps/web/src/
├── app/                    Routes (App Router)
│   ├── login/
│   ├── dashboard/
│   ├── documents/          vault, upload, processing, review
│   ├── actions/
│   ├── assistant/
│   ├── timeline/
│   └── settings/
├── components/
│   ├── layout/             AppShell, Header
│   ├── sidebar/
│   ├── cards/
│   ├── forms/
│   ├── upload/
│   ├── chat/
│   ├── ui/                 Button, Input, Card, Badge, Modal
│   └── providers/          Query + Auth
├── services/api/           auth, document, action, assistant, axios client
├── hooks/                  useAuth
├── data/                   mock JSON
├── types/
└── utils/
```

### Folder rules

| Folder | Put here | Do not put here |
| --- | --- | --- |
| `app/` | Pages, layouts, route-level composition | Shared UI primitives |
| `components/ui/` | Dumb reusable visuals | Fetching, routing, business rules |
| `components/layout/` | Shell, header | Feature-specific cards |
| `services/api/` | HTTP or mock I/O | JSX |
| `data/` | Fixtures until API exists | Secrets |
| `hooks/` | Reusable client state | One-off page handlers |
| `types/` | Shared TypeScript contracts | Runtime logic |

## Module map (backend — planned)

| Module | Responsibility |
| --- | --- |
| Identity / Auth | Users, sessions, OIDC adapter |
| Workspace | Personal workspace; `workspace_id` |
| Documents | Upload metadata, status machine, file keys |
| Intelligence | Parse, OCR, classify, extract |
| Actions | Suggested actions, confirmation |
| Reminders | Schedules, idempotent jobs |
| Assistant | RAG query path |
| Notifications | Email (and later push) |
| Audit | Who changed what |
| Privacy | Export, deletion |

Synchronous vs asynchronous:

- **Sync:** login, list documents, get dashboard, confirm action, chat request *acceptance*
- **Async:** parse/OCR, extraction, embedding, reminder send

## Design decisions and assumptions

1. **Modular monolith** — one API deployable, clear packages. Split only workers for heavy jobs.  
2. **Documents in object storage** — Postgres stores metadata and extracted fields, not PDF bytes.  
3. **pgvector first** — avoid a separate vector DB until scale requires it.  
4. **AI behind an adapter** — swap OCR/LLM vendors without rewriting domain code.  
5. **Confirmation before consequences** — reminders and actions require explicit user consent.  
6. **Authorization before retrieval** — RAG must filter by workspace before the LLM runs.  
7. **Frontend mock-first** — UI could be designed and tested without waiting for FastAPI.  
8. **`output: "standalone"`** in Next.js — Docker-friendly Node server later.

## Security baseline (must hold in production)

- Every tenant-owned row has `workspace_id`.
- Tests for cross-workspace leakage are release-blocking.
- Do not log document text or PII.
- Treat text inside PDFs as untrusted (prompt injection).
- Presigned upload URLs, type/size validation, malware scan hook.
- Secrets never in git (`.env` is gitignored).

## Architecture Decision Records (ADRs)

Until `docs/adr/` exists, record decisions here.

| ID | Decision | Status |
| --- | --- | --- |
| ADR-001 | Monorepo with `apps/web` (playbook also wants `services/api`) | Accepted |
| ADR-002 | Next.js App Router + TypeScript + Tailwind for UI | Accepted |
| ADR-003 | Mock JSON + service layer until FastAPI exists | Accepted |
| ADR-004 | React Context for auth; Zustand/Redux later if needed | Accepted |
| ADR-005 | Axios + TanStack Query for server state | Accepted |
| ADR-006 | FastAPI modular monolith (not microservices) | Accepted (not coded) |
| ADR-007 | PostgreSQL as system of record | Accepted (not coded) |
| ADR-008 | Celery/Redis workers for document/AI jobs | Accepted (not coded) |
| ADR-009 | Phase 3: email + password + JWT. OIDC (Google/Auth0) in Phase 8–9 before production. See [deferred-work.md](./deferred-work.md) AUTH-001 | Accepted |
| ADR-010 | Reset of the first generated FastAPI/Docker scaffold so the team learns and follows the playbook folder layout | Accepted |

See [technology-stack.md](./technology-stack.md) for alternatives considered.
