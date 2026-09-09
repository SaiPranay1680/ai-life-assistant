# Technology Stack

## What we use today (frontend)

| Technology | Version (package.json) | Role |
| --- | --- | --- |
| Next.js | 16.3.4 | App Router, routing, SSR/CSR mix, `standalone` output |
| React | 19.2.8 | UI |
| TypeScript | 5.x | Types |
| Tailwind CSS | 4.x | Styling (utility classes matching Figma) |
| TanStack Query | 5.90.x | Loading, caching, mutations |
| Axios | 1.12.x | HTTP client (interceptor attaches `ala-token`) |
| Lucide React | 0.544.x | Icons |
| ESLint + eslint-config-next | 9 / 16.3.4 | Lint |

Node **22+** is recommended (aligned with Next 16).

## What the playbook specifies next

| Technology | Role |
| --- | --- |
| Python 3.12+ | Backend language |
| FastAPI | HTTP API, OpenAPI |
| Pydantic v2 | Request/response schemas |
| SQLAlchemy 2 + Alembic | ORM and migrations |
| PostgreSQL 16 + pgvector | Data + embeddings |
| Redis | Queue / broker / cache |
| Celery (or equivalent) | Workers |
| S3-compatible storage | Files |
| OIDC provider | Real auth |
| GitHub Actions | CI |
| Docker | Local deps and deploys |
| Terraform | Infra as code (later) |
| Playwright | E2E (later) |
| Ruff, mypy/pyright | Python quality |
| pytest | Backend tests |

## Why these choices

### Next.js + React + TypeScript

- **Why:** App Router matches multi-page product (dashboard, vault, chat). TypeScript catches contract mistakes before the API exists.  
- **Alternatives:** Vite SPA (weaker SSR/routing conventions), Remix.  
- **Tradeoff:** Next is heavier than a Vite SPA; acceptable for a production SaaS UI.

### Tailwind CSS

- **Why:** Figma is utility-like (navy sidebar `#0b1b33`, blue `#2563eb`, green security badges). Fast to match screens without a separate CSS-in-JS runtime.  
- **Alternatives:** CSS modules, shadcn/ui (can be added later on top of Tailwind).  
- **Tradeoff:** Class-heavy JSX; enforce reuse via `components/ui`.

### TanStack Query + Axios

- **Why:** Query matches “get documents / get actions” server state. Axios instance is ready for `Authorization` headers.  
- **Alternatives:** fetch + SWR; Redux Toolkit Query.  
- **Tradeoff:** Overkill while all data is local JSON; pays off the day FastAPI is wired.

### React Context (not Redux)

- **Why:** Auth is a small global concern. Playbook/frontend prompt said prepare for Zustand/Redux later.  
- **Do not** put document lists in Context if Query already owns them.

### FastAPI (planned)

- **Why:** Python is required for OCR/NLP/workers; FastAPI gives typed APIs and OpenAPI.  
- **Alternatives:** Django Ninja, Node backend (would split AI in another language).  
- **Tradeoff:** Two runtimes (Node + Python) in the monorepo — accepted.

### PostgreSQL (planned)

- **Why:** Relational actions/documents/users; pgvector avoids extra vector infrastructure at MVP.  
- **Alternatives:** MongoDB (weaker relational integrity), separate Pinecone/Qdrant (more moving parts).

### Redis + workers (planned)

- **Why:** OCR/LLM must not block HTTP.  
- **Alternatives:** FastAPI BackgroundTasks (lost on process restart), SQS. Redis is enough for local and early production.

## Frontend design tokens (implemented)

| Token | Value | Use |
| --- | --- | --- |
| Navy | `#0b1b33` | Sidebar, assistant “Try asking” panel, dashboard AI card |
| Page background | `#f4f7fb` | Authenticated shell |
| Primary | Tailwind `blue-600` (`#2563eb`) | Buttons, user chat bubble |
| Success | emerald badges | Secure workspace, complete steps |
| Warning | orange | Renew / medium |
| Danger | rose | Due soon / high |

Font: **Inter** via `next/font/google`.

## Dependencies we intentionally did not add

- Redux / Zustand — not needed yet  
- UI kit (MUI, Chakra) — Figma is custom  
- Auth.js / NextAuth — would pretend we have OIDC; mock login is honest  
- i18n — English UI only for now  

## Limitations of the current stack

- Mock login is **not** security. Anyone who can open the browser can “sign in”.  
- Axios `apiClient` is unused by mock services (they import JSON). Wiring means replacing `wait()` + JSON with `apiClient.get/post`.  
- `NEXT_PUBLIC_*` variables are inlined at **build** time for Next.js.
