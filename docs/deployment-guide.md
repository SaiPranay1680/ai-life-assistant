# Deployment Guide

## What can be deployed today

The Next.js app in `apps/web`.

```bash
cd apps/web
npm ci
npm run lint
npm run typecheck
npm run build
npm start
```

`next.config.ts` sets `output: "standalone"` so a Docker image can copy `.next/standalone` and run `node server.js`.

No Dockerfile currently lives in the repo (removed in the foundation reset). Recreate under `infrastructure/docker/` per playbook when needed.

## Environments (playbook)

| Name | Purpose |
| --- | --- |
| Local | Developer laptop, mock data |
| DEV | Auto-deploy from `main` |
| QA | Test with synthetic documents |
| STAGING | Production-like; release tags |
| PRODUCTION | Manual approval |

Do not put production secrets in GitHub logs or git.

## Planned CI/CD

GitHub Actions (not present after reset):

```text
PR → lint → type-check → unit tests → security scan → build → images
main → DEV
tag → STAGING
approval → PRODUCTION
```

Include: caching, image naming, environment protection, migration strategy, rollback, SBOM/dependency scanning.

Frontend job today should at least: `npm ci`, `npm run lint`, `npm run typecheck`, `npm run build` in `apps/web`.

## Planned runtime (full stack)

- Next.js on a managed container or Node host
- FastAPI + workers on containers
- Managed PostgreSQL
- Managed Redis
- S3 bucket with lifecycle and encryption
- Secret store (not `.env` files on disk in prod)
- Alerts: API errors, queue depth, worker failures, DB health, AI cost

## Migrations

Run Alembic in the API deploy **before** switching traffic to a version that requires new columns. Prefer backward-compatible expands.

## Rollback

- Keep previous container image
- Database: expand/contract so rollback of app does not require immediate down-migration
- Feature flags for AI providers if a model regresses

## Go-live checklist (Phase 9 excerpt)

- IaC reviewed
- Secrets in a managed store
- Backup/restore tested
- Object storage deletion policy
- Incident contacts and runbooks
- Privacy policy / consent
- Rollback tested

Not started for this repository.

## Local “deployment” of the UI only

Share `npm run dev` on the LAN (`Network:` URL printed by Next). This is **not** production (mock auth).
