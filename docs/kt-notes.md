# Knowledge Transfer Notes (KT In / KT Out)

This file is for **people**. Architecture and setup details live in the other `docs/` files; this file captures what was learned, what was taught, how we work, and what changed in git.

Last updated: 2026-09-09

---

# Part A — KT In (knowledge received)

## Sources of truth that were ingested

1. **Product execution playbook** (Word): *AI Life Assistant Step-by-Step Product Execution Playbook*, Version 1.0, September 2026. Phases 0–10, exit gates, golden demo, deferred list, reusable prompts.  
2. **Figma / screenshots:** Login, Dashboard, Smart Inbox, Processing, Review, Actions, Documents, AI Assistant. Brand: LIFE AI, navy sidebar, Secure workspace, Anita Rao.  
3. **Frontend engineering prompt:** Next.js App Router, Tailwind, Lucide, Context, Axios, TanStack Query, mock JSON, route list, component list, responsive breakpoints.  
4. **Team working agreement:** Learn → understand → design → build; do not silently generate a full backend; playbook gates over “code everything”.  
5. **Early experiment (later removed):** A FastAPI + Postgres + Redis + Celery + Docker Compose + GitHub Actions scaffold existed in `frontend/` + `backend/` and was deleted so the repo could follow the playbook layout (`apps/web`, later `services/api`).

## Existing implementation understanding (today)

- Only **`apps/web`** is a running application.
- Auth is **localStorage**, not OIDC.
- All lists come from **`src/data/*.json`**.
- Processing and chat are **UX simulations**.
- Axios is **prepared**, not used by mock services.
- Playbook backend/AI is **specified**, not coded.

## Current processes

- Product: gated phases; do not skip to OCR.
- Engineering: UI can proceed with mocks; services keep stable function names.
- Git: do not commit `.env` or secrets.
- Demo data: synthetic only (Anita / BESCOM / ABC Insurance).

## Dependencies to be aware of

- Node 22 + npm for UI.
- Future: Python 3.12, Docker, Postgres, Redis, S3, OCR, LLM, email.
- Windows-specific: file locks on `.venv`, Node heap, Celery `solo` pool if workers return.

## Important areas (risk)

- Private documents → threat model before storing real files (playbook Phase 1).
- `workspace_id` on every query.
- Prompt injection via PDFs.
- Cost of OCR/LLM per user.
- Confirmation UX is a **product** requirement, not polish.

## What “done” means for MVP

A new user completes: register → upload realistic document → system understands → user verifies → suggested action → confirm → reminder → dashboard → ask a question → **answer grounded in source**. No engineer SQL required.

---

# Part B — KT Out (knowledge shared with the team)

## Feature walkthrough (demo script)

1. Open http://localhost:3000 → login (`name@example.com` / any 6+ char password).  
2. Dashboard: three cards, upcoming actions, Open AI Assistant.  
3. Smart Inbox: drop zone, privacy banner.  
4. Processing: `/documents/processing?file=car-insurance-policy.pdf` → stepper → review.  
5. Review: insurance fields, Edit details, Confirm.  
6. Actions: Renew, reminder dropdown, Create reminder.  
7. Documents vault + search.  
8. Timeline dates.  
9. Assistant: seeded Q&A + Try asking fills the input.  
10. Settings: sign out.  
11. Resize to ~375px: Open menu.

## Architecture explanation (one paragraph)

The **eventual** system is a Next.js client and a Python FastAPI monolith with Postgres, Redis workers, and S3. The **current** system is only the client, with a service layer that will be swapped from JSON to HTTP without rewriting screens. AI features are drawn in Figma and stubbed so UX can be validated early.

## Development guidelines

1. Read `docs/` before adding a feature. If it is OCR/RAG/reminders, you are in the wrong phase unless Phase 3 is done.  
2. Put I/O in `services/api`. Put visuals in `components`. Put routes in `app`.  
3. Do not duplicate buttons/inputs; use `components/ui`.  
4. Do not put secrets in git.  
5. Do not log document text.  
6. Prefer changing JSON fixtures to demonstrate UI; do not fake a second backend in the browser.  
7. When FastAPI lands, add tests next to the domain logic, not only in UI.  
8. Record ADRs in [architecture.md](./architecture.md) when a major choice changes.

## Coding standards (frontend)

- TypeScript strict; shared types in `src/types`.  
- Client components (`"use client"`) for hooks, events, Query.  
- Query keys: `["documents"]`, `["actions"]`, `["attention"]`, `["extraction"]`, `["timeline"]`.  
- Tailwind for layout; navy `#0b1b33`, primary `blue-600`.  
- Loading, empty, and error states on data screens.  
- Accessible labels on inputs (`Input` uses `htmlFor`).  
- ESLint: no synchronous setState in `useEffect`.  
- Comments only where the why is non-obvious (timers, mock vs real).

## Coding standards (backend, when added)

- Type hints, Pydantic v2, SQLAlchemy 2.  
- Thin routes, domain in services.  
- Ruff + pytest.  
- Tenant filter in every query.  
- Idempotent jobs.

## Operational processes

- Local run: [setup-guide.md](./setup-guide.md).  
- Incidents (future): queue depth, worker crash, provider outage — see playbook Phase 9.  
- Checkpoint scripts for management vs technical (playbook end).  

## Troubleshooting knowledge

See [troubleshooting.md](./troubleshooting.md) and [known-issues.md](./known-issues.md). First questions: Are you on mock UI only? Is `ala-token` set? Are you expecting a real `/health` API?

---

# Part C — Development changes (changelog)

## 2026-09 — Foundation experiment (reverted)

Created then **removed**: Next.js `frontend/`, FastAPI `backend/`, Celery `worker/`, Docker Compose, Alembic users migration, GitHub Actions CI, `.env.example`. Reason: skipped playbook Phases 0–2 and used a different folder layout than `apps/` + `services/`.

Git history may still contain commit `55795f7` (“working monorepo foundation”) on `main` before the delete. The working tree after reset is the source of truth.

## 2026-09-09 — Frontend application

**Added**

- `apps/web` Next.js 16 App Router + Tailwind 4 + TypeScript  
- Routes: login, dashboard, documents (list/upload/processing/review), actions, assistant, timeline, settings  
- Components: layout, sidebar, cards, forms, upload, chat, ui primitives, providers  
- Services: auth, document, action, assistant, axios client  
- Mock data JSON  
- `output: "standalone"`  
- Dependencies: `@tanstack/react-query`, `axios`, `lucide-react`  
- Docs site in `docs/`  
- Root `.gitignore` for env, node, python  
- `LICENSE` (MIT) retained  

**API / database**

- None implemented.  
- Axios base URL env `NEXT_PUBLIC_API_URL`.  

**Configuration**

- `apps/web/.env.example`  
- `apps/web/next.config.ts` standalone  
- Port 3000 in npm `dev` script  

**Not added (on purpose)**

- FastAPI, Postgres, Redis, Terraform, Playwright, NextAuth  

---

# Part D — Folder structure (why it exists)

```text
docs/                          Team knowledge; not generated by Next
  README.md                    Index
  project-overview.md          Business
  architecture.md              System design + ADRs
  technology-stack.md          Tools and reasons
  setup-guide.md               Run locally
  features.md                  Screen-level behaviour
  workflows.md                 Sequences and data flow
  api-documentation.md         Mock contracts + planned HTTP
  database-design.md           Planned schema
  ai-architecture.md           OCR/RAG rules
  deployment-guide.md          Build/CI/prod intent
  troubleshooting.md           Debug
  known-issues.md              Log + limitations
  future-enhancements.md       Roadmap
  kt-notes.md                  This file

apps/web/                      Only runnable product today
```

When backend work starts, add `services/api`, `services/worker`, `python/`, `infrastructure/`, `tests/` as in the playbook — and update this documentation in the **same PR**.

---

# Part E — Definition of documentation done

A new developer can:

- Explain the core flow in one sentence.  
- Run the UI without asking which port.  
- Know that login is fake.  
- Know where to put a new screen vs a new API call.  
- Know not to start microservices or OCR this week.  

If that fails, update `docs/` in the same change that confused them.
