# AI Life Assistant — Documentation

This folder is the **single source of truth** for the project. A new developer should be able to understand purpose, architecture, current code, planned work, and how to run the app by reading these files.

**Product name:** AI Life Assistant (UI brand: **LIFE AI**)  
**Type:** Personal Action Intelligence Platform  
**Core flow:** Upload → Understand → Extract → Action → Confirm → Remind → Ask  
**Docs version:** 1.0 · September 2026

## How to read this

| If you need… | Start here |
| --- | --- |
| What we are building and for whom | [project-overview.md](./project-overview.md) |
| How the system is designed | [architecture.md](./architecture.md) |
| Why Next.js / FastAPI / Postgres / etc. | [technology-stack.md](./technology-stack.md) |
| Clone, install, run | [setup-guide.md](./setup-guide.md) |
| Screens and behaviour | [features.md](./features.md) |
| User and data journeys | [workflows.md](./workflows.md) |
| HTTP APIs (current + planned) | [api-documentation.md](./api-documentation.md) |
| Data model (planned) | [database-design.md](./database-design.md) |
| OCR, extraction, RAG (planned) | [ai-architecture.md](./ai-architecture.md) |
| Docker, CI, production | [deployment-guide.md](./deployment-guide.md) |
| Debug problems | [troubleshooting.md](./troubleshooting.md) |
| Bugs, debt, gaps | [known-issues.md](./known-issues.md) |
| Roadmap | [future-enhancements.md](./future-enhancements.md) |
| KT In / KT Out for the team | [kt-notes.md](./kt-notes.md) |
| Phase 1 decisions (complete) | [phase-1-decisions.md](./phase-1-decisions.md) |
| Do later — do not forget (OIDC, S3, Docker, OCR, ClamAV) | [deferred-work.md](./deferred-work.md) |

## Current reality vs target

| Layer | Status (2026-09-09) |
| --- | --- |
| Frontend (`apps/web`) | **Implemented** — Next.js UI with mock JSON and API-shaped services |
| Backend (FastAPI) | **Not in the working tree** — specified in the product playbook |
| PostgreSQL, Redis, workers | **Planned** |
| OCR / extraction / RAG | **Planned** — UI simulates processing and chat |
| Real authentication (OIDC) | **Planned** — UI uses mock localStorage login |
| Object storage (S3) | **Planned** |

Do not assume a running API on port 8000. `NEXT_PUBLIC_API_URL` is reserved for when the backend exists.

## Playbook phases

Work is gated. Do not skip phases.

0. Discovery & product definition  
1. Solution architecture & security  
2. UX/UI design  
3. Engineering foundation (API, DB, CI, auth)  
4. Document intelligence  
5. Action intelligence & reminders  
6. RAG & assistant  
7. End-to-end MVP  
8. Testing & security  
9. Production  
10. Post-MVP measurement  

Frontend UI (Phase 2 design + a UI slice of Phase 3) is what exists in git today.

## Repository root

```text
ai-life-assistant/
├── apps/web/          Next.js frontend
├── docs/              This documentation
├── LICENSE
├── README.md
└── .gitignore
```

Target layout from the execution playbook (not all folders exist yet):

```text
apps/web/
services/api/
services/worker/
python/                  document_intelligence, retrieval, actions, common
infrastructure/          terraform, docker
tests/
docs/
scripts/
```
