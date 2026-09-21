# API Documentation

## Current state

There is **no live backend**. The UI talks to TypeScript functions that mimic APIs.

Axios is configured in `apps/web/src/services/api/client.ts`:

- `baseURL`: `process.env.NEXT_PUBLIC_API_URL` or `http://localhost:8000`
- `timeout`: 15000 ms
- Request interceptor: `Authorization: Bearer <ala-token>` if present in `localStorage`

Mock functions do **not** use `apiClient`. They will when FastAPI is available.

---

## Frontend service contracts (implemented)

Replace the body of these functions with HTTP calls; keep signatures where possible.

### Auth — `auth.service.ts`

| Function | Behaviour now | Future HTTP |
| --- | --- | --- |
| `login(email, password)` | Validates format/length; stores user + `mock-session-token` | `POST /auth/login` or OIDC redirect |
| `logout()` | Clears `ala-auth-user`, `ala-token` | `POST /auth/logout` |
| `getStoredUser()` | Reads localStorage | Session cookie / `/auth/me` |

### Documents — `document.service.ts`

| Function | Now | Future |
| --- | --- | --- |
| `getDocuments()` | Returns `documents.json` | `GET /documents` |
| `uploadDocument(file)` | Validates type/size; returns `{ fileName }` | `POST /documents` or presign + complete |
| `getExtraction()` | Returns `extraction.json` | `GET /documents/{id}/extraction` |

Allowed upload types: PDF, JPEG, PNG. Max 20 MB.

### Actions — `action.service.ts`

| Function | Backend |
| --- | --- |
| `getActions()` | `GET /actions` |
| `confirmAction(id)` | `POST /actions/{id}/confirm` |
| `startAction(id)` | `POST /actions/{id}/start` |
| `completeAction(id)` | `POST /actions/{id}/complete` |
| `dismissAction(id)` | `POST /actions/{id}/dismiss` |
| `createReminder(actionId, reminder)` | `POST /actions/{id}/reminders` (confirms if still suggested) |

### Assistant — `assistant.service.ts`

| Function | Now | Future |
| --- | --- | --- |
| `sendMessage(question, history)` | Map lookup in `messages.json` | `POST /assistant/messages` |
| `getSuggestedQuestions()` | Sync list from JSON | `GET /assistant/suggestions` |

---

## Planned HTTP API (FastAPI)

These routes are **design intent**, not implemented. Names may change; keep OpenAPI as source of truth once generated.

### Health

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness |
| GET | `/health/ready` | DB + Redis (recommended) |

### Auth / users / workspace

OIDC-first in production. Until then, avoid inventing a custom password API if OIDC is imminent.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/me` | Current user + workspace |
| GET | `/workspaces/current` | Workspace settings |

### Documents

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/documents` | List (workspace scoped) |
| POST | `/documents/upload-url` | Presign |
| POST | `/documents` | Register uploaded object |
| GET | `/documents/{id}` | Detail |
| GET | `/documents/{id}/status` | Processing state machine |
| GET | `/documents/{id}/extraction` | Fields + evidence |
| PATCH | `/documents/{id}/extraction` | User corrections |

### Actions / reminders

Statuses: `suggested` → `confirmed` → `in_progress` → `completed` | `dismissed`.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/actions` | List (suggested, confirmed, in_progress, completed; dismissals stay hidden) |
| POST | `/actions/{id}/confirm` | `suggested` → `confirmed` (stores `confirmed_by`, `confirmed_at`) |
| POST | `/actions/{id}/start` | `confirmed` → `in_progress` |
| POST | `/actions/{id}/complete` | `confirmed` or `in_progress` → `completed` (stores `completed_at`) |
| POST | `/actions/{id}/dismiss` | Not needed (`suggested` / `confirmed` / `in_progress` → `dismissed`) |
| POST | `/actions/{id}/reminders` | Schedule reminder; also confirms if still `suggested` |

### Assistant

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/assistant/query` | Question; returns answer + citations |

### Privacy / audit

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/privacy/export` | Data export |
| POST | `/privacy/delete` | Account deletion |
| GET | `/audit` | Workspace audit (admin/self) |

## Conventions (when implementing)

- JSON only; Pydantic v2 models.
- Errors: `{ "detail": "..." }` or structured error model with code.
- Correlation / request IDs on every response (playbook).
- All list/get queries filter `workspace_id` from the auth context, never from an unchecked client field alone.
- No business logic in route handlers.

## Breaking change policy

UI service names are the compatibility layer. Prefer adapting `services/api/*.ts` over rewriting every page when the backend path names change.
