# Known Issues, Limitations, and Issue Log

## Known limitations (product)

- No real authentication, authorization, or encryption of documents at rest.
- No persistence of uploads, edits, reminders, or chat beyond the browser session (except login keys).
- Assistant is a lookup table, not RAG.
- Extraction is a single insurance fixture.
- Actions page highlights one suggested action, not a full lifecycle manager.
- Settings checkboxes and name field do not persist.
- Delete account is a stub modal.
- No automated frontend unit/E2E tests in repo.
- No GitHub Actions workflow currently (removed in reset).
- No backend, database, Redis, or object storage.

## Technical debt

- Mock services mixed with a real Axios client that is unused.
- Hard-coded evidence copy on `ActionCard` (“car-insurance-policy.pdf • Page 1”).
- Greeting uses `firstName` from stored user but cards are always Anita’s fixture bills.
- Next.js may generate `AGENTS.md` / `CLAUDE.md` in `apps/web` on `next dev`; they are tool aids, not product docs — prefer `docs/`.
- Search input on documents vault lacks an accessible name in the snapshot (placeholder only).

## Issue log

### ISS-001 — create-next-app / npm heap out of memory (Windows)

- **Problem:** Scaffold or install crashed with “Committing semi space failed”.  
- **Root cause:** Default Node heap too small for this environment.  
- **Resolution:** Manual Next.js file scaffold; `NODE_OPTIONS=--max-old-space-size=8192` for `npm install`.  
- **Prevention:** Document the env var in [setup-guide.md](./setup-guide.md).

### ISS-002 — ESLint `react-hooks/set-state-in-effect`

- **Problem:** Lint failed on auth hydration and review form `setForm` in `useEffect`.  
- **Root cause:** React 19 ESLint flags synchronous setState in effects.  
- **Resolution:** Auth hydrate via `setTimeout(0)`; review form as child with initial `useState(data)`.  
- **Prevention:** Prefer derived state or keyed children over copying query data in effects.

### ISS-003 — Locked `.venv` when resetting the repo

- **Problem:** Could not delete `backend` while uvicorn/celery/python held DLLs.  
- **Root cause:** Processes still running after verification.  
- **Resolution:** Stop PIDs, then `rmdir`.  
- **Prevention:** Stop dev servers before deleting virtualenvs.

### ISS-004 — Health check / localhost vs IPv4 (historical backend)

- **Problem:** Next.js fetch to `localhost` failed or timed out when API bound to `127.0.0.1` only; sequential DB+Redis timeouts exceeded 3s.  
- **Resolution (then):** Bind `0.0.0.0`, parallel health checks, longer fetch timeout.  
- **Note:** Backend was later removed; re-apply when FastAPI returns.

### ISS-005 — First foundation vs playbook layout

- **Problem:** An early FastAPI/Docker tree (`frontend/`, `backend/`) did not match the playbook (`apps/web`, `services/api`) and skipped Phases 0–2.  
- **Resolution:** Deleted generated app folders; rebuilt UI under `apps/web`; documented playbook as source of truth.  
- **Prevention:** Phase exit gates; no feature code before architecture approval.

### ISS-006 — Browser MCP file upload denied

- **Problem:** Automated upload of `public/sample.png` blocked as outside workspace roots.  
- **Workaround:** Manual picker or processing URL with `?file=`.  
- **Prevention:** Keep sample files under the path the automation tool allows, or don’t rely on MCP for upload tests.

## Pending items

See [future-enhancements.md](./future-enhancements.md). Highest priority after docs: FastAPI foundation (Phase 3) with health, Postgres, Alembic, real auth adapter, worker ping.
