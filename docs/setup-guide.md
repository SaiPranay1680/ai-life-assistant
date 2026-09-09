# Setup Guide

## Required software

| Tool | Version | Why |
| --- | --- | --- |
| Git | 2.x | Clone and history |
| Node.js | 22.x recommended | Next.js 16 |
| npm | 10+ (comes with Node) | Install JS packages |
| A browser | Chrome/Edge/Firefox | Run the UI |

**Later (backend phase):** Python 3.12+, Docker Desktop (Postgres + Redis). Docker is **not** required to run the current frontend.

## Clone

```bash
git clone <repository-url> ai-life-assistant
cd ai-life-assistant
```

## Frontend install

```bash
cd apps/web
copy .env.example .env.local
# macOS/Linux: cp .env.example .env.local
npm install
```

### Environment variables

File: `apps/web/.env.local` (gitignored). Template: `apps/web/.env.example`.

| Variable | Example | Meaning |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | FastAPI base URL when the API exists |

Today, mock services **do not** call this URL. The Axios client still reads it so interceptors are ready.

Never commit `.env`, `.env.local`, or real secrets.

## Run locally

```bash
cd apps/web
npm run dev
```

- App: http://localhost:3000  
- Port is fixed in `package.json` (`next dev --port 3000`).

### Sign in (mock)

1. Open `/login` (or `/` which redirects).  
2. Email: any valid email (e.g. `anita@example.com`).  
3. Password: at least 6 characters.  
4. Session is stored in `localStorage` keys `ala-auth-user` and `ala-token`.

There is no password check against a database. Display name is always **Anita Rao** from `src/data/dashboard.json`.

### Other scripts

```bash
npm run lint
npm run typecheck
npm run build
npm start          # after build
```

If `npm install` or `create-next-app` fails with JavaScript heap out of memory on Windows, retry with:

```powershell
$env:NODE_OPTIONS='--max-old-space-size=8192'
npm install
```

## Database setup

**Not applicable yet.** No PostgreSQL in the current tree. When FastAPI is added:

1. Start Postgres (Docker Compose from the playbook).  
2. Set `DATABASE_URL`.  
3. Run Alembic `upgrade head`.  

See [database-design.md](./database-design.md) for the intended schema.

## Repository hygiene

Root `.gitignore` ignores:

- `.env`, `.env.local`, `.env.*.local`
- `node_modules/`, `.next/`
- Python `.venv/`, `__pycache__/`

Do not commit `apps/web/.next` or `node_modules`.

## IDE

Open the **repository root** in Cursor/VS Code so `@/` imports and docs stay consistent. Working directory for npm commands is `apps/web`.

## Team onboarding checklist

1. Read [docs/README.md](./README.md) and [project-overview.md](./project-overview.md).  
2. Run the frontend and click every sidebar item.  
3. Walk the upload → processing → review → actions path (`/documents/processing?file=demo.pdf` works without a real file).  
4. Read [kt-notes.md](./kt-notes.md) before changing architecture.
