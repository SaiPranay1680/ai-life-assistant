# Future Enhancements and Roadmap

Follow playbook **depth before breadth**. Do not start OCR until Phase 3 exit criteria are met.

## Immediate (engineering foundation)

- FastAPI modular monolith under `services/api`
- Python worker under `services/worker`
- Docker Compose: Postgres + Redis
- Alembic users/workspaces
- Health/readiness
- Structured logging, correlation IDs
- Restore CI (lint, typecheck, pytest, compose config)
- Replace mock login with OIDC adapter (or a clearly temporary session API)

## Document intelligence

- Presigned upload, MIME/size validation, malware hook
- Status state machine
- PDF text extract + OCR fallback
- Classification + schema extraction with evidence
- Review/edit persisted to DB
- Gold evaluation set

## Action intelligence

- Deterministic rules engine
- Duplicate control
- Reminder scheduler, email, idempotency
- Audit trail
- Dashboard fed from real actions

## Assistant

- Chunking, embeddings, pgvector
- Permission-safe retrieval
- Citations, refusals, injection tests
- Cost telemetry

## Product (post-MVP, evidence-based)

Only if metrics support them:

- Family workspace
- Email/calendar intake
- Vehicle/home domain packs
- PWA / native
- B2B SSO

## Intentionally deferred

Native apps, bank connections, payment execution, medical advice, government filing, autonomous renewals, Kubernetes, microservices, custom foundation models, marketplace.

## Enhancement opportunities on current UI

- Persist settings in localStorage until API exists
- Accessible name on document search
- Wire Axios in services behind a `USE_MOCK` flag
- Playwright smoke: login → dashboard → processing URL → review
- Dark/light theme (Figma is light content + dark sidebar only)

## Technical debt to retire

- Duplicate hardcoded assistant seed vs `messages.json`
- Action evidence strings not from extraction fixture
- Remove unused `apiClient` or use it
